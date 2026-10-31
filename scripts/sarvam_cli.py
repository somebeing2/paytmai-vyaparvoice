"""
CLI utilities for keyless Sarvam AI credit ledger, mock/live self-test, and cached audio activation.
Usage:
  python scripts/sarvam_cli.py set-balance --credits 500
  python scripts/sarvam_cli.py status
  python scripts/sarvam_cli.py selftest
  python scripts/sarvam_cli.py activate
"""
import argparse
import base64
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import Settings, get_settings, load_settings
from app.database import init_and_seed_db
from app.engine import get_voice_briefing
from app.ledger import CreditCapExceededError, SarvamCreditLedger
from app.providers.cache import PhraseAudioCache
from app.providers.sarvam import SarvamProvider, SarvamProviderError, reset_sarvam_runtime_counters
from tests.mock_sarvam_server import make_silent_wav_bytes, run_mock_sarvam_server


def cmd_set_balance(credits: float) -> int:
    settings = get_settings()
    ledger = SarvamCreditLedger(
        ledger_path=settings.sarvam_ledger_path,
        tts_cap_pct=settings.sarvam_tts_cap_pct,
        stt_cap_pct=settings.sarvam_stt_cap_pct,
        total_cap_pct=settings.sarvam_total_cap_pct,
    )
    summary = ledger.set_balance(credits=credits, reset_spend=True)
    print(json.dumps({"ok": True, "action": "ledger-set-balance", "ledger": summary}, indent=2))
    return 0


def cmd_status() -> int:
    provider = SarvamProvider()
    print(json.dumps(provider.status_dict(), indent=2))
    return 0


def cmd_selftest(live: bool = False) -> int:
    """
    Default selftest runs deterministically against local MockSarvamServer with temporary
    ledger and cache (zero keys, zero network, zero credits spent).
    Pass --live during Saturday sponsor window to run a minimal cached-briefing check.
    """
    if live:
        settings = load_settings(force_reload=True)
        if settings.public_deploy:
            print("ERROR: Cannot run live Sarvam selftest when PUBLIC_DEPLOY=true.", file=sys.stderr)
            return 1
        provider = SarvamProvider(settings=settings)
        res = provider.synthesize("Namaskara Ramesh avare, test check.", lang_code="kn-IN", strict=True)
        print(
            json.dumps(
                {
                    "ok": True,
                    "mode": "live",
                    "provider": res.provider,
                    "cached": res.cached,
                    "credits_used": res.credits_used,
                    "ledger": provider.ledger.summary(),
                },
                indent=2,
            )
        )
        return 0

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        mock_tok = "ephemeral-mock-sub-key"
        with run_mock_sarvam_server(expected_token=mock_tok) as (base_url, mock_state):
            base = get_settings()
            test_settings = Settings(
                **{
                    **base.__dict__,
                    "public_deploy": False,
                    "sarvam_enabled": True,
                    "sarvam_live_calls_enabled": True,
                    "sarvam_api_key": mock_tok,
                    "sarvam_base_url": base_url,
                    "sarvam_ledger_path": tmp_path / "ledger.json",
                    "sarvam_cache_dir": tmp_path / "cache",
                    "provider_cache_db_path": tmp_path / "provider_cache.db",
                }
            )
            reset_sarvam_runtime_counters()
            ledger = SarvamCreditLedger(test_settings.sarvam_ledger_path, 15.0, 15.0, 30.0)
            ledger.set_balance(10.0)  # 10 credits -> TTS cap = 1.50, STT cap = 1.50, total cap = 3.00
            cache = PhraseAudioCache(test_settings.sarvam_cache_dir)
            provider = SarvamProvider(settings=test_settings, ledger=ledger, cache=cache)

            # 1. Live mock TTS call
            r1 = provider.synthesize("Namaskara Ramesh avare!", lang_code="kn-IN", strict=True)
            assert r1.provider == "sarvam_live" and not r1.cached and r1.credits_used > 0

            # 2. Second identical call hits persistent SQLite cache at 0.0 credits
            req_count_before = len(mock_state.requests_log)
            r2 = provider.synthesize("Namaskara Ramesh avare!", lang_code="kn-IN", strict=True)
            assert r2.provider == "sarvam_cached" and r2.cached and r2.credits_used == 0.0
            assert len(mock_state.requests_log) == req_count_before

            # 3. Live mock STT call (saaras:v4 omitting 'mode')
            wav_b64 = base64.b64encode(make_silent_wav_bytes()).decode("ascii")
            s1 = provider.transcribe(wav_b64, lang_code="kn-IN", duration_seconds=4.0, strict=True)
            assert "approve" in s1.transcript.lower() and s1.credits_used > 0

            # 3b. Live mock Chat call (sarvam-105b-conversations on /v1/chat/completions) + cache hit
            c_txt1, c_cached1 = provider.chat_complete(
                messages=[{"role": "user", "content": "Summarize sales"}],
                lang_code="en-IN",
                cache_key_text="selftest-chat-key",
            )
            assert "917" in c_txt1 and c_cached1 is False
            req_count_chat = len(mock_state.requests_log)
            c_txt2, c_cached2 = provider.chat_complete(
                messages=[{"role": "user", "content": "Summarize sales"}],
                lang_code="en-IN",
                cache_key_text="selftest-chat-key",
            )
            assert c_txt2 == c_txt1 and c_cached2 is True and len(mock_state.requests_log) == req_count_chat

            # 4. Verify 15% TTS cap blocks oversized text (>500,000 chars @ 30/10k > 1.50 cap)
            try:
                provider.synthesize("A" * 600000, lang_code="en-IN", strict=True)
                raise AssertionError("Expected CreditCapExceededError on 15% TTS cap")
            except CreditCapExceededError:
                pass

            # 5. Verify HTTP 402 billing error trips fail-closed circuit breaker
            mock_state.force_status = 402
            try:
                provider.synthesize("Distinct uncached phrase", lang_code="en-IN", strict=True)
                raise AssertionError("Expected SarvamProviderError on HTTP 402")
            except SarvamProviderError:
                pass
            assert ledger.summary()["halted"] is True

    print("PASS: Keyless Sarvam mock selftest verified (Bulbul TTS, Saaras STT, SHA-256 cache, 15%/30% cap, HTTP 402 fail-closed).")
    return 0


def cmd_activate() -> int:
    """
    Pre-renders and caches en/kn/hi 8:30 PM closing voice briefings into data/audio_cache
    during the Saturday sponsor window so stage playback uses cached audio cleanly.
    """
    settings = load_settings(force_reload=True)
    if settings.public_deploy:
        print("ERROR: Cannot activate live Sarvam on PUBLIC_DEPLOY=true.", file=sys.stderr)
        return 1
    if not settings.sarvam_live_allowed:
        print(
            "ERROR: Set SARVAM_ENABLED=true, SARVAM_LIVE_CALLS_ENABLED=true, and SARVAM_API_KEY in local .env first.",
            file=sys.stderr,
        )
        return 1

    init_and_seed_db(force_reset=False)
    provider = SarvamProvider(settings=settings)
    results = []
    for lang in ("en", "kn", "hi"):
        br = get_voice_briefing(lang)
        short_res = provider.synthesize(br["short_script"], lang_code=br["lang_code"], strict=True)
        tts_res = provider.synthesize(br["script"], lang_code=br["lang_code"], strict=True)
        results.append(
            {
                "lang": lang,
                "lang_code": br["lang_code"],
                "provider": tts_res.provider,
                "cached_short": short_res.cached,
                "cached_detail": tts_res.cached,
                "credits_used": round(short_res.credits_used + tts_res.credits_used, 4),
            }
        )
    print(json.dumps({"ok": True, "activated_briefings": results, "ledger": provider.ledger.summary()}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="PaytmAI VyaparVoice Sarvam CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_bal = sub.add_parser("set-balance")
    p_bal.add_argument("--credits", type=float, required=True)

    sub.add_parser("status")

    p_self = sub.add_parser("selftest")
    p_self.add_argument("--live", action="store_true")

    sub.add_parser("activate")

    args = parser.parse_args()
    if args.cmd == "set-balance":
        return cmd_set_balance(args.credits)
    if args.cmd == "status":
        return cmd_status()
    if args.cmd == "selftest":
        return cmd_selftest(live=args.live)
    if args.cmd == "activate":
        return cmd_activate()
    return 1


if __name__ == "__main__":
    sys.exit(main())
