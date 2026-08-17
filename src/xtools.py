"""
LOSK X11 helpers.
Made by ZeshMC

Two jobs, both about speed:

 1. Tell the window manager that LOSK must never take keyboard focus. When
    that works, keys always land in your real app and no focus juggling is
    needed at all. This is how Onboard and other on-screen keyboards do it.

 2. Read and set the active window without spawning xdotool. A subprocess
    costs 20 to 30 ms; these calls cost well under a millisecond.

If python3-xlib is missing, or the session is Wayland, available stays False
and ui.py falls back to the old xdotool path.
"""

import os

try:
    from Xlib import X, Xutil, display, protocol
    _IMPORT_ERROR = None
except Exception as exc:
    X = None
    Xutil = None
    display = None
    protocol = None
    _IMPORT_ERROR = str(exc)


class XTools:
    def __init__(self):
        self.available = False
        self.reason = ""
        self._display = None
        self._root = None
        self._net_active = None

        if display is None:
            self.reason = "python3-xlib missing (%s)" % _IMPORT_ERROR
            return
        if os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland":
            self.reason = "wayland session"
            return

        try:
            self._display = display.Display()
            self._root = self._display.screen().root
            self._net_active = self._display.intern_atom("_NET_ACTIVE_WINDOW")
            self.available = True
            self.reason = "ready"
        except Exception as exc:
            self.reason = "no X display (%s)" % exc

    def _window(self, xid):
        return self._display.create_resource_object("window", xid)

    def set_never_focus(self, xid):
        """WM_HINTS input=False asks the window manager not to hand this window
        the keyboard. Clicks still work; only focus is refused."""
        if not self.available or not xid:
            return False
        try:
            win = self._window(xid)
            win.set_wm_hints(flags=Xutil.InputHint, input=0)
            self._display.flush()
            return True
        except Exception as exc:
            self.reason = "never-focus failed (%s)" % exc
            return False

    def active_window(self):
        """Which window currently has focus, as an integer id."""
        if not self.available:
            return None
        try:
            prop = self._root.get_full_property(self._net_active, X.AnyPropertyType)
            if prop and prop.value:
                return int(prop.value[0])
        except Exception:
            pass
        return None

    def activate(self, xid):
        """Give focus back to a window. Only needed as a fallback when the
        never-focus hint was refused by the window manager."""
        if not self.available or not xid:
            return False
        try:
            win = self._window(xid)
            event = protocol.event.ClientMessage(
                window=win,
                client_type=self._net_active,
                data=(32, [2, X.CurrentTime, 0, 0, 0]),
            )
            mask = X.SubstructureRedirectMask | X.SubstructureNotifyMask
            self._root.send_event(event, event_mask=mask)
            self._display.flush()
            return True
        except Exception:
            return False

    def close(self):
        try:
            if self._display is not None:
                self._display.close()
        except Exception:
            pass
        self._display = None
        self.available = False
