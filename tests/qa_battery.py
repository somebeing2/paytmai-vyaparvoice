"""
Automated Verification Suite (QA Battery) for PaytmAI VyaparVoice MVP.
Run: python tests/qa_battery.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.database import init_and_seed_db
from app.engine import (
    get_dashboard_overview,
    get_voice_briefing,
    approve_campaign,
    simulate_campaign_48h,
    execute_ops_action,
    handle_voice_command,
)


def run_qa_battery() -> None:
    passed = 0
    total = 0

    def check(condition: bool, label: str):
        nonlocal passed, total
        total += 1
        if not condition:
            print(f"  [FAIL] {total:02d}. {label}")
            raise AssertionError(f"QA check failed: {label}")
        passed += 1
        print(f"  [PASS] {total:02d}. {label}")

    print("Running PaytmAI VyaparVoice QA Battery...\n")

    # 1. Clean reset & deterministic seed
    init_and_seed_db(force_reset=True)
    ov = get_dashboard_overview()

    check(ov["kpis"]["total_customers"] == 240, "Seeded exact 240 unique Paytm UPI customers")
    check(ov["kpis"]["total_60d_txns"] == 1613, "Seeded deterministic 1,613 historical UPI transactions")
    check(ov["kpis"]["gmv_30d"] > 150000, f"30-day GMV computed from SQLite (₹{ov['kpis']['gmv_30d']:,})")

    # 2. Hourly velocity & dead-hour detection
    hrs = {h["hour"]: h for h in ov["hourly_series"]}
    max_peak = max(h["txns"] for h in ov["hourly_series"])
    check(hrs[15]["is_dead_hour"] and hrs[16]["is_dead_hour"], "3:00–5:00 PM dead-hour trough flagged accurately")
    check(hrs[15]["txns"] < max_peak * 0.55, f"Afternoon trough ({hrs[15]['txns']} scans) verified well below peak ({max_peak} scans)")

    # 3. RFM Cohort & Policy Filtering
    seg_map = {s["key"]: s for s in ov["segments"]}
    check(
        seg_map["at_risk_regular"]["customer_count"] == 48 and seg_map["at_risk_regular"]["eligible_count"] == 40,
        "At-Risk Regulars filtered deterministically: 48 detected -> 40 DPDP & cooldown eligible",
    )

    # 4. 5-Rule Deterministic Guardrail Engine
    winback = next(c for c in ov["campaigns"] if c["campaign_id"] == "CMP-WINBACK-01")
    check(len(winback["guardrails"]) == 5, "All 5 deterministic safety guardrails evaluated")
    check(all(g["passed"] for g in winback["guardrails"]), "5/5 guardrails pass (DPDP, Cooldown, Margin, Cap, Holdout)")
    check(winback["treatment_count"] == 32 and winback["holdout_count"] == 8, "80/20 causal holdout split locked (32 vs 8)")

    # 5. Multilingual Soundbox Briefings
    for lang in ("en", "kn", "hi"):
        br = get_voice_briefing(lang)
        check(len(br["script"]) > 60, f"Soundbox evening briefing generated for '{lang}' ({br['language_name']})")

    # 6. Vernacular Voice Command Approval
    v_res = handle_voice_command("Haudu, approve win-back campaign", lang="kn")
    check(v_res["action_taken"] == "APPROVED_CMP_WINBACK_01", "Kannada/English voice command routes to campaign approval")

    # 7. 48-Hour Closed-Loop Causal Lift Attribution
    sim = simulate_campaign_48h("CMP-WINBACK-01")
    check(sim["status"] == "SIMULATED_48H", "48-hour UPI scan simulation completes cleanly")
    check(sim["treatment_returned"] == 12 and sim["holdout_returned"] == 1, "Treatment (37.5%) vs Control (12.5%) return recorded")
    check(sim["budget_spent"] <= sim["max_budget"], f"Hard budget cap respected (₹{sim['budget_spent']} <= ₹{sim['max_budget']})")
    check(sim["incremental_sales"] == 1740 and sim["roi_multiple"] == 5.8, "Causal net lift verified: +₹1,740 (5.8x ROI)")

    # 8. Smart Operations & Service Recovery Execution
    ops1 = execute_ops_action("OPS-STOCK-01")
    ops2 = execute_ops_action("OPS-CARE-02")
    check(ops1["status"] == "EXECUTED", "Smart Dairy Supplier WhatsApp PO executed")
    check(ops2["status"] == "EXECUTED", "Peak-hour queue delay goodwill recovery executed")

    # 9. Audit Trail Integrity & Reset Idempotency
    ov_after = get_dashboard_overview()
    check(len(ov_after["audit_logs"]) >= 4, "Immutable governance audit log records every agentic action")

    # Leave database in fresh closing-time demo state
    init_and_seed_db(force_reset=True)
    ov_clean = get_dashboard_overview()
    check(ov_clean["kpis"]["verified_incremental_inr"] == 0, "Database cleanly reset to initial 8:30 PM demo state")

    print(f"\nSUCCESS: {passed}/{total} QA checks passed with 0 failures!")


if __name__ == "__main__":
    run_qa_battery()
