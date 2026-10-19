"""Client Groq partage — singleton avec rotation automatique des cles + retry backoff.

Avant ce module, gui.py gerait sa propre rotation de cles tandis que planner.py et
screen_vision.py creaient chacun un client Groq independant en piochant directement
dans .env : si la cle 1 etait limitee (429), gui.py basculait sur la cle 2 mais les
deux outils continuaient d'echouer silencieusement avec la cle 1. Tout le monde
passe maintenant par GroqClient.get().chat(...) pour partager la meme rotation.
"""
import os
import re
import json
import time
import socket
import threading
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()


def _new_groq(api_key: str):
    """Client Groq. Le paquet groq (~0,7 s à importer) n'est chargé qu'ici :
    plus au démarrage d'Amah (gui.py le précharge une fois la fenêtre affichée)."""
    from groq import Groq
    return Groq(api_key=api_key, max_retries=0)

_DELAYS = [1, 2, 4]

_FAILED_GENERATION_RE = re.compile(r"<function=(\w+)\s*(.*)</function>\s*$", re.DOTALL)


def repair_tool_use_failed(e: Exception):
    """Repare l'erreur Groq 400 'tool_use_failed'.

    Llama 3.3 70B emet parfois un pseudo-appel texte
    '<function=NOM{"arg": "valeur"}</function>' (au lieu d'un tool_calls
    structure). Groq rejette avec une erreur 400 AVANT de renvoyer le moindre
    objet response. Compatible avec le format Groq SDK (e.body) et LiteLLM
    (message texte contenant le JSON).

    Renvoie (nom_outil, args_dict) si l'erreur peut etre reparee, sinon None.
    """
    err = None

    # Format direct Groq SDK : e.body["error"]
    body = getattr(e, "body", None)
    if isinstance(body, dict):
        err = body.get("error")

    # Format LiteLLM/OpenAI SDK : JSON embarque dans e.message
    if not isinstance(err, dict):
        msg = str(getattr(e, "message", "") or str(e))
        # Extrait le JSON Groq par comptage de profondeur d'accolades (pas une
        # regex gourmande) : le message LiteLLM contient du texte APRES le
        # JSON ("\n. Received Model Group=...") qui ferait capturer une
        # regex r'\{.*\}' jusqu'a la derniere accolade du message entier,
        # produisant un JSON invalide.
        marker = "GroqException - {"
        i = msg.find(marker)
        if i != -1:
            start = i + len(marker) - 1  # position du '{' d'ouverture
            depth = 0
            end = None
            for j in range(start, len(msg)):
                if msg[j] == "{":
                    depth += 1
                elif msg[j] == "}":
                    depth -= 1
                    if depth == 0:
                        end = j + 1
                        break
            if end is not None:
                try:
                    parsed = json.loads(msg[start:end])
                    err = parsed.get("error")
                except Exception:
                    pass

    if not isinstance(err, dict) or err.get("code") != "tool_use_failed":
        return None

    failed = (err.get("failed_generation") or "").strip()

    # Format gpt-oss : JSON brut {"name": "...", "arguments": {...}}
    if failed.startswith("{"):
        try:
            data, _ = json.JSONDecoder().raw_decode(failed)
        except Exception:
            return None
        name, args = data.get("name"), data.get("arguments")
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception:
                return None
        if isinstance(name, str) and isinstance(args, dict):
            return name, args
        return None

    # Format Llama : <function=NOM{"arg": "valeur"}</function>
    m = _FAILED_GENERATION_RE.match(failed)
    if not m:
        return None

    name, rest = m.group(1), m.group(2).lstrip(">").strip()
    try:
        args, _ = json.JSONDecoder().raw_decode(rest)
    except Exception:
        return None
    if not isinstance(args, dict):
        return None
    return name, args


def _proxy_reachable(url: str) -> bool:
    """Sonde rapide d'un proxy LiteLLM local.

    Sous Windows une connexion refusee prend ~2s par adresse (localhost = ::1
    puis 127.0.0.1) : sans cette sonde, chaque session perdait plusieurs
    secondes au premier appel quand LITELLM_URL est defini mais le proxy eteint.
    """
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if host not in ("localhost", "127.0.0.1", "::1"):
        return True  # proxy distant : le repli normal gere l'erreur
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    # IPv4 d'abord : LiteLLM ecoute generalement sur 0.0.0.0
    candidates = ["127.0.0.1", "::1"] if host == "localhost" else [host]
    for candidate in candidates:
        try:
            socket.create_connection((candidate, port), timeout=0.3).close()
            return True
        except OSError:
            continue
    return False


class GroqClient:
    _instance = None
    _instance_lock = threading.Lock()

    def __init__(self):
        litellm_url = os.getenv("LITELLM_URL", "").strip()
        if litellm_url and _proxy_reachable(litellm_url):
            # Mode dev : LiteLLM proxy local (quota illimite, failover multi-providers)
            # Invisible pour les clients — ils n'ont pas LITELLM_URL dans leur .env
            import httpx
            from openai import OpenAI as _OpenAI
            self._use_litellm = True
            # max_retries=0 + connexion courte : si le proxy n'est pas lance, le
            # SDK OpenAI retentait 3 fois une connexion refusee (~16s perdues
            # au premier appel sous Windows) avant le repli sur Groq.
            self._litellm    = _OpenAI(
                base_url=litellm_url,
                api_key=os.getenv("LITELLM_KEY", "dev"),
                max_retries=0,
                timeout=httpx.Timeout(60.0, connect=2.0),
            )
            self._keys        = ["litellm"]
            self._index       = 0
            self._client      = None
            self._client_lock = threading.Lock()
            return

        self._use_litellm = False
        self._keys = [k for k in [
            os.getenv("GROQ_API_KEY"),
            os.getenv("GROQ_API_KEY_2"),
            os.getenv("GROQ_API_KEY_3"),
        ] if k and not k.startswith("AJOUTER")]
        if not self._keys:
            raise RuntimeError("GROQ_API_KEY introuvable dans le fichier .env")
        self._index       = 0
        self._client      = None          # créé au premier appel (ou par warm_up)
        self._client_lock = threading.Lock()

    def _ensure_client(self):
        with self._client_lock:
            if self._client is None and not getattr(self, "_use_litellm", False):
                self._client = _new_groq(self._keys[self._index])
            return self._client

    def warm_up(self):
        """Prépare le client en arrière-plan pour que le 1er message ne paie pas
        l'import de groq et la connexion sécurisée."""
        try:
            self._ensure_client()
        except Exception:
            pass

    @classmethod
    def get(cls) -> "GroqClient":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @property
    def backend(self) -> str:
        """Retourne 'LiteLLM' ou 'Groq' selon le mode actif."""
        return "LiteLLM" if getattr(self, "_use_litellm", False) else "Groq"

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
        self._client = _new_groq(self._keys[self._index])
        return True

    def chat(self, messages, model, tools=None, tool_choice=None, on_status=None, **kwargs):
        """Appel au modèle, noté dans le journal de session (tools/journal.py)."""
        started = time.time()
        response = self._chat(messages, model, tools=tools, tool_choice=tool_choice,
                              on_status=on_status, **kwargs)
        from tools import journal
        if journal.enabled():
            usage = getattr(response, "usage", None)
            journal.ia(model, time.time() - started, getattr(usage, "total_tokens", None))
        return response

    def _chat(self, messages, model, tools=None, tool_choice=None, on_status=None, **kwargs):
        """Appel chat.completions.create avec rotation de cles + retry backoff (1/2/4s).

        on_status(text: str) : callback optionnel (ex: mise a jour de la barre d'etat
        tkinter via root.after) pour informer l'utilisateur d'une rotation/attente.
        """
        params = dict(model=model, messages=messages, **kwargs)
        if tools:
            params["tools"]       = tools
            params["tool_choice"] = tool_choice or "auto"

        # Mode LiteLLM : failover gere par le proxy, on appelle directement
        # Si le proxy n'est pas lance (Connection refused), repli silencieux sur Groq.
        if getattr(self, "_use_litellm", False):
            for attempt in range(len(_DELAYS)):
                try:
                    return self._litellm.chat.completions.create(**params)
                except Exception as e:
                    err = str(e)
                    import httpx
                    proxy_down = isinstance(e.__cause__, (httpx.ConnectError, httpx.ConnectTimeout))
                    if proxy_down or "connection" in err.lower() or "refused" in err.lower() or "connect" in err.lower():
                        # LiteLLM pas demarre — on repasse sur Groq direct silencieusement
                        self._use_litellm = False
                        self._keys = [k for k in [
                            os.getenv("GROQ_API_KEY"),
                            os.getenv("GROQ_API_KEY_2"),
                            os.getenv("GROQ_API_KEY_3"),
                        ] if k and not k.startswith("AJOUTER")]
                        if not self._keys:
                            raise RuntimeError("LiteLLM non disponible et aucune cle Groq dans .env")
                        self._index  = 0
                        self._client = _new_groq(self._keys[0])
                        self._client_lock = threading.Lock()
                        break  # sort de la boucle LiteLLM, tombe sur Groq ci-dessous
                    if "503" in err or "timeout" in err.lower():
                        if on_status:
                            on_status("LiteLLM — attente avant nouvelle tentative...")
                        time.sleep(_DELAYS[attempt])
                    elif "429" in err:
                        # LiteLLM a deja essaye tous ses backends — inutile d'attendre
                        raise RuntimeError("LiteLLM : tous les providers sont limites (429)")
                    else:
                        raise
            if getattr(self, "_use_litellm", False):
                raise RuntimeError("LiteLLM proxy : echec apres plusieurs tentatives")

        keys_tried = 0
        waits = 0
        for _ in range((len(_DELAYS) + 1) * len(self._keys)):
            client = self._ensure_client()
            try:
                return client.chat.completions.create(**params)
            except Exception as e:
                err      = str(e)
                is_daily = "TPD" in err
                is_limit = "429" in err or "rate_limit" in err or is_daily or "TPM" in err

                if is_limit:
                    with self._client_lock:
                        switched = keys_tried < len(self._keys) - 1 and self._next_key()
                    if switched:
                        keys_tried += 1
                        if on_status:
                            on_status(f"Cle {self._index + 1}/{len(self._keys)} — limite atteinte, rotation...")
                        continue
                    # Toutes les cles epuisees : fail immediat pour quota journalier,
                    # courte attente pour rate-limit par minute puis nouveau tour de
                    # rotation (une autre cle a pu se liberer entre-temps).
                    if is_daily:
                        raise RuntimeError("Quota journalier Groq epuise sur toutes les cles")
                    if waits >= len(_DELAYS):
                        raise RuntimeError("Toutes les cles Groq sont limitees (429) — reessaie dans une minute")
                    delay = _DELAYS[waits]
                    waits += 1
                    if on_status:
                        on_status(f"Toutes les cles limitees — attente {delay}s...")
                    time.sleep(delay)
                    keys_tried = 0
                    with self._client_lock:
                        self._next_key()
                elif ("503" in err or "timeout" in err.lower() or "timed out" in err.lower()
                      or "connection" in err.lower()):
                    # max_retries=0 sur le SDK : les coupures reseau passageres
                    # (WinError 10054, APIConnectionError) sont retentees ici.
                    if waits >= len(_DELAYS):
                        raise
                    if on_status:
                        on_status("Reponse lente — nouvelle tentative...")
                    time.sleep(_DELAYS[waits])
                    waits += 1
                else:
                    raise

        raise RuntimeError("Echec Groq apres plusieurs tentatives (cles et backoff epuises)")
