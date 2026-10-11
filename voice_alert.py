"""
Non-blocking Text-to-Speech Voice Alert System.
Uses a background worker thread to prevent audio playback from blocking
the real-time video inference loop. Gracefully handles absence of pyttsx3.
"""

import queue
import threading
import time
from typing import Optional

try:
    import pyttsx3
    HAS_PYTTSX3 = True
except ImportError:
    HAS_PYTTSX3 = False


class VoiceAlertWorker:
    """
    Background worker thread that receives alert text and announces it via TTS.
    """

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.queue = queue.Queue(maxsize=5)
        self.worker_thread: Optional[threading.Thread] = None
        self._running = False
        self.engine = None

        if self.enabled and HAS_PYTTSX3:
            try:
                self.engine = pyttsx3.init()
                self.engine.setProperty("rate", 160)
            except Exception as e:
                print(f"[VOICE] Error initializing pyttsx3: {e}. Falling back to console.")
                self.engine = None

        if self.enabled:
            self._running = True
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()

    def _worker_loop(self):
        while self._running:
            try:
                message = self.queue.get(timeout=0.2)
                if message is None:
                    break
                
                if self.engine is not None:
                    try:
                        self.engine.say(message)
                        self.engine.runAndWait()
                    except Exception as e:
                        print(f"[VOICE ERROR] {e}")
                else:
                    # Visual console cue if TTS engine is unavailable
                    print(f"[AUDIO ALERT]: {message}")

                self.queue.task_done()
            except queue.Empty:
                continue

    def alert(self, message: str):
        """Pushes an alert message to the voice queue if queue is not full."""
        if not self.enabled:
            return
        try:
            self.queue.put_nowait(message)
        except queue.Full:
            pass

    def stop(self):
        self._running = False
        try:
            self.queue.put_nowait(None)
        except queue.Full:
            pass
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=1.0)
