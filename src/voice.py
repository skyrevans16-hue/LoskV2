"""
LOSK offline voice input.
Made by ZeshMC

Uses Vosk, which runs entirely on your machine. No audio ever leaves the
computer. The speech model is a separate one-time download because it is
around 50 MB, far too big to ship inside the .deb.

Install on Zorin:
    sudo apt install python3-pip
    pip3 install --break-system-packages vosk sounddevice
    mkdir -p ~/.local/share/losk
    cd ~/.local/share/losk
    wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
    unzip vosk-model-small-en-us-0.15.zip
    mv vosk-model-small-en-us-0.15 model

If any of that is missing, LOSK still starts and the Mic button just reports
what is not set up yet.
"""

import json
import os
import queue
import threading

MODEL_DIR = os.path.join(
    os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
    "losk",
    "model",
)

SAMPLE_RATE = 16000


class VoiceInput:
    def __init__(self):
        self.available = False
        self.listening = False
        self.reason = ""

        self._model = None
        self._thread = None
        self._stop_flag = threading.Event()
        self._audio = queue.Queue()
        self._callback = None

        try:
            import vosk            # noqa: F401
            import sounddevice     # noqa: F401
        except Exception as exc:
            self.reason = "vosk/sounddevice not installed (%s)" % type(exc).__name__
            return

        if not os.path.isdir(MODEL_DIR):
            self.reason = "no model at %s" % MODEL_DIR
            return

        self.available = True
        self.reason = "ready"

    def _load_model(self):
        if self._model is not None:
            return True
        try:
            import vosk
            vosk.SetLogLevel(-1)
            self._model = vosk.Model(MODEL_DIR)
            return True
        except Exception as exc:
            self.reason = "model failed to load (%s)" % exc
            self.available = False
            return False

    def start(self, callback):
        """Begin listening. callback(text) fires on the audio thread for each
        finished phrase, so the caller must hop back to the GTK thread."""
        if not self.available or self.listening:
            return False
        if not self._load_model():
            return False
        self._callback = callback
        self._stop_flag.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self.listening = True
        return True

    def stop(self):
        self._stop_flag.set()
        self.listening = False
        thread = self._thread
        self._thread = None
        if thread is not None and thread.is_alive():
            thread.join(timeout=2)

    def _run(self):
        try:
            import sounddevice as sd
            import vosk
        except Exception:
            self.listening = False
            return

        def on_audio(indata, _frames, _time, _status):
            if not self._stop_flag.is_set():
                self._audio.put(bytes(indata))

        try:
            recognizer = vosk.KaldiRecognizer(self._model, SAMPLE_RATE)
            with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=8000,
                                   dtype="int16", channels=1, callback=on_audio):
                while not self._stop_flag.is_set():
                    try:
                        chunk = self._audio.get(timeout=0.3)
                    except queue.Empty:
                        continue
                    if recognizer.AcceptWaveform(chunk):
                        text = json.loads(recognizer.Result()).get("text", "")
                        if text and self._callback:
                            self._callback(text)
                # Flush whatever was mid-sentence when you pressed Stop.
                tail = json.loads(recognizer.FinalResult()).get("text", "")
                if tail and self._callback:
                    self._callback(tail)
        except Exception as exc:
            self.reason = "audio error (%s)" % exc
        finally:
            self.listening = False
            while not self._audio.empty():
                try:
                    self._audio.get_nowait()
                except queue.Empty:
                    break
