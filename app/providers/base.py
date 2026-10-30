from dataclasses import dataclass
from typing import Optional


@dataclass
class TTSResult:
    text: str
    lang_code: str
    provider: str
    mode: str
    audio_base64: Optional[str] = None
    mime_type: str = "audio/wav"
    cached: bool = False
    credits_used: float = 0.0
    fallback_reason: Optional[str] = None


@dataclass
class STTResult:
    transcript: str
    lang_code: str
    provider: str
    mode: str
    credits_used: float = 0.0
    fallback_reason: Optional[str] = None
