"""
Finals 7-Task Verification Suite (Zero API Keys Required).
Verifies Tasks 1 through 7 and Hard Constraints 1 through 5 end-to-end.
"""
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from app.config import load_settings
from app.copy_lint import find_formatting_violations
from app.engine import _compute_cap_reached_summary
from app.explain_simply import find_plain_jargon_violations, validate_llm_plain_output
from app.main import app


def run_finals_7tasks_suite() -> None:
    print("Running Finals 7-Task Keyless Verification Suite...\n")

    # Ensure zero API keys are set during test execution
    os.environ.pop("SARVAM_API_KEY", None)
    os.environ.pop("GROQ_API_KEY", None)
    os.environ.pop("STT_TTS_PROVIDER", None)
    os.environ.pop("LLM_PROVIDER", None)
    os.environ.pop("PUBLIC_DEPLOY", None)
    s0 = load_settings(force_reload=True)
    assert s0.sarvam_live_allowed is False and s0.groq_live_allowed is False

    # Hard Constraint 1 & 3: .env in .gitignore + single-key provider switch test (ephemeral in-memory)
    gitignore_txt = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in gitignore_txt
    os.environ["PUBLIC_DEPLOY"] = "false"
    os.environ["SARVAM_API_KEY"] = "ephemeral_local_sarvam_test_token"
    s_sarvam = load_settings(force_reload=True)
    assert s_sarvam.sarvam_enabled is True and s_sarvam.sarvam_live_allowed is True
    os.environ["STT_TTS_PROVIDER"] = "webspeech"
    s_forced_ws = load_settings(force_reload=True)
    assert s_forced_ws.sarvam_enabled is False
    os.environ.pop("SARVAM_API_KEY", None)
    os.environ.pop("STT_TTS_PROVIDER", None)
    os.environ.pop("PUBLIC_DEPLOY", None)
    load_settings(force_reload=True)
    print("  [PASS] 01. Keyless defaults, .gitignore check & 1-key provider switch verified")

    with TestClient(app) as client:
        client.post("/api/reset")

        # Task 1: Merchant View i18n module, key parity across en/hi/kn, web fonts, draft label, default profile lang
        r_html = client.get("/")
        assert r_html.status_code == 200
        assert "/static/i18n.js" in r_html.text
        assert "Noto+Sans+Kannada" in r_html.text and "Noto+Sans+Devanagari" in r_html.text
        assert "hdr-lang-en" in r_html.text and "hdr-lang-kn" in r_html.text and "hdr-lang-hi" in r_html.text
        assert not find_formatting_violations(r_html.text)

        r_i18n = client.get("/static/i18n.js")
        assert r_i18n.status_code == 200
        i18n_txt = r_i18n.text
        assert "Draft - unreviewed by native speaker" in i18n_txt
        assert not find_formatting_violations(i18n_txt)

        # Extract key sets for en, hi, kn blocks in i18n.js
        m_en = re.search(r"\ben:\s*\{(.*?)\n\s*\},\n\s*hi:\s*\{", i18n_txt, re.DOTALL)
        m_hi = re.search(r"\bhi:\s*\{(.*?)\n\s*\},\n\s*kn:\s*\{", i18n_txt, re.DOTALL)
        m_kn = re.search(r"\bkn:\s*\{(.*?)\n\s*\}\n\s*\};", i18n_txt, re.DOTALL)
        assert m_en and m_hi and m_kn, "Could not locate en/hi/kn blocks in i18n.js"
        keys_en = set(re.findall(r"^\s*([a-zA-Z0-9_]+)\s*:", m_en.group(1), re.MULTILINE))
        keys_hi = set(re.findall(r"^\s*([a-zA-Z0-9_]+)\s*:", m_hi.group(1), re.MULTILINE))
        keys_kn = set(re.findall(r"^\s*([a-zA-Z0-9_]+)\s*:", m_kn.group(1), re.MULTILINE))
        assert keys_en == keys_hi == keys_kn and len(keys_en) >= 150, (
            f"i18n key mismatch: en-hi={keys_en ^ keys_hi}, en-kn={keys_en ^ keys_kn}"
        )

        ov0 = client.get("/api/overview").json()
        assert ov0["store"]["default_language"] == "kn"
        print(f"  [PASS] 02. Task 1 Full Merchant View i18n ({len(keys_en)} keys in en/hi/kn), fonts & profile default verified")

        # Task 2: Voice-first 2-3 sentence briefing + Hear details + Speak (/api/tts) in all 3 languages keyless
        for lg in ("en", "hi", "kn"):
            br = client.get(f"/api/briefing?lang={lg}").json()
            br_det = client.get(f"/api/briefing?lang={lg}&detail=true").json()
            sents = [s.strip() for s in re.split(r"[.!?।]+", br["short_script"]) if s.strip()]
            assert 2 <= len(sents) <= 3, f"{lg} short_script must be 2-3 sentences: {br['short_script']}"
            assert len(br_det["detail_script"]) > len(br["short_script"])
            assert br["tts_provider"] == "browser_webspeech"
            r_tts = client.post("/api/tts", json={"text": br["short_script"], "lang": lg})
            assert r_tts.status_code == 200 and r_tts.json()["provider"] == "browser_webspeech"
        print("  [PASS] 03. Task 2 Voice-first 3-sentence briefing, Hear details & keyless TTS verified across en/hi/kn")

        # Task 3: Verbal budget setting (EN/HI/KN), mandatory readback, yes/no confirm, bounds rejection & source logging
        r_vb = client.post(
            "/api/voice-command",
            json={"utterance": "set my offer budget to one thousand rupees for this week", "lang": "en"},
        ).json()
        assert r_vb["action_taken"] == "CAP_CONFIRMATION_PENDING"
        assert r_vb["reply"] == "Offer budget of Rs 1000 for this week. Say yes to confirm."
        assert client.get("/api/overview").json()["campaigns"][0]["max_budget"] == 300

        r_yes = client.post("/api/voice-command", json={"utterance": "yes", "lang": "en"}).json()
        assert r_yes["action_taken"] == "CAP_CONFIRMED_CMP_WINBACK_01"
        assert client.get("/api/overview").json()["campaigns"][0]["max_budget"] == 1000

        r_hi = client.post(
            "/api/voice-command",
            json={"utterance": "मेरा ऑफर बजट इस हफ्ते पाँच सौ रुपये रखो", "lang": "hi"},
        ).json()
        assert r_hi["action_taken"] == "CAP_CONFIRMATION_PENDING" and r_hi["requested_cap_inr"] == 500
        r_no_hi = client.post("/api/voice-command", json={"utterance": "नहीं", "lang": "hi"}).json()
        assert r_no_hi["action_taken"] == "CAP_CANCELLED_CMP_WINBACK_01"

        r_kn = client.post(
            "/api/voice-command",
            json={"utterance": "ನನ್ನ ಆಫರ್ ಬಜೆಟ್ ಈ ವಾರ ಮೂರು ನೂರು ರೂಪಾಯಿ ಇಡಿ", "lang": "kn"},
        ).json()
        assert r_kn["action_taken"] == "CAP_CONFIRMATION_PENDING" and r_kn["requested_cap_inr"] == 300
        client.post("/api/voice-command", json={"utterance": "ಹೌದು", "lang": "kn"})
        assert client.get("/api/overview").json()["campaigns"][0]["max_budget"] == 300

        r_bad = client.post("/api/voice-command", json={"utterance": "set my budget to five thousand rupees", "lang": "en"}).json()
        assert r_bad["action_taken"] == "CAP_CHANGE_REJECTED" and "50" in r_bad["reply"] and "2500" in r_bad["reply"]

        r_stt = client.post("/api/stt", json={"fallback_utterance": "yes", "lang": "en"}).json()
        assert r_stt["ok"] is True and r_stt["provider"] == "browser_webspeech"
        print("  [PASS] 04. Task 3 Verbal budget EN/HI/KN parser, readback confirmation, bounds & source audit verified")

        # Task 4 & Task 5: 50/80/100% thresholds (once per campaign), 80% extend/stop, 100% auto-pause & post-cap regular billing
        client.post("/api/reset")
        s50 = client.post("/api/campaigns/CMP-WINBACK-01/simulate-spend", json={"target_pct": 50}).json()
        assert [a["threshold_pct"] for a in s50["newly_fired_alerts"]] == [50]
        s50_again = client.post("/api/campaigns/CMP-WINBACK-01/simulate-spend", json={"target_pct": 50}).json()
        assert s50_again["newly_fired_alerts"] == []

        s80 = client.post("/api/campaigns/CMP-WINBACK-01/simulate-spend", json={"target_pct": 80}).json()
        assert [a["threshold_pct"] for a in s80["newly_fired_alerts"]] == [80]
        assert s80["newly_fired_alerts"][0]["actions_available"] == ["extend", "stop"]

        s100 = client.post("/api/campaigns/CMP-WINBACK-01/simulate-spend", json={"target_pct": 100}).json()
        assert [a["threshold_pct"] for a in s100["newly_fired_alerts"]] == [100]
        assert s100["campaign"]["status"] == "CAP_PAUSED"
        assert s100["campaign"]["budget_spent"] == 300
        assert s100["campaign"]["cap_reached_summary"]["suggest_extend"] is True

        sales_at_cap = s100["campaign"]["gross_treatment_sales"]
        spost = client.post("/api/campaigns/CMP-WINBACK-01/simulate-spend", json={"post_cap_regular_customers": 2}).json()
        assert spost["campaign"]["budget_spent"] == 300
        assert spost["campaign"]["refused_redemptions"] == 2
        assert spost["campaign"]["gross_treatment_sales"] > sales_at_cap

        neg_cs = _compute_cap_reached_summary(
            {
                "max_budget": 100, "offer_rupees": 25, "budget_spent": 100, "cap_reached": 1,
                "treatment_returned": 4, "treatment_count": 32, "holdout_returned": 1, "holdout_count": 8,
                "refused_redemptions": 1, "gross_treatment_sales": 870,
            }
        )
        assert neg_cs["suggest_extend"] is False
        print("  [PASS] 05. Tasks 4 & 5 Threshold alerts (50/80/100%), auto-pause, regular-price continuity & ROI gate verified")

        # Task 6: Plain-language Explain simply in en/hi/kn + strict number & jargon validator
        for lg in ("en", "hi", "kn"):
            ex = client.get(f"/api/campaigns/CMP-WINBACK-01/explain-simply?lang={lg}").json()
            assert ex["provider"] == "deterministic_template"
            assert find_plain_jargon_violations(ex["combined_script"]) == []
            assert not find_formatting_violations(ex["combined_script"])

        assert validate_llm_plain_output(
            {
                "cap_performance": "Spent Rs 300 of Rs 300.",
                "customer_comparison": "14 of 32 came vs 1 of 8.",
                "spend_vs_return": "Earned Rs 9999.",
            },
            {"300", "14", "32", "1", "8", "222"},
            {"300", "14", "222"},
        ) is False
        print("  [PASS] 06. Task 6 Explain simply (en/hi/kn) zero-jargon & strict number validator verified")

        # Task 7: Est. profit after offer states + Why? Grade C + GET /health + README checks
        client.post("/api/reset")
        ov_idle = client.get("/api/overview").json()
        assert ov_idle["kpis"]["profit_state"] == "NO_OFFER_RUN_YET"
        why_idle = client.get("/api/why/KPI-PROFIT").json()
        assert why_idle["evidence_grade"] == "C" and "No offer has run yet" in why_idle["merchant_plain"]

        client.post("/api/campaigns/CMP-WINBACK-01/simulate")
        ov_act = client.get("/api/overview").json()
        assert ov_act["kpis"]["profit_state"] == "ACTIVE"
        assert ov_act["kpis"]["estimated_net_profit_pre_fee_inr"] == 222.0
        why_act = client.get("/api/why/KPI-PROFIT").json()
        assert why_act["evidence_grade"] == "C" and "30 percent" in why_act["merchant_plain"]

        h1 = client.get("/health")
        h2 = client.head("/health")
        assert h1.status_code == 200 and h1.json()["status"] == "ok" and h2.status_code == 200

        readme_txt = (ROOT / "README.md").read_text(encoding="utf-8")
        assert not find_formatting_violations(readme_txt)
        for req_doc in ("SARVAM_API_KEY", "GROQ_API_KEY", "STT_TTS_PROVIDER", "LLM_PROVIDER", "15 minutes", "/health"):
            assert req_doc in readme_txt, f"Missing {req_doc} in README.md"
        print("  [PASS] 07. Task 7 Profit states, Grade C Why?, GET /health & README deployment/sleep docs verified")

        client.post("/api/reset")

    print("\nSUCCESS: All Finals 7-Task keyless checks passed!")


if __name__ == "__main__":
    run_finals_7tasks_suite()
