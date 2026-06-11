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

import sounddevice as sd
from google import genai
from google.genai import types

from gemini_tools import get_tools, GEMINI_SYSTEM_INSTRUCTION
from tools import TOOL_FUNCTIONS

MODEL = "gemini-2.5-flash-native-audio-latest"

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
        self._stop_event = threading.Event()

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

    # ── Thread + boucle asyncio ──────────────────────────────────────────────

    def _run_thread(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._main())
        except Exception as e:
            self.on_status(f"Erreur Live : {e}")
        finally:
            self._loop.close()
            self._loop = None

    async def _main(self):
        client = genai.Client(api_key=self.api_key)
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=types.Content(
                parts=[types.Part(text=GEMINI_SYSTEM_INSTRUCTION)]
            ),
            tools=get_tools(),
            speech_config=types.SpeechConfig(language_code="fr-FR"),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            input_audio_transcription=types.AudioTranscriptionConfig(),
        )

        self.on_status("Connexion a Gemini Live...")
        async with client.aio.live.connect(model=MODEL, config=config) as session:
            self.on_status("Connecte -- a vous la parole")

            send_task = asyncio.create_task(self._send_audio_loop(session))
            recv_task = asyncio.create_task(self._receive_loop(session))

            try:
                while not self._stop_event.is_set():
                    if send_task.done() or recv_task.done():
                        break
                    await asyncio.sleep(0.1)
            finally:
                send_task.cancel()
                recv_task.cancel()
                for t in (send_task, recv_task):
                    try:
                        await t
                    except (asyncio.CancelledError, Exception):
                        pass

        self.on_status("Session Live fermee")

    # ── Microphone -> Gemini ─────────────────────────────────────────────────

    async def _send_audio_loop(self, session):
        loop = asyncio.get_event_loop()
        audio_q: queue.Queue = queue.Queue()

        def _callback(indata, frames, time_info, status):
            loop.call_soon_threadsafe(audio_q.put_nowait, bytes(indata))

        stream = sd.RawInputStream(
            samplerate=SEND_RATE, channels=1, dtype="int16",
            blocksize=CHUNK_SAMPLES, callback=_callback,
        )
        with stream:
            while not self._stop_event.is_set():
                try:
                    chunk = await asyncio.wait_for(audio_q.get(), timeout=0.2)
                except asyncio.TimeoutError:
                    continue
                await session.send_realtime_input(
                    audio=types.Blob(data=chunk, mime_type=f"audio/pcm;rate={SEND_RATE}")
                )

    # ── Gemini -> Haut-parleurs + outils ─────────────────────────────────────

    async def _receive_loop(self, session):
        loop = asyncio.get_event_loop()
        play_q: queue.Queue = queue.Queue()
        stop_play = threading.Event()

        def _player():
            with sd.RawOutputStream(samplerate=RECEIVE_RATE, channels=1, dtype="int16") as out:
                while not stop_play.is_set():
                    try:
                        chunk = play_q.get(timeout=0.2)
                    except queue.Empty:
                        continue
                    if chunk is None:
                        continue
                    out.write(chunk)

        player_thread = threading.Thread(target=_player, daemon=True)
        player_thread.start()

        user_chunks: list[str] = []
        reply_chunks: list[str] = []

        try:
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
                        # L'utilisateur a coupe la parole : on vide la file audio
                        while not play_q.empty():
                            try:
                                play_q.get_nowait()
                            except queue.Empty:
                                break
                    if sc.turn_complete:
                        user_chunks = []
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
