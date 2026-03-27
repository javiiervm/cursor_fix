import AppKit
import Quartz
import objc
import signal
import ApplicationServices
import threading
import time
import os
from Foundation import NSTimer, NSMakePoint, NSMakeRect, NSSize

# --- CURSOR CONFIGURATION ---
CURSOR_SIZE = 32 

# Define states, filenames, and their precise click points (Hotspots) from Top-Left.
CURSORS = {
    'ARROW':  {'file': 'default.png',    'hotspot': (10, 10)},
    'HAND':   {'file': 'hand.png',       'hotspot': (12, 10)}, 
    'CELL':   {'file': 'cell.png',       'hotspot': (16, 16)},
    'TEXT':   {'file': 'textcursor.png', 'hotspot': (16, 16)}
}

# --- GLOBAL STATE ---
app_running = True
current_cursor_state = 'ARROW'
last_cursor_state = None

current_directory = os.path.dirname(os.path.abspath(__file__))

# --- LOAD IMAGES ---
images = {}
for state, data in CURSORS.items():
    image_path = os.path.join(current_directory, data['file'])
    img = AppKit.NSImage.alloc().initWithContentsOfFile_(image_path)
    if img:
        images[state] = img
    else:
        print(f"⚠️ Warning: Could not find {data['file']} in {current_directory}")
        fallback = AppKit.NSImage.alloc().initWithSize_(NSSize(CURSOR_SIZE, CURSOR_SIZE))
        images[state] = fallback

# --- 1. APP AND WINDOW CONFIGURATION ---
app = AppKit.NSApplication.sharedApplication()
app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)

# Anti-lag fix: Keep reference to activity token
process_info = AppKit.NSProcessInfo.processInfo()
activity_token = process_info.beginActivityWithOptions_reason_(
    AppKit.NSActivityUserInitiated | AppKit.NSActivityLatencyCritical, 
    "Critical UI element (Hardware Cursor Replacement)"
)

# Hide hardware cursor
empty_img = AppKit.NSImage.alloc().initWithSize_(NSSize(1, 1))
invisible_cursor = AppKit.NSCursor.alloc().initWithImage_hotSpot_(empty_img, NSMakePoint(0, 0))
invisible_cursor.set()
invisible_cursor.push()

# Create window sized to our PNGs
win = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
    NSMakeRect(0, 0, CURSOR_SIZE, CURSOR_SIZE),
    AppKit.NSWindowStyleMaskBorderless,
    AppKit.NSBackingStoreBuffered,
    False)
win.setBackgroundColor_(AppKit.NSColor.clearColor())
win.setOpaque_(False)
win.setIgnoresMouseEvents_(True)
win.setLevel_(Quartz.CGWindowLevelForKey(Quartz.kCGCursorWindowLevelKey))
win.setCollectionBehavior_(
    AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces |
    AppKit.NSWindowCollectionBehaviorStationary |
    AppKit.NSWindowCollectionBehaviorIgnoresCycle)
win.setHidesOnDeactivate_(False)

# --- 2. RENDER LAYER ---
view = win.contentView()
view.setWantsLayer_(True)
layer = view.layer()

win.orderFrontRegardless()

def exit_app(signum, frame):
    global app_running
    app_running = False
    AppKit.NSCursor.pop()
    app.terminate_(None)

signal.signal(signal.SIGINT, exit_app)

# --- 3. BACKGROUND THREAD (THE DETECTIVE) ---
def hover_logic_thread():
    global current_cursor_state
    system_wide = ApplicationServices.AXUIElementCreateSystemWide()
    
    while app_running:
        pool = AppKit.NSAutoreleasePool.alloc().init()
        try:
            cg_event = Quartz.CGEventCreate(None)
            cg_loc = Quartz.CGEventGetLocation(cg_event)
            detected_state = 'ARROW'

            # A. CHECK FOR ACCESSIBILITY ELEMENTS
            err, element = ApplicationServices.AXUIElementCopyElementAtPosition(
                system_wide, cg_loc.x, cg_loc.y, None
            )

            is_special_state = False
            
            if err == 0 and element:
                err, role = ApplicationServices.AXUIElementCopyAttributeValue(
                    element, 'AXRole', None
                )
                if err == 0:
                    hand_roles = [
                        'AXButton', 'AXLink', 'AXPopUpButton', 
                        'AXMenuItem', 'AXCheckBox', 'AXRadioButton'
                    ]
                    
                    text_roles = [
                        'AXTextField', 'AXTextArea'
                    ]
                    
                    cell_roles = [
                        'AXSplitGroup', 'AXSlider', 'AXComboBox', 'AXValueIndicator'
                    ]
                    
                    if role in hand_roles:
                        detected_state = 'HAND'
                        is_special_state = True
                    elif role in text_roles:
                        detected_state = 'TEXT'
                        is_special_state = True
                    elif role in cell_roles:
                        detected_state = 'CELL'
                        is_special_state = True

            # B. CHECK FOR WINDOW BORDERS
            if not is_special_state:
                MARGIN = 6
                window_list = Quartz.CGWindowListCopyWindowInfo(
                    Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
                    Quartz.kCGNullWindowID
                )
                
                if window_list:
                    for window in window_list:
                        if window.get('kCGWindowLayer', 0) != 0: continue
                        bounds = window.get('kCGWindowBounds')
                        if not bounds: continue
                            
                        x, y = bounds.get('X', 0), bounds.get('Y', 0)
                        w, h = bounds.get('Width', 0), bounds.get('Height', 0)
                        
                        if w < 50 or h < 50 or window.get('kCGWindowAlpha', 1.0) == 0.0: continue
                        
                        in_total_area = (x - MARGIN) <= cg_loc.x <= (x + w + MARGIN) and \
                                        (y - MARGIN) <= cg_loc.y <= (y + h + MARGIN)
                                        
                        in_inner_area = (x + MARGIN) < cg_loc.x < (x + w - MARGIN) and \
                                        (y + MARGIN) < cg_loc.y < (y + h - MARGIN)
                        
                        if in_total_area:
                            if in_inner_area:
                                break 
                            else:
                                detected_state = 'CELL'
                                break
            
            current_cursor_state = detected_state
            
        finally:
            del pool
            
        time.sleep(0.05)

logic_thread = threading.Thread(target=hover_logic_thread)
logic_thread.daemon = True
logic_thread.start()

# --- 4. MAIN THREAD (THE RENDERER) ---
class Ticker(AppKit.NSObject):
    def tick_(self, timer):
        global current_cursor_state, last_cursor_state
        
        # 1. SWAP IMAGE IF STATE CHANGED
        if current_cursor_state != last_cursor_state:
            Quartz.CATransaction.begin()
            Quartz.CATransaction.setDisableActions_(True)
            layer.setContents_(images[current_cursor_state])
            Quartz.CATransaction.commit()
            last_cursor_state = current_cursor_state

        # 2. CALCULATE PRECISE POSITION BASED ON HOTSPOT
        loc = AppKit.NSEvent.mouseLocation()
        hx, hy = CURSORS[current_cursor_state]['hotspot']
        
        win_x = loc.x - hx
        win_y = loc.y - CURSOR_SIZE + hy
        
        win.setFrameOrigin_(NSMakePoint(win_x, win_y))

ticker = Ticker.alloc().init()

# Anti-lag fix: Bind to CommonModes
timer = NSTimer.timerWithTimeInterval_target_selector_userInfo_repeats_(
    1.0/120.0, ticker, 'tick:', None, True)
AppKit.NSRunLoop.currentRunLoop().addTimer_forMode_(timer, AppKit.NSRunLoopCommonModes)

print("Software Cursor Active. Press Ctrl+C to exit.")
app.run()

del activity_token
AppKit.NSCursor.pop()