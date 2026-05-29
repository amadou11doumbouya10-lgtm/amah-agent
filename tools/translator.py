LANGS = {
    "français": "fr", "french": "fr",
    "anglais": "en", "english": "en",
    "espagnol": "es", "spanish": "es",
    "arabe": "ar", "arabic": "ar",
    "allemand": "de", "german": "de",
    "italien": "it", "italian": "it",
    "portugais": "pt", "portuguese": "pt",
    "chinois": "zh-CN", "chinese": "zh-CN",
    "japonais": "ja", "japanese": "ja",
    "russe": "ru", "russian": "ru",
    "néerlandais": "nl", "dutch": "nl",
    "turc": "tr", "turkish": "tr",
    "coréen": "ko", "korean": "ko",
}


def translate(text: str, to_lang: str = "fr", from_lang: str = "auto") -> dict:
    """
    Traduit un texte vers n'importe quelle langue.
    to_lang : code langue (fr, en, es, ar...) ou nom complet (français, anglais...)
    """
    try:
        from deep_translator import GoogleTranslator

        to   = LANGS.get(to_lang.lower(),   to_lang.lower())
        frm  = LANGS.get(from_lang.lower(), from_lang.lower())

        result = GoogleTranslator(source=frm, target=to).translate(text)
        return {
            "success":  True,
            "original": text,
            "traduit":  result,
            "vers":     to,
        }
    except ImportError:
        return {"error": "deep-translator manquant — lance : pip install deep-translator"}
    except Exception as e:
        return {"error": str(e)}


def detect_language(text: str) -> dict:
    """Détecte la langue d'un texte."""
    try:
        from deep_translator import GoogleTranslator, single_detection
        lang = single_detection(text, api_key=None)
        noms = {v: k for k, v in LANGS.items()}
        return {"success": True, "langue": lang, "nom": noms.get(lang, lang)}
    except Exception as e:
        return {"error": str(e)}
