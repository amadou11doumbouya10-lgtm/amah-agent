import sys
from pathlib import Path
from datetime import datetime

if getattr(sys, 'frozen', False):
    DEFAULT_PATH = str(Path(sys.executable).parent)
else:
    DEFAULT_PATH = str(Path.home() / "Documents")


def create_qrcode(text: str, output: str = None, size: int = 10) -> dict:
    """
    Génère un QR code depuis un texte, URL ou données.
    size : taille des cases (1-20, défaut 10)
    """
    try:
        import qrcode
        from PIL import Image

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=size,
            border=4,
        )
        qr.add_data(text)
        qr.make(fit=True)

        img = qr.make_image(fill_color="#1a1a17", back_color="#f5f0e8")

        if not output:
            ts     = datetime.now().strftime("%Y%m%d_%H%M%S")
            output = str(Path(DEFAULT_PATH) / f"qrcode_{ts}.png")

        img.save(output)
        return {
            "success": True,
            "fichier": output,
            "contenu": text[:80],
            "taille":  f"{img.size[0]}x{img.size[1]} px",
        }
    except ImportError:
        return {"error": "qrcode manquant — lance : pip install qrcode[pil]"}
    except Exception as e:
        return {"error": str(e)}
