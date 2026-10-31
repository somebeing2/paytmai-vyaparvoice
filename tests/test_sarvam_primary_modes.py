"""
Comprehensive Verification Suite for Sarvam-Primary Mode, Card Refinement,
Credit Protection, Public Deploy DEMO_PIN + Rate-Limiting, and Deterministic Voice Q&A
(Tasks A, B, C, D, E + 4-Mode Delivery Matrix).

Runs 100% locally against ephemeral MockSarvamServer + MockGroqServer with zero real keys.
"""
import base64
import contextlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
from typing import Any, Dict, Iterator, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app.config import load_settings
from app.database import init_and_seed_db
from app.main import app
from app.providers.groq_qa import get_groq_qa
from app.providers.sarvam import reset_sarvam_runtime_counters
from app.security import reset_security_state_for_tests
from scripts.export_prewarmed import export_prewarmed_assets
from tests.mock_sarvam_server import make_silent_wav_bytes, run_mock_sarvam_server


class FullMockGroqState:
    def __init__(self, expected_token: str = "ephemeral-groq-tok") -> None:
        self.expected_token = expected_token
        self.force_status = 200
        self.next_chat_reply = (
            "In 30 days your shop recorded 917 Paytm QR payments worth 174685 rupees. "
            "Your average customer bill is 190 rupees."
        )
        self.requests_log: List[Dict[str, Any]] = []


@contextlib.contextmanager
def run_full_mock_groq_server(
    expected_token: str = "ephemeral-groq-tok",
) -> Iterator[Tuple[str, FullMockGroqState]]:
    state = FullMockGroqState(expected_token=expected_token)
    wav_bytes = make_silent_wav_bytes()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            return

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b""
            ctype = self.headers.get("Content-Type", "")
            auth = self.headers.get("Authorization", "")
            state.requests_log.append({"path": self.path, "has_bearer": auth.startswith("Bearer ")})

            if state.force_status != 200:
                self._json(state.force_status, {"error": {"message": f"HTTP {state.force_status}"}})
                return
            if auth != f"Bearer {state.expected_token}":
                self._json(401, {"error": {"message": "Unauthorized"}})
                return

            if self.path.endswith("/chat/completions"):
                self._json(
                    200,
                    {
                        "id": "groq-chat-01",
                        "choices": [{"index": 0, "message": {"role": "assistant", "content": state.next_chat_reply}}],
                    },
                )
            elif self.path.endswith("/audio/transcriptions"):
                if "multipart/form-data" not in ctype.lower():
                    self._json(400, {"error": "Expected multipart"})
                    return
                self._json(200, {"text": "Customers today"})
            elif self.path.endswith("/audio/speech"):
                self.send_response(200)
                self.send_header("Content-Type", "audio/wav")
                self.send_header("Content-Length", str(len(wav_bytes)))
                self.end_headers()
                self.wfile.write(wav_bytes)
            else:
                self._json(404, {"error": "Not found"})

        def _json(self, code: int, payload: Dict[str, Any]) -> None:
            enc = json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(enc)))
            self.end_headers()
            self.wfile.write(enc)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    host, port = server.server_address
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://{host}:{port}/v1", state
    finally:
        server.shutdown()


def _reset_all_env(tmpdir: str, extra: Dict[str, str]) -> None:
    for k in (
        "SARVAM_API_KEY",
        "GROQ_API_KEY",
        "SARVAM_BASE_URL",
        "GROQ_BASE_URL",
        "STT_TTS_PROVIDER",
        "LLM_PROVIDER",
        "PUBLIC_DEPLOY",
        "DEMO_PIN",
        "DEMO_LIVE_UNLOCKED",
        "SARVAM_MAX_CALLS",
        "SARVAM_SESSION_MAX_CALLS",
        "RATE_LIMIT_PER_MINUTE",
        "PROVIDER_CACHE_DB_PATH",
        "PREWARMED_ASSETS_DIR",
        "SARVAM_CACHE_DIR",
        "SARVAM_LEDGER_PATH",
    ):
        os.environ.pop(k, None)
    os.environ["SESSION_STORAGE_DIR"] = tmpdir
    os.environ["ISOLATE_VISITORS"] = "true"
    os.environ["SARVAM_CACHE_DIR"] = str(Path(tmpdir) / "audio_cache")
    os.environ["SARVAM_LEDGER_PATH"] = str(Path(tmpdir) / "ledger.json")
    os.environ["PROVIDER_CACHE_DB_PATH"] = str(Path(tmpdir) / "provider_cache.db")
    os.environ["PREWARMED_ASSETS_DIR"] = str(Path(tmpdir) / "empty_prewarmed")
    for k, v in extra.items():
        os.environ[k] = v
    reset_sarvam_runtime_counters()
    reset_security_state_for_tests()
    load_settings(force_reload=True)
    get_groq_qa(reset=True)


def run_suite() -> int:
    orig_env = dict(os.environ)
    print("Running Sarvam-Primary 4-Mode & Tasks A-E Verification Suite...\n")

    try:
        # ------------------------------------------------------------------
        # 1. TASK A & TASK E (MODE 1: NO KEYS)
        # ------------------------------------------------------------------
        with tempfile.TemporaryDirectory() as tmp1:
            _reset_all_env(tmp1, {"PUBLIC_DEPLOY": "false"})
            init_and_seed_db(force_reset=True)
            with TestClient(app) as client:
                h = {"X-Demo-Session": "mode1-nokeys-sess"}
                ps = client.get("/api/providers/status", headers=h).json()
                assert ps["tier"] == "tertiary", ps
                assert "Web Speech" in ps["provider_in_use"]

                # Task A & Task G.3: OPS-CARE-02 ledger-only detection, inferred cause, consistent Monthly spend at risk (2 x 205 x 12 = 4920)
                ov = client.get("/api/overview", headers=h).json()
                care = next(o for o in ov["ops_actions"] if o["action_id"] == "OPS-CARE-02")
                assert care["est_value_inr"] == 4920
                dr = care["delayed_regulars"]
                assert dr["customers_affected"] == 2
                assert dr["avg_bill_inr"] == 205
                assert dr["visits_per_month"] == 12
                assert dr["monthly_spend_at_risk_inr"] == 2 * 205 * 12 == 4920
                assert dr["note"] == "historical spend, not guaranteed lift; synthetic ledger"

                why = client.get("/api/why/OPS-CARE-02", headers=h).json()
                assert "possibly after a busy rush" in why["merchant_plain"].lower()
                assert "4,920" in why["merchant_plain"] and "205" in why["merchant_plain"]
                assert "historical spend, not guaranteed lift; synthetic ledger" in why["merchant_plain"].lower()
                assert "feedback" not in json.dumps(why).lower()
                assert "3-star" not in json.dumps(why).lower()

                i18n_js = (ROOT / "app" / "static" / "i18n.js").read_text(encoding="utf-8")
                assert "Sales Protected" not in i18n_js
                assert "Monthly spend at risk:" in i18n_js
                assert "संभवतः" in i18n_js and "ಬಹುಶಃ" in i18n_js

                # Mode 1 keyless TTS / STT / QA / Explain Simply
                for lg in ("en", "hi", "kn"):
                    r_tts = client.post("/api/tts", headers=h, json={"text": "Test keyless audio", "lang": lg}).json()
                    assert r_tts["provider"] == "browser_webspeech"
                    r_qa = client.post("/api/merchant-qa", headers=h, json={"question": "Summarize my 30 day store sales.", "lang": lg}).json()
                    assert r_qa["mode"] == "deterministic_fallback"

                # Task E & Task G.1: Deterministic voice answers ('25 October 2026, the latest day in the sample data' in EN/HI/KN)
                expected_date_phrases = {
                    "en": "25 October 2026, the latest day in the sample data",
                    "hi": "25 अक्टूबर 2026, नमूना डेटा के सबसे नए दिन",
                    "kn": "25 ಅಕ್ಟೋಬರ್ 2026, ಮಾದರಿ ಡೇಟಾದ ಕೊನೆಯ ದಿನ",
                }
                for lg in ("en", "hi", "kn"):
                    v_today = client.post("/api/voice-command", headers=h, json={"utterance": "How many customers today?", "lang": lg}).json()
                    assert v_today["action_taken"] == "DETERMINISTIC_CUSTOMERS_TODAY"
                    assert expected_date_phrases[lg] in v_today["reply"], v_today["reply"]
                    assert "9" in v_today["reply"] and "1750" in v_today["reply"]

                    v_prof0 = client.post("/api/voice-command", headers=h, json={"utterance": "What is my profit?", "lang": lg}).json()
                    assert v_prof0["action_taken"] == "DETERMINISTIC_PROFIT"
                    assert "30" in v_prof0["reply"] and "5" in v_prof0["reply"]

                    v_rep = client.post("/api/voice-command", headers=h, json={"utterance": "How many repeat customers?", "lang": lg}).json()
                    assert v_rep["action_taken"] == "DETERMINISTIC_REPEAT_OR_TOTAL_CUSTOMERS"
                    assert "240" in v_rep["reply"] and "175" in v_rep["reply"]

                # Task G.2 & G.4: Verify profit figures match across Dashboard KPI, Why? panel, and spoken profit (1 campaign & 2 campaigns)
                why_idle = client.get("/api/why/KPI-PROFIT", headers=h).json()
                assert "+Rs 0" in why_idle["merchant_plain"] and "Grade C" in why_idle["merchant_plain"]

                client.post("/api/campaigns/CMP-WINBACK-01/simulate", headers=h, json={"mode": "canonical"})
                v_prof1 = client.post("/api/voice-command", headers=h, json={"utterance": "What is my profit?", "lang": "en"}).json()
                assert "222" in v_prof1["reply"] and "91.5" in v_prof1["reply"] and "5 percent Paytm promo fee" in v_prof1["reply"]

                # Simulate 2nd campaign too (CMP-DEADHOUR-02) and verify spoken profit matches multi-campaign KPI sum!
                client.post("/api/campaigns/CMP-DEADHOUR-02/simulate", headers=h, json={"mode": "canonical"})
                ov_both = client.get("/api/overview", headers=h).json()["kpis"]
                why_both = client.get("/api/why/KPI-PROFIT", headers=h).json()
                v_prof_both = client.post("/api/voice-command", headers=h, json={"utterance": "What is my profit?", "lang": "en"}).json()
                pre_val = ov_both["estimated_net_profit_pre_fee_inr"]
                exp_pre = str(int(round(pre_val))) if abs(pre_val - round(pre_val)) < 0.05 else f"{pre_val:.2f}"
                assert exp_pre in v_prof_both["reply"] and exp_pre in why_both["merchant_plain"]

            print("  [PASS] 01. Tasks A, E, G & Mode 1 (No Keys, sample-date wording, 2x205x12=4920, multi-campaign profit parity) verified")

        # ------------------------------------------------------------------
        # 2. MODE 2: GROQ ONLY (Sarvam unset, Groq active)
        # ------------------------------------------------------------------
        with tempfile.TemporaryDirectory() as tmp2, run_full_mock_groq_server("groq-tok-m2") as (groq_url, groq_state):
            _reset_all_env(
                tmp2,
                {
                    "PUBLIC_DEPLOY": "false",
                    "GROQ_API_KEY": "groq-tok-m2",
                    "GROQ_BASE_URL": groq_url,
                },
            )
            with TestClient(app) as client:
                h = {"X-Demo-Session": "mode2-groq-sess"}
                ps = client.get("/api/providers/status", headers=h).json()
                assert ps["tier"] == "groq" and ps["provider_in_use"] == "Groq (Secondary)"

                # Groq TTS (EN) + persistent cache hit on 2nd call
                t1 = client.post("/api/tts", headers=h, json={"text": "Hello Ramesh", "lang": "en"}).json()
                assert t1["provider"] == "groq_live" and t1["audio_base64"]
                calls_b4 = len(groq_state.requests_log)
                t2 = client.post("/api/tts", headers=h, json={"text": "Hello Ramesh", "lang": "en"}).json()
                assert t2["provider"] == "groq_cached" and t2["cached"] is True
                assert len(groq_state.requests_log) == calls_b4

                # Groq STT (multilingual Whisper)
                wav_b64 = base64.b64encode(make_silent_wav_bytes()).decode("ascii")
                s1 = client.post("/api/stt", headers=h, json={"audio_base64": wav_b64, "lang": "hi", "duration_seconds": 3.0}).json()
                assert s1["provider"] == "groq_live" and s1["transcript"] == "Customers today"

                # Groq Chat + repeat cache hit
                q1 = client.post("/api/merchant-qa", headers=h, json={"question": "Summarize my 30 day store sales.", "lang": "en"}).json()
                assert q1["mode"] == "groq_grounded" and q1["provider"] == "groq" and q1["cached"] is False
                calls_b4_q = len(groq_state.requests_log)
                q2 = client.post("/api/merchant-qa", headers=h, json={"question": "Summarize my 30 day store sales.", "lang": "en"}).json()
                assert q2["mode"] == "groq_grounded" and q2["cached"] is True
                assert len(groq_state.requests_log) == calls_b4_q

            print("  [PASS] 02. Mode 2 (Groq Only: TTS, Whisper STT, Chat & SQLite Cache) verified")

        # ------------------------------------------------------------------
        # 3. MODE 3: SARVAM ONLY (Primary TTS/STT/Chat + Pre-warm + 10s Cap + SARVAM_MAX_CALLS)
        # ------------------------------------------------------------------
        with tempfile.TemporaryDirectory() as tmp3, run_mock_sarvam_server("sarvam-tok-m3") as (sarvam_url, sarvam_state):
            _reset_all_env(
                tmp3,
                {
                    "PUBLIC_DEPLOY": "false",
                    "SARVAM_API_KEY": "sarvam-tok-m3",
                    "SARVAM_BASE_URL": sarvam_url,
                    "SARVAM_MAX_CALLS": "45",
                    "SARVAM_SESSION_MAX_CALLS": "40",
                },
            )
            with TestClient(app) as client:
                h = {"X-Demo-Session": "mode3-sarvam-sess"}
                ps = client.get("/api/providers/status", headers=h).json()
                assert ps["tier"] == "sarvam" and ps["provider_in_use"] == "Sarvam (Primary)"
                assert ps["sarvam"]["models"]["chat"] == "sarvam-105b-conversations"
                assert ps["sarvam"]["models"]["stt"] == "saaras:v4"
                assert ps["sarvam"]["models"]["tts"] == "bulbul:v3"

                # Sarvam Chat across EN / HI / KN + Indic-digit hallucination rejection
                sarvam_state.next_chat_reply = "30 ದಿನಗಳಲ್ಲಿ 917 ಪೇಮೆಂಟ್ ಮೂಲಕ 174685 ರೂಪಾಯಿ ಬಂದಿದೆ."
                q_kn = client.post("/api/merchant-qa", headers=h, json={"question": "Give an evening reflection in Kannada", "lang": "kn"}).json()
                assert q_kn["mode"] == "sarvam_grounded" and q_kn["provider"] == "sarvam", q_kn

                # Hallucinated Devanagari number ('९९९९९९' = 999999) MUST be caught by numeric grounding gate!
                sarvam_state.next_chat_reply = "आपकी दुकान में ९९९९९९ रुपये की बिक्री हुई।"
                q_bad = client.post("/api/merchant-qa", headers=h, json={"question": "Open ended Hindi reflection", "lang": "hi"}).json()
                assert q_bad["mode"] == "deterministic_fallback" and q_bad["grounded_verified"] is False
                assert "999999" in q_bad["ungrounded_numbers"]

                # 10-second spoken recording cap blocks >10s clip with 0 HTTP calls
                wav_b64 = base64.b64encode(make_silent_wav_bytes()).decode("ascii")
                cnt_before_long = len(sarvam_state.requests_log)
                s_long = client.post("/api/stt", headers=h, json={"audio_base64": wav_b64, "lang": "kn", "duration_seconds": 12.0}).json()
                assert s_long["provider"] == "browser_webspeech"
                assert "10-second" in (s_long["fallback_reason"] or "")
                assert len(sarvam_state.requests_log) == cnt_before_long

                # Valid <=10s STT clip succeeds on saaras:v4
                s_ok = client.post("/api/stt", headers=h, json={"audio_base64": wav_b64, "lang": "kn", "duration_seconds": 4.0}).json()
                assert s_ok["provider"] == "sarvam_live" and "approve" in s_ok["transcript"].lower()

                # Pre-warm caches all 30 fixed phrases (10 x 3 languages); 2nd pre-warm makes 0 API calls!
                pw1 = client.post("/api/providers/prewarm", headers=h).json()
                assert pw1["total_fixed_phrases"] == 30
                assert pw1["cached_available"] == 30 and pw1["newly_cached"] >= 27 and pw1["fallback_unrecorded"] == 0
                cnt_after_pw1 = len(sarvam_state.requests_log)

                pw2 = client.post("/api/providers/prewarm", headers=h).json()
                assert pw2["already_cached"] == 30 and pw2["newly_cached"] == 0
                assert len(sarvam_state.requests_log) == cnt_after_pw1

            # Verify SARVAM_MAX_CALLS hard ceiling falls back cleanly once reached
            _reset_all_env(
                tmp3,
                {
                    "PUBLIC_DEPLOY": "false",
                    "SARVAM_API_KEY": "sarvam-tok-m3",
                    "SARVAM_BASE_URL": sarvam_url,
                    "SARVAM_MAX_CALLS": "2",
                    "PROVIDER_CACHE_DB_PATH": str(Path(tmp3) / "cap_test_cache.db"),
                    "SARVAM_CACHE_DIR": str(Path(tmp3) / "cap_test_audio"),
                    "SARVAM_LEDGER_PATH": str(Path(tmp3) / "cap_test_ledger.json"),
                },
            )
            with TestClient(app) as client:
                h_cap = {"X-Demo-Session": "mode3-cap-sess"}
                c1 = client.post("/api/tts", headers=h_cap, json={"text": "Unique phrase one", "lang": "en"}).json()
                c2 = client.post("/api/tts", headers=h_cap, json={"text": "Unique phrase two", "lang": "en"}).json()
                c3 = client.post("/api/tts", headers=h_cap, json={"text": "Unique phrase three", "lang": "en"}).json()
                assert c1["provider"] == "sarvam_live" and c2["provider"] == "sarvam_live"
                assert c3["provider"] == "browser_webspeech"

            print("  [PASS] 03. Mode 3 (Sarvam Only: bulbul:v3, saaras:v4, sarvam-105b-conversations, Pre-warm 30/30, 10s & call caps) verified")

        # ------------------------------------------------------------------
        # 4. MODE 4: SARVAM FORCED FAILURE -> SILENT FALLBACK TO GROQ & TEMPLATES
        # ------------------------------------------------------------------
        with (
            tempfile.TemporaryDirectory() as tmp4,
            run_mock_sarvam_server("sarvam-tok-m4") as (sarvam_url, sarvam_state),
            run_full_mock_groq_server("groq-tok-m4") as (groq_url, groq_state),
        ):
            sarvam_state.force_status = 503  # Simulate Sarvam outage / quota failure
            _reset_all_env(
                tmp4,
                {
                    "PUBLIC_DEPLOY": "false",
                    "SARVAM_API_KEY": "sarvam-tok-m4",
                    "SARVAM_BASE_URL": sarvam_url,
                    "GROQ_API_KEY": "groq-tok-m4",
                    "GROQ_BASE_URL": groq_url,
                },
            )
            with TestClient(app) as client:
                h = {"X-Demo-Session": "mode4-failover-sess"}
                # Chat falls back from Sarvam 503 -> Groq silently!
                qa_fb = client.post("/api/merchant-qa", headers=h, json={"question": "Summarize my 30 day store sales.", "lang": "en"}).json()
                assert qa_fb["mode"] == "groq_grounded" and qa_fb["provider"] == "groq", qa_fb

                # STT falls back from Sarvam -> Groq Whisper silently!
                wav_b64 = base64.b64encode(make_silent_wav_bytes()).decode("ascii")
                stt_fb = client.post("/api/stt", headers=h, json={"audio_base64": wav_b64, "lang": "en", "duration_seconds": 3.0}).json()
                assert stt_fb["provider"] == "groq_live"

                # Kannada TTS falls back from Sarvam -> Browser Web Speech silently!
                tts_kn_fb = client.post("/api/tts", headers=h, json={"text": "Namaskara Ramesh", "lang": "kn"}).json()
                assert tts_kn_fb["provider"] == "browser_webspeech"

                # Technical View status exposes small non-blocking fallback notice
                ps_after = client.get("/api/providers/status", headers=h).json()
                assert ps_after["last_fallback_notice"] and "503" in ps_after["last_fallback_notice"]

            print("  [PASS] 04. Mode 4 (Sarvam Forced 503 -> Automatic Silent Fallback to Groq & Web Speech + Technical Notice) verified")

        # ------------------------------------------------------------------
        # 5. TASK D: PUBLIC_DEPLOY=true + DEMO_PIN UNLOCK + IP RATE LIMIT + ZERO SECRET LEAKAGE
        # ------------------------------------------------------------------
        with tempfile.TemporaryDirectory() as tmp5, run_mock_sarvam_server("secret-sarvam-k5") as (sarvam_url, sarvam_state):
            secret_pin = "pin-9482-test"
            _reset_all_env(
                tmp5,
                {
                    "PUBLIC_DEPLOY": "true",
                    "DEMO_PIN": secret_pin,
                    "SARVAM_API_KEY": "secret-sarvam-k5",
                    "SARVAM_BASE_URL": sarvam_url,
                    "RATE_LIMIT_PER_MINUTE": "6",
                },
            )
            with TestClient(app) as client:
                h_pub = {"X-Demo-Session": "public-visitor-a"}
                h_other = {"X-Demo-Session": "public-visitor-b"}

                # Locked by default on PUBLIC_DEPLOY=true -> 0 Sarvam calls
                t_locked = client.post("/api/tts", headers=h_pub, json={"text": "Public locked test", "lang": "en"}).json()
                assert t_locked["provider"] == "browser_webspeech"
                assert len(sarvam_state.requests_log) == 0

                # Wrong PIN rejected with 403
                r_bad_pin = client.post("/api/demo/unlock", headers=h_pub, json={"pin": "wrong-pin"})
                assert r_bad_pin.status_code == 403

                # Correct DEMO_PIN unlocks session A ONLY; session B stays locked!
                r_ok_pin = client.post("/api/demo/unlock", headers=h_pub, json={"pin": secret_pin})
                assert r_ok_pin.status_code == 200 and r_ok_pin.json()["demo_unlocked"] is True

                t_unlocked = client.post("/api/tts", headers=h_pub, json={"text": "Public unlocked phrase", "lang": "en"}).json()
                assert t_unlocked["provider"] == "sarvam_live"

                # Session B is still locked for uncached phrases, BUT CAN play cached phrase at 0 API calls!
                t_b_uncached = client.post("/api/tts", headers=h_other, json={"text": "Uncached for B", "lang": "en"}).json()
                assert t_b_uncached["provider"] == "browser_webspeech"
                cnt_b4_cached = len(sarvam_state.requests_log)
                t_b_cached = client.post("/api/tts", headers=h_other, json={"text": "Public unlocked phrase", "lang": "en"}).json()
                assert t_b_cached["provider"] == "sarvam_cached" and len(sarvam_state.requests_log) == cnt_b4_cached

                # Confirm zero secret/PIN leakage across responses
                for check_path in ("/", "/api/health", "/api/overview", "/api/providers/status"):
                    body_txt = client.get(check_path, headers=h_pub).text
                    assert "secret-sarvam-k5" not in body_txt
                    assert secret_pin not in body_txt

                # Per-IP rate limiting (limit=6 per bucket -> 7th TTS call in 60s returns 429)
                got_429 = False
                for idx in range(6):
                    resp_rl = client.post("/api/tts", headers=h_other, json={"text": f"RL {idx}", "lang": "en"})
                    if resp_rl.status_code == 429:
                        got_429 = True
                        break
                assert got_429 is True, "Expected per-IP rate limiter to return HTTP 429"

            print("  [PASS] 05. Task D (PUBLIC_DEPLOY + DEMO_PIN isolation + cached playback + IP rate limit + zero secret leakage) verified")

        # ------------------------------------------------------------------
        # 6. TASK F: EXPORT PRE-WARMED ASSETS -> DELETE DB -> RESTART -> LOCKED VISITOR PLAYS EN/HI/KN AT 0 CALLS
        # ------------------------------------------------------------------
        with tempfile.TemporaryDirectory() as tmp6, run_mock_sarvam_server("sarvam-tok-f6") as (sarvam_url, sarvam_state):
            cache_db_f6 = Path(tmp6) / "provider_cache.db"
            prewarm_dir_f6 = Path(tmp6) / "assets_prewarmed"

            # Step 1: Pre-warm locally with key, then export to assets_prewarmed/
            _reset_all_env(
                tmp6,
                {
                    "PUBLIC_DEPLOY": "false",
                    "SARVAM_API_KEY": "sarvam-tok-f6",
                    "SARVAM_BASE_URL": sarvam_url,
                    "PROVIDER_CACHE_DB_PATH": str(cache_db_f6),
                    "PREWARMED_ASSETS_DIR": str(prewarm_dir_f6),
                },
            )
            with TestClient(app) as client:
                pw_res = client.post("/api/providers/prewarm", headers={"X-Demo-Session": "prewarm-builder"}).json()
                assert pw_res["cached_available"] == 30

            exp_summary = export_prewarmed_assets(cache_db_path=cache_db_f6, out_dir=prewarm_dir_f6)
            assert exp_summary["exported_unique_entries"] >= 27
            idx_txt = (prewarm_dir_f6 / "index.json").read_text(encoding="utf-8")
            assert "sarvam-tok-f6" not in idx_txt and "DEMO_PIN" not in idx_txt

            # Step 2: Delete provider_cache.db + runtime ledger (simulating Render ephemeral disk restart!)
            cache_db_f6.unlink()
            (Path(tmp6) / "ledger.json").unlink(missing_ok=True)
            assert not cache_db_f6.exists()
            sarvam_state.requests_log.clear()

            # Step 3: Restart app with PUBLIC_DEPLOY=true and DEMO_PIN locked
            _reset_all_env(
                tmp6,
                {
                    "PUBLIC_DEPLOY": "true",
                    "DEMO_PIN": "pin-locked-f6",
                    "SARVAM_API_KEY": "sarvam-tok-f6",
                    "SARVAM_BASE_URL": sarvam_url,
                    "PROVIDER_CACHE_DB_PATH": str(cache_db_f6),
                    "PREWARMED_ASSETS_DIR": str(prewarm_dir_f6),
                },
            )
            with TestClient(app) as client:
                h_locked = {"X-Demo-Session": "locked-render-visitor"}
                for lg in ("en", "hi", "kn"):
                    br = client.get(f"/api/briefing?lang={lg}&detail=false", headers=h_locked).json()
                    assert br["tts_provider"] == "sarvam_cached", (lg, br["tts_provider"])
                    assert br["audio_base64"], f"Missing seeded audio_base64 for {lg}"

                    tts_r = client.post("/api/tts", headers=h_locked, json={"text": br["short_script"], "lang": lg}).json()
                    assert tts_r["provider"] == "sarvam_cached" and tts_r["cached"] is True
                    assert tts_r["audio_base64"]

                # Confirm ZERO API calls hit MockSarvamServer and Sarvam call counter == 0!
                assert len(sarvam_state.requests_log) == 0
                ps_f6 = client.get("/api/providers/status", headers=h_locked).json()
                assert ps_f6["sarvam"]["calls"]["global_calls"] == 0
                assert ps_f6["sarvam"]["calls"]["session_calls"] == 0
                assert ps_f6["cache"]["tts_cached_count"] >= 27

            print("  [PASS] 06. Task F (Export prewarmed -> delete DB -> restart -> locked visitor plays EN/HI/KN at 0 API calls & 0 counter) verified")

        print("\nALL SARVAM-PRIMARY 4-MODE & TASKS A-F CHECKS PASSED.")
        return 0
    finally:
        os.environ.clear()
        os.environ.update(orig_env)
        reset_sarvam_runtime_counters()
        reset_security_state_for_tests()
        load_settings(force_reload=True)
        get_groq_qa(reset=True)


if __name__ == "__main__":
    raise SystemExit(run_suite())
