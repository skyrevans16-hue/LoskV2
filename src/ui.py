"""
LOSK GTK 4 window.
Made by ZeshMC
"""

import glob
import os
import shutil
import subprocess

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, GLib

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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# One "unit" is the width of a normal letter key. Everything scales from this,
# which is what keeps the whole board compact instead of tablet sized.
NORMAL_UNIT = 38
BIG_UNIT = 50
GAP = 3

CSS = b"""
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
    font-size: 13px;
    box-shadow: none;
}
.key:hover { background-color: #384254; }
.key:active { background-color: #4d81d8; }
.key-big { font-size: 16px; }
.key-mod { background-color: #333c4e; }
.key-latched { background-color: #4d81d8; border-color: #6d9bea; }
.key-locked { background-color: #c9762f; border-color: #e0913f; }
.suggest {
    background-image: none;
    background-color: #232b38;
    color: #cfe0ff;
    border: 1px solid #384254;
    border-radius: 5px;
    font-size: 12px;
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
"""


def find_logo():
    """Packaged icon first, then whatever PNG is sitting in assets/icons."""
    packaged = "/usr/share/icons/hicolor/512x512/apps/losk.png"
    if os.path.exists(packaged):
        return packaged
    local_dir = os.path.join(BASE_DIR, "..", "assets", "icons")
    matches = sorted(glob.glob(os.path.join(local_dir, "*.png")))
    if matches:
        return matches[0]
    return None


class LoskWindow(Gtk.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("LOSK")

        self.kb = VirtualKeyboard()
        self.words = SuggestionEngine()

        self.unit = NORMAL_UNIT
        self.big = False

        self._sized = []          # (widget, width_units, height_units)
        self._keys = []           # every key button, for the big/normal font swap
        self._labels = []         # (button, normal_label, shift_label, is_letter)
        self._mod_buttons = {}
        self._latched = set()
        self._locked = set()
        self._caps = False
        self._word = ""
        self._suggestions = []

        self._xdotool = shutil.which("xdotool")
        self._wmctrl = shutil.which("wmctrl")
        self._last_window = None
        self._session = os.environ.get("XDG_SESSION_TYPE", "unknown")

        self._load_css()
        self._build()

        self.set_default_size(-1, -1)
        self.connect("realize", self._on_realize)
        self.connect("notify::is-active", self._on_active_changed)
        self.connect("close-request", self._on_close)

    # ---------- setup ----------

    def _load_css(self):
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        display = Gdk.Display.get_default()
        if display is not None:
            Gtk.StyleContext.add_provider_for_display(
                display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

    def _px(self, units):
        return int(round(units * self.unit + (units - 1) * GAP))

    def _build(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        root.set_margin_top(8)
        root.set_margin_bottom(8)
        root.set_margin_start(8)
        root.set_margin_end(8)
        self.set_child(root)

        root.append(self._build_toolbar())
        root.append(self._build_suggestion_bar())
        root.append(self._build_keyboard())

    def _build_toolbar(self):
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        logo = find_logo()
        if logo:
            image = Gtk.Image.new_from_file(logo)
            image.set_pixel_size(28)
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

        self.top_button = Gtk.Button(label="Stay On Top")
        self.top_button.add_css_class("tool")
        self.top_button.set_focus_on_click(False)
        self.top_button.connect("clicked", lambda _b: self._apply_always_on_top())
        bar.append(self.top_button)

        self.size_button = Gtk.Button(label="Make Big")
        self.size_button.add_css_class("tool")
        self.size_button.set_focus_on_click(False)
        self.size_button.connect("clicked", self._toggle_big)
        bar.append(self.size_button)

        return bar

    def _status_text(self):
        if self.kb.available:
            return "typing: on"
        return "typing: off (%s)" % self.kb.reason

    def _build_suggestion_bar(self):
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.suggest_buttons = []
        for index in range(6):
            button = Gtk.Button(label="")
            button.add_css_class("suggest")
            button.set_hexpand(True)
            button.set_focus_on_click(False)
            button.set_can_focus(False)
            button.connect("clicked", self._on_suggestion, index)
            bar.append(button)
            self.suggest_buttons.append(button)
        self._refresh_suggestions()
        return bar

    def _build_keyboard(self):
        board = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=GAP * 5)
        board.set_halign(Gtk.Align.CENTER)

        # Main block
        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=GAP)
        main.append(self._build_row(FUNCTION_ROW))
        gap_row = Gtk.Box()
        gap_row.set_size_request(-1, 6)
        main.append(gap_row)
        for row in ROWS:
            main.append(self._build_row(row))
        board.append(main)

        # Navigation and arrows share one column so the rows line up
        nav = Gtk.Grid(row_spacing=GAP, column_spacing=GAP)
        for label, name, col, row in NAV_GRID:
            nav.attach(self._make_key(label, name, 1.0, 1.0), col, row, 1, 1)
        blank = Gtk.Box()
        self._track_size(blank, 1.0, 1.0)
        nav.attach(blank, 0, 3, 3, 1)
        for label, name, col, row in ARROW_GRID:
            nav.attach(self._make_key(label, name, 1.0, 1.0), col, row, 1, 1)
        board.append(nav)

        # Numpad, offset down one row so it starts under the function row
        pad = Gtk.Grid(row_spacing=GAP, column_spacing=GAP)
        pad_top = Gtk.Box()
        self._track_size(pad_top, 1.0, 1.0)
        pad.attach(pad_top, 0, 0, 4, 1)
        for label, name, col, row, colspan, rowspan in NUMPAD_GRID:
            key = self._make_key(label, name, float(colspan), float(rowspan))
            pad.attach(key, col, row + 1, colspan, rowspan)
        board.append(pad)

        return board

    def _build_row(self, row):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=GAP)
        for label, name, width, shift_label in row:
            if name is None:
                spacer = Gtk.Box()
                self._track_size(spacer, width, 1.0)
                box.append(spacer)
            else:
                box.append(self._make_key(label, name, width, 1.0, shift_label))
        return box

    def _track_size(self, widget, width_units, height_units):
        self._sized.append((widget, width_units, height_units))
        widget.set_size_request(self._px(width_units), self._px(height_units))

    def _make_key(self, label, name, width, height, shift_label=None):
        button = Gtk.Button(label=label)
        button.add_css_class("key")
        button.set_focus_on_click(False)
        button.set_can_focus(False)
        self._track_size(button, width, height)
        self._keys.append(button)

        is_letter = name in LETTER_KEYS
        if shift_label or is_letter:
            self._labels.append((button, label, shift_label, is_letter))

        if name in MODIFIERS:
            button.add_css_class("key-mod")
            self._mod_buttons[name] = button
        if name == "KEY_CAPSLOCK":
            button.add_css_class("key-mod")
            self._mod_buttons[name] = button

        button.connect("clicked", self._on_key, name, label, shift_label)
        return button

    # ---------- window behaviour ----------

    def _on_realize(self, *_args):
        GLib.timeout_add(400, self._apply_always_on_top)
        if self._xdotool:
            GLib.timeout_add(600, self._remember_window)

    def _apply_always_on_top(self):
        """Ask the window manager to keep LOSK above other windows."""
        if not self._wmctrl:
            self.top_button.set_label("wmctrl missing")
            return False
        for flag in ("add,above", "add,sticky", "add,skip_taskbar"):
            try:
                subprocess.run(
                    ["wmctrl", "-r", "LOSK", "-b", flag],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                    timeout=2,
                )
            except Exception:
                pass
        self.top_button.add_css_class("tool-on")
        return False

    def _remember_window(self):
        """Keep track of the last app you were actually typing into."""
        try:
            result = subprocess.run(
                ["xdotool", "getactivewindow"],
                capture_output=True,
                text=True,
                timeout=1,
                check=False,
            )
            window_id = result.stdout.strip()
            if window_id and not self.is_active():
                self._last_window = window_id
        except Exception:
            pass
        return True

    def _on_active_changed(self, *_args):
        # If LOSK grabs focus, hand it straight back so your keystrokes land
        # in the app you were using instead of in LOSK.
        if self.is_active() and self._last_window:
            GLib.timeout_add(20, self._restore_focus)

    def _restore_focus(self):
        if not self._xdotool or not self._last_window:
            return False
        try:
            subprocess.run(
                ["xdotool", "windowactivate", self._last_window],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=1,
                check=False,
            )
        except Exception:
            pass
        return False

    def _on_close(self, *_args):
        self.kb.close()
        return False

    # ---------- sizing ----------

    def _toggle_big(self, button):
        self.big = not self.big
        self.unit = BIG_UNIT if self.big else NORMAL_UNIT
        for widget, width_units, height_units in self._sized:
            widget.set_size_request(self._px(width_units), self._px(height_units))
        for key in self._keys:
            if self.big:
                key.add_css_class("key-big")
            else:
                key.remove_css_class("key-big")
        button.set_label("Normal Size" if self.big else "Make Big")
        GLib.idle_add(self._shrink_to_fit)

    def _shrink_to_fit(self):
        self.set_default_size(1, 1)
        return False

    # ---------- typing ----------

    def _shift_on(self):
        return bool(self._latched & set(SHIFT_KEYS) or self._locked & set(SHIFT_KEYS))

    def _active_mods(self):
        return sorted(self._latched | self._locked)

    def _on_key(self, _button, name, label, shift_label):
        if name in MODIFIERS:
            self._cycle_modifier(name)
            return

        if name == "KEY_CAPSLOCK":
            self._caps = not self._caps
            self.kb.tap(name)
            self._style_modifiers()
            self._refresh_labels()
            return

        self.kb.tap(name, self._active_mods())
        self._update_word(name, label, shift_label)
        self._clear_latched()

    def _cycle_modifier(self, name):
        """Click once to latch for the next key, click again to lock, again to clear."""
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
                continue
            if name in self._locked:
                button.add_css_class("key-locked")
            elif name in self._latched:
                button.add_css_class("key-latched")

    def _refresh_labels(self):
        shift = self._shift_on()
        for button, normal, shifted, is_letter in self._labels:
            if is_letter:
                upper = shift != self._caps
                button.set_label(normal.upper() if upper else normal)
            elif shifted:
                button.set_label(shifted if shift else normal)

    def _update_word(self, name, label, shift_label):
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
        mods = ["KEY_LEFTSHIFT"] if needs_shift else []
        self.kb.tap(name, mods)
