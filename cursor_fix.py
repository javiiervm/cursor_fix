import AppKit
import Quartz
from Foundation import NSTimer, NSMakePoint, NSMakeRect
import signal

TAM = 10
MITAD = TAM / 2

app = AppKit.NSApplication.sharedApplication()
app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)

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
layer = view.layer()
layer.setCornerRadius_(MITAD)
layer.setBackgroundColor_(AppKit.NSColor.whiteColor().CGColor())

win.orderFrontRegardless()

Quartz.CGDisplayHideCursor(Quartz.CGMainDisplayID())
AppKit.NSCursor.hide()

def salir(signum, frame):
    AppKit.NSCursor.unhide()
    Quartz.CGDisplayShowCursor(Quartz.CGMainDisplayID())
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
AppKit.NSCursor.unhide()
Quartz.CGDisplayShowCursor(Quartz.CGMainDisplayID())
