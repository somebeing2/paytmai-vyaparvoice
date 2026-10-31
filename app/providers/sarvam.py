import base64
import threading
from typing import Any, Dict, List, Optional, Tuple
import httpx

from ..config import Settings, get_settings
from ..ledger import CreditCapExceededError, SarvamCreditLedger
from ..security import assert_paid_calls_permitted, get_current_request_session, is_session_demo_unlocked
from .base import STTResult, TTSResult
from .cache import PhraseAudioCache
from .persistent_cache import PersistentProviderCache
from .webspeech import WebSpeechFallbackProvider

_LEGACY_V2_SPEAKER_MAP = {
    "anushka": "priya",
    "manisha": "priya",
    "vidya": "ishita",
    "arya": "roopa",
    "abhilash": "shubh",
    "karun": "mani",
    "hitesh": "shubh",
}

_CALL_TRACKER_LOCK = threading.RLock()
_GLOBAL_SARVAM_CALLS: int = 0
_SESSION_SARVAM_CALLS: Dict[str, int] = {}
_LAST_FALLBACK_NOTICE: Optional[str] = None


def record_sarvam_call(session_id: Optional[str] = None) -> Tuple[int, int]:
    global _GLOBAL_SARVAM_CALLS
    sid = (session_id if session_id is not None else get_current_request_session()) or "default"
    with _CALL_TRACKER_LOCK:
        _GLOBAL_SARVAM_CALLS += 1
        _SESSION_SARVAM_CALLS[sid] = _SESSION_SARVAM_CALLS.get(sid, 0) + 1
        return _GLOBAL_SARVAM_CALLS, _SESSION_SARVAM_CALLS[sid]


def get_sarvam_call_counts(session_id: Optional[str] = None) -> Dict[str, int]:
    sid = (session_id if session_id is not None else get_current_request_session()) or "default"
    with _CALL_TRACKER_LOCK:
        return {
            "global_calls": _GLOBAL_SARVAM_CALLS,
            "session_calls": _SESSION_SARVAM_CALLS.get(sid, 0),
        }


def set_fallback_notice(notice: Optional[str]) -> None:
    global _LAST_FALLBACK_NOTICE
    with _CALL_TRACKER_LOCK:
        _LAST_FALLBACK_NOTICE = notice


def get_fallback_notice() -> Optional[str]:
    with _CALL_TRACKER_LOCK:
        return _LAST_FALLBACK_NOTICE


def reset_sarvam_runtime_counters() -> None:
    global _GLOBAL_SARVAM_CALLS, _LAST_FALLBACK_NOTICE
    with _CALL_TRACKER_LOCK:
        _GLOBAL_SARVAM_CALLS = 0
        _SESSION_SARVAM_CALLS.clear()
        _LAST_FALLBACK_NOTICE = None


class SarvamProviderError(RuntimeError):
    """Raised in strict mode when Sarvam call is blocked or fails."""


class SarvamProvider:
    """
    Keyless Sarvam AI primary provider (Bulbul v3 TTS + Saaras v4 STT + Sarvam-105B Chat).
    - Reads credentials exclusively from Settings (loaded from .env / environment).
    - Checks persistent SQLite cache (provider, language, voice, exact_text) + PhraseAudioCache first (0 API calls).
    - Enforces PUBLIC_DEPLOY / DEMO_PIN lock, 10s recording limit, per-session & global SARVAM_MAX_CALLS, and 30% credit cap.
    - Trips fail-closed circuit breaker on HTTP 401/402/403/429/5xx or network timeout and falls back silently.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        ledger: Optional[SarvamCreditLedger] = None,
        cache: Optional[PhraseAudioCache] = None,
        persistent_cache: Optional[PersistentProviderCache] = None,
    ) -> None:
        self.settings = settings or get_settings()
        default_bal = self.settings.sarvam_initial_balance if bool(self.settings.sarvam_api_key.strip()) else 0.0
        self.ledger = ledger or SarvamCreditLedger(
            ledger_path=self.settings.sarvam_ledger_path,
            tts_cap_pct=self.settings.sarvam_tts_cap_pct,
            stt_cap_pct=self.settings.sarvam_stt_cap_pct,
            total_cap_pct=self.settings.sarvam_total_cap_pct,
            default_initial_balance=default_bal,
        )
        self.cache = cache or PhraseAudioCache(self.settings.sarvam_cache_dir)
        self.persistent_cache = persistent_cache or PersistentProviderCache(
            self.settings.provider_cache_db_path,
            prewarmed_dir=self.settings.prewarmed_assets_dir,
        )
        self.fallback = WebSpeechFallbackProvider()

    def estimate_tts_cost(self, text: str) -> float:
        chars = max(1, len(text))
        return round((chars / 10000.0) * self.settings.sarvam_tts_cost_per_10k_inr, 6)

    def estimate_stt_cost(self, duration_seconds: float) -> float:
        secs = max(0.5, float(duration_seconds))
        return round((secs / 3600.0) * self.settings.sarvam_stt_cost_per_hour_inr, 6)

    def _check_call_caps(self, session_id: Optional[str] = None) -> None:
        counts = get_sarvam_call_counts(session_id)
        ledger_calls = int(self.ledger.summary().get("calls_made", 0))
        eff_global = max(counts["global_calls"], ledger_calls)
        if eff_global >= max(1, int(self.settings.sarvam_max_calls)):
            raise SarvamProviderError(
                f"Global Sarvam call limit ({self.settings.sarvam_max_calls}) reached; using fallback provider."
            )
        if counts["session_calls"] >= max(1, int(self.settings.sarvam_session_max_calls)):
            raise SarvamProviderError(
                f"Session Sarvam call limit ({self.settings.sarvam_session_max_calls}) reached; using fallback provider."
            )

    def _assert_live_ready(self, session_id: Optional[str] = None) -> None:
        unlocked = is_session_demo_unlocked(session_id)
        try:
            assert_paid_calls_permitted("Sarvam AI", demo_unlocked=unlocked)
        except PermissionError as exc:
            raise SarvamProviderError(str(exc)) from exc

        if not self.settings.is_sarvam_live_allowed(demo_unlocked=unlocked):
            raise SarvamProviderError(
                "Sarvam live calls disabled (requires SARVAM_API_KEY in .env, and DEMO_PIN unlock when PUBLIC_DEPLOY=true)."
            )
        self._check_call_caps(session_id)

    def get_cached_tts(self, text: str, lang_code: str = "en-IN") -> Optional[TTSResult]:
        model = self.settings.sarvam_tts_model
        speaker = self.settings.sarvam_speakers.get(lang_code, "priya").strip().lower()
        if model.startswith("bulbul:v3") and speaker in _LEGACY_V2_SPEAKER_MAP:
            speaker = _LEGACY_V2_SPEAKER_MAP[speaker]

        p_hit = self.persistent_cache.get_tts("sarvam", lang_code, speaker, text)
        if p_hit is not None:
            b64_audio, mime = p_hit
            return TTSResult(
                text=text,
                lang_code=lang_code,
                provider="sarvam_cached",
                mode="cached_audio",
                audio_base64=b64_audio,
                mime_type=mime,
                cached=True,
                credits_used=0.0,
            )

        f_hit = self.cache.get(model=model, lang_code=lang_code, speaker=speaker, text=text)
        if f_hit is not None:
            b64_audio, mime = f_hit
            self.persistent_cache.put_tts("sarvam", lang_code, speaker, text, b64_audio, mime)
            return TTSResult(
                text=text,
                lang_code=lang_code,
                provider="sarvam_cached",
                mode="cached_audio",
                audio_base64=b64_audio,
                mime_type=mime,
                cached=True,
                credits_used=0.0,
            )
        return None

    def synthesize(
        self,
        text: str,
        lang_code: str = "en-IN",
        strict: bool = False,
        session_id: Optional[str] = None,
    ) -> TTSResult:
        model = self.settings.sarvam_tts_model
        speaker = self.settings.sarvam_speakers.get(lang_code, "priya").strip().lower()
        if model.startswith("bulbul:v3") and speaker in _LEGACY_V2_SPEAKER_MAP:
            speaker = _LEGACY_V2_SPEAKER_MAP[speaker]

        # 1. Check persistent SQLite + file cache first (0 API calls, safe everywhere including PUBLIC_DEPLOY=true)
        cached_res = self.get_cached_tts(text, lang_code=lang_code)
        if cached_res is not None:
            return cached_res

        # 2. Enforce PUBLIC_DEPLOY / DEMO_PIN, key presence, and call caps
        try:
            self._assert_live_ready(session_id)
        except SarvamProviderError as exc:
            if strict:
                raise
            return self.fallback.synthesize(text, lang_code, reason=str(exc))

        # 3. Check 15% TTS / 30% total credit cap before touching network
        est_cost = self.estimate_tts_cost(text)
        try:
            self.ledger.check_allowance("tts", est_cost)
        except CreditCapExceededError as exc:
            set_fallback_notice(f"Sarvam TTS credit cap reached; switched to fallback ({exc}).")
            if strict:
                raise
            return self.fallback.synthesize(text, lang_code, reason=str(exc))

        # 4. Perform live request (Sarvam Bulbul v3 REST contract:POST /text-to-speech with api-subscription-key)
        url = f"{self.settings.sarvam_base_url}{self.settings.sarvam_tts_endpoint}"
        headers = {
            "api-subscription-key": self.settings.sarvam_api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "text": text,
            "target_language_code": lang_code,
            "speaker": speaker,
            "model": model,
            "speech_sample_rate": 22050,
            "output_audio_codec": "wav",
        }

        try:
            record_sarvam_call(session_id)
            with httpx.Client(timeout=self.settings.sarvam_timeout_seconds) as client:
                resp = client.post(url, headers=headers, json=payload)
        except Exception as exc:
            self.ledger.trip_circuit_breaker(f"Network/timeout error on TTS: {type(exc).__name__}")
            set_fallback_notice(f"Sarvam TTS timeout/network error ({type(exc).__name__}); using fallback.")
            if strict:
                raise SarvamProviderError(f"Sarvam TTS network error: {exc}") from exc
            return self.fallback.synthesize(text, lang_code, reason="Sarvam TTS network error")

        if resp.status_code != 200:
            detail_snip = resp.text[:220] if resp.text else ""
            if resp.status_code in (401, 402, 403, 429) or resp.status_code >= 500:
                self.ledger.trip_circuit_breaker("Billing/auth/rate/server error on TTS", resp.status_code)
            set_fallback_notice(f"Sarvam TTS HTTP {resp.status_code}; fell back automatically.")
            if strict:
                raise SarvamProviderError(f"Sarvam TTS HTTP {resp.status_code}: {detail_snip}")
            return self.fallback.synthesize(text, lang_code, reason=f"Sarvam HTTP {resp.status_code}")

        data = resp.json()
        audios = data.get("audios") or []
        if not audios or not isinstance(audios[0], str):
            self.ledger.trip_circuit_breaker("Malformed Sarvam TTS response missing audios[0]")
            set_fallback_notice("Sarvam TTS returned malformed audio payload; fell back automatically.")
            if strict:
                raise SarvamProviderError("Malformed Sarvam TTS response")
            return self.fallback.synthesize(text, lang_code, reason="Malformed Sarvam TTS response")

        audio_b64 = audios[0]
        self.ledger.record_spend("tts", est_cost, note=f"TTS {lang_code} ({len(text)} chars)")
        self.cache.put(model=model, lang_code=lang_code, speaker=speaker, text=text, audio_base64=audio_b64)
        self.persistent_cache.put_tts("sarvam", lang_code, speaker, text, audio_b64, "audio/wav")

        return TTSResult(
            text=text,
            lang_code=lang_code,
            provider="sarvam_live",
            mode="bulbul_tts",
            audio_base64=audio_b64,
            mime_type="audio/wav",
            cached=False,
            credits_used=est_cost,
        )

    def transcribe(
        self,
        audio_base64: str,
        lang_code: str = "en-IN",
        duration_seconds: float = 5.0,
        strict: bool = False,
        session_id: Optional[str] = None,
        mime_type: str = "audio/wav",
    ) -> STTResult:
        # Enforce 10-second spoken recording cap
        max_secs = float(self.settings.sarvam_max_recording_seconds)
        if float(duration_seconds) > max_secs + 0.25:
            reason = f"Spoken input exceeds {int(max_secs)}-second recording limit ({duration_seconds:.1f}s)."
            set_fallback_notice(reason)
            if strict:
                raise SarvamProviderError(reason)
            return self.fallback.transcribe_Simulated("", lang_code, reason=reason)

        try:
            self._assert_live_ready(session_id)
        except SarvamProviderError as exc:
            if strict:
                raise
            return self.fallback.transcribe_Simulated("", lang_code, reason=str(exc))

        est_cost = self.estimate_stt_cost(min(float(duration_seconds), max_secs))
        try:
            self.ledger.check_allowance("stt", est_cost)
        except CreditCapExceededError as exc:
            set_fallback_notice(f"Sarvam STT credit cap reached; switched to fallback ({exc}).")
            if strict:
                raise
            return self.fallback.transcribe_Simulated("", lang_code, reason=str(exc))

        # Sarvam Saaras REST contract: POST /speech-to-text (multipart/form-data, api-subscription-key)
        # Note from docs.sarvam.ai: 'mode' parameter applies ONLY to saaras:v3, omit for saaras:v4.
        url = f"{self.settings.sarvam_base_url}{self.settings.sarvam_stt_endpoint}"
        headers = {
            "api-subscription-key": self.settings.sarvam_api_key,
        }
        try:
            wav_bytes = base64.b64decode(audio_base64)
        except Exception as exc:
            if strict:
                raise SarvamProviderError("Invalid base64 audio payload for STT") from exc
            return self.fallback.transcribe_Simulated("", lang_code, reason="Invalid base64 audio")

        stt_model = self.settings.sarvam_stt_model
        form_data: Dict[str, str] = {
            "model": stt_model,
            "language_code": lang_code,
        }
        if stt_model == "saaras:v3":
            form_data["mode"] = "transcribe"

        ext = "webm" if "webm" in mime_type.lower() else ("ogg" if "ogg" in mime_type.lower() else "wav")
        files = {
            "file": (f"utterance.{ext}", wav_bytes, mime_type or "audio/wav"),
        }

        try:
            record_sarvam_call(session_id)
            with httpx.Client(timeout=self.settings.sarvam_timeout_seconds) as client:
                resp = client.post(url, headers=headers, data=form_data, files=files)
        except Exception as exc:
            self.ledger.trip_circuit_breaker(f"Network/timeout error on STT: {type(exc).__name__}")
            set_fallback_notice(f"Sarvam STT timeout/network error ({type(exc).__name__}); using fallback.")
            if strict:
                raise SarvamProviderError(f"Sarvam STT network error: {exc}") from exc
            return self.fallback.transcribe_Simulated("", lang_code, reason="Sarvam STT network error")

        if resp.status_code != 200:
            detail_snip = resp.text[:220] if resp.text else ""
            if resp.status_code in (401, 402, 403, 429) or resp.status_code >= 500:
                self.ledger.trip_circuit_breaker("Billing/auth/rate/server error on STT", resp.status_code)
            set_fallback_notice(f"Sarvam STT HTTP {resp.status_code}; fell back automatically.")
            if strict:
                raise SarvamProviderError(f"Sarvam STT HTTP {resp.status_code}: {detail_snip}")
            return self.fallback.transcribe_Simulated("", lang_code, reason=f"Sarvam HTTP {resp.status_code}")

        data = resp.json()
        transcript = str(data.get("transcript", "")).strip()
        self.ledger.record_spend("stt", est_cost, note=f"STT {lang_code} ({duration_seconds:.1f}s)")

        return STTResult(
            transcript=transcript,
            lang_code=lang_code,
            provider="sarvam_live",
            mode="saaras_stt",
            credits_used=est_cost,
        )

    def chat_complete(
        self,
        messages: List[Dict[str, str]],
        lang_code: str = "en-IN",
        cache_key_text: str = "",
        max_tokens: int = 110,
        session_id: Optional[str] = None,
    ) -> Tuple[str, bool]:
        """
        Sarvam Chat Completions contract (docs.sarvam.ai/api-reference/chat/chat-completions-v1.md):
        - POST https://api.sarvam.ai/v1/chat/completions
        - Header: api-subscription-key: <SARVAM_API_KEY> (never combined with Authorization)
        - Model: sarvam-105b-conversations (default) or sarvam-105b (reasoning_effort='none')
        Returns (completion_text, was_cached). Raises SarvamProviderError on any block/failure
        so the router can fall back silently to Groq -> deterministic templates.
        """
        chat_model = self.settings.sarvam_chat_model
        exact_key = cache_key_text or repr(messages)
        cached_txt = self.persistent_cache.get_llm("sarvam", lang_code, chat_model, exact_key)
        if cached_txt is not None:
            return cached_txt, True

        self._assert_live_ready(session_id)
        est_cost = float(self.settings.sarvam_chat_cost_credits)
        try:
            self.ledger.check_allowance("chat", est_cost)
        except CreditCapExceededError as exc:
            set_fallback_notice(f"Sarvam Chat credit cap reached; switched to fallback ({exc}).")
            raise SarvamProviderError(str(exc)) from exc

        url = f"{self.settings.sarvam_base_url}{self.settings.sarvam_chat_endpoint}"
        headers = {
            "api-subscription-key": self.settings.sarvam_api_key,
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": chat_model,
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": int(max_tokens),
        }
        if chat_model == "sarvam-105b":
            payload["reasoning_effort"] = "none"

        try:
            record_sarvam_call(session_id)
            with httpx.Client(timeout=self.settings.sarvam_timeout_seconds) as client:
                resp = client.post(url, headers=headers, json=payload)
        except Exception as exc:
            self.ledger.trip_circuit_breaker(f"Network/timeout error on Chat: {type(exc).__name__}")
            set_fallback_notice(f"Sarvam Chat timeout/network error ({type(exc).__name__}); switched to fallback.")
            raise SarvamProviderError(f"Sarvam Chat network error: {exc}") from exc

        if resp.status_code != 200:
            detail_snip = resp.text[:220] if resp.text else ""
            if resp.status_code in (401, 402, 403, 429) or resp.status_code >= 500:
                self.ledger.trip_circuit_breaker("Billing/auth/rate/server error on Chat", resp.status_code)
            set_fallback_notice(f"Sarvam Chat HTTP {resp.status_code}; switched to fallback.")
            raise SarvamProviderError(f"Sarvam Chat HTTP {resp.status_code}: {detail_snip}")

        data = resp.json()
        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        if not content:
            set_fallback_notice("Sarvam Chat returned empty completion; switched to fallback.")
            raise SarvamProviderError("Empty Sarvam Chat completion")

        self.ledger.record_spend("chat", est_cost, note=f"Chat {lang_code} ({chat_model})")
        self.persistent_cache.put_llm("sarvam", lang_code, chat_model, exact_key, content)
        return content, False

    def status_dict(self, session_id: Optional[str] = None) -> dict:
        unlocked = is_session_demo_unlocked(session_id)
        counts = get_sarvam_call_counts(session_id)
        ledger_sum = self.ledger.summary()
        eff_global_calls = max(counts["global_calls"], int(ledger_sum.get("calls_made", 0)))
        return {
            "public_deploy": self.settings.public_deploy,
            "demo_unlocked": unlocked,
            "sarvam_enabled": self.settings.sarvam_enabled,
            "sarvam_live_calls_enabled": self.settings.sarvam_live_calls_enabled,
            "api_key_configured": bool(self.settings.sarvam_api_key),
            "live_allowed": self.settings.is_sarvam_live_allowed(demo_unlocked=unlocked) and not ledger_sum["halted"],
            "models": {
                "tts": self.settings.sarvam_tts_model,
                "stt": self.settings.sarvam_stt_model,
                "chat": self.settings.sarvam_chat_model,
            },
            "calls": {
                "global_calls": eff_global_calls,
                "global_max_calls": self.settings.sarvam_max_calls,
                "session_calls": counts["session_calls"],
                "session_max_calls": self.settings.sarvam_session_max_calls,
                "max_recording_seconds": self.settings.sarvam_max_recording_seconds,
            },
            "cache": self.persistent_cache.stats(),
            "last_fallback_notice": get_fallback_notice(),
            "ledger": ledger_sum,
        }
