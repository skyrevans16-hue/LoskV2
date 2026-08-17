"""
LOSK GTK 4 window.
Made by ZeshMC

Layout: the whole keyboard is one homogeneous Gtk.Grid, which is what makes
keys grow and shrink with the window. One key unit = 4 grid columns, so a
2.25 unit Shift is 9 columns.

Speed: the old build spawned xdotool on every keypress to hand focus back,
costing 20 to 30 ms per key. Now LOSK asks the window manager never to give
it keyboard focus in the first place (WM_HINTS input=False), so there is
nothing to hand back and typing costs almost nothing. xdotool is only used
as a fallback when python3-xlib is missing or the hint is refused.

Repeat: press and hold a key and it repeats, like a real keyboard.
"""

import glob
import os
import shutil
import subprocess

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, GLib, Pango

try:
    gi.require_version("GdkX11", "4.0")
    from gi.repository import GdkX11
except Exception:
    GdkX11 = None

from layouts import (
    FUNCTION_ROW,
    ROWS,
    NAV_GRID,
    ARROW_GRID,
    NUMPAD_GRID,
    MODIFIERS,
    SHIFT_KEYS,
    CHAR_TO_KEY,
    LETTER_KEYS,
)
from keyboard import VirtualKeyboard
from suggestions import SuggestionEngine

try:
    from xtools import XTools
except Exception:
    XTools = None

try:
    from voice import VoiceInput
except Exception:
    VoiceInput = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CPU = 4
MAIN_COLS = 15 * CPU
NAV_COLS = 3 * CPU
PAD_COLS = 4 * CPU
CLUSTER_GAP = 3
NAV_START = MAIN_COLS + CLUSTER_GAP
PAD_START = NAV_START + NAV_COLS + CLUSTER_GAP

# Windows OSK proportions: wide and short. Chosen values, not measured.
DEFAULT_W, DEFAULT_H = 1000, 330
MIN_W, MIN_H = 780, 260
SIZE_PRESETS = (("S", 800, 270), ("M", 1000, 330), ("L", 1320, 440))

# Hold-to-repeat, matching typical desktop defaults.
REPEAT_DELAY_MS = 400
REPEAT_RATE_MS = 45

# Keys that must never auto-repeat.
NO_REPEAT = set(MODIFIERS) | {"KEY_CAPSLOCK", "KEY_NUMLOCK", "KEY_SCROLLLOCK"}

BASE_WIDTH = 1000
BASE_FONT = 13

STATIC_CSS = b"""
window { background-color: #1b202b; }
.toolbar-title { font-size: 15px; font-weight: bold; color: #eef2f8; }
.toolbar-sub { font-size: 10px; color: #8d9ab2; }
.status { font-size: 10px; color: #8d9ab2; }
.key {
    background-image: none;
    background-color: #2b3342;
    color: #eef2f8;
    border: 1px solid #3c4759;
    border-radius: 5px;
    padding: 0;
    margin: 0;
    min-width: 0;
    min-height: 0;
    box-shadow: none;
}
.key:hover { background-color: #384254; }
.key:active { background-color: #4d81d8; }
.key-mod { background-color: #333c4e; }
.key-latched { background-color: #4d81d8; border-color: #6d9bea; }
.key-locked { background-color: #c9762f; border-color: #e0913f; }
.suggest {
    background-image: none;
    background-color: #232b38;
    color: #cfe0ff;
    border: 1px solid #384254;
    border-radius: 5px;
    padding: 2px 6px;
    box-shadow: none;
}
.suggest:hover { background-color: #33425c; }
.suggest:disabled { color: #5a6478; background-color: #1f2530; }
.tool {
    background-image: none;
    background-color: #2b3342;
    color: #eef2f8;
    border: 1px solid #3c4759;
    border-radius: 5px;
    font-size: 11px;
    padding: 3px 9px;
    box-shadow: none;
}
.tool:hover { background-color: #384254; }
.tool-on { background-color: #4d81d8; border-color: #6d9bea; }
.tool-rec { background-color: #c0392b; border-color: #e05c4b; }
"""


def find_logo():
    packaged = "/usr/share/icons/hicolor/512x512/apps/losk.png"
    if os.path.exists(packaged):
        return packaged
    local_dir = os.path.join(BASE_DIR, "..", "assets", "icons")
    matches = sorted(glob.glob(os.path.join(local_dir, "*.png")))
    return matches[0] if matches else None


class LoskWindow(Gtk.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("LOSK")

        self.kb = VirtualKeyboard()
        self.words = SuggestionEngine()
        self.xt = XTools() if XTools else None
        self.voice = VoiceInput() if VoiceInput else None

        self._keys = []
        self._labels = []
        self._mod_buttons = {}
        self._latched = set()
        self._locked = set()
        self._caps = False
        self._word = ""
        self._suggestions = []
        self._font_size = 0

        self._repeat_source = None
        self._repeat_key = None

        self._wmctrl = shutil.which("wmctrl")
        self._xdotool = shutil.which("xdotool")
        self._own_id = None
        self._last_window = None
        self._pinned = True
        self._never_focus = False

        self._load_css()
        self._build()

        self.set_default_size(DEFAULT_W, DEFAULT_H)
        self.set_size_request(MIN_W, MIN_H)
        self.connect("notify::default-width", self._on_size_changed)
        self.connect("notify::is-active", self._on_active_changed)
        self.connect("realize", self._on_realize)
        self.connect("close-request", self._on_close)
        self._apply_font(DEFAULT_W)

    # ---------- styling ----------

    def _load_css(self):
        display = Gdk.Display.get_default()
        if display is None:
            return
        static = Gtk.CssProvider()
        static.load_from_data(STATIC_CSS)
        Gtk.StyleContext.add_provider_for_display(
            display, static, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        self._font_provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_display(
            display, self._font_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1
        )

    def _on_size_changed(self, *_args):
        self._apply_font(self.get_width() or DEFAULT_W)

    def _apply_font(self, width):
        if not width:
            return
        scale = max(0.65, min(2.4, float(width) / BASE_WIDTH))
        size = int(round(BASE_FONT * scale))
        if size == self._font_size:
            return
        self._font_size = size
        css = ".key label { font-size: %dpx; } .suggest { font-size: %dpx; }" % (
            size,
            max(10, size - 1),
        )
        try:
            self._font_provider.load_from_data(css.encode())
        except Exception:
            pass

    # ---------- building ----------

    def _build(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        root.set_margin_top(6)
        root.set_margin_bottom(6)
        root.set_margin_start(6)
        root.set_margin_end(6)
        self.set_child(root)

        root.append(self._build_toolbar())
        root.append(self._build_suggestion_bar())

        grid = self._build_grid()
        grid.set_hexpand(True)
        grid.set_vexpand(True)
        root.append(grid)

    def _no_focus(self, widget):
        widget.set_focus_on_click(False)
        widget.set_can_focus(False)
        try:
            widget.set_focusable(False)
        except Exception:
            pass
        return widget

    def _tool_button(self, label, handler, *args):
        button = Gtk.Button(label=label)
        button.add_css_class("tool")
        self._no_focus(button)
        button.connect("clicked", handler, *args)
        return button

    def _build_toolbar(self):
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        logo = find_logo()
        if logo:
            image = Gtk.Image.new_from_file(logo)
            image.set_pixel_size(24)
            bar.append(image)

        titles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        name = Gtk.Label(label="LOSK")
        name.set_xalign(0.0)
        name.add_css_class("toolbar-title")
        sub = Gtk.Label(label="Linux On-Screen Keyboard \u00b7 Made by ZeshMC")
        sub.set_xalign(0.0)
        sub.add_css_class("toolbar-sub")
        titles.append(name)
        titles.append(sub)
        bar.append(titles)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        bar.append(spacer)

        self.status = Gtk.Label(label=self._status_text())
        self.status.add_css_class("status")
        bar.append(self.status)

        self.mic_button = self._tool_button("Mic", self._toggle_voice)
        bar.append(self.mic_button)

        self.pin_button = self._tool_button("Pinned", self._toggle_pin)
        self.pin_button.add_css_class("tool-on")
        bar.append(self.pin_button)

        for label, width, height in SIZE_PRESETS:
            bar.append(self._tool_button(label, self._set_size, width, height))

        bar.append(self._tool_button("Hide", self._on_hide))

        return bar

    def _status_text(self):
        if not self.kb.available:
            return "typing: off (%s)" % self.kb.reason
        if self._never_focus:
            return "typing: on \u00b7 fast"
        return "typing: on"

    def _set_status(self, text):
        self.status.set_label(text)

    def _build_suggestion_bar(self):
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.suggest_buttons = []
        for index in range(6):
            button = Gtk.Button(label="")
            button.add_css_class("suggest")
            button.set_hexpand(True)
            self._no_focus(button)
            button.connect("clicked", self._on_suggestion, index)
            bar.append(button)
            self.suggest_buttons.append(button)
        self._refresh_suggestions()
        return bar

    def _build_grid(self):
        grid = Gtk.Grid(column_spacing=3, row_spacing=3)
        grid.set_column_homogeneous(True)
        grid.set_row_homogeneous(True)

        col = 0
        for label, name, width, shift_label in FUNCTION_ROW:
            span = int(round(width * CPU))
            if name:
                grid.attach(self._make_key(label, name, shift_label), col, 0, span, 1)
            col += span

        for row_index, row in enumerate(ROWS):
            col = 0
            for label, name, width, shift_label in row:
                span = int(round(width * CPU))
                if name:
                    key = self._make_key(label, name, shift_label)
                    if row_index == 0:
                        key.set_margin_top(5)
                    grid.attach(key, col, row_index + 1, span, 1)
                col += span

        for label, name, col_unit, row in NAV_GRID:
            key = self._make_key(label, name, None)
            if row == 1:
                key.set_margin_top(5)
            grid.attach(key, NAV_START + col_unit * CPU, row, CPU, 1)

        for label, name, col_unit, row in ARROW_GRID:
            grid.attach(self._make_key(label, name, None),
                        NAV_START + col_unit * CPU, row, CPU, 1)

        for label, name, col_unit, row, colspan, rowspan in NUMPAD_GRID:
            key = self._make_key(label, name, None)
            if row == 0:
                key.set_margin_top(5)
            grid.attach(key, PAD_START + col_unit * CPU, row + 1,
                        colspan * CPU, rowspan)

        return grid

    def _make_key(self, label, name, shift_label=None):
        button = Gtk.Button()
        # An ellipsizing label keeps long text from forcing the key wider,
        # which is what would otherwise stop the window from shrinking.
        text = Gtk.Label(label=label)
        text.set_ellipsize(Pango.EllipsizeMode.END)
        text.set_single_line_mode(True)
        button.set_child(text)

        button.add_css_class("key")
        self._no_focus(button)
        button.set_hexpand(True)
        button.set_vexpand(True)
        button.set_size_request(16, 18)
        self._keys.append(button)

        is_letter = name in LETTER_KEYS
        if shift_label or is_letter:
            self._labels.append((text, label, shift_label, is_letter))

        if name in MODIFIERS or name == "KEY_CAPSLOCK":
            button.add_css_class("key-mod")
            self._mod_buttons[name] = button

        # Press and release instead of clicked, so a held key can repeat.
        gesture = Gtk.GestureClick()
        gesture.connect("pressed", self._on_key_pressed, name)
        gesture.connect("released", self._on_key_released)
        gesture.connect("cancel", self._on_key_cancel)
        button.add_controller(gesture)
        return button

    def _set_size(self, _button, width, height):
        self.set_default_size(width, height)
        self._apply_font(width)

    def _on_hide(self, _button):
        self._stop_repeat()
        self.minimize()

    # ---------- window behaviour ----------

    def _on_realize(self, *_args):
        GLib.timeout_add(300, self._setup_window)
        GLib.timeout_add(1000, self._track_other_window)

    def _own_xid(self):
        try:
            surface = self.get_surface()
            if GdkX11 and isinstance(surface, GdkX11.X11Surface):
                return surface.get_xid()
        except Exception:
            pass
        return None

    def _setup_window(self):
        xid = self._own_xid()
        if xid:
            self._own_id = str(xid)
            if self.xt and self.xt.available:
                self._never_focus = self.xt.set_never_focus(xid)
        elif self._xdotool:
            try:
                result = subprocess.run(
                    ["xdotool", "search", "--name", "^LOSK$"],
                    capture_output=True, text=True, timeout=2, check=False,
                )
                ids = result.stdout.split()
                if ids:
                    self._own_id = ids[-1]
            except Exception:
                pass
        self._keep_above()
        self._set_status(self._status_text())
        return False

    def _keep_above(self):
        """Ask the window manager to keep LOSK above other windows. Called on
        startup, on activation and on pin toggle, not on a timer, because every
        call restacks the window and made the taskbar indicators flash."""
        if not self._pinned or not self._wmctrl:
            return False
        target = ["-i", "-r", self._own_id] if self._own_id else ["-r", "LOSK"]
        for flag in ("add,above", "add,sticky"):
            try:
                subprocess.run(["wmctrl"] + target + ["-b", flag],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               timeout=2, check=False)
            except Exception:
                pass
        return False

    def _track_other_window(self):
        """Remember the app you were typing into, for the fallback path only."""
        if self._never_focus:
            return True  # nothing to track, LOSK never steals focus
        if self.is_active():
            return True
        if self.xt and self.xt.available:
            window_id = self.xt.active_window()
            if window_id and str(window_id) != str(self._own_id):
                self._last_window = window_id
            return True
        if not self._xdotool:
            return False
        try:
            result = subprocess.run(
                ["xdotool", "getactivewindow"],
                capture_output=True, text=True, timeout=1, check=False,
            )
            window_id = result.stdout.strip()
            if window_id and window_id != self._own_id:
                self._last_window = window_id
        except Exception:
            pass
        return True

    def _return_focus(self):
        """Only needed when the never-focus hint was refused."""
        if self._never_focus or not self._last_window:
            return
        if str(self._last_window) == str(self._own_id):
            return
        if self.xt and self.xt.available:
            self.xt.activate(int(self._last_window))
            return
        if not self._xdotool:
            return
        try:
            subprocess.run(["xdotool", "windowactivate", str(self._last_window)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=1, check=False)
        except Exception:
            pass

    def _on_active_changed(self, *_args):
        if self.is_active():
            self._keep_above()
            if not self._never_focus and self._last_window:
                GLib.timeout_add(10, self._bounce_focus)

    def _bounce_focus(self):
        self._return_focus()
        return False

    def _toggle_pin(self, button):
        self._pinned = not self._pinned
        if self._pinned:
            button.set_label("Pinned")
            button.add_css_class("tool-on")
            self._keep_above()
        else:
            button.set_label("Unpinned")
            button.remove_css_class("tool-on")
            if self._wmctrl:
                target = ["-i", "-r", self._own_id] if self._own_id else ["-r", "LOSK"]
                try:
                    subprocess.run(["wmctrl"] + target + ["-b", "remove,above"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   timeout=2, check=False)
                except Exception:
                    pass

    def _on_close(self, *_args):
        self._stop_repeat()
        if self.voice:
            self.voice.stop()
        if self.xt:
            self.xt.close()
        self.kb.close()
        return False

    # ---------- voice ----------

    def _toggle_voice(self, button):
        if self.voice is None or not self.voice.available:
            reason = self.voice.reason if self.voice else "voice module missing"
            self._set_status("voice: %s" % reason)
            return
        if self.voice.listening:
            self.voice.stop()
            button.set_label("Mic")
            button.remove_css_class("tool-rec")
            self._set_status(self._status_text())
        else:
            self.voice.start(self._on_transcript)
            button.set_label("Stop")
            button.add_css_class("tool-rec")
            self._set_status("voice: listening")

    def _on_transcript(self, text):
        GLib.idle_add(self._type_transcript, text)

    def _type_transcript(self, text):
        if not text:
            return False
        self._return_focus()
        for char in text:
            self._type_char(char)
        self._type_char(" ")
        for word in text.split():
            self.words.learn(word)
        self._word = ""
        self._refresh_suggestions()
        return False

    # ---------- key repeat ----------

    def _on_key_pressed(self, _gesture, _n_press, _x, _y, name):
        self._fire_key(name)
        if name in NO_REPEAT:
            return
        self._stop_repeat()
        self._repeat_key = name
        self._repeat_source = GLib.timeout_add(REPEAT_DELAY_MS, self._begin_repeat)

    def _begin_repeat(self):
        """First delay has passed, now repeat quickly until release."""
        if self._repeat_key is None:
            return False
        self._repeat_source = GLib.timeout_add(REPEAT_RATE_MS, self._do_repeat)
        return False

    def _do_repeat(self):
        if self._repeat_key is None:
            return False
        self._fire_key(self._repeat_key)
        return True

    def _on_key_released(self, *_args):
        self._stop_repeat()

    def _on_key_cancel(self, *_args):
        self._stop_repeat()

    def _stop_repeat(self):
        if self._repeat_source is not None:
            try:
                GLib.source_remove(self._repeat_source)
            except Exception:
                pass
        self._repeat_source = None
        self._repeat_key = None

    # ---------- typing ----------

    def _shift_on(self):
        return bool((self._latched | self._locked) & set(SHIFT_KEYS))

    def _active_mods(self):
        return sorted(self._latched | self._locked)

    def _fire_key(self, name):
        if name in MODIFIERS:
            self._cycle_modifier(name)
            return

        if name == "KEY_CAPSLOCK":
            self._caps = not self._caps
            self._return_focus()
            self.kb.tap(name)
            self._style_modifiers()
            self._refresh_labels()
            return

        self._return_focus()
        self.kb.tap(name, self._active_mods())
        self._update_word(name)
        self._clear_latched()

    def _cycle_modifier(self, name):
        """Click once to latch for the next key, again to lock, again to clear.
        Nothing is sent to the system here, so Shift alone cannot trigger a
        desktop shortcut."""
        if name in self._latched:
            self._latched.discard(name)
            self._locked.add(name)
        elif name in self._locked:
            self._locked.discard(name)
        else:
            self._latched.add(name)
        self._style_modifiers()
        self._refresh_labels()

    def _clear_latched(self):
        if self._latched:
            self._latched.clear()
            self._style_modifiers()
            self._refresh_labels()

    def _style_modifiers(self):
        for name, button in self._mod_buttons.items():
            button.remove_css_class("key-latched")
            button.remove_css_class("key-locked")
            if name == "KEY_CAPSLOCK":
                if self._caps:
                    button.add_css_class("key-locked")
            elif name in self._locked:
                button.add_css_class("key-locked")
            elif name in self._latched:
                button.add_css_class("key-latched")

    def _refresh_labels(self):
        shift = self._shift_on()
        for text, normal, shifted, is_letter in self._labels:
            if is_letter:
                upper = shift != self._caps
                text.set_label(normal.upper() if upper else normal)
            elif shifted:
                text.set_label(shifted if shift else normal)

    def _update_word(self, name):
        if name in ("KEY_SPACE", "KEY_ENTER", "KEY_TAB", "KEY_KPENTER"):
            self.words.learn(self._word)
            self._word = ""
        elif name == "KEY_BACKSPACE":
            self._word = self._word[:-1]
        elif name in LETTER_KEYS:
            base = LETTER_KEYS[name]
            upper = self._shift_on() != self._caps
            self._word += base.upper() if upper else base
        elif name == "KEY_APOSTROPHE" and not self._shift_on():
            self._word += "'"
        else:
            self._word = ""
        self._refresh_suggestions()

    def _refresh_suggestions(self):
        self._suggestions = self.words.suggest(self._word, len(self.suggest_buttons))
        for index, button in enumerate(self.suggest_buttons):
            if index < len(self._suggestions):
                button.set_label(self._suggestions[index])
                button.set_sensitive(True)
            else:
                button.set_label("")
                button.set_sensitive(False)

    def _on_suggestion(self, _button, index):
        if index >= len(self._suggestions):
            return
        word = self._suggestions[index]
        if word.lower().startswith(self._word.lower()):
            remainder = word[len(self._word):]
        else:
            remainder = word
        self._return_focus()
        for char in remainder:
            self._type_char(char)
        self._type_char(" ")
        self.words.learn(word)
        self._word = ""
        self._refresh_suggestions()

    def _type_char(self, char):
        entry = CHAR_TO_KEY.get(char)
        if entry is None:
            return
        name, needs_shift = entry
        self.kb.tap(name, ["KEY_LEFTSHIFT"] if needs_shift else [])