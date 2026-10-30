from typing import Optional
import httpx

from ..config import Settings, get_settings
from ..ledger import CreditCapExceededError, SarvamCreditLedger
from ..security import assert_paid_calls_permitted
from .base import STTResult, TTSResult
from .cache import PhraseAudioCache
from .webspeech import WebSpeechFallbackProvider


class SarvamProviderError(RuntimeError):
    """Raised in strict mode when Sarvam call is blocked or fails."""


class SarvamProvider:
    """
    Keyless Sarvam AI voice provider (Bulbul TTS + Saaras STT + Translate).
    - Reads credentials exclusively from Settings (loaded from .env / environment).
    - Checks local SHA-256 PhraseAudioCache first (0 credits, works offline & on public deploy).
    - Enforces PUBLIC_DEPLOY block, dual feature flags, and 15%/15% (30% total) credit caps.
    - Trips fail-closed circuit breaker on HTTP 401/402/403/429/5xx or network timeout.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        ledger: Optional[SarvamCreditLedger] = None,
        cache: Optional[PhraseAudioCache] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.ledger = ledger or SarvamCreditLedger(
            ledger_path=self.settings.sarvam_ledger_path,
            tts_cap_pct=self.settings.sarvam_tts_cap_pct,
            stt_cap_pct=self.settings.sarvam_stt_cap_pct,
            total_cap_pct=self.settings.sarvam_total_cap_pct,
        )
        self.cache = cache or PhraseAudioCache(self.settings.sarvam_cache_dir)
        self.fallback = WebSpeechFallbackProvider()

    def estimate_tts_cost(self, text: str) -> float:
        chars = max(1, len(text))
        return round((chars / 10000.0) * self.settings.sarvam_tts_cost_per_10k_inr, 6)

    def estimate_stt_cost(self, duration_seconds: float) -> float:
        secs = max(0.5, float(duration_seconds))
        return round((secs / 3600.0) * self.settings.sarvam_stt_cost_per_hour_inr, 6)

    def synthesize(self, text: str, lang_code: str = "en-IN", strict: bool = False) -> TTSResult:
        speaker = self.settings.sarvam_speakers.get(lang_code, "anushka")
        model = self.settings.sarvam_tts_model

        # 1. Check phrase audio cache first (0 credits, safe everywhere)
        cached_hit = self.cache.get(model=model, lang_code=lang_code, speaker=speaker, text=text)
        if cached_hit is not None:
            b64_audio, mime = cached_hit
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

        # 2. Enforce PUBLIC_DEPLOY and feature flags
        try:
            assert_paid_calls_permitted("Sarvam AI")
        except PermissionError as exc:
            if strict:
                raise SarvamProviderError(str(exc)) from exc
            return self.fallback.synthesize(text, lang_code, reason=str(exc))

        if not self.settings.sarvam_live_allowed:
            reason = (
                "Sarvam live calls disabled (requires SARVAM_ENABLED=true, "
                "SARVAM_LIVE_CALLS_ENABLED=true, and SARVAM_API_KEY in .env)."
            )
            if strict:
                raise SarvamProviderError(reason)
            return self.fallback.synthesize(text, lang_code, reason=reason)

        # 3. Check 15% TTS / 30% total credit cap before touching network
        est_cost = self.estimate_tts_cost(text)
        try:
            self.ledger.check_allowance("tts", est_cost)
        except CreditCapExceededError as exc:
            if strict:
                raise
            return self.fallback.synthesize(text, lang_code, reason=str(exc))

        # 4. Perform live request
        url = f"{self.settings.sarvam_base_url}{self.settings.sarvam_tts_endpoint}"
        headers = {
            "api-subscription-key": self.settings.sarvam_api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "inputs": [text],
            "target_language_code": lang_code,
            "speaker": speaker,
            "model": model,
            "speech_sample_rate": 16000,
        }

        try:
            with httpx.Client(timeout=self.settings.sarvam_timeout_seconds) as client:
                resp = client.post(url, headers=headers, json=payload)
        except Exception as exc:
            self.ledger.trip_circuit_breaker(f"Network/timeout error on TTS: {type(exc).__name__}")
            if strict:
                raise SarvamProviderError(f"Sarvam TTS network error: {exc}") from exc
            return self.fallback.synthesize(text, lang_code, reason="Sarvam TTS network error")

        if resp.status_code != 200:
            if resp.status_code in (401, 402, 403, 429) or resp.status_code >= 500:
                self.ledger.trip_circuit_breaker("Billing/auth/rate/server error on TTS", resp.status_code)
            if strict:
                raise SarvamProviderError(f"Sarvam TTS HTTP {resp.status_code}")
            return self.fallback.synthesize(text, lang_code, reason=f"Sarvam HTTP {resp.status_code}")

        data = resp.json()
        audios = data.get("audios") or []
        if not audios or not isinstance(audios[0], str):
            self.ledger.trip_circuit_breaker("Malformed Sarvam TTS response missing audios[0]")
            if strict:
                raise SarvamProviderError("Malformed Sarvam TTS response")
            return self.fallback.synthesize(text, lang_code, reason="Malformed Sarvam TTS response")

        audio_b64 = audios[0]
        self.ledger.record_spend("tts", est_cost, note=f"TTS {lang_code} ({len(text)} chars)")
        self.cache.put(model=model, lang_code=lang_code, speaker=speaker, text=text, audio_base64=audio_b64)

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
    ) -> STTResult:
        try:
            assert_paid_calls_permitted("Sarvam AI")
        except PermissionError as exc:
            if strict:
                raise SarvamProviderError(str(exc)) from exc
            return self.fallback.transcribe_Simulated("", lang_code, reason=str(exc))

        if not self.settings.sarvam_live_allowed:
            reason = "Sarvam live STT disabled."
            if strict:
                raise SarvamProviderError(reason)
            return self.fallback.transcribe_Simulated("", lang_code, reason=reason)

        est_cost = self.estimate_stt_cost(duration_seconds)
        try:
            self.ledger.check_allowance("stt", est_cost)
        except CreditCapExceededError as exc:
            if strict:
                raise
            return self.fallback.transcribe_Simulated("", lang_code, reason=str(exc))

        url = f"{self.settings.sarvam_base_url}{self.settings.sarvam_stt_endpoint}"
        headers = {
            "api-subscription-key": self.settings.sarvam_api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "audio_base64": audio_base64,
            "language_code": lang_code,
            "model": self.settings.sarvam_stt_model,
        }

        try:
            with httpx.Client(timeout=self.settings.sarvam_timeout_seconds) as client:
                resp = client.post(url, headers=headers, json=payload)
        except Exception as exc:
            self.ledger.trip_circuit_breaker(f"Network/timeout error on STT: {type(exc).__name__}")
            if strict:
                raise SarvamProviderError(f"Sarvam STT network error: {exc}") from exc
            return self.fallback.transcribe_Simulated("", lang_code, reason="Sarvam STT network error")

        if resp.status_code != 200:
            if resp.status_code in (401, 402, 403, 429) or resp.status_code >= 500:
                self.ledger.trip_circuit_breaker("Billing/auth/rate/server error on STT", resp.status_code)
            if strict:
                raise SarvamProviderError(f"Sarvam STT HTTP {resp.status_code}")
            return self.fallback.transcribe_Simulated("", lang_code, reason=f"Sarvam HTTP {resp.status_code}")

        data = resp.json()
        transcript = str(data.get("transcript", "")).strip()
        self.ledger.record_spend("stt", est_cost, note=f"STT {lang_code} ({duration_seconds}s)")

        return STTResult(
            transcript=transcript,
            lang_code=lang_code,
            provider="sarvam_live",
            mode="saaras_stt",
            credits_used=est_cost,
        )

    def status_dict(self) -> dict:
        return {
            "public_deploy": self.settings.public_deploy,
            "sarvam_enabled": self.settings.sarvam_enabled,
            "sarvam_live_calls_enabled": self.settings.sarvam_live_calls_enabled,
            "api_key_configured": bool(self.settings.sarvam_api_key),
            "live_allowed": self.settings.sarvam_live_allowed,
            "ledger": self.ledger.summary(),
        }
