import AppKit
import Quartz
import objc
import signal
from Foundation import NSTimer, NSMakePoint, NSMakeRect, NSSize

TAM = 12
MITAD = TAM / 2

app = AppKit.NSApplication.sharedApplication()
app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)

img = AppKit.NSImage.alloc().initWithSize_(NSSize(1, 1))
img.lockFocus()
AppKit.NSColor.clearColor().set()
AppKit.NSRectFill(NSMakeRect(0, 0, 1, 1))
img.unlockFocus()
cursor_invisible = AppKit.NSCursor.alloc().initWithImage_hotSpot_(img, NSMakePoint(0, 0))
cursor_invisible.set()
cursor_invisible.push()

win = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
    NSMakeRect(0, 0, TAM, TAM),
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

view = win.contentView()
view.setWantsLayer_(True)

CAGradientLayer = objc.lookUpClass('CAGradientLayer')
gradient = CAGradientLayer.layer()
gradient.setFrame_(NSMakeRect(0, 0, TAM, TAM))
gradient.setCornerRadius_(MITAD)
blanco = AppKit.NSColor.whiteColor().CGColor()
cian = AppKit.NSColor.colorWithRed_green_blue_alpha_(0.1, 0.95, 1.0, 1.0).CGColor()
gradient.setColors_([blanco, cian])
gradient.setStartPoint_((0.0, 1.0))
gradient.setEndPoint_((1.0, 0.0))
view.layer().addSublayer_(gradient)

win.orderFrontRegardless()

def salir(signum, frame):
    AppKit.NSCursor.pop()
    app.terminate_(None)

signal.signal(signal.SIGINT, salir)

class Ticker(AppKit.NSObject):
    def tick_(self, timer):
        loc = AppKit.NSEvent.mouseLocation()
        win.setFrameOrigin_(NSMakePoint(loc.x - MITAD, loc.y - MITAD))

ticker = Ticker.alloc().init()
NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
    1.0/120.0, ticker, 'tick:', None, True)

print("Activo. Ctrl+C para salir.")
app.run()
AppKit.NSCursor.pop()
