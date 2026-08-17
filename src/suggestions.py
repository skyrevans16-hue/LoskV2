"""
LOSK offline word suggestions.
Made by ZeshMC

No internet. A built in common word list plus words you actually use, saved to
~/.local/share/losk/words.json so LOSK gets better the more you type.
"""

import json
import os

STORE_DIR = os.path.join(
    os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
    "losk",
)
STORE_FILE = os.path.join(STORE_DIR, "words.json")

_COMMON = """
the be to of and a in that have it for not on with he as you do at this but his
by from they we say her she or an will my one all would there their what so up
out if about who get which go me when make can like time no just him know take
people into year your good some could them see other than then now look only
come over think also back after use two how our work first well way even new
want because any these give day most us is are was were been being has had did
does am hello hi hey help home how however here please thanks thank sorry yes
maybe okay sure name email password phone address city state country computer
keyboard mouse screen window file folder open close save print search internet
browser google message text send receive morning afternoon evening night today
tomorrow yesterday week month monday tuesday wednesday thursday friday saturday
sunday january february march april june july august september october november
december love need feel understand remember forget water food coffee drink eat
sleep walk run drive family friend mother father brother sister child children
school job money life world place thing where why something everything nothing
anything someone everyone great really very much many little always never often
before while every same right left down under between through around again
should must might really please again welcome goodbye later soon
"""


class SuggestionEngine:
    def __init__(self):
        self.builtin = {}
        words = [w for w in _COMMON.split() if w]
        total = len(words)
        for index, word in enumerate(words):
            # Earlier words in the list are more common, so they score higher.
            score = total - index
            if score > self.builtin.get(word, 0):
                self.builtin[word] = score
        self.learned = {}
        self._load()

    def _load(self):
        try:
            with open(STORE_FILE, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(key, str) and isinstance(value, int):
                        self.learned[key] = value
        except Exception:
            self.learned = {}

    def _save(self):
        try:
            os.makedirs(STORE_DIR, exist_ok=True)
            with open(STORE_FILE, "w", encoding="utf-8") as handle:
                json.dump(self.learned, handle)
        except Exception:
            pass

    def learn(self, word):
        clean = (word or "").strip().lower()
        if len(clean) < 2 or not clean.isalpha():
            return
        self.learned[clean] = self.learned.get(clean, 0) + 40
        self._save()

    def suggest(self, prefix, limit=6):
        typed = (prefix or "").strip().lower()
        scored = []
        seen = set()
        for source in (self.learned, self.builtin):
            for word, score in source.items():
                if word in seen:
                    continue
                if typed:
                    if not word.startswith(typed) or word == typed:
                        continue
                    # Nudge shorter completions up, they are usually what you meant.
                    bonus = 60 if len(word) - len(typed) <= 3 else 0
                    scored.append((score + bonus, -len(word), word))
                else:
                    scored.append((score, -len(word), word))
                seen.add(word)
        scored.sort(reverse=True)
        out = [item[2] for item in scored[:limit]]
        if prefix and prefix[:1].isupper():
            out = [w.capitalize() for w in out]
        return out
