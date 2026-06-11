import io
import base64
import tempfile
import concurrent.futures
from pathlib import Path

from groq_client import GroqClient
from tools.webcam import read_frame

_PREVIEW_PATH = Path(tempfile.gettempdir()) / "amah_webcam_last.jpg"


def _capture_and_ask(question: str) -> dict:
    import cv2
    from PIL import Image

    frame = read_frame()
    if frame is None:
        return {"error": "Webcam introuvable ou deja utilisee par une autre application."}

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(rgb)
    img.thumbnail((1280, 720))

    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=82)
    b64 = base64.b64encode(buf.getvalue()).decode()
    img.save(_PREVIEW_PATH, format='JPEG', quality=82)

    client = GroqClient.get()
    resp = client.chat(
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                {"type": "text", "text": question},
            ]
        }],
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        max_tokens=1024,
    )
    return {
        "success":   True,
        "question":  question,
        "analyse":   resp.choices[0].message.content,
        "resolution": f"{img.width}x{img.height}",
        "image_path": str(_PREVIEW_PATH),
    }


def analyze_webcam(question: str = "Decris precisement ce que tu vois.") -> dict:
    """Capture une image via la webcam et l'analyse par IA visuelle (Groq llama-4-scout, multimodal).
    Utilisation : qui est devant la camera ? / que vois-tu via la webcam ? / decris ce que tu vois devant toi."""
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(_capture_and_ask, question)
        try:
            return future.result(timeout=15)
        except concurrent.futures.TimeoutError:
            return {"error": "Webcam : delai depasse (15s) -- capture ou analyse trop lente."}
    except ImportError as e:
        return {"error": f"Dependance manquante: {e} -- verifie opencv-python-headless et Pillow"}
    except Exception as e:
        return {"error": str(e)}
    finally:
        executor.shutdown(wait=False)
