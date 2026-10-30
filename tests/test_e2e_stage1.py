"""
Stage 1 End-to-End API, Session Isolation, and Admin Security Suite.
Run: python3 tests/test_e2e_stage1.py
"""
import os
from pathlib import Path
import sys
import tempfile

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import load_settings
from app.copy_lint import find_formatting_violations
from app.main import app


def run_e2e() -> None:
    print("Running Stage 1 FastAPI End-to-End & Session Isolation Suite...\n")
    with tempfile.TemporaryDirectory() as tmp_sess_dir:
        prev_sess_dir = os.environ.get("SESSION_STORAGE_DIR")
        prev_admin = os.environ.get("ADMIN_TOKEN")
        os.environ["SESSION_STORAGE_DIR"] = tmp_sess_dir
        os.environ["ADMIN_TOKEN"] = "test-stage1-admin-token"
        load_settings(force_reload=True)

        try:
            with TestClient(app) as visitor_a, TestClient(app) as visitor_b:
                # 1. Index HTML hygiene check (zero em/en dashes, zero emojis)
                r_html = visitor_a.get("/")
                assert r_html.status_code == 200
                html_issues = find_formatting_violations(r_html.text)
                assert not html_issues, f"index.html formatting violations: {html_issues}"
                assert "2,100+" not in r_html.text
                print("  [PASS] 01. Root HTML served cleanly with zero em/en dashes and zero emojis")

                # 2. Health & distinct session IDs assigned automatically
                ha = visitor_a.get("/api/health").json()
                hb = visitor_b.get("/api/health").json()
                assert ha["status"] == "ok" and hb["status"] == "ok"
                assert ha["session_id"] and hb["session_id"] and ha["session_id"] != hb["session_id"]
                print("  [PASS] 02. Concurrent visitors receive isolated session IDs and SQLite sandboxes")

                # 3. Briefings & draft status
                b_en = visitor_a.get("/api/briefing?lang=en").json()
                b_kn = visitor_a.get("/api/briefing?lang=kn").json()
                assert b_en["is_draft_translation"] is False
                assert b_kn["is_draft_translation"] is True
                print("  [PASS] 03. Multilingual briefings return deterministic scripts and KN draft badge")

                # 4. Power endpoint verification
                p80 = visitor_a.get("/api/power?allocation_ratio=4.0").json()
                p50 = visitor_a.get("/api/power?allocation_ratio=1.0").json()
                assert p80["n_control"] == 31 and p80["n_treatment"] == 124 and p80["total_n"] == 155
                assert p50["n_control"] == 46 and p50["n_treatment"] == 46
                print("  [PASS] 04. /api/power verifies 31C+124T=155 (80/20) and 46/arm (50/50)")

                # 5. Visitor A mutates campaign & simulates 48h; Visitor B stays untouched!
                va_voice = visitor_a.post(
                    "/api/voice-command",
                    json={"utterance": "Haudu, approve win-back campaign", "lang": "kn"},
                ).json()
                assert va_voice["action_taken"] == "APPROVED_CMP_WINBACK_01"

                va_sim = visitor_a.post("/api/campaigns/CMP-WINBACK-01/simulate", json={}).json()
                cmp_a = va_sim["campaign"]
                assert cmp_a["status"] == "SIMULATED_48H"
                assert cmp_a["passes_issued_count"] == 32
                assert cmp_a["cap_reached"] == 1
                assert cmp_a["refused_redemptions"] == 0
                assert cmp_a["evaluation"]["profit_waterfall"]["net_profit_pre_fee_inr"] == 222.0
                assert cmp_a["evaluation"]["profit_waterfall"]["paytm_fee_on_all_redeemed_bills_inr"] == 130.5
                assert cmp_a["evaluation"]["profit_waterfall"]["net_profit_post_fee_inr"] == 91.5

                ov_b = visitor_b.get("/api/overview").json()
                cmp_b = next(c for c in ov_b["campaigns"] if c["campaign_id"] == "CMP-WINBACK-01")
                assert cmp_b["status"] == "PENDING_APPROVAL"
                assert ov_b["kpis"]["verified_incremental_inr"] == 0
                print("  [PASS] 05. Visitor A full approval + 48h ITT simulation does not affect Visitor B")

                # 6. Visitor B approves; Visitor A resets -> Visitor B remains LIVE_DISPATCHED
                visitor_b.post("/api/campaigns/CMP-WINBACK-01/approve", json={"via": "1-Tap"})
                visitor_a.post("/api/reset")
                ov_a_after = visitor_a.get("/api/overview").json()
                ov_b_after = visitor_b.get("/api/overview").json()
                assert ov_a_after["campaigns"][0]["status"] == "PENDING_APPROVAL"
                assert ov_b_after["campaigns"][0]["status"] == "LIVE_DISPATCHED"
                print("  [PASS] 06. Per-session /api/reset resets only caller's sandbox")

                # 7. Admin token enforcement
                unauth = visitor_a.get("/api/admin/provider-status")
                wrong = visitor_a.get("/api/admin/provider-status", headers={"X-Admin-Token": "wrong"})
                good = visitor_a.get(
                    "/api/admin/provider-status", headers={"X-Admin-Token": "test-stage1-admin-token"}
                )
                assert unauth.status_code == 403 and wrong.status_code == 403 and good.status_code == 200
                print("  [PASS] 07. Admin endpoints fail closed (403) without valid X-Admin-Token")

        finally:
            if prev_sess_dir is None:
                os.environ.pop("SESSION_STORAGE_DIR", None)
            else:
                os.environ["SESSION_STORAGE_DIR"] = prev_sess_dir
            if prev_admin is None:
                os.environ.pop("ADMIN_TOKEN", None)
            else:
                os.environ["ADMIN_TOKEN"] = prev_admin
            load_settings(force_reload=True)

    print("\nSUCCESS: 7/7 Stage 1 E2E & Safeguard checks passed!")


if __name__ == "__main__":
    run_e2e()
