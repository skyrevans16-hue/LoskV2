"""
LOSK layout tables.
Made by ZeshMC

Every key is a tuple: (label, keyname, width_units, shift_label)
A keyname of None means it is just a blank spacer.
Width is in "units" where 1.0 = one normal letter key, like a real keyboard.
"""

FUNCTION_ROW = [
    ("Esc", "KEY_ESC", 1.0, None),
    (None, None, 0.6, None),
    ("F1", "KEY_F1", 1.0, None),
    ("F2", "KEY_F2", 1.0, None),
    ("F3", "KEY_F3", 1.0, None),
    ("F4", "KEY_F4", 1.0, None),
    (None, None, 0.5, None),
    ("F5", "KEY_F5", 1.0, None),
    ("F6", "KEY_F6", 1.0, None),
    ("F7", "KEY_F7", 1.0, None),
    ("F8", "KEY_F8", 1.0, None),
    (None, None, 0.5, None),
    ("F9", "KEY_F9", 1.0, None),
    ("F10", "KEY_F10", 1.0, None),
    ("F11", "KEY_F11", 1.0, None),
    ("F12", "KEY_F12", 1.0, None),
]

# Main block. Each row adds up to 15.0 units, exactly like a real ANSI keyboard.
ROWS = [
    [
        ("`", "KEY_GRAVE", 1.0, "~"),
        ("1", "KEY_1", 1.0, "!"),
        ("2", "KEY_2", 1.0, "@"),
        ("3", "KEY_3", 1.0, "#"),
        ("4", "KEY_4", 1.0, "$"),
        ("5", "KEY_5", 1.0, "%"),
        ("6", "KEY_6", 1.0, "^"),
        ("7", "KEY_7", 1.0, "&"),
        ("8", "KEY_8", 1.0, "*"),
        ("9", "KEY_9", 1.0, "("),
        ("0", "KEY_0", 1.0, ")"),
        ("-", "KEY_MINUS", 1.0, "_"),
        ("=", "KEY_EQUAL", 1.0, "+"),
        ("Backspace", "KEY_BACKSPACE", 2.0, None),
    ],
    [
        ("Tab", "KEY_TAB", 1.5, None),
        ("q", "KEY_Q", 1.0, "Q"),
        ("w", "KEY_W", 1.0, "W"),
        ("e", "KEY_E", 1.0, "E"),
        ("r", "KEY_R", 1.0, "R"),
        ("t", "KEY_T", 1.0, "T"),
        ("y", "KEY_Y", 1.0, "Y"),
        ("u", "KEY_U", 1.0, "U"),
        ("i", "KEY_I", 1.0, "I"),
        ("o", "KEY_O", 1.0, "O"),
        ("p", "KEY_P", 1.0, "P"),
        ("[", "KEY_LEFTBRACE", 1.0, "{"),
        ("]", "KEY_RIGHTBRACE", 1.0, "}"),
        ("\\", "KEY_BACKSLASH", 1.5, "|"),
    ],
    [
        ("Caps", "KEY_CAPSLOCK", 1.75, None),
        ("a", "KEY_A", 1.0, "A"),
        ("s", "KEY_S", 1.0, "S"),
        ("d", "KEY_D", 1.0, "D"),
        ("f", "KEY_F", 1.0, "F"),
        ("g", "KEY_G", 1.0, "G"),
        ("h", "KEY_H", 1.0, "H"),
        ("j", "KEY_J", 1.0, "J"),
        ("k", "KEY_K", 1.0, "K"),
        ("l", "KEY_L", 1.0, "L"),
        (";", "KEY_SEMICOLON", 1.0, ":"),
        ("'", "KEY_APOSTROPHE", 1.0, '"'),
        ("Enter", "KEY_ENTER", 2.25, None),
    ],
    [
        ("Shift", "KEY_LEFTSHIFT", 2.25, None),
        ("z", "KEY_Z", 1.0, "Z"),
        ("x", "KEY_X", 1.0, "X"),
        ("c", "KEY_C", 1.0, "C"),
        ("v", "KEY_V", 1.0, "V"),
        ("b", "KEY_B", 1.0, "B"),
        ("n", "KEY_N", 1.0, "N"),
        ("m", "KEY_M", 1.0, "M"),
        (",", "KEY_COMMA", 1.0, "<"),
        (".", "KEY_DOT", 1.0, ">"),
        ("/", "KEY_SLASH", 1.0, "?"),
        ("Shift", "KEY_RIGHTSHIFT", 2.75, None),
    ],
    [
        ("Ctrl", "KEY_LEFTCTRL", 1.25, None),
        ("Super", "KEY_LEFTMETA", 1.25, None),
        ("Alt", "KEY_LEFTALT", 1.25, None),
        ("Space", "KEY_SPACE", 6.25, None),
        ("AltGr", "KEY_RIGHTALT", 1.25, None),
        ("Super", "KEY_RIGHTMETA", 1.25, None),
        ("Menu", "KEY_COMPOSE", 1.25, None),
        ("Ctrl", "KEY_RIGHTCTRL", 1.25, None),
    ],
]

# Navigation cluster: (label, keyname, column, row)
NAV_GRID = [
    ("PrtSc", "KEY_SYSRQ", 0, 0),
    ("ScrLk", "KEY_SCROLLLOCK", 1, 0),
    ("Pause", "KEY_PAUSE", 2, 0),
    ("Ins", "KEY_INSERT", 0, 1),
    ("Home", "KEY_HOME", 1, 1),
    ("PgUp", "KEY_PAGEUP", 2, 1),
    ("Del", "KEY_DELETE", 0, 2),
    ("End", "KEY_END", 1, 2),
    ("PgDn", "KEY_PAGEDOWN", 2, 2),
]

# Arrow cluster sits at the bottom of the same column.
ARROW_GRID = [
    ("\u2191", "KEY_UP", 1, 4),
    ("\u2190", "KEY_LEFT", 0, 5),
    ("\u2193", "KEY_DOWN", 1, 5),
    ("\u2192", "KEY_RIGHT", 2, 5),
]

# Numpad: (label, keyname, column, row, colspan, rowspan)
# Tall + and tall Enter, wide 0. The duplicate + key is gone.
NUMPAD_GRID = [
    ("Num", "KEY_NUMLOCK", 0, 0, 1, 1),
    ("/", "KEY_KPSLASH", 1, 0, 1, 1),
    ("*", "KEY_KPASTERISK", 2, 0, 1, 1),
    ("-", "KEY_KPMINUS", 3, 0, 1, 1),
    ("7", "KEY_KP7", 0, 1, 1, 1),
    ("8", "KEY_KP8", 1, 1, 1, 1),
    ("9", "KEY_KP9", 2, 1, 1, 1),
    ("+", "KEY_KPPLUS", 3, 1, 1, 2),
    ("4", "KEY_KP4", 0, 2, 1, 1),
    ("5", "KEY_KP5", 1, 2, 1, 1),
    ("6", "KEY_KP6", 2, 2, 1, 1),
    ("1", "KEY_KP1", 0, 3, 1, 1),
    ("2", "KEY_KP2", 1, 3, 1, 1),
    ("3", "KEY_KP3", 2, 3, 1, 1),
    ("Enter", "KEY_KPENTER", 3, 3, 1, 2),
    ("0", "KEY_KP0", 0, 4, 2, 1),
    (".", "KEY_KPDOT", 2, 4, 1, 1),
]

# Modifiers latch instead of being held, because you cannot hold a mouse button
# and click another key at the same time.
MODIFIERS = (
    "KEY_LEFTSHIFT",
    "KEY_RIGHTSHIFT",
    "KEY_LEFTCTRL",
    "KEY_RIGHTCTRL",
    "KEY_LEFTALT",
    "KEY_RIGHTALT",
    "KEY_LEFTMETA",
    "KEY_RIGHTMETA",
)

SHIFT_KEYS = ("KEY_LEFTSHIFT", "KEY_RIGHTSHIFT")

# Used by the suggestion bar to type a whole word one character at a time.
CHAR_TO_KEY = {}
for _ch in "abcdefghijklmnopqrstuvwxyz":
    CHAR_TO_KEY[_ch] = ("KEY_" + _ch.upper(), False)
    CHAR_TO_KEY[_ch.upper()] = ("KEY_" + _ch.upper(), True)
for _d in "0123456789":
    CHAR_TO_KEY[_d] = ("KEY_" + _d, False)
CHAR_TO_KEY[" "] = ("KEY_SPACE", False)
CHAR_TO_KEY["'"] = ("KEY_APOSTROPHE", False)
CHAR_TO_KEY["-"] = ("KEY_MINUS", False)
CHAR_TO_KEY["."] = ("KEY_DOT", False)
CHAR_TO_KEY[","] = ("KEY_COMMA", False)

# Maps a key back to the letter it produces, so LOSK knows what word is being typed.
LETTER_KEYS = {}
for _ch in "abcdefghijklmnopqrstuvwxyz":
    LETTER_KEYS["KEY_" + _ch.upper()] = _ch


def all_key_names():
    """Every keyname LOSK can send. The virtual device registers all of these."""
    names = set()
    for _l, name, _w, _s in FUNCTION_ROW:
        if name:
            names.add(name)
    for row in ROWS:
        for _l, name, _w, _s in row:
            if name:
                names.add(name)
    for _l, name, _c, _r in NAV_GRID:
        names.add(name)
    for _l, name, _c, _r in ARROW_GRID:
        names.add(name)
    for _l, name, _c, _r, _cs, _rs in NUMPAD_GRID:
        names.add(name)
    names.update(MODIFIERS)
    for name, _shift in CHAR_TO_KEY.values():
        names.add(name)
    return sorted(names)
