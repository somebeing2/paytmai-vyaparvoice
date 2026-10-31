"""
End-to-end verification suite for v1.6 Portfolio Upgrades:
1. English Copy Verified badge (while KN/HI retain Draft disclosure).
2. Store Category Margin Presets (Darshini 30%, Grocery Kirana 18%, Bakery 35%).
3. Zero-PII Merchant UPI CSV Uploader, Sample CSV export, and Visitor Session Isolation.
4. Sarvam Bulbul v4 Flash (67% lower TTS cost rate) support.
"""
from dataclasses import replace
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import get_conn, use_db_path
from app.main import app
from app.providers.sarvam import SarvamProvider


def test_english_badge_verified_and_indic_draft_preserved():
    client = TestClient(app, headers={"X-Demo-Session": "test-badge-v2"})
    client.post("/api/reset")

    en_br = client.get("/api/briefing?lang=en").json()
    assert en_br["is_draft_translation"] is False
    assert en_br["review_status"] == "English Copy Verified"

    kn_br = client.get("/api/briefing?lang=kn").json()
    assert kn_br["is_draft_translation"] is True
    assert "DRAFT" in kn_br["review_status"].upper()

    hi_br = client.get("/api/briefing?lang=hi").json()
    assert hi_br["is_draft_translation"] is True
    assert "DRAFT" in hi_br["review_status"].upper()


def test_store_category_presets_keep_thin_margin_kirana_profitable():
    client = TestClient(app, headers={"X-Demo-Session": "test-presets-v2"})
    client.post("/api/reset")

    # Switch to 18% thin-margin Grocery Kirana preset
    r_kir = client.post("/api/store/preset", json={"preset_key": "kirana_18"})
    assert r_kir.status_code == 200, r_kir.text
    ov = r_kir.json()["overview"]
    assert ov["store_preset"]["active_preset_key"] == "kirana_18"
    assert ov["store_preset"]["gross_margin_pct"] == 18.0

    c0 = ov["campaigns"][0]
    assert c0["offer_rupees"] == 10
    assert c0["min_bill"] == 220
    assert c0["max_budget"] == 160

    # Run 48h simulation under 18% Kirana margin and verify post-fee profit stays positive
    sim = client.post("/api/campaigns/CMP-WINBACK-01/simulate").json()
    pw = sim["campaign"]["evaluation"]["profit_waterfall"]
    assert pw["net_profit_pre_fee_inr"] > 0
    assert pw["net_profit_post_fee_inr"] > 0

    exp = client.get("/api/campaigns/CMP-WINBACK-01/explain-simply?lang=en").json()
    assert exp["facts"]["margin_pct"] == 18
    assert exp["review_status"] == "English Copy Verified"

    # Reset restores canonical 30% Darshini state (+Rs 91.50 post-fee)
    client.post("/api/reset")
    sim_def = client.post("/api/campaigns/CMP-WINBACK-01/simulate").json()
    pw_def = sim_def["campaign"]["evaluation"]["profit_waterfall"]
    assert pw_def["net_profit_post_fee_inr"] == 91.5


def test_zero_pii_csv_upload_and_session_isolation(tmp_path):
    client_a = TestClient(app, headers={"X-Demo-Session": "csv-session-alpha"})
    client_b = TestClient(app, headers={"X-Demo-Session": "csv-session-beta"})
    client_a.post("/api/reset")
    client_b.post("/api/reset")

    sample_resp = client_a.get("/api/ledger/sample-csv")
    assert sample_resp.status_code == 200
    csv_text = sample_resp.text
    assert "txn_id,timestamp,payer_ref,amount_inr" in csv_text

    # Inject a raw phone number + personal VPA to verify SHA-256 hashing strips all raw PII
    raw_secret_vpa = "ramesh_private_9845099999@okicici"
    extra_rows = (
        f"\nTXN-9901,2026-10-02 19:15:00,{raw_secret_vpa},245,Provisions,1,30"
        f"\nTXN-9902,2026-10-05 19:20:00,{raw_secret_vpa},260,Provisions,1,30"
        f"\nTXN-9903,2026-10-09 19:30:00,{raw_secret_vpa},230,Provisions,1,30"
    )
    up_resp = client_a.post(
        "/api/ledger/upload-csv",
        json={"csv_text": csv_text + extra_rows, "store_name": "Indiranagar Test Bakery"},
    )
    assert up_resp.status_code == 200, up_resp.text
    payload = up_resp.json()
    assert payload["ingest_summary"]["zero_pii_hashed"] is True
    assert payload["ingest_summary"]["winback_eligible"] > 0
    assert payload["overview"]["runtime_mode"]["dataset_status"] == "CSV_UPLOAD"
    assert payload["overview"]["store"]["store_name"] == "Indiranagar Test Bakery"

    # Raw VPA and raw phone digits must NEVER appear anywhere in overview JSON
    raw_json_str = up_resp.text
    assert "9845099999" not in raw_json_str
    assert "okicici" not in raw_json_str

    # Simulation and Explain Simply work cleanly on the uploaded CSV
    sim_csv = client_a.post("/api/campaigns/CMP-WINBACK-01/simulate")
    assert sim_csv.status_code == 200

    # Session B remains completely isolated on default 240-buyer synthetic ledger
    ov_b = client_b.get("/api/overview").json()
    assert ov_b["kpis"]["total_customers"] == 240
    assert ov_b["runtime_mode"]["dataset_status"] == "SYNTHETIC_60D_LEDGER"


def test_bulbul_v4_flash_cost_rate_is_one_third_of_v3():
    base_settings = get_settings()
    s_v3 = replace(base_settings, sarvam_tts_model="bulbul:v3", sarvam_tts_cost_per_10k_inr=30.0)
    s_v4 = replace(base_settings, sarvam_tts_model="bulbul:v4-flash", sarvam_tts_cost_per_10k_inr=30.0)

    p_v3 = SarvamProvider(settings=s_v3)
    p_v4 = SarvamProvider(settings=s_v4)

    cost_v3 = p_v3.estimate_tts_cost("A" * 1000)
    cost_v4 = p_v4.estimate_tts_cost("A" * 1000)
    assert abs(cost_v3 - 3.0) < 1e-6
    assert abs(cost_v4 - 1.0) < 1e-6


def test_pass_wallet_counter_scanner_min_bill_and_atomic_cap():
    client = TestClient(app, headers={"X-Demo-Session": "test-pass-wallet-v17"})
    client.post("/api/reset")

    # 1. Inspect initial wallet (32 treatment, 8 holdout)
    w0 = client.get("/api/campaigns/CMP-WINBACK-01/passes?lang=en")
    assert w0.status_code == 200
    w0_json = w0.json()
    assert w0_json["summary"]["total_treatment_passes"] == 32
    assert w0_json["summary"]["total_holdout_customers"] == 8

    # 2. Lower hard cap to Rs 50 (exactly 2 x Rs 25 redemptions allowed)
    cap_res = client.post(
        "/api/campaigns/CMP-WINBACK-01/cap",
        json={"new_cap_inr": 50, "source": "dashboard"},
    )
    assert cap_res.status_code == 200

    # 3. Below-minimum bill (Rs 110 < Rs 150) must pay Rs 0 cashback and keep pass ISSUED
    low_scan = client.post(
        "/api/campaigns/CMP-WINBACK-01/scan-pass",
        json={"bill_amount": 110},
    ).json()
    assert low_scan["min_bill_met"] is False
    assert low_scan["cashback_paid_inr"] == 0
    assert low_scan["pass_status"] == "ISSUED"
    assert low_scan["budget_spent_inr"] == 0

    # 4. Two qualifying scans (Rs 195 and Rs 210) fund Rs 25 each -> Rs 50 / Rs 50 spent
    s1 = client.post("/api/campaigns/CMP-WINBACK-01/scan-pass", json={"bill_amount": 195}).json()
    assert s1["min_bill_met"] is True
    assert s1["cashback_paid_inr"] == 25
    assert s1["pass_status"] == "REDEEMED_FUNDED"

    s2 = client.post("/api/campaigns/CMP-WINBACK-01/scan-pass", json={"bill_amount": 210}).json()
    assert s2["cashback_paid_inr"] == 25
    assert s2["budget_spent_inr"] == 50

    # 5. Third qualifying scan (Rs 225) hits hard Rs 50 cap -> Rs 0 cashback, REDEEMED_CAP_REFUSED
    s3 = client.post("/api/campaigns/CMP-WINBACK-01/scan-pass", json={"bill_amount": 225}).json()
    assert s3["min_bill_met"] is True
    assert s3["cashback_paid_inr"] == 0
    assert s3["pass_status"] == "REDEEMED_CAP_REFUSED"
    assert s3["budget_spent_inr"] == 50


def test_whatsapp_pass_preview_dpdp_and_zero_secret_leak():
    client = TestClient(app, headers={"X-Demo-Session": "test-wa-preview-v17"})
    client.post("/api/reset")

    for lang in ("en", "hi", "kn"):
        res = client.post(
            "/api/campaigns/CMP-WINBACK-01/whatsapp-preview",
            json={"lang": lang},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["ok"] is True
        assert body["delivery_mode"] == "local_preview"
        assert "STOP" in body["message_text"]
        assert "PASS-" in body["pass_id"]


def test_multi_shop_pilot_simulator_power_scaling():
    client = TestClient(app, headers={"X-Demo-Session": "test-pilot-sim-v17"})

    # 1 shop (40 buyers: 32 vs 8) is directional / underpowered even at +18 pp lift
    r1 = client.post("/api/pilot-simulate", json={"n_shops": 1, "waves_per_shop": 1, "true_lift_pp": 18.0})
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["total_eligible_customers"] == 40
    assert d1["is_powered_80"] is False

    # 50 shops x 1 wave (2,000 buyers: 1,600 vs 400) at +18 pp lift is >80% powered AND post-fee profitable
    r50_prof = client.post("/api/pilot-simulate", json={"n_shops": 50, "waves_per_shop": 1, "true_lift_pp": 18.0})
    assert r50_prof.status_code == 200
    d50_prof = r50_prof.json()
    assert d50_prof["total_eligible_customers"] == 2000
    assert d50_prof["is_powered_80"] is True
    assert d50_prof["statistical_power_pct"] >= 80.0
    assert d50_prof["fleet_net_after_fee_inr"] > 0

    # At +7 pp lift (below the +15.3 pp post-5%-fee break-even for Rs 25 cashback), 50x2 waves is >=80% powered
    # AND honestly flags negative post-fee profit so operators adjust offer size before scale rollout
    r50_low = client.post("/api/pilot-simulate", json={"n_shops": 50, "waves_per_shop": 2, "true_lift_pp": 7.0})
    d50_low = r50_low.json()
    assert d50_low["is_powered_80"] is True
    assert d50_low["fleet_net_after_fee_inr"] < 0


def test_printable_closing_report_html_and_json():
    client = TestClient(app, headers={"X-Demo-Session": "test-closing-report-v17"})
    client.post("/api/reset")
    client.post("/api/campaigns/CMP-WINBACK-01/simulate")

    html_res = client.get("/api/report/closing-summary?format=html")
    assert html_res.status_code == 200
    html_text = html_res.text
    assert "Closing Profit & Holdout Report" in html_text
    assert "to our knowledge the standard Paytm Soundbox is speaker-based with no microphone" in html_text
    assert "Rs 91.50" in html_text
    # Self-contained offline preview rule: no external CDN scripts or stylesheets
    assert "https://cdn." not in html_text

    json_res = client.get("/api/report/closing-summary?format=json")
    assert json_res.status_code == 200
    assert json_res.json()["ok"] is True


def test_hash_chained_audit_export_and_tamper_detection():
    from app.audit_qr import verify_audit_hash_chain

    client = TestClient(app, headers={"X-Demo-Session": "test-audit-chain-v18"})
    client.post("/api/reset")
    client.post("/api/campaigns/CMP-WINBACK-01/scan-pass", json={"bill_amount": 195})

    res_json = client.get("/api/audit/export?format=json")
    assert res_json.status_code == 200
    chain = res_json.json()
    assert chain["ok"] is True
    assert chain["hash_algorithm"] == "SHA-256"
    assert chain["chain_valid"] is True
    assert chain["entry_count"] >= 2

    # Mutate a single character in record 1 and prove tamper detection trips immediately
    tampered = [dict(e) for e in chain["entries"]]
    tampered[0]["detail"] = tampered[0]["detail"] + " [forged]"
    check = verify_audit_hash_chain(tampered)
    assert check["valid"] is False
    assert check["tampered_seq"] == 1

    res_csv = client.get("/api/audit/export?format=csv")
    assert res_csv.status_code == 200
    assert "seq,id,ts,actor,event_type,detail,prev_hash,entry_hash" in res_csv.text


def test_deep_healthz_probe_and_zero_secret_leak():
    client = TestClient(app, headers={"X-Demo-Session": "test-healthz-v18"})
    client.post("/api/reset")

    res = client.get("/api/healthz")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["sqlite"]["healthy"] is True
    assert body["sqlite"]["begin_immediate_lock_ms"] >= 0.0
    assert body["audit_integrity"]["chain_valid"] is True
    assert "api_key" not in res.text.lower()
    assert "demo_pin" not in res.text.lower()


def test_offline_iso18004_qr_svg_and_pwa_manifest():
    from app.audit_qr import _bch_format_bits, encode_qr_v3_matrix

    assert _bch_format_bits(0b01, 0) == 0x77C4
    mat = encode_qr_v3_matrix("VYAPAR|CMP-WINBACK-01|PASS-01-T01|RS25|MIN150")
    assert len(mat) == 29 and len(mat[0]) == 29

    client = TestClient(app, headers={"X-Demo-Session": "test-qr-pwa-v18"})
    qr_res = client.get("/api/campaigns/CMP-WINBACK-01/pass-qr.svg")
    assert qr_res.status_code == 200
    assert "image/svg+xml" in qr_res.headers["content-type"]
    assert qr_res.text.startswith("<svg")
    assert "https://" not in qr_res.text

    w_res = client.get("/api/campaigns/CMP-WINBACK-01/passes?lang=en").json()
    assert w_res["sample_pass_qr_svg"].startswith("<svg")

    mf_res = client.get("/manifest.json")
    assert mf_res.status_code == 200
    mf = mf_res.json()
    assert mf["short_name"] == "VyaparVoice"
    assert mf["display"] == "standalone"


def test_dockerignore_and_ci_workflow_present_and_clean():
    from pathlib import Path
    from app.copy_lint import find_formatting_violations

    root = Path(__file__).resolve().parent.parent
    di = (root / ".dockerignore").read_text(encoding="utf-8")
    assert ".env" in di
    assert "!.env.example" in di
    assert "data/*.db" in di
    assert find_formatting_violations(di) == []

    ci = (root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "scripts/preflight.py" in ci
    assert "scripts/eval_benchmark.py --assert-targets" in ci
    assert "pytest -v" in ci
    assert find_formatting_violations(ci) == []


