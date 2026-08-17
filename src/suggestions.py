"""
LOSK offline word suggestions.
Made by ZeshMC

Two kinds of prediction, both fully offline:

  1. Prefix completion. Type "th" and you get the, this, that, there.
  2. Next word prediction. Finish a word and LOSK guesses what usually
     follows it, the way phone keyboards do.

Everything you type is remembered in ~/.local/share/losk/words.json so the
suggestions get better the more you use it. No internet, ever.
"""

import json
import os

STORE_DIR = os.path.join(
    os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
    "losk",
)
STORE_FILE = os.path.join(STORE_DIR, "words.json")

# Roughly ordered by how common the word is. Earlier means higher score.
_COMMON = """
the be to of and a in that have it for not on with he as you do at this but his
by from they we say her she or an will my one all would there their what so up
out if about who get which go me when make can like time no just him know take
people into year your good some could them see other than then now look only
come over think also back after use two how our work first well way even new
want because any give day most us is are was were been being has had did does
am i me myself yourself himself herself itself ourselves themselves
hello hi hey help home however here please thanks thank sorry yes yeah no nope
maybe okay ok sure right wrong true false correct
name email password phone address city state country zip code
computer keyboard mouse screen window file folder open close save print search
internet browser google message text send receive delete edit copy paste undo
download upload install update settings account login logout profile
morning afternoon evening night today tomorrow yesterday week weekend month year
monday tuesday wednesday thursday friday saturday sunday
january february march april may june july august september october november
december
love need feel understand remember forget hope wish try keep start stop finish
water food coffee tea drink eat sleep walk run drive ride fly buy sell pay
family friend mother father brother sister child children son daughter wife
husband parent baby people person man woman boy girl
school work job money life world place thing time home house room car street
city town country road store shop office
where why what when who how which whose
something everything nothing anything someone everyone anyone nobody
great really very much many little few lot more less best better worse
always never often sometimes usually rarely again still yet already soon later
before while during after until since between through around under over above
below inside outside near far away back forward
should must might could would will can may shall
welcome goodbye bye see later thanks again
question answer problem solution reason example idea plan project
number letter word line page book paper list note
big small large tiny long short high low fast slow easy hard simple
new old young early late first last next previous other same different
happy sad angry tired busy free ready sick fine well bad
"""

# Pairs that show up constantly in ordinary typing. Seeds the next-word model
# so it is useful before you have typed anything.
_PAIRS = """
how are|how do|how much|how many|how is
thank you|thanks for
i am|i have|i will|i think|i need|i want|i can|i was|i would|i just
you are|you can|you have|you should|you will
what is|what do|what are|what time|what about
can you|can i|can we
do you|do i|do we|do not
this is|this was|that is|that was
there is|there are|there was
it is|it was|it will
we are|we can|we have|we will
let me|let us
going to|want to|need to|have to|used to|try to|able to
a lot|a little|a few|a good
in the|on the|at the|to the|for the|of the|with the|from the
good morning|good night|good luck|good job
see you|talk to|thanks again
please let|please send|please check
"""


def _tokenize(text):
    return [w for w in text.split() if w]


class SuggestionEngine:
    def __init__(self):
        self.builtin = {}
        words = _tokenize(_COMMON)
        total = len(words)
        for index, word in enumerate(words):
            score = total - index
            if score > self.builtin.get(word, 0):
                self.builtin[word] = score

        # follows[first][second] = how often second comes after first
        self.follows = {}
        for chunk in _PAIRS.replace("\n", "|").split("|"):
            parts = chunk.split()
            if len(parts) == 2:
                first, second = parts[0].lower(), parts[1].lower()
                self.follows.setdefault(first, {})
                self.follows[first][second] = self.follows[first].get(second, 0) + 25

        self.learned = {}
        self._previous = ""
        self._load()

    # ---------- storage ----------

    def _load(self):
        try:
            with open(STORE_FILE, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception:
            return
        if not isinstance(data, dict):
            return
        # Older versions stored a flat word->count dict. Keep those counts.
        if "words" not in data and "follows" not in data:
            for key, value in data.items():
                if isinstance(key, str) and isinstance(value, int):
                    self.learned[key] = value
            return
        for key, value in data.get("words", {}).items():
            if isinstance(key, str) and isinstance(value, int):
                self.learned[key] = value
        for first, seconds in data.get("follows", {}).items():
            if not isinstance(seconds, dict):
                continue
            target = self.follows.setdefault(first, {})
            for second, count in seconds.items():
                if isinstance(count, int):
                    target[second] = target.get(second, 0) + count

    def _save(self):
        try:
            os.makedirs(STORE_DIR, exist_ok=True)
            payload = {"words": self.learned, "follows": self.follows}
            with open(STORE_FILE, "w", encoding="utf-8") as handle:
                json.dump(payload, handle)
        except Exception:
            pass

    # ---------- learning ----------

    def learn(self, word):
        """Called when a word is finished. Records the word and what preceded it."""
        clean = (word or "").strip().lower()
        if len(clean) < 2 or not clean.isalpha():
            self._previous = ""
            return
        self.learned[clean] = self.learned.get(clean, 0) + 40
        if self._previous:
            pair = self.follows.setdefault(self._previous, {})
            pair[clean] = pair.get(clean, 0) + 30
        self._previous = clean
        self._save()

    def reset_context(self):
        self._previous = ""

    # ---------- suggesting ----------

    def suggest(self, prefix, limit=6):
        typed = (prefix or "").strip().lower()

        if not typed:
            return self._next_word(limit, prefix)

        followers = self.follows.get(self._previous, {})
        scored = []
        seen = set()

        for source in (self.learned, self.builtin):
            for word, score in source.items():
                if word in seen or not word.startswith(typed) or word == typed:
                    continue
                seen.add(word)
                total = score
                # A word that usually follows the previous word gets a big lift.
                total += followers.get(word, 0) * 4
                # Short completions are usually the intended one.
                if len(word) - len(typed) <= 3:
                    total += 60
                scored.append((total, -len(word), word))

        # Words you have used that are not in either list still deserve a slot.
        for word in followers:
            if word not in seen and word.startswith(typed) and word != typed:
                scored.append((followers[word] * 4, -len(word), word))
                seen.add(word)

        scored.sort(reverse=True)
        return self._match_case([item[2] for item in scored[:limit]], prefix)

    def _next_word(self, limit, prefix):
        """Nothing typed yet, so predict what usually comes after the last word."""
        followers = self.follows.get(self._previous, {})
        scored = [(count, -len(word), word) for word, count in followers.items()]
        scored.sort(reverse=True)
        out = [item[2] for item in scored[:limit]]

        if len(out) < limit:
            filler = sorted(self.builtin.items(), key=lambda kv: -kv[1])
            for word, _score in filler:
                if word not in out:
                    out.append(word)
                if len(out) >= limit:
                    break
        return self._match_case(out[:limit], prefix)

    def _match_case(self, words, prefix):
        if prefix and prefix[:1].isupper():
            return [w.capitalize() for w in words]
        return words