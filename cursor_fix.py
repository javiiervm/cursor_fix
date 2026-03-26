import AppKit
import Quartz
import objc
import signal
import ApplicationServices
from Foundation import NSTimer, NSMakePoint, NSMakeRect, NSSize

SIZE = 12
HALF_SIZE = SIZE / 2

# --- 1. APP AND WINDOW CONFIGURATION ---
app = AppKit.NSApplication.sharedApplication()
app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)

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
win.setLevel_(AppKit.NSScreenSaverWindowLevel)
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
    AppKit.NSCursor.pop()
    app.terminate_(None)

signal.signal(signal.SIGINT, exit_app)

# --- 3. ADVANCED TICKER LOGIC ---
class Ticker(AppKit.NSObject):
    def init(self):
        self = objc.super(Ticker, self).init()
        self.frame_count = 0
        self.system_wide = ApplicationServices.AXUIElementCreateSystemWide()
        return self

    def tick_(self, timer):
        # Move the cursor window
        loc = AppKit.NSEvent.mouseLocation()
        win.setFrameOrigin_(NSMakePoint(loc.x - HALF_SIZE, loc.y - HALF_SIZE))

        # Check the element under the cursor 1 out of every 10 frames
        self.frame_count += 1
        if self.frame_count % 10 == 0:
            self.check_element_under_mouse()

    def check_element_under_mouse(self):
        cg_event = Quartz.CGEventCreate(None)
        cg_loc = Quartz.CGEventGetLocation(cg_event)
        is_interactive = False

        # --- A. CHECK BUTTONS AND TEXT (Accessibility) ---
        err, element = ApplicationServices.AXUIElementCopyElementAtPosition(
            self.system_wide, cg_loc.x, cg_loc.y, None
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
                    is_interactive = True

        # --- B. CHECK WINDOW BORDERS (CoreGraphics Geometry) ---
        if not is_interactive:
            MARGIN = 6 # Invisible border thickness in pixels
            
            # Get windows ordered from front to back
            window_list = Quartz.CGWindowListCopyWindowInfo(
                Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
                Quartz.kCGNullWindowID
            )
            
            for window in window_list:
                # Filter only normal windows (usually Layer 0)
                if window.get('kCGWindowLayer', 0) != 0:
                    continue
                    
                bounds = window.get('kCGWindowBounds')
                if not bounds:
                    continue
                    
                x = bounds.get('X', 0)
                y = bounds.get('Y', 0)
                w = bounds.get('Width', 0)
                h = bounds.get('Height', 0)
                
                # Ignore very small or invisible windows
                if w < 50 or h < 50 or window.get('kCGWindowAlpha', 1.0) == 0.0:
                    continue
                
                # Geometry: check if we are in a "ring" around the window
                in_total_area = (x - MARGIN) <= cg_loc.x <= (x + w + MARGIN) and \
                                (y - MARGIN) <= cg_loc.y <= (y + h + MARGIN)
                                
                in_inner_area = (x + MARGIN) < cg_loc.x < (x + w - MARGIN) and \
                                (y + MARGIN) < cg_loc.y < (y + h - MARGIN)
                
                if in_total_area:
                    if in_inner_area:
                        # The mouse is inside a front window.
                        # Stop searching to avoid detecting borders of hidden windows underneath.
                        break
                    else:
                        # It is in the window area, but NOT inside: It's on the border!
                        is_interactive = True
                        break

        # --- C. APPLY COLORS INSTANTLY ---
        Quartz.CATransaction.begin()
        Quartz.CATransaction.setDisableActions_(True)
        if is_interactive:
            gradient.setColors_([white, dark_blue])
        else:
            gradient.setColors_([white, cyan])
        Quartz.CATransaction.commit()

ticker = Ticker.alloc().init()
NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
    1.0/120.0, ticker, 'tick:', None, True)

print("Active. Press Ctrl+C to exit.")
app.run()
AppKit.NSCursor.pop()