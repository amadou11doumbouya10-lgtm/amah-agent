"""Surveillance webcam pour l'auto-mute (vie privee).

Detecte l'arrivee d'une ou plusieurs autres personnes devant la camera
(2+ visages) et coupe automatiquement le son d'Amah ; le son est retabli
quand la camera ne voit plus qu'une seule personne (ou personne).

Desactive par defaut (vie privee) -- ne demarre que via start_auto_mute()
(tools/webcam_guard.py), jamais automatiquement au lancement de l'app.
La camera est partagee avec analyze_webcam via tools/webcam.py (acces
ref-compte) pour eviter les conflits "camera deja utilisee".
"""
import threading
import time

from tools.webcam import acquire, release
from tools.computer_settings import mute_audio

MULTI_FACE_DELAY  = 3.0   # secondes de detection 2+ visages avant mute
SINGLE_FACE_DELAY = 2.0   # secondes de retour a 0/1 visage avant unmute
POLL_INTERVAL     = 0.5   # frequence de scan de la webcam


class WebcamMonitor:
    _instance = None
    _instance_lock = threading.Lock()

    def __init__(self):
        self._thread      = None
        self._stop_event  = threading.Event()
        self._paused      = False
        self._on_pause    = None
        self._on_resume   = None
        self._lock        = threading.Lock()

    @classmethod
    def get(cls) -> "WebcamMonitor":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def set_callbacks(self, on_pause=None, on_resume=None):
        """Definit les callbacks appeles quand le son est coupe / retabli."""
        self._on_pause  = on_pause
        self._on_resume = on_resume

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def is_paused(self) -> bool:
        return self._paused

    def start(self) -> bool:
        """Demarre la surveillance. Retourne False si deja active ou si cv2 manque."""
        with self._lock:
            if self.is_running():
                return False
            try:
                import cv2  # noqa: F401
            except ImportError:
                return False
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
            return True

    def stop(self):
        """Arrete la surveillance et retablit le son si coupe."""
        with self._lock:
            self._stop_event.set()
            thread = self._thread
        if thread is not None:
            thread.join(timeout=2)
        with self._lock:
            self._thread = None
        if self._paused:
            self._resume()

    def _loop(self):
        import cv2

        cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        cap = acquire()
        if cap is None:
            return

        try:
            multi_since  = None
            single_since = None
            while not self._stop_event.is_set():
                ok, frame = cap.read()
                if ok:
                    gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    faces = cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(60, 60))
                    count = len(faces)
                    now   = time.time()

                    if count >= 2:
                        single_since = None
                        if multi_since is None:
                            multi_since = now
                        elif not self._paused and now - multi_since >= MULTI_FACE_DELAY:
                            self._pause()
                    else:
                        multi_since = None
                        if self._paused:
                            if single_since is None:
                                single_since = now
                            elif now - single_since >= SINGLE_FACE_DELAY:
                                self._resume()
                        else:
                            single_since = None

                self._stop_event.wait(POLL_INTERVAL)
        finally:
            release()

    def _pause(self):
        self._paused = True
        try:
            mute_audio()
        except Exception:
            pass
        if self._on_pause:
            try:
                self._on_pause()
            except Exception:
                pass

    def _resume(self):
        self._paused = False
        try:
            mute_audio()
        except Exception:
            pass
        if self._on_resume:
            try:
                self._on_resume()
            except Exception:
                pass
