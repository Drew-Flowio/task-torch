"""InsightEngine — the one object the UI layer is allowed to talk to.

Every model, storage, and adapter detail lives behind this class. The UI
never imports llama_cpp, whisper, piper, or sqlite3 directly — it only
calls methods here and receives plain dataclasses / strings back. That
boundary is what makes it possible to swap models, swap STT/TTS engines,
flip on mock mode, or eventually split this into separate processes,
without touching `ui/` at all.
"""

from __future__ import annotations

import logging
import shutil
import threading
import time
import uuid
from pathlib import Path
from typing import Callable

from config.loader import AppConfig
from engine.audio_recorder import AudioRecorder
from engine.llm_adapter import LlmAdapter, LlmConfig
from engine.mock_adapters import MockLlmAdapter, MockSttAdapter, MockTtsAdapter, MockVisionAdapter
from engine.prompt_builder import PromptBuilder
from engine.session import SessionManager
from engine.speech_text import prepare_for_speech
from engine.stt_adapter import SttAdapter, SttConfig
from engine.tts_adapter import TtsAdapter, TtsConfig
from engine.types import AppState, SessionStateView, TurnResult
from engine.vision_adapter import VisionAdapter, VisionConfig
from engine.visual_context import VisualContext
from storage.models import MemoryFact, Message, PromptVersion
from storage.repository import Repository

logger = logging.getLogger("insight.engine")


class InsightEngine:
    def __init__(self, config: AppConfig):
        self._config = config
        self._repo = Repository(config.resolve(config.storage.db_path))
        self._session = SessionManager(self._repo, config.interaction.history_turns_in_prompt)
        self._prompt_builder = PromptBuilder()

        self._llm, self._stt, self._tts, self._vision = self._build_adapters(config)

        self._recorder = AudioRecorder(
            sample_rate=config.audio.sample_rate,
            device=config.audio.input_device,
            max_seconds=config.audio.max_recording_seconds,
        )

        self._visual_context: VisualContext | None = None
        self._uploads_dir = Path(config.resolve("insight_desktop/data/uploads"))
        self._uploads_dir.mkdir(parents=True, exist_ok=True)

        self._cancel_event = threading.Event()
        self._busy_lock = threading.Lock()

        self._ensure_active_prompt_version()

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    def _build_adapters(self, config: AppConfig):
        if config.mock_mode:
            logger.info("Running in MOCK MODE - no real models are loaded.")
            return MockLlmAdapter(), MockSttAdapter(), MockTtsAdapter(), MockVisionAdapter()

        logger.info("Loading LLM: %s", config.models.llm_model_path)
        llm = LlmAdapter(LlmConfig(
            model_path=config.resolve(config.models.llm_model_path),
            n_ctx=config.models.llm_n_ctx,
            n_threads=config.models.llm_n_threads,
            max_tokens=config.models.llm_max_tokens,
            temperature=config.models.llm_temperature,
            top_p=config.models.llm_top_p,
        ))
        logger.info("Loading STT: %s", config.models.whisper_model_path)
        stt = SttAdapter(SttConfig(
            whisper_cli_path=config.resolve(config.models.whisper_cli_path),
            model_path=config.resolve(config.models.whisper_model_path),
            threads=config.models.whisper_threads,
        ))
        logger.info("Loading TTS: %s", config.models.tts_voice_model_path)
        tts = TtsAdapter(TtsConfig(
            voice_model_path=config.resolve(config.models.tts_voice_model_path),
            length_scale=config.models.tts_length_scale,
            noise_scale=config.models.tts_noise_scale,
            noise_w=config.models.tts_noise_w,
        ))
        vision = self._try_build_vision(config)
        return llm, stt, tts, vision

    def _try_build_vision(self, config: AppConfig):
        if not config.models.vision_enabled:
            logger.info("Vision disabled in config.")
            return None
        mtmd = config.resolve(config.models.mtmd_cli_path)
        model = config.resolve(config.models.vision_model_path)
        mmproj = config.resolve(config.models.vision_mmproj_path)
        missing = [p for p in (mtmd, model, mmproj) if not Path(p).exists()]
        if missing:
            logger.warning("Vision models missing (%s) — photo features disabled.", ", ".join(missing))
            return None
        logger.info("Vision ready: %s", config.models.vision_model_path)
        return VisionAdapter(VisionConfig(
            mtmd_cli_path=mtmd,
            model_path=model,
            mmproj_path=mmproj,
            n_predict=config.models.vision_n_predict,
            temperature=config.models.vision_temperature,
            gpu_layers=config.models.vision_gpu_layers,
        ))

    def _ensure_active_prompt_version(self) -> None:
        if self._repo.get_active_prompt_version() is not None:
            return
        prompt_path = Path(self._config.resolve(self._config.prompts.system_prompt_path))
        content = prompt_path.read_text(encoding="utf-8")
        self._repo.save_prompt_version(content, label="initial")

    # ------------------------------------------------------------------
    # Public interface - text
    # ------------------------------------------------------------------

    def send_text_message(
        self,
        text: str,
        on_token: Callable[[str], None] | None = None,
        on_state: Callable[[AppState], None] | None = None,
    ) -> TurnResult:
        result = self._run_turn(text, source="text", transcript=None, on_token=on_token, on_state=on_state)
        if on_state:
            on_state(AppState.IDLE)
        return result

    def greet_after_photo(
        self,
        on_token: Callable[[str], None] | None = None,
        on_state: Callable[[AppState], None] | None = None,
    ) -> TurnResult:
        """Brief assistant opener after a photo attach — not shown as a user message."""
        prompt = (
            "The user just attached a photo. In 1-2 casual sentences, say what you see "
            "and ask what they want to know about it."
        )
        result = self._run_turn(
            prompt, source="photo", transcript=None,
            on_token=on_token, on_state=on_state, record_user=False,
        )
        if on_state:
            on_state(AppState.IDLE)
        return result

    # ------------------------------------------------------------------
    # Public interface - voice
    # ------------------------------------------------------------------

    def start_recording(self, on_state: Callable[[AppState], None] | None = None) -> None:
        self._recorder.start()
        if on_state:
            on_state(AppState.LISTENING)

    def cancel_recording(self, on_state: Callable[[AppState], None] | None = None) -> None:
        self._recorder.cancel()
        if on_state:
            on_state(AppState.IDLE)

    def send_voice_utterance(
        self,
        on_transcript: Callable[[str], None] | None = None,
        on_token: Callable[[str], None] | None = None,
        on_state: Callable[[AppState], None] | None = None,
    ) -> TurnResult | None:
        """Stops the current recording, transcribes it, and - if there's
        real content - runs it through the same turn pipeline a typed
        message uses, then speaks the reply. Returns None if the
        recording was too short/empty to transcribe (e.g. an accidental
        tap of the mic button)."""
        audio_path = self._recorder.stop()
        if audio_path is None:
            if on_state:
                on_state(AppState.IDLE)
            return None

        if on_state:
            on_state(AppState.TRANSCRIBING)
        try:
            transcript = self._stt.transcribe(audio_path)
        finally:
            Path(audio_path).unlink(missing_ok=True)  # no raw audio retained on disk

        if not transcript:
            if on_state:
                on_state(AppState.IDLE)
            return None

        if on_transcript:
            on_transcript(transcript)

        result = self._run_turn(
            transcript, source="voice", transcript=transcript, on_token=on_token, on_state=on_state,
        )

        if not result.cancelled and result.reply_text and not self._cancel_event.is_set():
            if on_state:
                on_state(AppState.SPEAKING)
            self._tts.speak(prepare_for_speech(result.reply_text))

        if on_state:
            on_state(AppState.IDLE)
        return result

    def speak(self, text: str, on_state: Callable[[AppState], None] | None = None) -> None:
        """Exposed separately so the UI can replay a reply out loud on
        demand without re-running the LLM."""
        if on_state:
            on_state(AppState.SPEAKING)
        self._tts.speak(prepare_for_speech(text))
        if on_state:
            on_state(AppState.IDLE)

    # ------------------------------------------------------------------
    # Photos / visual context
    # ------------------------------------------------------------------

    def get_visual_context(self) -> VisualContext | None:
        return self._visual_context

    def clear_visual_context(self) -> None:
        self._visual_context = None

    def attach_photo(
        self,
        source_path: str,
        on_state: Callable[[AppState], None] | None = None,
    ) -> VisualContext:
        """Copy (if needed), caption with the vision model, and keep the
        result as active context for follow-up questions."""
        if self._vision is None:
            raise RuntimeError(
                "Photo analysis is not available. Run poc/setup_vision_mac.sh "
                "or enable mock_mode for UI testing."
            )

        with self._busy_lock:
            self._cancel_event.clear()
            if on_state:
                on_state(AppState.ANALYZING)

            stored_path = self._persist_photo(source_path)
            caption = self._vision.describe_image(stored_path)
            self._visual_context = VisualContext(image_path=stored_path, caption=caption)
            logger.info("Photo attached: %s", caption[:120])

            if on_state:
                on_state(AppState.IDLE)
            return self._visual_context

    def record_photo_message(self, caption: str) -> None:
        self._session.record_user_message(f"📷 Photo attached\n{caption}", source="photo")

    def _persist_photo(self, source_path: str) -> str:
        source = Path(source_path)
        uploads_resolved = self._uploads_dir.resolve()
        if source.resolve().parent == uploads_resolved:
            return str(source)
        dest = self._uploads_dir / f"photo-{uuid.uuid4().hex}{source.suffix.lower() or '.jpg'}"
        shutil.copy2(source, dest)
        return str(dest)

    # ------------------------------------------------------------------
    # Cancellation - one entry point for the UI's Stop/Cancel button,
    # regardless of whether Insight is currently listening, thinking, or
    # speaking.
    # ------------------------------------------------------------------

    def cancel_current(self) -> None:
        if self._recorder.is_recording:
            self._recorder.cancel()
        self._cancel_event.set()
        self._tts.stop()

    # ------------------------------------------------------------------
    # Turn pipeline (shared by text and voice)
    # ------------------------------------------------------------------

    def _run_turn(
        self,
        utterance: str,
        source: str,
        transcript: str | None,
        on_token: Callable[[str], None] | None,
        on_state: Callable[[AppState], None] | None,
        record_user: bool = True,
    ) -> TurnResult:
        with self._busy_lock:
            self._cancel_event.clear()
            start = time.monotonic()

            active_prompt = self._repo.get_active_prompt_version()
            personality_prompt = active_prompt.content if active_prompt else ""
            memory_facts = [f.text for f in self._repo.list_memory_facts()]
            history_messages, summary_note = self._session.get_prompt_history_messages()

            messages, debug_text = self._prompt_builder.build(
                personality_prompt,
                memory_facts,
                history_messages,
                summary_note,
                utterance,
                visual_context=self._visual_context,
            )

            if record_user:
                self._session.record_user_message(utterance, source=source)

            if on_state:
                on_state(AppState.THINKING)

            reply_text = self._llm.generate(
                messages,
                on_token=on_token,
                should_cancel=self._cancel_event.is_set,
            )
            cancelled = self._cancel_event.is_set()
            latency_ms = int((time.monotonic() - start) * 1000)

            self._session.record_assistant_message(
                reply_text or "(cancelled before any reply was generated)",
                prompt_version_id=active_prompt.id if active_prompt else None,
                latency_ms=latency_ms,
                cancelled=cancelled,
            )

            return TurnResult(
                transcript=transcript,
                reply_text=reply_text,
                cancelled=cancelled,
                latency_ms=latency_ms,
                prompt_version_id=active_prompt.id if active_prompt else None,
                assembled_prompt_debug=debug_text,
                image_caption=self._visual_context.caption if self._visual_context else None,
            )

    # ------------------------------------------------------------------
    # Personality / prompt inspection + editing
    # ------------------------------------------------------------------

    def get_system_prompt(self) -> str:
        active = self._repo.get_active_prompt_version()
        return active.content if active else ""

    def update_prompt(self, new_text: str, label: str | None = None) -> PromptVersion:
        return self._repo.save_prompt_version(new_text, label=label)

    def get_prompt_history(self) -> list[PromptVersion]:
        return self._repo.list_prompt_versions()

    def activate_prompt_version(self, version_id: str) -> PromptVersion | None:
        return self._repo.activate_prompt_version(version_id)

    # ------------------------------------------------------------------
    # Long-term memory facts
    # ------------------------------------------------------------------

    def list_memory_facts(self) -> list[MemoryFact]:
        return self._repo.list_memory_facts()

    def add_memory_fact(self, text: str) -> MemoryFact:
        return self._repo.add_memory_fact(text)

    def remove_memory_fact(self, fact_id: str) -> None:
        self._repo.remove_memory_fact(fact_id)

    # ------------------------------------------------------------------
    # Session / history
    # ------------------------------------------------------------------

    def get_history(self) -> list[Message]:
        return self._session.get_all_messages()

    def reset_memory(self, scope: str = "session") -> None:
        """scope="session" (default): clears the visible chat and starts
        a fresh session; long-term memory facts are kept. scope="all":
        also clears long-term memory facts - a genuinely full reset.
        Nothing is ever deleted from SQLite by this call; prior sessions
        are simply marked ended and left in place."""
        self._session.reset(clear_memory_facts=(scope == "all"))
        self._visual_context = None

    def get_session_state(self) -> SessionStateView:
        active_prompt = self._repo.get_active_prompt_version()
        count = self._session.message_count()
        return SessionStateView(
            session_id=self._session.current_session.id,
            message_count=count,
            active_prompt_label=active_prompt.label if active_prompt else None,
            active_prompt_version_id=active_prompt.id if active_prompt else None,
            memory_fact_count=len(self._repo.list_memory_facts()),
            current_state=AppState.IDLE,
            session_summary=f"{count} message(s) in the current session.",
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        self._repo.close()
