"""
LOSK virtual keyboard via Linux uinput.
Made by ZeshMC

If uinput is not usable (Codespaces, missing permissions, evdev not installed)
the class still constructs fine and every send becomes a harmless no-op, so the
GTK window always opens.
"""

import threading

import layouts

try:
    from evdev import UInput, ecodes
    _IMPORT_ERROR = None
except Exception as exc:
    UInput = None
    ecodes = None
    _IMPORT_ERROR = str(exc)


class VirtualKeyboard:
    def __init__(self):
        self.available = False
        self.reason = ""
        self._device = None
        self._lock = threading.Lock()

        if ecodes is None:
            self.reason = "python3-evdev not available (%s)" % _IMPORT_ERROR
            return

        try:
            codes = []
            for name in layouts.all_key_names():
                code = getattr(ecodes, name, None)
                if code is not None:
                    codes.append(code)
            self._device = UInput(
                {ecodes.EV_KEY: sorted(set(codes))},
                name="LOSK Virtual Keyboard",
                version=1,
            )
            self.available = True
            self.reason = "connected"
        except PermissionError:
            self.reason = "no permission for /dev/uinput"
        except FileNotFoundError:
            self.reason = "/dev/uinput not present"
        except Exception as exc:
            self.reason = str(exc)

    def _code(self, name):
        if ecodes is None:
            return None
        return getattr(ecodes, name, None)

    def press(self, name):
        return self._write(name, 1)

    def release(self, name):
        return self._write(name, 0)

    def _write(self, name, value):
        if not self.available:
            return False
        code = self._code(name)
        if code is None:
            return False
        with self._lock:
            self._device.write(ecodes.EV_KEY, code, value)
            self._device.syn()
        return True

    def tap(self, name, modifiers=()):
        """Press and release one key, with any modifiers held around it."""
        if not self.available:
            return False
        code = self._code(name)
        if code is None:
            return False
        mod_codes = []
        for mod in modifiers:
            mc = self._code(mod)
            if mc is not None:
                mod_codes.append(mc)
        with self._lock:
            for mc in mod_codes:
                self._device.write(ecodes.EV_KEY, mc, 1)
            self._device.write(ecodes.EV_KEY, code, 1)
            self._device.write(ecodes.EV_KEY, code, 0)
            for mc in reversed(mod_codes):
                self._device.write(ecodes.EV_KEY, mc, 0)
            self._device.syn()
        return True

    def close(self):
        with self._lock:
            if self._device is not None:
                try:
                    self._device.close()
                except Exception:
                    pass
            self._device = None
            self.available = False
