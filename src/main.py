"""
LOSK entry point.
Made by ZeshMC
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio

from ui import LoskWindow


class LoskApplication(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id="com.zeshmc.losk",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.window = None

    def do_activate(self):
        if self.window is None:
            self.window = LoskWindow(application=self)
        self.window.present()

    def do_shutdown(self):
        if self.window is not None:
            self.window.kb.close()
        Gtk.Application.do_shutdown(self)


def main():
    return LoskApplication().run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
