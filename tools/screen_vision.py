import io
import base64

from groq_client import GroqClient


def analyze_screen(question: str = "Decris precisement ce que tu vois sur cet ecran.") -> dict:
    """Capture l'ecran complet et l'analyse par IA visuelle (Groq llama-4-scout, multimodal).
    Utilisation : que vois-tu sur mon ecran ? / lis ce texte / analyse cette fenetre."""
    try:
        from PIL import ImageGrab

        # Capture + redimensionnement pour limiter les tokens
        img = ImageGrab.grab()
        img.thumbnail((1280, 720))

        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=82)
        b64 = base64.b64encode(buf.getvalue()).decode()

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
        }
    except ImportError as e:
        return {"error": f"Dependance manquante: {e} — verifie Pillow et groq"}
    except Exception as e:
        return {"error": str(e)}
