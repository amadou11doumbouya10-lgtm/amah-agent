import io
import base64

from groq_client import GroqClient

VISION_MODEL = "qwen/qwen3.8-27b"


def analyze_screen(question: str = "Décris précisément ce que tu vois sur cet écran.") -> dict:
    """Capture l'écran et l'analyse avec le modèle multimodal actif de Groq."""
    try:
        from PIL import ImageGrab

        img = ImageGrab.grab()
        img.thumbnail((1280, 720))

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=82)
        b64 = base64.b64encode(buf.getvalue()).decode()

        client = GroqClient.get()
        resp = client.chat(
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    {"type": "text", "text": question},
                ],
            }],
            model=VISION_MODEL,
            max_tokens=1024,
            reasoning_effort="none",
        )
        return {
            "success": True,
            "question": question,
            "analyse": resp.choices[0].message.content,
            "resolution": f"{img.width}x{img.height}",
            "modele": VISION_MODEL,
        }
    except ImportError as e:
        return {"error": f"Dépendance manquante: {e} — vérifie Pillow et Groq"}
    except Exception as e:
        return {"error": str(e)}
