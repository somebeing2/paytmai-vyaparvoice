"""
Export Pre-Warmed Fixed-Phrase Audio Cache to Committed Assets (Task F).

Reads the fixed-phrase entries (collect_fixed_prewarm_phrases() across EN, HI, KN)
from data/provider_cache.db and writes:
  - assets/prewarmed/<hash>.wav
  - assets/prewarmed/index.json (keyed strictly by provider, language, voice, exact_text)

Includes ZERO API keys, PINs, user data, timestamps, IPs, or request logs.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.database import DB_PATH, init_and_seed_db, use_db_path
from app.engine import collect_fixed_prewarm_phrases
from app.providers.persistent_cache import PersistentProviderCache

FORBIDDEN_SECRET_RES = [
    re.compile(r"gsk_[A-Za-z0-9]{16,}"),
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"SARVAM_API_KEY", re.IGNORECASE),
    re.compile(r"GROQ_API_KEY", re.IGNORECASE),
    re.compile(r"DEMO_PIN", re.IGNORECASE),
    re.compile(r"api-subscription-key", re.IGNORECASE),
]


def export_prewarmed_assets(
    cache_db_path: Path,
    out_dir: Path,
) -> Dict[str, Any]:
    """
    Export fixed-phrase TTS audio clips from cache_db_path into out_dir (WAV files + index.json).
    """
    with use_db_path(DB_PATH):
        init_and_seed_db(force_reset=False)
        phrases = collect_fixed_prewarm_phrases()

    settings = get_settings()
    pcache = PersistentProviderCache(cache_db_path, prewarmed_dir=None)
    out_dir.mkdir(parents=True, exist_ok=True)

    seen_keys = set()
    entries: List[Dict[str, str]] = []

    for item in phrases:
        lang_code = item["lang_code"]
        text = item["text"]
        speaker = settings.sarvam_speakers.get(lang_code, "priya").strip().lower()
        candidates = [("sarvam", lang_code, speaker)]
        if lang_code.startswith("en"):
            candidates.append(
                ("groq", "en", settings.groq_tts_voice)
            )

        for prov, lg, voice in candidates:
            key = pcache.make_key(prov, lg, voice, text)
            if key in seen_keys:
                continue
            hit = pcache.get_tts(prov, lg, voice, text)
            if hit is None:
                continue
            audio_b64, mime = hit
            raw_bytes = base64.b64decode(audio_b64)
            ext = ".mp3" if "mpeg" in mime or "mp3" in mime else ".wav"
            fname = f"{key[:24]}{ext}"
            (out_dir / fname).write_bytes(raw_bytes)
            sha = hashlib.sha256(raw_bytes).hexdigest()
            entries.append(
                {
                    "provider": prov,
                    "language": lg,
                    "voice": voice,
                    "exact_text": text,
                    "mime_type": mime,
                    "audio_file": fname,
                    "sha256": sha,
                }
            )
            seen_keys.add(key)
            break

    entries.sort(key=lambda e: (e["provider"], e["language"], e["voice"], e["exact_text"]))

    # Remove stale audio files in out_dir not referenced by index.json
    active_files = {e["audio_file"] for e in entries}
    for fp in out_dir.iterdir():
        if fp.is_file() and fp.suffix.lower() in (".wav", ".mp3") and fp.name not in active_files:
            fp.unlink()

    index_obj = {
        "schema_version": 1,
        "entries": entries,
    }
    serialized = json.dumps(index_obj, ensure_ascii=False, indent=2) + "\n"
    for pat in FORBIDDEN_SECRET_RES:
        if pat.search(serialized):
            raise RuntimeError(f"Refusing to write index.json: matched forbidden pattern {pat.pattern}")

    (out_dir / "index.json").write_text(serialized, encoding="utf-8")
    return {
        "total_fixed_phrases": len(phrases),
        "exported_unique_entries": len(entries),
        "out_dir": str(out_dir),
    }


def main(argv: List[str] | None = None) -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(
        description="Export pre-warmed fixed-phrase TTS cache entries to assets/prewarmed/ (zero secrets/logs)."
    )
    parser.add_argument(
        "--cache-db",
        type=Path,
        default=settings.provider_cache_db_path,
        help="Path to SQLite provider cache DB (default: data/provider_cache.db).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=settings.prewarmed_assets_dir,
        help="Destination folder for committed prewarmed assets (default: assets/prewarmed).",
    )
    args = parser.parse_args(argv)

    summary = export_prewarmed_assets(cache_db_path=args.cache_db, out_dir=args.out_dir)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
