import sys
from pathlib import Path
from datetime import datetime

if getattr(sys, 'frozen', False):
    DEFAULT_PATH = str(Path(sys.executable).parent)
else:
    DEFAULT_PATH = str(Path.home() / "Documents")


def screenshot_full(path: str = None) -> dict:
    """Capture l'intégralité de l'écran (bureau + fenêtres ouvertes)."""
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()

        if not path:
            ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = str(Path.home() / "Documents" / f"screenshot_{ts}.png")

        img.save(path)
        return {
            "success":     True,
            "fichier":     path,
            "resolution":  f"{img.width}x{img.height}",
        }
    except ImportError:
        return {"error": "Pillow manquant — lance : pip install pillow"}
    except Exception as e:
        return {"error": str(e)}


def resize_image(path: str, width: int = None, height: int = None,
                 output: str = None) -> dict:
    """Redimensionne une image en conservant les proportions si une seule dimension est donnée."""
    try:
        from PIL import Image
        p   = Path(path).expanduser()
        img = Image.open(str(p))
        ow, oh = img.size

        if width and height:
            new_size = (width, height)
        elif width:
            new_size = (width, int(oh * width / ow))
        elif height:
            new_size = (int(ow * height / oh), height)
        else:
            return {"error": "Fournis au moins width ou height."}

        img_resized = img.resize(new_size, Image.LANCZOS)

        if not output:
            output = str(p.parent / f"{p.stem}_resized{p.suffix}")

        img_resized.save(output)
        return {
            "success":       True,
            "original":      f"{ow}x{oh}",
            "nouveau":       f"{new_size[0]}x{new_size[1]}",
            "fichier":       output,
        }
    except ImportError:
        return {"error": "Pillow manquant — lance : pip install pillow"}
    except Exception as e:
        return {"error": str(e)}


def get_image_info(path: str) -> dict:
    """Retourne les métadonnées d'une image (taille, format, mode couleur)."""
    try:
        from PIL import Image
        p   = Path(path).expanduser()
        img = Image.open(str(p))
        return {
            "success":  True,
            "fichier":  p.name,
            "format":   img.format,
            "mode":     img.mode,
            "largeur":  img.width,
            "hauteur":  img.height,
            "taille_fichier": f"{p.stat().st_size / 1024:.1f} Ko",
        }
    except Exception as e:
        return {"error": str(e)}


def convert_image(path: str, to_format: str, output: str = None) -> dict:
    """Convertit une image vers un autre format (PNG, JPEG, BMP, WEBP...)."""
    try:
        from PIL import Image
        p   = Path(path).expanduser()
        img = Image.open(str(p))
        fmt = to_format.upper().replace("JPG", "JPEG")

        if not output:
            output = str(p.parent / f"{p.stem}.{to_format.lower()}")

        if fmt == "JPEG" and img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        img.save(output, format=fmt)
        return {"success": True, "original": p.name, "converti": output, "format": fmt}
    except Exception as e:
        return {"error": str(e)}


def list_processes(top: int = 15) -> dict:
    """Liste les processus Windows actifs triés par utilisation CPU."""
    try:
        import psutil
        procs = []
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                procs.append(p.info)
            except Exception:
                pass

        # Tri par CPU puis mémoire
        procs.sort(key=lambda x: (x.get('cpu_percent') or 0), reverse=True)
        top_procs = [
            {
                "pid":    p['pid'],
                "nom":    p['name'],
                "cpu":    f"{p.get('cpu_percent', 0):.1f}%",
                "ram":    f"{p.get('memory_percent', 0):.1f}%",
            }
            for p in procs[:top]
        ]
        return {"success": True, "total": len(procs), "top": top_procs}
    except Exception as e:
        return {"error": str(e)}


def get_network_info() -> dict:
    """Retourne l'adresse IP locale et vérifie la connectivité internet."""
    try:
        import socket
        import subprocess

        # IP locale
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()

        # Test internet (ping Google)
        result = subprocess.run(
            ["ping", "-n", "1", "-w", "2000", "8.8.8.8"],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        internet = result.returncode == 0

        return {
            "success":   True,
            "ip_locale": local_ip,
            "internet":  "Connecté" if internet else "Hors ligne",
        }
    except Exception as e:
        return {"error": str(e)}
