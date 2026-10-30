"""
Stage 1 Unit, Statistical Reference, Concurrency, Cap-Invariance, Sarvam Mock, and Copy Lint Suite.
Run: python3 tests/test_stage1_unit.py
"""
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import Settings, get_settings, load_settings
from app.copy_lint import lint_merchant_copy
from app.database import init_and_seed_db, use_db_path
from app.engine import (
    approve_campaign,
    get_dashboard_overview,
    get_voice_briefing,
    handle_voice_command,
    redeem_single_pass_atomic,
    simulate_campaign_48h,
)
from app.ledger import CreditCapExceededError, SarvamCreditLedger
from app.providers.cache import PhraseAudioCache
from app.providers.sarvam import SarvamProvider, SarvamProviderError
from app.stats import (
    compute_breakeven_lift,
    compute_cap_binding_risk,
    compute_pooled_pilot_power_table,
    evaluate_itt_holdout_and_profit,
    fisher_exact_2x2,
    required_sample_size_two_prop,
    wilson_ci_95,
)
from tests.mock_sarvam_server import run_mock_sarvam_server


def test_config_and_public_deploy_safeguards() -> None:
    prev_render = os.environ.get("RENDER")
    prev_pub = os.environ.get("PUBLIC_DEPLOY")
    prev_sarvam = os.environ.get("SARVAM_ENABLED")
    prev_live = os.environ.get("SARVAM_LIVE_CALLS_ENABLED")
    prev_key = os.environ.get("SARVAM_API_KEY")
    try:
        os.environ["RENDER"] = "true"
        os.environ.pop("PUBLIC_DEPLOY", None)
        os.environ["SARVAM_ENABLED"] = "true"
        os.environ["SARVAM_LIVE_CALLS_ENABLED"] = "true"
        os.environ["SARVAM_API_KEY"] = "ephemeral-test-key"
        s = load_settings(force_reload=True)
        assert s.public_deploy is True, "RENDER=true must default public_deploy=True"
        assert s.sarvam_live_allowed is False, "public_deploy=True must block Sarvam live calls"
        assert s.groq_live_allowed is False, "public_deploy=True must block Groq live calls"
    finally:
        for k, v in [
            ("RENDER", prev_render),
            ("PUBLIC_DEPLOY", prev_pub),
            ("SARVAM_ENABLED", prev_sarvam),
            ("SARVAM_LIVE_CALLS_ENABLED", prev_live),
            ("SARVAM_API_KEY", prev_key),
        ]:
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        load_settings(force_reload=True)


def test_power_calculator_reference_values() -> None:
    # Decision 2 reference 1: Even 50/50 split (r = 1.0) for 12.5% vs 37.5% -> 46 per arm (92 total)
    even = required_sample_size_two_prop(0.125, 0.375, alpha=0.05, power=0.80, allocation_ratio=1.0)
    assert even["n_control"] == 46 and even["n_treatment"] == 46 and even["total_n"] == 92

    even_cc = required_sample_size_two_prop(
        0.125, 0.375, alpha=0.05, power=0.80, allocation_ratio=1.0, continuity_correction=True
    )
    assert even_cc["n_control"] == 54 and even_cc["n_treatment"] == 54

    # Decision 2 reference 2: Actual 80/20 split (r = 4.0) with 40/wave -> 31 control + 124 nudged = 155 (~4 waves)
    split_80_20 = required_sample_size_two_prop(
        0.125, 0.375, alpha=0.05, power=0.80, allocation_ratio=4.0, eligible_per_wave=40
    )
    assert split_80_20["n_control"] == 31
    assert split_80_20["n_treatment"] == 124
    assert split_80_20["total_n"] == 155
    assert split_80_20["waves_needed"] == 4

    # Textbook Fleiss reference: p1=0.20, p2=0.40, alpha=0.05, power=0.80, r=1.0 -> n=82 per arm
    ref_textbook = required_sample_size_two_prop(0.20, 0.40, alpha=0.05, power=0.80, allocation_ratio=1.0)
    assert ref_textbook["n_control"] == 82 and ref_textbook["n_treatment"] == 82

    # Exact Fisher & Wilson checks
    assert wilson_ci_95(12, 32) == (22.93, 54.75)
    assert wilson_ci_95(1, 8) == (2.24, 47.09)
    f = fisher_exact_2x2(12, 20, 1, 7)
    assert abs(f["p_two_sided"] - 0.236382) < 1e-5


def test_cap_vs_holdout_itt_invariance_and_warnings() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = str(Path(tmpdir) / "itt_test.db")
        with use_db_path(db_file):
            init_and_seed_db(force_reset=True)

            # 1. Verify cap-binding warning (>10% threshold) and suggested cap
            risk = compute_cap_binding_risk(32, 25, 300, assumed_redemption_rate=0.375, warn_threshold=0.10)
            assert risk["passes_issued"] == 32
            assert risk["face_exposure_inr"] == 800
            assert risk["max_funded_redemptions"] == 12
            assert risk["prob_exceeds_cap_pct"] == 42.2
            assert risk["warn_above_threshold"] is True
            assert risk["suggested_cap_inr"] == 400

            # 2. Verify passes are issued to ALL 32 nudged buyers (not limited to 12)
            approved = approve_campaign("CMP-WINBACK-01")
            assert approved["passes_issued_count"] == 32

            # 3. Canonical run at uncapped Rs 800 vs canonical Rs 300 vs tightly binding Rs 150 cap
            res_uncapped = simulate_campaign_48h("CMP-WINBACK-01", mode="canonical", override_max_budget=800)
            res_300 = simulate_campaign_48h("CMP-WINBACK-01", mode="canonical", override_max_budget=300)
            res_150 = simulate_campaign_48h("CMP-WINBACK-01", mode="canonical", override_max_budget=150)

            assert res_uncapped["cap_reached"] == 0 and res_uncapped["funded_redemptions"] == 12 and res_uncapped["refused_redemptions"] == 0
            assert res_300["cap_reached"] == 1 and res_300["funded_redemptions"] == 12 and res_300["refused_redemptions"] == 0
            assert res_150["cap_reached"] == 1 and res_150["funded_redemptions"] == 6 and res_150["refused_redemptions"] == 6
            assert res_150["budget_spent"] == 150

            # CRITICAL INVARIANCE CHECK: Holdout ITT comparison is 100% unchanged when cap binds!
            assert res_uncapped["evaluation"]["itt"] == res_300["evaluation"]["itt"]
            assert res_uncapped["evaluation"]["itt"] == res_150["evaluation"]["itt"]

            # 4. Also verify invariance in stochastic random-draw mode across seeds
            for seed in (42, 108, 2026):
                init_and_seed_db(force_reset=True)
                s_open = simulate_campaign_48h("CMP-WINBACK-01", mode="stochastic", seed=seed, override_max_budget=800)
                init_and_seed_db(force_reset=True)
                s_tight = simulate_campaign_48h("CMP-WINBACK-01", mode="stochastic", seed=seed, override_max_budget=100)
                assert s_open["evaluation"]["itt"] == s_tight["evaluation"]["itt"], (
                    f"ITT holdout comparison changed under binding cap for seed={seed}!"
                )
                assert s_tight["budget_spent"] <= 100
                expected_refused = max(0, s_open["treatment_returned"] - 4)
                assert s_tight["refused_redemptions"] == expected_refused


def test_atomic_concurrency_under_simultaneous_scans() -> None:
    """
    25 concurrent threads attempt to redeem Rs 25 passes at the exact same instant
    against a Rs 300 cap (12 funded redemptions max).
    Verifies zero race conditions: exactly 12 funded (Rs 300), 13 refused, 25 ITT returned.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = str(Path(tmpdir) / "concurrency_test.db")
        with use_db_path(db_file):
            init_and_seed_db(force_reset=True)
            approve_campaign("CMP-WINBACK-01")  # Issues 32 passes, cap = Rs 300 (12 redemptions)

            from app.database import get_conn
            conn = get_conn()
            cids = [
                r["customer_id"]
                for r in conn.execute(
                    "SELECT customer_id FROM campaign_passes WHERE campaign_id='CMP-WINBACK-01' AND arm='TREATMENT' ORDER BY pass_id ASC LIMIT 25"
                ).fetchall()
            ]
            conn.close()
            assert len(cids) == 25

        barrier = threading.Barrier(25)

        def worker(cid: str):
            with use_db_path(db_file):
                barrier.wait(timeout=10.0)
                return redeem_single_pass_atomic("CMP-WINBACK-01", cid, bill_amount=220)

        with ThreadPoolExecutor(max_workers=25) as pool:
            outcomes = list(pool.map(worker, cids))

        funded_threads = sum(1 for o in outcomes if o["status"] == "REDEEMED_FUNDED")
        refused_threads = sum(1 for o in outcomes if o["status"] == "REDEEMED_CAP_REFUSED")
        assert funded_threads == 12, f"Expected 12 funded, got {funded_threads}"
        assert refused_threads == 13, f"Expected 13 refused, got {refused_threads}"

        with use_db_path(db_file):
            ov = get_dashboard_overview()
            winback = next(c for c in ov["campaigns"] if c["campaign_id"] == "CMP-WINBACK-01")
            assert winback["budget_spent"] == 300
            assert winback["funded_redemptions"] == 12
            assert winback["refused_redemptions"] == 13
            assert winback["treatment_returned"] == 25
            assert winback["cap_reached"] == 1


def test_sarvam_credit_caps_and_fail_closed_circuit() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        ledger = SarvamCreditLedger(tmp / "ledger.json", tts_cap_pct=15.0, stt_cap_pct=15.0, total_cap_pct=30.0)

        # 0-balance fail-closed
        try:
            ledger.check_allowance("tts", 0.01)
            raise AssertionError("Expected 0-balance rejection")
        except CreditCapExceededError:
            pass

        # Set 100 credits -> 15 TTS, 15 STT, 30 Total
        ledger.set_balance(100.0)
        ledger.record_spend("tts", 12.0, "tts batch 1")
        ledger.record_spend("stt", 12.0, "stt batch 1")

        # Exceeding 15% TTS cap blocked
        try:
            ledger.check_allowance("tts", 3.5)
            raise AssertionError("Expected 15% TTS cap block")
        except CreditCapExceededError:
            pass

        # Combined 30% cap (12 + 12 + 7 = 31 > 30) blocked via translate
        try:
            ledger.check_allowance("translate", 7.0)
            raise AssertionError("Expected 30% combined cap block")
        except CreditCapExceededError:
            pass

        # Mock server HTTP 429 trips circuit breaker fail-closed
        with run_mock_sarvam_server(expected_token="mock-tok") as (url, state):
            base = get_settings()
            cfg = Settings(
                **{
                    **base.__dict__,
                    "public_deploy": False,
                    "sarvam_enabled": True,
                    "sarvam_live_calls_enabled": True,
                    "sarvam_api_key": "mock-tok",
                    "sarvam_base_url": url,
                    "sarvam_ledger_path": tmp / "ledger.json",
                    "sarvam_cache_dir": tmp / "cache",
                }
            )
            prov = SarvamProvider(settings=cfg, ledger=ledger, cache=PhraseAudioCache(tmp / "cache"))
            state.force_status = 429
            fallback_res = prov.synthesize("Uncached rate limit test", lang_code="en-IN", strict=False)
            assert fallback_res.provider == "browser_webspeech"
            assert ledger.summary()["halted"] is True


def test_merchant_copy_lint_and_draft_badges() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = str(Path(tmpdir) / "copy_test.db")
        with use_db_path(db_file):
            init_and_seed_db(force_reset=True)
            for lang in ("en", "kn", "hi"):
                br = get_voice_briefing(lang)
                res = lint_merchant_copy(br["script"], check_sentence_length=(lang == "en"))
                assert res["passed"], f"Briefing '{lang}' failed lint: {res['issues']}"
                if lang in ("kn", "hi"):
                    assert br["is_draft_translation"] is True
                    assert "DRAFT" in br["review_status"]
                else:
                    assert br["is_draft_translation"] is False
                    assert br["review_status"] == "EN author-checked, native review pending"

            for utt in ("Approve win-back", "Fast forward 48 hours", "Milk stock", "How were sales"):
                vr = handle_voice_command(utt, lang="en")
                res = lint_merchant_copy(vr["reply"], check_sentence_length=True)
                assert res["passed"], f"Voice reply failed lint: {res['issues']}"

    # Verify linter catches banned jargon, em dashes, and emojis
    bad_jargon = lint_merchant_copy("Your RFM cohort holdout p-value shows 5.8x ROI under DPDP.")
    assert not bad_jargon["passed"] and len(bad_jargon["issues"]) >= 5

    bad_dash = lint_merchant_copy("Good evening \u2014 your sales rose today.")
    assert not bad_dash["passed"]


def test_pooled_50_shop_power_and_breakeven_lift() -> None:
    tbl = compute_pooled_pilot_power_table(
        n_shops=50, control_per_shop=8, treatment_per_shop=32, p_control=0.125, lifts_pp=[4, 5, 6, 7, 8, 10]
    )
    assert tbl["n_control"] == 400 and tbl["n_treatment"] == 1600 and tbl["total_n"] == 2000
    by_lift = {int(r["lift_pp"]): r["power_pct"] for r in tbl["rows"]}
    assert by_lift == {4: 50.3, 5: 68.8, 6: 83.3, 7: 92.5, 8: 97.2, 10: 99.8}, f"Got {by_lift}"

    be = compute_breakeven_lift(p_control=0.125, avg_bill_inr=217.50, gross_margin_pct=30.0, offer_rupees=25.0, paytm_fee_pct=5.0)
    assert be["breakeven_lift_pre_fee_pp"] == 7.8
    assert be["breakeven_lift_post_fee_pp"] == 15.3


def test_session_ttl_max_count_and_size_limits() -> None:
    """
    Verifies all Render free-tier per-visitor session DB resource bounds:
      1. Idle TTL eviction (session_ttl_seconds).
      2. Max session count LRU eviction of oldest (max_active_sessions).
      3. Per-DB size limit eviction (max_session_db_bytes).
      4. Total session directory disk limit LRU eviction (max_total_sessions_bytes).
    """
    import time
    from app.sessions import (
        _SESSION_LAST_SEEN,
        active_session_summary,
        evict_stale_sessions,
        reset_session_tracker,
    )

    prev = {
        k: os.environ.get(k)
        for k in (
            "SESSION_STORAGE_DIR",
            "SESSION_TTL_SECONDS",
            "MAX_ACTIVE_SESSIONS",
            "MAX_SESSION_DB_BYTES",
            "MAX_TOTAL_SESSIONS_BYTES",
        )
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            os.environ["SESSION_STORAGE_DIR"] = tmpdir
            os.environ["SESSION_TTL_SECONDS"] = "60"
            os.environ["MAX_ACTIVE_SESSIONS"] = "3"
            os.environ["MAX_SESSION_DB_BYTES"] = "524288"        # 512 KB per DB
            os.environ["MAX_TOTAL_SESSIONS_BYTES"] = "1048576"  # 1 MB total dir
            load_settings(force_reload=True)
            reset_session_tracker()

            t0 = time.time()
            # Seed 4 sessions with staggered timestamps -> max_active_sessions=3 must evict oldest (s1)
            for idx, sid in enumerate(("sess0001", "sess0002", "sess0003", "sess0004")):
                p = Path(tmpdir) / f"sess_{sid}.db"
                p.write_bytes(b"x" * 200_000)  # 200 KB each
                _SESSION_LAST_SEEN[sid] = t0 + idx

            evict_stale_sessions(now_ts=t0 + 10)
            assert not (Path(tmpdir) / "sess_sess0001.db").exists(), "Oldest session should be evicted at max_count=3"
            assert (Path(tmpdir) / "sess_sess0002.db").exists()
            assert (Path(tmpdir) / "sess_sess0004.db").exists()

            # Per-DB size limit: bloat sess0003 beyond 512 KB -> evicted
            (Path(tmpdir) / "sess_sess0003.db").write_bytes(b"y" * 600_000)
            evict_stale_sessions(now_ts=t0 + 11)
            assert not (Path(tmpdir) / "sess_sess0003.db").exists(), "Oversized session DB must be evicted"

            # Total directory byte cap (1 MB): 3 files x 400 KB = 1.2 MB -> oldest evicted to stay <= 1 MB
            for idx, sid in enumerate(("capA0001", "capB0002", "capC0003")):
                (Path(tmpdir) / f"sess_{sid}.db").write_bytes(b"z" * 400_000)
                _SESSION_LAST_SEEN[sid] = t0 + 20 + idx
            _SESSION_LAST_SEEN.pop("sess0002", None)
            (Path(tmpdir) / "sess_sess0002.db").unlink(missing_ok=True)
            _SESSION_LAST_SEEN.pop("sess0004", None)
            (Path(tmpdir) / "sess_sess0004.db").unlink(missing_ok=True)

            evict_stale_sessions(now_ts=t0 + 25)
            summary = active_session_summary()
            assert int(summary["total_disk_bytes"]) <= 1_048_576, f"Total bytes exceeded cap: {summary}"
            assert not (Path(tmpdir) / "sess_capA0001.db").exists(), "Oldest session must be evicted under total byte cap"

            # TTL expiry: advance clock past 60s -> remaining sessions evicted
            evict_stale_sessions(now_ts=t0 + 200)
            assert active_session_summary()["active_sessions"] == 0
        finally:
            reset_session_tracker()
            for k, v in prev.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
            load_settings(force_reload=True)


def run_all() -> None:
    tests = [
        ("Config & PUBLIC_DEPLOY safeguards", test_config_and_public_deploy_safeguards),
        ("Power calculator (80/20 & 50/50) + Fisher/Wilson", test_power_calculator_reference_values),
        ("Pooled 50-shop pilot power table & break-even lift", test_pooled_50_shop_power_and_breakeven_lift),
        ("Cap-vs-Holdout ITT invariance & >10% warning", test_cap_vs_holdout_itt_invariance_and_warnings),
        ("25-thread atomic spend-cap concurrency stress test", test_atomic_concurrency_under_simultaneous_scans),
        ("Keyless Sarvam 15%/30% credit caps & fail-closed circuit", test_sarvam_credit_caps_and_fail_closed_circuit),
        ("Merchant copy linter & EN/KN/HI review badges", test_merchant_copy_lint_and_draft_badges),
        ("Render session TTL, max-count LRU, and DB/total size limits", test_session_ttl_max_count_and_size_limits),
    ]
    print("Running Stage 1 Unit & Concurrency Suite...\n")
    for idx, (label, fn) in enumerate(tests, start=1):
        fn()
        print(f"  [PASS] {idx:02d}. {label}")
    print(f"\nSUCCESS: {len(tests)}/{len(tests)} Stage 1 unit test groups passed!")


if __name__ == "__main__":
    run_all()
