"""
Session Gemini Live (mode vocal temps reel) pour Amah.

Encapsule :
- la connexion bidirectionnelle audio (bidiGenerateContent),
- le pont microphone/haut-parleurs (sounddevice <-> asyncio),
- l'execution des outils Amah demandes par le modele (function calling).

Usage :
    session = GeminiLiveSession(
        api_key=...,
        on_status=lambda s: print("status:", s),
        on_user_text=lambda t: print("utilisateur:", t),
        on_reply_text=lambda t: print("amah:", t),
        on_tool=lambda name, args, result: print("outil:", name, args, result),
    )
    session.start()
    ...
    session.stop()
"""
import asyncio
import functools
import json
import queue
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path

import sounddevice as sd
from google import genai
from google.genai import types

from gemini_tools import get_tools, GEMINI_SYSTEM_INSTRUCTION
from tools import TOOL_FUNCTIONS

MODEL = "gemini-2.5-flash-native-audio-latest"

_LIVE_LOG = Path(__file__).parent / "live_debug.log"

def _log(msg):
    """Debug temporaire : trace le cycle de vie du Mode Live dans un fichier."""
    try:
        with open(_LIVE_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat(timespec='milliseconds')} {msg}\n")
    except Exception:
        pass

SEND_RATE    = 16000   # frequence d'echantillonnage attendue par Gemini en entree
RECEIVE_RATE = 24000   # frequence d'echantillonnage de l'audio renvoye par Gemini
CHUNK_SAMPLES = 1024   # taille des blocs lus depuis le micro


class GeminiLiveSession:
    """Session Live audio temps reel, executee dans un thread dedie."""

    def __init__(self, api_key, on_status=None, on_user_text=None,
                 on_reply_text=None, on_tool=None):
        self.api_key       = api_key
        self.on_status     = on_status     or (lambda s: None)
        self.on_user_text  = on_user_text  or (lambda t: None)
        self.on_reply_text = on_reply_text or (lambda t: None)
        self.on_tool       = on_tool       or (lambda name, args, result: None)

        self._thread = None
        self._loop   = None
        self._session = None
        self._stop_event = threading.Event()
        # Coupe le micro pendant que Amah parle (et juste apres) -- sans
        # annulation d'echo materielle, le micro reenregistre la voix sortie
        # par les haut-parleurs et Gemini se met a "repondre" a sa propre
        # voix en boucle.
        self._speaking = threading.Event()

    # ── Cycle de vie ─────────────────────────────────────────────────────────

    def start(self):
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_thread, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()

    def join(self, timeout=None):
        if self._thread:
            self._thread.join(timeout)

    def send_text(self, text: str) -> bool:
        """Envoie un message texte a Gemini comme un tour utilisateur complet
        (saisi au clavier, en plus/au lieu du micro). Thread-safe : peut etre
        appele depuis le thread UI tkinter."""
        if self._loop is None or self._session is None:
            return False

        async def _send():
            await self._session.send_client_content(
                turns=types.Content(role="user", parts=[types.Part(text=text)]),
                turn_complete=True,
            )

        asyncio.run_coroutine_threadsafe(_send(), self._loop)
        return True

    # ── Thread + boucle asyncio ──────────────────────────────────────────────

    def _run_thread(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        _log("_run_thread: demarrage")
        # La connexion Gemini Live se ferme parfois seule apres quelques
        # dizaines de secondes (1006 abnormal closure / 1011 keepalive ping
        # timeout) ou n'arrive pas a s'etablir (handshake timeout). Plutot
        # que de planter tout le Mode Live, on retente automatiquement avec
        # un backoff exponentiel -- l'utilisateur n'a pas besoin de
        # ressortir/rentrer en mode Live a la main.
        MAX_RETRIES = 4
        retries = 0
        backoff = 1.0
        try:
            while not self._stop_event.is_set():
                error, duration = self._loop.run_until_complete(self._main())
                if self._stop_event.is_set() or error is None:
                    break
                if duration > 10:
                    # La connexion a tenu un moment avant de tomber : on
                    # repart sur une serie fraiche de tentatives.
                    retries = 0
                    backoff = 1.0
                retries += 1
                if retries > MAX_RETRIES:
                    _log(f"_run_thread: abandon apres {retries - 1} reconnexion(s), "
                         f"derniere erreur: {error}")
                    self.on_status(f"Erreur Live : {error}")
                    break
                _log(f"_run_thread: reconnexion {retries}/{MAX_RETRIES} dans "
                     f"{backoff:.0f}s ({error})")
                self.on_status(f"Connexion interrompue -- reconnexion ({retries}/{MAX_RETRIES})...")
                waited = 0.0
                while waited < backoff and not self._stop_event.is_set():
                    time.sleep(0.2)
                    waited += 0.2
                backoff = min(backoff * 2, 15)
            _log("_run_thread: termine")
        except Exception as e:
            _log(f"_run_thread: EXCEPTION\n{traceback.format_exc()}")
            self.on_status(f"Erreur Live : {e}")
        finally:
            self._loop.close()
            self._loop = None

    async def _main(self):
        """Gere une tentative de connexion Live. Retourne (error, duration) :
        error est None si l'arret a ete demande par l'utilisateur (stop()),
        sinon le message de l'erreur qui a interrompu la connexion. duration
        est le temps (s) pendant lequel la session est restee connectee (0
        si la connexion n'a jamais ete etablie)."""
        client = genai.Client(api_key=self.api_key)
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=types.Content(
                parts=[types.Part(text=GEMINI_SYSTEM_INSTRUCTION)]
            ),
            tools=get_tools(),
            speech_config=types.SpeechConfig(
                language_code="fr-FR",
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Charon")
                ),
            ),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            # Sensibilite max : un micro avec un faible niveau d'entree peut
            # ne pas declencher la detection vocale par defaut de Gemini.
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_HIGH,
                ),
            ),
        )

        self.on_status("Connexion a Gemini Live...")
        error = None
        connected_at = None
        try:
            async with client.aio.live.connect(model=MODEL, config=config) as session:
                connected_at = time.monotonic()
                self._session = session
                self.on_status("Connecte -- a vous la parole")
                _log("_main: connecte, demarrage send/recv loops")

                send_task = asyncio.create_task(self._send_audio_loop(session))
                recv_task = asyncio.create_task(self._receive_loop(session))

                try:
                    while not self._stop_event.is_set():
                        if send_task.done() or recv_task.done():
                            _log(f"_main: boucle terminee (send.done={send_task.done()} "
                                 f"recv.done={recv_task.done()})")
                            break
                        await asyncio.sleep(0.1)
                finally:
                    send_task.cancel()
                    recv_task.cancel()
                    for name, t in (("send", send_task), ("recv", recv_task)):
                        try:
                            await t
                        except asyncio.CancelledError:
                            pass
                        except Exception as e:
                            _log(f"_main: {name}_task EXCEPTION\n{traceback.format_exc()}")
                            error = error or str(e)
        except Exception as e:
            _log(f"_main: connexion EXCEPTION\n{traceback.format_exc()}")
            error = error or str(e)

        self._session = None
        duration = (time.monotonic() - connected_at) if connected_at else 0.0
        _log(f"_main: termine (error={error!r} duration={duration:.1f}s)")
        if self._stop_event.is_set():
            self.on_status("Session Live fermee")
        return error, duration

    # ── Microphone -> Gemini ─────────────────────────────────────────────────

    async def _send_audio_loop(self, session):
        loop = asyncio.get_event_loop()
        # asyncio.Queue (et non queue.Queue) : un .get() bloquant sur une
        # queue.Queue, evalue avant d'etre passe a asyncio.wait_for, gele la
        # boucle d'evenements -- _receive_loop ne demarre alors jamais et
        # aucun audio n'est envoye a Gemini (mode Live "silencieux").
        audio_q: asyncio.Queue = asyncio.Queue()

        def _callback(indata, frames, time_info, status):
            loop.call_soon_threadsafe(audio_q.put_nowait, bytes(indata))

        stream = sd.RawInputStream(
            samplerate=SEND_RATE, channels=1, dtype="int16",
            blocksize=CHUNK_SAMPLES, callback=_callback,
        )
        _log(f"_send_audio_loop: ouverture micro device={stream.device}")
        with stream:
            _log("_send_audio_loop: micro demarre")
            while not self._stop_event.is_set():
                try:
                    chunk = await asyncio.wait_for(audio_q.get(), timeout=0.2)
                except asyncio.TimeoutError:
                    continue
                if self._speaking.is_set():
                    # Amah parle (ou vient de parler) : on n'envoie pas son
                    # propre echo au micro vers Gemini.
                    continue
                await session.send_realtime_input(
                    audio=types.Blob(data=chunk, mime_type=f"audio/pcm;rate={SEND_RATE}")
                )
        _log("_send_audio_loop: arret")

    # ── Gemini -> Haut-parleurs (AUDIO) + outils ─────────────────────────────

    async def _receive_loop(self, session):
        loop = asyncio.get_event_loop()
        play_q: queue.Queue = queue.Queue()
        stop_play = threading.Event()

        ECHO_HANGOVER   = 0.35
        PREBUFFER_CHUNKS = 3

        def _player():
            _log("_player: ouverture haut-parleur")
            try:
                with sd.RawOutputStream(samplerate=RECEIVE_RATE, channels=1, dtype="int16",
                                         latency="high") as out:
                    _log("_player: haut-parleur demarre")
                    n = 0
                    playback_end = 0.0
                    prebuffer: list = []
                    primed = False
                    while not stop_play.is_set():
                        try:
                            chunk = play_q.get(timeout=0.2)
                        except queue.Empty:
                            if (self._speaking.is_set()
                                    and time.monotonic() > playback_end + ECHO_HANGOVER):
                                self._speaking.clear()
                            continue
                        if chunk is None:
                            continue
                        if not primed:
                            prebuffer.append(chunk)
                            if len(prebuffer) < PREBUFFER_CHUNKS:
                                continue
                            primed = True
                            to_write, prebuffer = prebuffer, []
                        else:
                            to_write = [chunk]
                        for c in to_write:
                            self._speaking.set()
                            out.write(c)
                            duration = len(c) / (RECEIVE_RATE * 2)
                            playback_end = max(playback_end, time.monotonic()) + duration
                            n += 1
                            if n == 1:
                                _log("_player: premier chunk ecrit")
            except Exception as e:
                _log(f"_player: EXCEPTION\n{traceback.format_exc()}")
                self.on_status(f"Erreur Live (audio) : {e}")
            _log("_player: arret")

        player_thread = threading.Thread(target=_player, daemon=True)
        player_thread.start()

        user_chunks: list[str]  = []
        reply_chunks: list[str] = []

        try:
            while not self._stop_event.is_set():
                async for msg in session.receive():
                    if self._stop_event.is_set():
                        break

                    sc = msg.server_content
                    if sc:
                        if sc.input_transcription and sc.input_transcription.text:
                            user_chunks.append(sc.input_transcription.text)
                            self.on_user_text("".join(user_chunks))
                        if sc.output_transcription and sc.output_transcription.text:
                            reply_chunks.append(sc.output_transcription.text)
                            self.on_reply_text("".join(reply_chunks))
                        if sc.model_turn:
                            for part in sc.model_turn.parts:
                                if part.inline_data and part.inline_data.data:
                                    play_q.put_nowait(part.inline_data.data)
                        if sc.interrupted:
                            while not play_q.empty():
                                try:
                                    play_q.get_nowait()
                                except queue.Empty:
                                    break
                        if sc.turn_complete:
                            user_chunks  = []
                            reply_chunks = []
                            self.on_status("ECOUTE")

                    if msg.tool_call:
                        for fc in msg.tool_call.function_calls:
                            result = await loop.run_in_executor(
                                None, self._execute_tool, fc.name, fc.args or {}
                            )
                            self.on_tool(fc.name, fc.args or {}, result)
                            await session.send_tool_response(
                                function_responses=[types.FunctionResponse(
                                    id=fc.id, name=fc.name, response={"result": result},
                                )]
                            )
        finally:
            stop_play.set()

    # ── Execution d'un outil Amah ────────────────────────────────────────────

    def _execute_tool(self, name, args):
        func = TOOL_FUNCTIONS.get(name)
        if not func:
            return {"error": f"Outil inconnu : {name}"}
        try:
            result = func(**args)
        except Exception as e:
            result = {"error": str(e)}
        # Normalise en types JSON-safe (datetime, Path, etc.)
        return json.loads(json.dumps(result, ensure_ascii=False, default=str))
