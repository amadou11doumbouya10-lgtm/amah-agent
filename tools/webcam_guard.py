"""Activation/desactivation de la surveillance webcam auto-mute (vie privee).

Coupe automatiquement le son d'Amah quand 2+ personnes sont detectees devant
la camera, et le retablit quand il n'y en a plus qu'une (ou personne).
Desactive par defaut -- l'utilisateur doit l'activer explicitement.
"""
from webcam_monitor import WebcamMonitor


def start_auto_mute() -> dict:
    """Active la surveillance webcam : coupe le son automatiquement si plusieurs personnes apparaissent devant la camera."""
    monitor = WebcamMonitor.get()
    if monitor.is_running():
        return {"success": True, "message": "Surveillance webcam deja active."}
    if monitor.start():
        return {"success": True, "message": "Surveillance webcam activee : le son sera coupe automatiquement si plusieurs personnes sont detectees devant la camera."}
    return {"error": "Webcam indisponible (non detectee ou opencv non installe)."}


def stop_auto_mute() -> dict:
    """Desactive la surveillance webcam auto-mute et retablit le son si besoin."""
    monitor = WebcamMonitor.get()
    if not monitor.is_running():
        return {"success": True, "message": "Surveillance webcam deja inactive."}
    monitor.stop()
    return {"success": True, "message": "Surveillance webcam desactivee."}
