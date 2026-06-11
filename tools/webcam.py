"""Acces partage a la webcam (ref-counte) pour analyze_webcam et WebcamMonitor.

Un seul cv2.VideoCapture est ouvert a la fois, partage entre l'outil de vision
(analyze_webcam) et la surveillance auto-mute (WebcamMonitor) -- evite les
conflits "camera deja utilisee" entre les deux fonctionnalites.
"""
import threading

_lock = threading.Lock()
_cap = None
_ref_count = 0


def acquire():
    """Ouvre (ou reutilise) la webcam partagee. Retourne le VideoCapture, ou None si indisponible."""
    global _cap, _ref_count
    import cv2
    with _lock:
        if _cap is None:
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap.release()
                return None
            _cap = cap
        _ref_count += 1
        return _cap


def release():
    """Relache une reference. Ferme la camera quand plus personne ne l'utilise."""
    global _cap, _ref_count
    with _lock:
        if _ref_count > 0:
            _ref_count -= 1
        if _ref_count <= 0 and _cap is not None:
            _cap.release()
            _cap = None


def read_frame():
    """Capture une frame unique (acquire + read + release) pour un usage ponctuel."""
    cap = acquire()
    if cap is None:
        return None
    try:
        with _lock:
            ok, frame = cap.read()
        return frame if ok else None
    finally:
        release()


def read_locked():
    """Lit une frame sur la camera deja acquise (thread-safe). Suppose acquire() deja appele."""
    with _lock:
        if _cap is None:
            return None
        ok, frame = _cap.read()
    return frame if ok else None
