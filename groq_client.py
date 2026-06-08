"""Client Groq partage — singleton avec rotation automatique des cles + retry backoff.

Avant ce module, gui.py gerait sa propre rotation de cles tandis que planner.py et
screen_vision.py creaient chacun un client Groq independant en piochant directement
dans .env : si la cle 1 etait limitee (429), gui.py basculait sur la cle 2 mais les
deux outils continuaient d'echouer silencieusement avec la cle 1. Tout le monde
passe maintenant par GroqClient.get().chat(...) pour partager la meme rotation.
"""
import os
import time
import threading

from groq import Groq

_DELAYS = [1, 2, 4]


class GroqClient:
    _instance = None
    _instance_lock = threading.Lock()

    def __init__(self):
        self._keys = [k for k in [
            os.getenv("GROQ_API_KEY"),
            os.getenv("GROQ_API_KEY_2"),
            os.getenv("GROQ_API_KEY_3"),
        ] if k and not k.startswith("AJOUTER")]
        if not self._keys:
            raise RuntimeError("GROQ_API_KEY introuvable dans le fichier .env")
        self._index       = 0
        self._client      = Groq(api_key=self._keys[0])
        self._client_lock = threading.Lock()

    @classmethod
    def get(cls) -> "GroqClient":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @property
    def key_index(self) -> int:
        return self._index

    @property
    def key_count(self) -> int:
        return len(self._keys)

    def _next_key(self) -> bool:
        if len(self._keys) <= 1:
            return False
        self._index = (self._index + 1) % len(self._keys)
        self._client = Groq(api_key=self._keys[self._index])
        return True

    def chat(self, messages, model, tools=None, tool_choice=None, on_status=None, **kwargs):
        """Appel chat.completions.create avec rotation de cles + retry backoff (1/2/4s).

        on_status(text: str) : callback optionnel (ex: mise a jour de la barre d'etat
        tkinter via root.after) pour informer l'utilisateur d'une rotation/attente.
        """
        params = dict(model=model, messages=messages, **kwargs)
        if tools:
            params["tools"]       = tools
            params["tool_choice"] = tool_choice or "auto"

        keys_tried = 0
        for attempt in range(len(_DELAYS) * len(self._keys)):
            with self._client_lock:
                client = self._client
            try:
                return client.chat.completions.create(**params)
            except Exception as e:
                err      = str(e)
                is_limit = "429" in err or "rate_limit" in err or "TPD" in err or "TPM" in err

                if is_limit:
                    with self._client_lock:
                        switched = keys_tried < len(self._keys) - 1 and self._next_key()
                    if switched:
                        keys_tried += 1
                        if on_status:
                            on_status(f"Cle {self._index + 1}/{len(self._keys)} — limite atteinte, rotation...")
                        continue
                    delay = _DELAYS[min(attempt, len(_DELAYS) - 1)]
                    if on_status:
                        on_status(f"Toutes les cles limitees — attente {delay}s...")
                    time.sleep(delay)
                elif "503" in err:
                    time.sleep(_DELAYS[min(attempt, len(_DELAYS) - 1)])
                elif "timeout" in err.lower() or "timed out" in err.lower():
                    # Un timeout est presque toujours un alea reseau passager
                    # (recherche web lente, Groq momentanement lent...) -- on
                    # retente avec backoff au lieu de remonter direct une
                    # erreur a l'utilisateur des le premier coup.
                    if on_status:
                        on_status("Reponse lente — nouvelle tentative...")
                    time.sleep(_DELAYS[min(attempt, len(_DELAYS) - 1)])
                else:
                    raise

        raise RuntimeError("Echec Groq apres plusieurs tentatives (cles et backoff epuises)")
