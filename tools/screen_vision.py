import os
import io
import base64


def _get_groq_key() -> str:
    """Retourne la première clé Groq disponible."""
    for k in ["GROQ_API_KEY", "GROQ_API_KEY_2", "GROQ_API_KEY_3"]:
        v = os.getenv(k)
        if v and not v.startswith("AJOUTER"):
            return v
    return None


def analyze_screen(question: str = "Decris precisement ce que tu vois sur cet ecran.") -> dict:
    """Capture l'ecran complet et l'analyse par IA visuelle (Groq llama-3.2-vision).
    Utilisation : que vois-tu sur mon ecran ? / lis ce texte / analyse cette fenetre."""
    try:
        from PIL import ImageGrab
        from groq import Groq

        key = _get_groq_key()
        if not key:
            return {"error": "Cle API Groq introuvable dans .env"}

        # Capture + redimensionnement pour limiter les tokens
        img = ImageGrab.grab()
        img.thumbnail((1280, 720))

        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=82)
        b64 = base64.b64encode(buf.getvalue()).decode()

        client = Groq(api_key=key)
        resp = client.chat.completions.create(
            model="llama-3.2-11b-vision-preview",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    {"type": "text", "text": question},
                ]
            }],
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
