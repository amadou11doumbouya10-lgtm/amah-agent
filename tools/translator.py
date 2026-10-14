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


_CHUNK = 4500  # limite safe GoogleTranslator (max 5000 chars)

# Google (deep-translator) bloque regulierement l'adresse IP ("too many
# requests") : repli sur un modele Groq. Apres un refus, Google n'est plus
# sollicite pendant _GOOGLE_PAUSE secondes pour ne pas perdre ~3s par appel.
_LLM_MODEL = "openai/gpt-oss-20b"
_GOOGLE_PAUSE = 600
_google_blocked_until = 0.0

# Noms lisibles des codes, pour le prompt du modele et detect_language
_NOMS = {
    "fr": "français", "en": "anglais", "es": "espagnol", "ar": "arabe",
    "de": "allemand", "it": "italien", "pt": "portugais", "zh-CN": "chinois",
    "ja": "japonais", "ru": "russe", "nl": "néerlandais", "tr": "turc", "ko": "coréen",
}


def _chunks(text: str) -> list:
    """Decoupe par paragraphes pour eviter de couper au milieu d'une phrase."""
    if len(text) <= _CHUNK:
        return [text]
    parts, current = [], ""
    for line in text.splitlines(keepends=True):
        if len(current) + len(line) > _CHUNK:
            if current:
                parts.append(current)
            current = line
        else:
            current += line
    if current:
        parts.append(current)
    return parts


def _translate_google(parts: list, to: str, frm: str) -> str:
    from deep_translator import GoogleTranslator
    translator = GoogleTranslator(source=frm, target=to)
    return "".join(translator.translate(p) for p in parts)


def _translate_llm(parts: list, to: str) -> str:
    from groq_client import GroqClient
    target = _NOMS.get(to, to)
    out = []
    for part in parts:
        resp = GroqClient.get().chat(
            [
                {"role": "system", "content": (
                    f"Tu es un traducteur professionnel. Traduis le texte de l'utilisateur en {target}. "
                    "Réponds uniquement avec la traduction, sans commentaire, sans guillemets ajoutés, "
                    "en conservant la mise en forme (paragraphes, listes)."
                )},
                {"role": "user", "content": part},
            ],
            model=_LLM_MODEL,
            max_tokens=min(8192, len(part) + 1024),
            temperature=0.2,
            reasoning_effort="low",
        )
        out.append((resp.choices[0].message.content or "").strip())
    return "\n\n".join(out) if len(out) > 1 else out[0]


def translate(text: str, to_lang: str = "fr", from_lang: str = "auto") -> dict:
    """
    Traduit un texte vers n'importe quelle langue.
    to_lang : code langue (fr, en, es, ar...) ou nom complet (français, anglais...)
    Les textes longs sont decoupes automatiquement en morceaux de 4500 caracteres.
    Google Traduction d'abord, modele Groq en repli si Google refuse.
    """
    global _google_blocked_until
    import time

    text = str(text or "")
    if not text.strip():
        return {"error": "Texte vide à traduire."}
    to  = LANGS.get(to_lang.lower(),   to_lang.lower())
    frm = LANGS.get(from_lang.lower(), from_lang.lower())
    parts = _chunks(text)

    result, service, google_error = None, "google", None
    if time.time() >= _google_blocked_until:
        try:
            result = _translate_google(parts, to, frm)
        except Exception as e:
            google_error = str(e)
            _google_blocked_until = time.time() + _GOOGLE_PAUSE
    if not result:
        try:
            result, service = _translate_llm(parts, to), "ia"
        except Exception as e:
            detail = f" (Google : {google_error[:120]})" if google_error else ""
            return {"error": f"Traduction impossible : {e}{detail}"}

    return {
        "success":  True,
        "original": text[:200] + "..." if len(text) > 200 else text,
        "traduit":  result,
        "vers":     to,
        "service":  service,
    }


def detect_language(text: str) -> dict:
    """Détecte la langue d'un texte (modele Groq : la detection gratuite de
    deep-translator exige une cle detectlanguage.com et ne marchait jamais)."""
    import re
    try:
        from groq_client import GroqClient
        resp = GroqClient.get().chat(
            [
                {"role": "system", "content": (
                    "Identifie la langue du texte de l'utilisateur. Réponds uniquement par son code "
                    "ISO 639-1 en minuscules (ex : fr, en, es, ar, wo, ff), rien d'autre."
                )},
                {"role": "user", "content": str(text or "")[:1000]},
            ],
            model=_LLM_MODEL,
            max_tokens=256,
            temperature=0,
            reasoning_effort="low",
        )
        answer = (resp.choices[0].message.content or "").strip().lower()
        match = re.search(r"\b([a-z]{2,3})(?:-[a-z]{2})?\b", answer)
        if not match:
            return {"error": f"Langue non reconnue (réponse : {answer[:40]!r})"}
        lang = match.group(1)
        return {"success": True, "langue": lang, "nom": _NOMS.get(lang, lang)}
    except Exception as e:
        return {"error": str(e)}
