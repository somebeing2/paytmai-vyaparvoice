from typing import Optional
from .base import STTResult, TTSResult


class WebSpeechFallbackProvider:
    """Zero-cost deterministic fallback delegating speech rendering to browser Web Speech API."""

    def synthesize(self, text: str, lang_code: str, reason: Optional[str] = None) -> TTSResult:
        return TTSResult(
            text=text,
            lang_code=lang_code,
            provider="browser_webspeech",
            mode="client_speech_synthesis",
            audio_base64=None,
            cached=False,
            credits_used=0.0,
            fallback_reason=reason,
        )

    def transcribe_Simulated(self, fallback_utterance: str, lang_code: str, reason: Optional[str] = None) -> STTResult:
        return STTResult(
            transcript=fallback_utterance,
            lang_code=lang_code,
            provider="browser_webspeech",
            mode="client_speech_recognition",
            credits_used=0.0,
            fallback_reason=reason,
        )
