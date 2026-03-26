import AppKit
import Quartz
import objc
import signal
import ApplicationServices
import threading
import time
from Foundation import NSTimer, NSMakePoint, NSMakeRect, NSSize

SIZE = 12
HALF_SIZE = SIZE / 2

# --- GLOBAL STATE FOR THREAD COMMUNICATION ---
app_running = True
is_interactive_global = False
last_interactive_global = False

# --- 1. APP AND WINDOW CONFIGURATION ---
app = AppKit.NSApplication.sharedApplication()
app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)

# Prevent App Nap and request maximum responsiveness
process_info = AppKit.NSProcessInfo.processInfo()
activity_options = (
    AppKit.NSActivityUserInitiated | 
    AppKit.NSActivityLatencyCritical
)
activity_reason = "Critical UI element (Hardware Cursor Replacement)"
process_info.beginActivityWithOptions_reason_(activity_options, activity_reason)

img = AppKit.NSImage.alloc().initWithSize_(NSSize(1, 1))
img.lockFocus()
AppKit.NSColor.clearColor().set()
AppKit.NSRectFill(NSMakeRect(0, 0, 1, 1))
img.unlockFocus()
invisible_cursor = AppKit.NSCursor.alloc().initWithImage_hotSpot_(img, NSMakePoint(0, 0))
invisible_cursor.set()
invisible_cursor.push()

win = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
    NSMakeRect(0, 0, SIZE, SIZE),
    AppKit.NSWindowStyleMaskBorderless,
    AppKit.NSBackingStoreBuffered,
    False)
win.setBackgroundColor_(AppKit.NSColor.clearColor())
win.setOpaque_(False)
win.setIgnoresMouseEvents_(True)
# Elevate window level to cursor level so it stays on top of system dialogs
win.setLevel_(Quartz.CGWindowLevelForKey(Quartz.kCGCursorWindowLevelKey))
win.setCollectionBehavior_(
    AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces |
    AppKit.NSWindowCollectionBehaviorStationary |
    AppKit.NSWindowCollectionBehaviorIgnoresCycle)
win.setHidesOnDeactivate_(False)

# --- 2. COLORS AND VIEW CONFIGURATION ---
view = win.contentView()
view.setWantsLayer_(True)

CAGradientLayer = objc.lookUpClass('CAGradientLayer')
gradient = CAGradientLayer.layer()
gradient.setFrame_(NSMakeRect(0, 0, SIZE, SIZE))
gradient.setCornerRadius_(HALF_SIZE)

white = AppKit.NSColor.whiteColor().CGColor()
cyan = AppKit.NSColor.colorWithRed_green_blue_alpha_(0.1, 0.95, 1.0, 1.0).CGColor()
dark_blue = AppKit.NSColor.colorWithRed_green_blue_alpha_(0.1, 0.2, 0.8, 1.0).CGColor()

gradient.setColors_([white, cyan])
gradient.setStartPoint_((0.0, 1.0))
gradient.setEndPoint_((1.0, 0.0))
view.layer().addSublayer_(gradient)

win.orderFrontRegardless()

def exit_app(signum, frame):
    global app_running
    app_running = False
    AppKit.NSCursor.pop()
    app.terminate_(None)

signal.signal(signal.SIGINT, exit_app)

# --- 3. BACKGROUND THREAD (THE DETECTIVE) ---
def hover_logic_thread():
    global is_interactive_global
    system_wide = ApplicationServices.AXUIElementCreateSystemWide()
    
    while app_running:
        # NSAutoreleasePool prevents memory leaks in background threads in PyObjC
        pool = AppKit.NSAutoreleasePool.alloc().init()
        try:
            cg_event = Quartz.CGEventCreate(None)
            cg_loc = Quartz.CGEventGetLocation(cg_event)
            is_interactive_local = False

            # --- A. CHECK BUTTONS AND TEXT (Accessibility) ---
            err, element = ApplicationServices.AXUIElementCopyElementAtPosition(
                system_wide, cg_loc.x, cg_loc.y, None
            )

            if err == 0 and element:
                err, role = ApplicationServices.AXUIElementCopyAttributeValue(
                    element, 'AXRole', None
                )
                if err == 0:
                    interactive_roles = [
                        'AXButton', 'AXLink', 'AXPopUpButton', 'AXSlider',
                        'AXMenuItem', 'AXSplitGroup', 'AXTextField', 'AXTextArea',
                        'AXCheckBox', 'AXRadioButton', 'AXComboBox'
                    ]
                    if role in interactive_roles:
                        is_interactive_local = True

            # --- B. CHECK WINDOW BORDERS (CoreGraphics Geometry) ---
            if not is_interactive_local:
                MARGIN = 6
                window_list = Quartz.CGWindowListCopyWindowInfo(
                    Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
                    Quartz.kCGNullWindowID
                )
                
                if window_list:
                    for window in window_list:
                        if window.get('kCGWindowLayer', 0) != 0:
                            continue
                            
                        bounds = window.get('kCGWindowBounds')
                        if not bounds:
                            continue
                            
                        x = bounds.get('X', 0)
                        y = bounds.get('Y', 0)
                        w = bounds.get('Width', 0)
                        h = bounds.get('Height', 0)
                        
                        if w < 50 or h < 50 or window.get('kCGWindowAlpha', 1.0) == 0.0:
                            continue
                        
                        in_total_area = (x - MARGIN) <= cg_loc.x <= (x + w + MARGIN) and \
                                        (y - MARGIN) <= cg_loc.y <= (y + h + MARGIN)
                                        
                        in_inner_area = (x + MARGIN) < cg_loc.x < (x + w - MARGIN) and \
                                        (y + MARGIN) < cg_loc.y < (y + h - MARGIN)
                        
                        if in_total_area:
                            if in_inner_area:
                                break
                            else:
                                is_interactive_local = True
                                break
            
            # Update global state
            is_interactive_global = is_interactive_local
            
        finally:
            # Clean up memory for this loop iteration
            del pool
            
        # Run this check 20 times per second (0.05s). Fast enough for UI, light on CPU.
        time.sleep(0.05)

# Start the background thread
logic_thread = threading.Thread(target=hover_logic_thread)
logic_thread.daemon = True # Ensures the thread dies when the main app closes
logic_thread.start()

# --- 4. MAIN THREAD (THE RENDERER) ---
class Ticker(AppKit.NSObject):
    def tick_(self, timer):
        # 1. Update Position INSTANTLY (Never blocked)
        loc = AppKit.NSEvent.mouseLocation()
        win.setFrameOrigin_(NSMakePoint(loc.x - HALF_SIZE, loc.y - HALF_SIZE))

        # 2. Update Color ONLY if the background thread changed the state
        global is_interactive_global, last_interactive_global
        if is_interactive_global != last_interactive_global:
            Quartz.CATransaction.begin()
            Quartz.CATransaction.setDisableActions_(True)
            if is_interactive_global:
                gradient.setColors_([white, dark_blue])
            else:
                gradient.setColors_([white, cyan])
            Quartz.CATransaction.commit()
            last_interactive_global = is_interactive_global

ticker = Ticker.alloc().init()
# Run rendering at 120 FPS
NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
    1.0/120.0, ticker, 'tick:', None, True)

print("Active. Press Ctrl+C to exit.")
app.run()
AppKit.NSCursor.pop()