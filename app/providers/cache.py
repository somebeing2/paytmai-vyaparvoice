import base64
import hashlib
import json
from pathlib import Path
from typing import Optional, Tuple


class PhraseAudioCache:
    """Deterministic SHA-256 phrase audio cache so repeat briefings cost 0 credits."""

    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = Path(cache_dir)

    def _key(self, model: str, lang_code: str, speaker: str, text: str) -> str:
        norm = " ".join(text.strip().split())
        payload = f"{model}|{lang_code}|{speaker}|{norm}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:24]

    def get(self, model: str, lang_code: str, speaker: str, text: str) -> Optional[Tuple[str, str]]:
        digest = self._key(model, lang_code, speaker, text)
        wav_path = self.cache_dir / f"{digest}.wav"
        meta_path = self.cache_dir / f"{digest}.json"
        if not wav_path.exists():
            return None
        mime = "audio/wav"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                mime = meta.get("mime_type", "audio/wav")
            except Exception:
                pass
        b64 = base64.b64encode(wav_path.read_bytes()).decode("ascii")
        return b64, mime

    def put(
        self,
        model: str,
        lang_code: str,
        speaker: str,
        text: str,
        audio_base64: str,
        mime_type: str = "audio/wav",
    ) -> Path:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        digest = self._key(model, lang_code, speaker, text)
        wav_path = self.cache_dir / f"{digest}.wav"
        meta_path = self.cache_dir / f"{digest}.json"
        raw_bytes = base64.b64decode(audio_base64)
        wav_path.write_bytes(raw_bytes)
        meta_path.write_text(
            json.dumps(
                {
                    "model": model,
                    "lang_code": lang_code,
                    "speaker": speaker,
                    "char_len": len(text),
                    "mime_type": mime_type,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return wav_path
