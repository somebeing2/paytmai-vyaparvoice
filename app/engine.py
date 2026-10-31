from datetime import datetime
import math
import random
import re
from typing import Any, Dict, List, Optional, Tuple

from .config import get_settings
from .copy_lint import assert_valid_merchant_copy
from .database import get_conn, get_db_lock
from .providers.groq_qa import get_groq_qa
from .providers.sarvam import SarvamProvider
from .stats import (
    compute_bayesian_profit_posterior,
    compute_breakeven_lift,
    compute_cap_binding_risk,
    compute_evidence_meter,
    compute_margin_fee_sensitivity_table,
    compute_what_if_scenario,
    evaluate_itt_holdout_and_profit,
    simulate_dose_response_curve,
)
from .templates import (
    EVIDENCE_GRADES,
    render_cap_warning_merchant,
    render_closing_briefing,
    render_merchant_question_answer,
    render_merchant_scorecard_summary,
    render_merchant_scorecard_verdict,
    render_voice_cap_confirmation_prompt,
    render_voice_cap_confirmed_reply,
    render_why_explanation,
)

STORE_INFO = {
    "merchant_id": "PYTM-BLR-88412",
    "store_name": "Sri Krishna Darshini & Provisions",
    "owner_name": "Ramesh Rao",
    "locality": "100 Feet Rd, Indiranagar, Bengaluru",
    "device": "Paytm AI Soundbox 4G (v3.2)",
    "default_language": "kn",
    "max_discount_pct": 22.0,
    "dataset_disclosure": "SYNTHETIC_SEED_20261025",
}


def now_label() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _ensure_pending_table(cur) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS pending_confirmations (
            campaign_id TEXT PRIMARY KEY,
            requested_cap_inr INTEGER NOT NULL,
            previous_cap_inr INTEGER NOT NULL,
            requested_via TEXT NOT NULL,
            ts TEXT NOT NULL
        )
        """
    )


def _get_campaign_assumed_rate(campaign_id: str) -> float:
    settings = get_settings()
    rates = settings.assumed_redemption_rates
    return float(rates.get(campaign_id, rates.get("default", 0.35)))


def _partition_eligible_customers(cur, segment_key: str, treatment_count: int, holdout_count: int) -> Tuple[List[str], List[str]]:
    settings = get_settings()
    rows = cur.execute(
        """
        SELECT customer_id FROM customers
        WHERE archetype = ? AND dpdp_consent = 1 AND last_promo_days_ago >= ?
        ORDER BY customer_id ASC
        """,
        (segment_key, settings.cooldown_days),
    ).fetchall()
    cids = [r["customer_id"] for r in rows]
    treat_cids = cids[:treatment_count]
    holdout_cids = cids[treatment_count : treatment_count + holdout_count]
    return treat_cids, holdout_cids


def _enrich_campaign_dict(cur, cmp_row: Dict[str, Any]) -> Dict[str, Any]:
    settings = get_settings()
    _ensure_pending_table(cur)
    item = dict(cmp_row)
    item["guardrails"] = compute_guardrails_for_campaign(cur, item)
    item["why_explanation"] = render_why_explanation(item["campaign_id"], item)

    assumed_p = _get_campaign_assumed_rate(item["campaign_id"])
    cap_risk = compute_cap_binding_risk(
        treatment_count=item["treatment_count"],
        offer_rupees=item["offer_rupees"],
        max_budget=item["max_budget"],
        assumed_redemption_rate=assumed_p,
        warn_threshold=settings.cap_overrun_warn_threshold,
    )
    if cap_risk["warn_above_threshold"]:
        cap_risk["merchant_warning"] = render_cap_warning_merchant(
            treatment_count=item["treatment_count"],
            offer_rupees=item["offer_rupees"],
            max_budget=item["max_budget"],
            max_funded_redemptions=cap_risk["max_funded_redemptions"],
            overrun_prob_pct=cap_risk["prob_exceeds_cap_pct"],
            suggested_cap_rupees=cap_risk["suggested_cap_inr"],
        )
    else:
        cap_risk["merchant_warning"] = None
    item["cap_risk"] = cap_risk

    pending_row = cur.execute(
        "SELECT * FROM pending_confirmations WHERE campaign_id = ?",
        (item["campaign_id"],),
    ).fetchone()
    item["cap_editor"] = {
        "min_cap_inr": settings.min_cap_inr,
        "max_cap_inr": settings.max_cap_inr,
        "presets_inr": list(settings.cap_presets_inr),
        "pending_confirmation": dict(pending_row) if pending_row else None,
    }

    passes_count = cur.execute(
        "SELECT COUNT(*) AS c FROM campaign_passes WHERE campaign_id = ? AND arm = 'TREATMENT'",
        (item["campaign_id"],),
    ).fetchone()["c"]
    item["passes_issued_count"] = int(passes_count)

    is_interim = item["status"] in ("LIVE_DISPATCHED", "PAUSED_STOP_LOSS")
    item["live_interim"] = {
        "is_interim": is_interim,
        "is_paused_stop_loss": item["status"] == "PAUSED_STOP_LOSS",
        "interim_banner": (
            "PAUSED BY MERCHANT STOP-LOSS - PASS REDEMPTIONS HALTED"
            if item["status"] == "PAUSED_STOP_LOSS"
            else "INTERIM DIRECTIONAL READOUT - DO NOT STOP EARLY FOR WINNER"
        ),
        "budget_spent_inr": int(item["budget_spent"]),
        "max_budget_inr": int(item["max_budget"]),
        "remaining_budget_inr": max(0, int(item["max_budget"]) - int(item["budget_spent"])),
        "budget_burn_pct": min(
            100.0, round((int(item["budget_spent"]) / max(1, int(item["max_budget"]))) * 100.0, 1)
        ),
    }

    has_readout = item["status"] == "SIMULATED_48H" or (is_interim and int(item["treatment_returned"]) > 0)
    if has_readout:
        funded_sales_row = cur.execute(
            """
            SELECT COALESCE(SUM(redeemed_bill_inr), 0) AS s
            FROM campaign_passes
            WHERE campaign_id = ? AND status = 'REDEEMED_FUNDED'
            """,
            (item["campaign_id"],),
        ).fetchone()
        funded_sales = float(funded_sales_row["s"] or 0.0)
        if funded_sales <= 0 and item["funded_redemptions"] > 0 and item["treatment_returned"] > 0:
            avg_b = item["gross_treatment_sales"] / max(1, item["treatment_returned"])
            funded_sales = item["funded_redemptions"] * avg_b

        evaluation = evaluate_itt_holdout_and_profit(
            treatment_count=item["treatment_count"],
            itt_treatment_returned=item["treatment_returned"],
            holdout_count=item["holdout_count"],
            holdout_returned=item["holdout_returned"],
            funded_redemptions=item["funded_redemptions"],
            refused_redemptions=item["refused_redemptions"],
            cap_reached=bool(item["cap_reached"]),
            offer_rupees=item["offer_rupees"],
            max_budget=item["max_budget"],
            gross_returning_sales_inr=float(item["gross_treatment_sales"]),
            funded_redeemed_sales_inr=funded_sales,
            gross_margin_pct=settings.default_gross_margin_pct,
            paytm_fee_pct=settings.paytm_promo_fee_pct,
            alpha=settings.alpha_two_sided,
            target_power=settings.target_power,
        )
        if is_interim:
            evaluation["itt"]["status_banner"] = (
                "INTERIM LIVE READOUT (wave still in progress; wait for full 48h window before judging)"
            )
        item["evaluation"] = evaluation

        pw = evaluation["profit_waterfall"]
        pow_80 = evaluation["power"]["at_campaign_split_80_20"]
        avg_ret_bill = (
            float(item["gross_treatment_sales"]) / max(1, int(item["treatment_returned"]))
            if int(item["treatment_returned"]) > 0
            else 217.50
        )
        bayes = compute_bayesian_profit_posterior(
            treatment_count=item["treatment_count"],
            itt_treatment_returned=item["treatment_returned"],
            holdout_count=item["holdout_count"],
            holdout_returned=item["holdout_returned"],
            offer_rupees=item["offer_rupees"],
            max_budget=item["max_budget"],
            avg_bill_inr=avg_ret_bill,
            gross_margin_pct=settings.default_gross_margin_pct,
            paytm_fee_pct=settings.paytm_promo_fee_pct,
        )
        ev_meter = compute_evidence_meter(
            n_current=int(item["treatment_count"]) + int(item["holdout_count"]),
            is_statistically_significant=evaluation["itt"]["is_statistically_significant"],
            single_effect_target_n=pow_80["total_n"],
            pooled_pilot_target_n=2000,
        )
        sens_table = compute_margin_fee_sensitivity_table(
            incremental_sales_inr=pw["incremental_sales_inr"],
            budget_spent_inr=float(item["budget_spent"]),
            funded_redeemed_sales_inr=funded_sales,
        )
        verdict = render_merchant_scorecard_verdict(
            net_profit_pre_fee=pw["net_profit_pre_fee_inr"],
            net_profit_post_fee=pw["net_profit_post_fee_inr"],
            prob_profit_pre_fee_pct=bayes["prob_profit_pre_fee_pct"],
            prob_profit_post_fee_pct=bayes["prob_profit_post_fee_pct"],
            is_significant=evaluation["itt"]["is_statistically_significant"],
            gross_margin_pct=settings.default_gross_margin_pct,
        )
        item["scorecard_detail"] = {
            "verdict": verdict,
            "bayesian_posterior": bayes,
            "evidence_meter": ev_meter,
            "sensitivity_table": sens_table,
            "evidence_grades": EVIDENCE_GRADES,
        }
        item["merchant_scorecard"] = render_merchant_scorecard_summary(
            treated_returned=item["treatment_returned"],
            treatment_count=item["treatment_count"],
            control_returned=item["holdout_returned"],
            control_count=item["holdout_count"],
            funded_redemptions=item["funded_redemptions"],
            refused_redemptions=item["refused_redemptions"],
            cap_reached=bool(item["cap_reached"]),
            budget_spent=item["budget_spent"],
            max_budget=item["max_budget"],
            gross_margin_pct=settings.default_gross_margin_pct,
            net_profit_pre_fee=pw["net_profit_pre_fee_inr"],
            net_profit_post_fee=pw["net_profit_post_fee_inr"],
            waves_needed_80_20=pow_80["waves_needed"],
            is_significant=evaluation["itt"]["is_statistically_significant"],
        )
    else:
        item["evaluation"] = None
        item["scorecard_detail"] = None
        item["merchant_scorecard"] = None

    return item


def get_dashboard_overview() -> Dict[str, Any]:
    settings = get_settings()
    conn = get_conn()
    cur = conn.cursor()
    _ensure_pending_table(cur)

    kpi_30d = cur.execute(
        """
        SELECT
            COUNT(*) AS txn_count,
            COALESCE(SUM(amount), 0) AS gmv_30d,
            ROUND(AVG(amount), 0) AS avg_ticket,
            COUNT(DISTINCT customer_id) AS active_customers
        FROM transactions
        WHERE days_ago <= 30 AND is_simulated = 0
        """
    ).fetchone()

    total_60d_txns = cur.execute(
        "SELECT COUNT(*) AS c FROM transactions WHERE is_simulated = 0"
    ).fetchone()["c"]
    total_customers = cur.execute("SELECT COUNT(*) AS c FROM customers").fetchone()["c"]

    repeat_custs = cur.execute(
        """
        SELECT COUNT(*) AS c FROM (
            SELECT customer_id FROM transactions WHERE is_simulated = 0 GROUP BY customer_id HAVING COUNT(*) >= 3
        )
        """
    ).fetchone()["c"]

    hourly_rows = cur.execute(
        """
        SELECT hour_of_day, COUNT(*) AS txns, COALESCE(SUM(amount), 0) AS revenue
        FROM transactions
        WHERE days_ago <= 30 AND is_simulated = 0
        GROUP BY hour_of_day
        ORDER BY hour_of_day ASC
        """
    ).fetchall()
    hourly_map = {r["hour_of_day"]: {"txns": r["txns"], "revenue": r["revenue"]} for r in hourly_rows}
    hourly_series = []
    for hr in range(7, 22):
        entry = hourly_map.get(hr, {"txns": 0, "revenue": 0})
        label = f"{hr if hr <= 12 else hr - 12}{'AM' if hr < 12 else 'PM'}"
        is_dead_hour = hr in (15, 16)
        hourly_series.append(
            {
                "hour": hr,
                "label": label,
                "txns": entry["txns"],
                "revenue": entry["revenue"],
                "is_dead_hour": is_dead_hour,
            }
        )

    segments_raw = cur.execute(
        """
        SELECT
            c.archetype,
            COUNT(DISTINCT c.customer_id) AS customer_count,
            SUM(CASE WHEN c.dpdp_consent = 1 AND c.last_promo_days_ago >= ? THEN 1 ELSE 0 END) AS eligible_count,
            ROUND(AVG(t_agg.visit_count), 1) AS avg_visits,
            ROUND(AVG(t_agg.min_days_ago), 0) AS avg_last_seen_days,
            COALESCE(SUM(t_agg.total_spend), 0) AS historical_gmv
        FROM customers c
        LEFT JOIN (
            SELECT
                customer_id,
                COUNT(*) AS visit_count,
                MIN(days_ago) AS min_days_ago,
                SUM(amount) AS total_spend
            FROM transactions
            WHERE is_simulated = 0
            GROUP BY customer_id
        ) t_agg ON c.customer_id = t_agg.customer_id
        GROUP BY c.archetype
        """,
        (settings.cooldown_days,),
    ).fetchall()

    segment_meta = {
        "loyal_champion": {
            "name": "Frequent Regulars",
            "badge": "Healthy Core",
            "color": "emerald",
            "action_hint": "Protect queue speed and milestone perks",
        },
        "at_risk_regular": {
            "name": "Silent Regulars (16 to 38d Silent)",
            "badge": "Priority Win-Back",
            "color": "amber",
            "action_hint": "Rs 25 return cashback on Rs 150+ UPI scan",
        },
        "afternoon_snack": {
            "name": "Afternoon 3 to 5 PM Visitors",
            "badge": "Slow-Hour Window",
            "color": "cyan",
            "action_hint": "Rs 20 Filter Coffee and Snack combo pass",
        },
        "new_or_casual": {
            "name": "First-Time / Casual Scanners",
            "badge": "2nd-Visit Opportunity",
            "color": "indigo",
            "action_hint": "Turn first scan into second visit within 10 days",
        },
    }

    segments = []
    for row in segments_raw:
        meta = segment_meta.get(
            row["archetype"],
            {"name": row["archetype"], "badge": "Group", "color": "slate", "action_hint": ""},
        )
        segments.append(
            {
                "key": row["archetype"],
                "name": meta["name"],
                "badge": meta["badge"],
                "color": meta["color"],
                "action_hint": meta["action_hint"],
                "customer_count": row["customer_count"],
                "eligible_count": row["eligible_count"],
                "avg_visits": row["avg_visits"],
                "avg_last_seen_days": int(row["avg_last_seen_days"] or 0),
                "historical_gmv": row["historical_gmv"],
            }
        )

    order_idx = {"at_risk_regular": 0, "afternoon_snack": 1, "loyal_champion": 2, "new_or_casual": 3}
    segments.sort(key=lambda x: order_idx.get(x["key"], 99))

    campaigns_raw = [
        dict(r)
        for r in cur.execute(
            "SELECT * FROM campaigns ORDER BY CASE WHEN campaign_id='CMP-WINBACK-01' THEN 0 ELSE 1 END, campaign_id ASC"
        ).fetchall()
    ]
    campaigns = [_enrich_campaign_dict(cur, c) for c in campaigns_raw]

    ops_actions = []
    for r in cur.execute("SELECT * FROM ops_actions ORDER BY action_id ASC").fetchall():
        od = dict(r)
        od["why_explanation"] = render_why_explanation(od["action_id"], od)
        ops_actions.append(od)

    recent_txns = [
        dict(r)
        for r in cur.execute(
            """
            SELECT t.txn_id, t.amount, t.days_ago, t.hour_of_day, t.category,
                   t.campaign_id, t.is_simulated, c.name_hint, c.upi_handle, c.archetype
            FROM transactions t
            JOIN customers c ON t.customer_id = c.customer_id
            ORDER BY t.is_simulated DESC, t.days_ago ASC, t.hour_of_day DESC
            LIMIT 18
            """
        ).fetchall()
    ]

    audit_logs = [dict(r) for r in cur.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 16").fetchall()]

    total_incremental = sum(c["incremental_sales"] for c in campaigns)
    total_net_profit_pre_fee = round(
        sum(
            c["evaluation"]["profit_waterfall"]["net_profit_pre_fee_inr"]
            for c in campaigns
            if c.get("evaluation")
        ),
        2,
    )
    conn.close()

    return {
        "store": STORE_INFO,
        "evidence_grades": EVIDENCE_GRADES,
        "runtime_mode": {
            "public_deploy": settings.public_deploy,
            "sarvam_live_allowed": settings.sarvam_live_allowed,
            "dataset_status": "SYNTHETIC_60D_LEDGER",
        },
        "cap_editor_bounds": {
            "min_cap_inr": settings.min_cap_inr,
            "max_cap_inr": settings.max_cap_inr,
            "presets_inr": list(settings.cap_presets_inr),
        },
        "breakeven_defaults": compute_breakeven_lift(),
        "kpis": {
            "gmv_30d": kpi_30d["gmv_30d"],
            "txn_count_30d": kpi_30d["txn_count"],
            "total_60d_txns": total_60d_txns,
            "avg_ticket": int(kpi_30d["avg_ticket"] or 0),
            "total_customers": total_customers,
            "repeat_rate_pct": round((repeat_custs / max(1, total_customers)) * 100, 1),
            "verified_incremental_inr": total_incremental,
            "estimated_net_profit_pre_fee_inr": total_net_profit_pre_fee,
        },
        "hourly_series": hourly_series,
        "segments": segments,
        "campaigns": campaigns,
        "ops_actions": ops_actions,
        "recent_txns": recent_txns,
        "audit_logs": audit_logs,
        "dose_response_preview": simulate_dose_response_curve(),
    }


def compute_guardrails_for_campaign(cur, cmp_row: Dict[str, Any]) -> List[Dict[str, Any]]:
    settings = get_settings()
    seg = cmp_row["segment_key"]
    total_seg = cur.execute("SELECT COUNT(*) AS c FROM customers WHERE archetype = ?", (seg,)).fetchone()["c"]
    consented = cur.execute(
        "SELECT COUNT(*) AS c FROM customers WHERE archetype = ? AND dpdp_consent = 1", (seg,)
    ).fetchone()["c"]
    cooldown_ok = cur.execute(
        "SELECT COUNT(*) AS c FROM customers WHERE archetype = ? AND dpdp_consent = 1 AND last_promo_days_ago >= ?",
        (seg, settings.cooldown_days),
    ).fetchone()["c"]

    disc_pct = round((cmp_row["offer_rupees"] / max(1, cmp_row["min_bill"])) * 100, 1)
    max_redemptions = cmp_row["max_budget"] // max(1, cmp_row["offer_rupees"])
    face_exposure = cmp_row["treatment_count"] * cmp_row["offer_rupees"]

    return [
        {
            "rule": "DPDP Act Consent Filter",
            "passed": True,
            "metric": f"{consented}/{total_seg} opted-in ({total_seg - consented} excluded)",
        },
        {
            "rule": "14-Day Anti-Spam Cooldown",
            "passed": True,
            "metric": f"{cooldown_ok}/{consented} clear ({consented - cooldown_ok} cooled down)",
        },
        {
            "rule": "Merchant Margin Floor (<=22%)",
            "passed": disc_pct <= STORE_INFO["max_discount_pct"],
            "metric": f"{disc_pct}% effective discount (Rs {cmp_row['offer_rupees']} on Rs {cmp_row['min_bill']}+)",
        },
        {
            "rule": "Hard Spend Stop vs Face Exposure",
            "passed": settings.min_cap_inr <= int(cmp_row["max_budget"]) <= settings.max_cap_inr,
            "metric": f"All {cmp_row['treatment_count']} passes issued (Rs {face_exposure} face); spend hard-stops at Rs {cmp_row['max_budget']} ({max_redemptions} paid)",
        },
        {
            "rule": "80/20 Intention-to-Treat Holdout",
            "passed": int(cmp_row["holdout_count"]) > 0,
            "metric": f"{cmp_row['treatment_count']} Nudged vs {cmp_row['holdout_count']} Silent Control",
        },
    ]


def evaluate_guardrail_attack(
    attack_text: str,
    record_audit: bool = False,
) -> Dict[str, Any]:
    """
    Task 4 interactive guardrail red-team evaluator ('Type your own attack').
    Deterministically parses prompt-injection phrases, discount ratios, consent/cooldown
    bypasses, cap bounds, and holdout removal, returning rule-by-rule PASS/BLOCK status.
    """
    settings = get_settings()
    raw = (attack_text or "").strip()
    low = raw.lower()

    injection_markers = [
        "ignore previous",
        "ignore all",
        "system prompt",
        "bypass",
        "override",
        "jailbreak",
        "disable guardrail",
        "forget rules",
        "sudo",
        "developer mode",
    ]
    hit_injection = [m for m in injection_markers if m in low]

    consent_bypass = any(
        p in low
        for p in [
            "without consent",
            "no consent",
            "unconsented",
            "all 240",
            "every customer",
            "all customers",
            "everyone",
            "opted out",
            "opt-out",
        ]
    )
    cooldown_bypass = any(
        p in low
        for p in [
            "every day",
            "daily",
            "every hour",
            "hourly",
            "spam",
            "every 2 days",
            "yesterday",
            "ignore cooldown",
            "no cooldown",
        ]
    )
    holdout_bypass = any(
        p in low
        for p in [
            "no holdout",
            "zero holdout",
            "0 holdout",
            "100% treatment",
            "no control",
            "without holdout",
            "send to all 40",
        ]
    )

    # Parse explicit percentage discount or Rs offer / Rs min_bill pairs
    offer_inr = 25
    min_bill_inr = 150
    cap_inr = 300

    pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%\s*(?:off|discount|cashback)?", low)
    pair_match = re.search(
        r"(?:rs\.?|inr|rupees?)?\s*(\d+)\s*(?:rupees?|rs\.?|inr)?\s*(?:off|cashback|voucher|pass|free)(?:\s+on|\s+above|\s+for)?\s*(?:rs\.?|inr|rupees?)?\s*(\d+)",
        low,
    )
    single_off_match = re.search(
        r"(?:give|send|offer)\s+(?:rs\.?|inr)?\s*(\d+)\s*(?:rupees?|rs\.?|inr)?\s*(?:off|cashback|free)",
        low,
    )
    cap_match = re.search(
        r"(?:cap|limit|budget)\s*(?:of|to|at|=)?\s*(?:rs\.?|inr)?\s*(-?\d+)",
        low,
    )

    if "free" in low and not pair_match and not pct_match:
        offer_inr, min_bill_inr = 150, 150
    elif pair_match:
        offer_inr = int(pair_match.group(1))
        min_bill_inr = max(1, int(pair_match.group(2)))
    elif pct_match:
        pct_val = float(pct_match.group(1))
        min_bill_inr = 100
        offer_inr = int(round(pct_val))
    elif single_off_match:
        offer_inr = int(single_off_match.group(1))
        min_bill_inr = 150

    if any(p in low for p in ["unlimited", "no cap", "no limit", "infinite budget", "zero limit"]):
        cap_inr = 999999
    elif cap_match:
        cap_inr = int(cap_match.group(1))

    eff_disc_pct = round((offer_inr / max(1, min_bill_inr)) * 100.0, 1)
    margin_ok = (0 < offer_inr) and (eff_disc_pct <= settings.max_discount_floor_pct)
    cap_ok = (settings.min_cap_inr <= cap_inr <= settings.max_cap_inr) and (cap_inr >= max(1, offer_inr))

    rules = [
        {
            "rule": "Closed-Schema & Prompt-Injection Lock",
            "passed": len(hit_injection) == 0,
            "detail": (
                "No override or prompt-injection tokens detected."
                if not hit_injection
                else f"Blocked override directive ({', '.join(hit_injection)}); offer terms are SQL/policy-locked."
            ),
        },
        {
            "rule": "DPDP Act Consent Filter",
            "passed": not consent_bypass,
            "detail": (
                "Restricted strictly to opted-in customers (dpdp_consent = 1)."
                if not consent_bypass
                else "Blocked attempt to message unconsented or opted-out UPI payers."
            ),
        },
        {
            "rule": "14-Day Anti-Spam Cooldown",
            "passed": not cooldown_bypass,
            "detail": (
                f"Enforces >= {settings.cooldown_days}-day gap since last campaign message."
                if not cooldown_bypass
                else f"Blocked high-frequency messaging violating the {settings.cooldown_days}-day cooldown."
            ),
        },
        {
            "rule": f"Merchant Margin Floor (<={settings.max_discount_floor_pct:.0f}%)",
            "passed": margin_ok,
            "detail": (
                f"Effective discount {eff_disc_pct}% (Rs {offer_inr} on Rs {min_bill_inr}+) is within {settings.max_discount_floor_pct:.0f}% floor."
                if margin_ok
                else f"Blocked {eff_disc_pct}% discount (Rs {offer_inr} on Rs {min_bill_inr}+) exceeding {settings.max_discount_floor_pct:.0f}% margin floor."
            ),
        },
        {
            "rule": f"Hard Spend Cap Bounds (Rs {settings.min_cap_inr} to Rs {settings.max_cap_inr})",
            "passed": cap_ok,
            "detail": (
                f"Hard spend stop Rs {cap_inr} lies within [Rs {settings.min_cap_inr}, Rs {settings.max_cap_inr}]."
                if cap_ok
                else f"Blocked cap Rs {cap_inr}; spend stop must stay within Rs {settings.min_cap_inr} to Rs {settings.max_cap_inr}."
            ),
        },
        {
            "rule": "Mandatory Silent Comparison Group",
            "passed": not holdout_bypass,
            "detail": (
                "Preserves 20% silent comparison group to measure normal walk-ins."
                if not holdout_bypass
                else "Blocked removal of silent comparison group; VyaparVoice never runs unmeasured blasts."
            ),
        },
    ]

    failed_rules = [r for r in rules if not r["passed"]]
    overall_passed = len(failed_rules) == 0

    if overall_passed:
        merchant_msg = (
            f"Safety check passed. Sending {offer_inr} rupees on {min_bill_inr} rupee bills "
            f"within a {cap_inr} rupee spending limit follows all store margin and privacy rules."
        )
    else:
        merchant_msg = (
            f"Safety lock blocked that request ({len(failed_rules)} rule violation"
            f"{'s' if len(failed_rules) != 1 else ''}). "
            f"Shop discounts cannot cross 22 percent, spending limits stay between {settings.min_cap_inr} and {settings.max_cap_inr} rupees, "
            f"and only permitted buyers clear of the 14-day gap can be messaged."
        )
    assert_valid_merchant_copy(merchant_msg, check_sentence_length=True)

    if record_audit:
        lock = get_db_lock()
        with lock:
            conn = get_conn()
            conn.execute(
                "INSERT INTO audit_logs (ts, actor, event_type, detail) VALUES (?, ?, ?, ?)",
                (
                    now_label(),
                    "Guardrail Red-Team",
                    "GUARDRAIL_CHECK_PASSED" if overall_passed else "GUARDRAIL_ATTACK_BLOCKED",
                    f"Input='{raw[:90]}' -> {'ALLOWED' if overall_passed else 'BLOCKED'} "
                    f"({len(failed_rules)} violations; parsed Rs {offer_inr}/Rs {min_bill_inr}, cap Rs {cap_inr}).",
                ),
            )
            conn.commit()
            conn.close()

    return {
        "attack_text": raw,
        "passed": overall_passed,
        "verdict": "ALLOWED" if overall_passed else "BLOCKED",
        "violations_count": len(failed_rules),
        "parsed_terms": {
            "offer_rupees": offer_inr,
            "min_bill": min_bill_inr,
            "effective_discount_pct": eff_disc_pct,
            "max_budget": cap_inr,
        },
        "rules": rules,
        "merchant_safe_reply": merchant_msg,
    }


def evaluate_what_if(
    offer_rupees: int = 25,
    min_bill: int = 150,
    max_budget: int = 300,
    gross_margin_pct: float = 30.0,
    paytm_fee_pct: float = 5.0,
    allocation_ratio: float = 4.0,
) -> Dict[str, Any]:
    settings = get_settings()
    return compute_what_if_scenario(
        offer_rupees=offer_rupees,
        min_bill=min_bill,
        max_budget=max_budget,
        gross_margin_pct=gross_margin_pct,
        paytm_fee_pct=paytm_fee_pct,
        allocation_ratio=allocation_ratio,
        eligible_count=40,
        avg_bill_inr=217.50,
        max_discount_floor_pct=settings.max_discount_floor_pct,
        min_cap_inr=settings.min_cap_inr,
        max_cap_inr=settings.max_cap_inr,
    )


def update_campaign_cap(
    campaign_id: str,
    new_cap_inr: int,
    actor: str = "Merchant Cap Editor",
    confirmed: bool = True,
) -> Dict[str, Any]:
    """
    Task 9 Cap Editor with hard bounds check ([min_cap_inr, max_cap_inr]),
    two-step voice confirmation support, and immutable audit logging.
    """
    settings = get_settings()
    lock = get_db_lock()
    with lock:
        conn = get_conn()
        cur = conn.cursor()
        _ensure_pending_table(cur)
        cmp_row = cur.execute("SELECT * FROM campaigns WHERE campaign_id = ?", (campaign_id,)).fetchone()
        if not cmp_row:
            conn.close()
            raise ValueError("Campaign not found")

        offer = int(cmp_row["offer_rupees"])
        old_cap = int(cmp_row["max_budget"])
        min_allowed = max(settings.min_cap_inr, offer)
        max_allowed = settings.max_cap_inr

        if new_cap_inr < min_allowed or new_cap_inr > max_allowed:
            cur.execute(
                "INSERT INTO audit_logs (ts, actor, event_type, detail) VALUES (?, ?, ?, ?)",
                (
                    now_label(),
                    actor,
                    "CAP_CHANGE_REJECTED",
                    f"Rejected cap Rs {new_cap_inr} on {campaign_id}; valid bounds are Rs {min_allowed} to Rs {max_allowed}.",
                ),
            )
            conn.commit()
            conn.close()
            raise ValueError(
                f"Spending limit must be between Rs {min_allowed} and Rs {max_allowed} (at least 1 pass of Rs {offer})."
            )

        assumed_p = _get_campaign_assumed_rate(campaign_id)
        new_risk = compute_cap_binding_risk(
            treatment_count=int(cmp_row["treatment_count"]),
            offer_rupees=offer,
            max_budget=new_cap_inr,
            assumed_redemption_rate=assumed_p,
            warn_threshold=settings.cap_overrun_warn_threshold,
        )

        if not confirmed:
            ts = now_label()
            cur.execute(
                """
                INSERT OR REPLACE INTO pending_confirmations
                (campaign_id, requested_cap_inr, previous_cap_inr, requested_via, ts)
                VALUES (?, ?, ?, ?, ?)
                """,
                (campaign_id, int(new_cap_inr), old_cap, actor, ts),
            )
            cur.execute(
                "INSERT INTO audit_logs (ts, actor, event_type, detail) VALUES (?, ?, ?, ?)",
                (
                    ts,
                    actor,
                    "CAP_CONFIRMATION_REQUESTED",
                    f"Pending merchant confirmation on {campaign_id}: Rs {old_cap} -> Rs {new_cap_inr} "
                    f"(up to {new_risk['max_funded_redemptions']} paid redemptions; overrun risk {new_risk['prob_exceeds_cap_pct']}%).",
                ),
            )
            conn.commit()
            enriched = _enrich_campaign_dict(cur, dict(cmp_row))
            enriched["confirmation_prompt"] = render_voice_cap_confirmation_prompt(
                old_cap=old_cap,
                new_cap=int(new_cap_inr),
                offer_rupees=offer,
                overrun_prob_pct=new_risk["prob_exceeds_cap_pct"],
            )
            conn.close()
            return enriched

        spent = int(cmp_row["budget_spent"])
        new_cap_reached = 1 if (spent >= int(new_cap_inr) and int(new_cap_inr) > 0) or int(cmp_row["refused_redemptions"]) > 0 else 0
        cur.execute(
            "UPDATE campaigns SET max_budget = ?, cap_reached = ? WHERE campaign_id = ?",
            (int(new_cap_inr), new_cap_reached, campaign_id),
        )
        cur.execute("DELETE FROM pending_confirmations WHERE campaign_id = ?", (campaign_id,))
        cur.execute(
            "INSERT INTO audit_logs (ts, actor, event_type, detail) VALUES (?, ?, ?, ?)",
            (
                now_label(),
                actor,
                "CAP_UPDATED",
                f"Updated {campaign_id} hard spend cap: Rs {old_cap} -> Rs {new_cap_inr} "
                f"({new_risk['max_funded_redemptions']} max funded redemptions; overrun risk {new_risk['prob_exceeds_cap_pct']}%).",
            ),
        )
        conn.commit()
        updated_raw = dict(cur.execute("SELECT * FROM campaigns WHERE campaign_id = ?", (campaign_id,)).fetchone())
        enriched = _enrich_campaign_dict(cur, updated_raw)
        conn.close()
        return enriched


def resolve_pending_cap_change(
    campaign_id: str,
    confirm: bool = True,
    actor: str = "Merchant Voice Confirmation",
) -> Dict[str, Any]:
    lock = get_db_lock()
    with lock:
        conn = get_conn()
        cur = conn.cursor()
        _ensure_pending_table(cur)
        pending = cur.execute(
            "SELECT * FROM pending_confirmations WHERE campaign_id = ?", (campaign_id,)
        ).fetchone()
        if not pending:
            conn.close()
            raise ValueError("No pending spending limit change awaiting confirmation.")

        req_cap = int(pending["requested_cap_inr"])
        prev_cap = int(pending["previous_cap_inr"])
        if not confirm:
            cur.execute("DELETE FROM pending_confirmations WHERE campaign_id = ?", (campaign_id,))
            cur.execute(
                "INSERT INTO audit_logs (ts, actor, event_type, detail) VALUES (?, ?, ?, ?)",
                (
                    now_label(),
                    actor,
                    "CAP_CHANGE_CANCELLED",
                    f"Cancelled pending cap change on {campaign_id} (kept Rs {prev_cap}; discarded Rs {req_cap}).",
                ),
            )
            conn.commit()
            cmp_raw = dict(cur.execute("SELECT * FROM campaigns WHERE campaign_id = ?", (campaign_id,)).fetchone())
            enriched = _enrich_campaign_dict(cur, cmp_raw)
            conn.close()
            return enriched
        conn.close()

    return update_campaign_cap(campaign_id, req_cap, actor=actor, confirmed=True)


def set_campaign_stop_loss(
    campaign_id: str,
    pause: bool = True,
    actor: str = "Merchant Stop-Loss",
) -> Dict[str, Any]:
    """
    Task 9 Live Campaign Stop-Loss control: halts or resumes pass redemptions immediately.
    """
    lock = get_db_lock()
    with lock:
        conn = get_conn()
        cur = conn.cursor()
        cmp_row = cur.execute("SELECT * FROM campaigns WHERE campaign_id = ?", (campaign_id,)).fetchone()
        if not cmp_row:
            conn.close()
            raise ValueError("Campaign not found")

        if pause:
            new_status = "PAUSED_STOP_LOSS"
            ev_type = "STOP_LOSS_TRIGGERED"
            detail = f"Stop-loss activated on {campaign_id} at Rs {cmp_row['budget_spent']} / Rs {cmp_row['max_budget']}; new redemptions halted."
        else:
            new_status = "LIVE_DISPATCHED"
            ev_type = "STOP_LOSS_RESUMED"
            detail = f"Resumed live pass redemptions on {campaign_id} (remaining cap Rs {max(0, int(cmp_row['max_budget']) - int(cmp_row['budget_spent']))})."

        cur.execute("UPDATE campaigns SET status = ? WHERE campaign_id = ?", (new_status, campaign_id))
        cur.execute(
            "INSERT INTO audit_logs (ts, actor, event_type, detail) VALUES (?, ?, ?, ?)",
            (now_label(), actor, ev_type, detail),
        )
        conn.commit()
        raw_updated = dict(cur.execute("SELECT * FROM campaigns WHERE campaign_id = ?", (campaign_id,)).fetchone())
        enriched = _enrich_campaign_dict(cur, raw_updated)
        conn.close()
        return enriched


def get_voice_briefing(lang: str = "en") -> Dict[str, Any]:
    settings = get_settings()
    conn = get_conn()
    cur = conn.cursor()

    recent_day_txns = cur.execute(
        "SELECT COUNT(*) AS c FROM transactions WHERE days_ago <= 3 AND is_simulated = 0"
    ).fetchone()["c"]

    gap_stats = cur.execute(
        """
        SELECT MIN(t_min.min_d) AS min_gap, MAX(t_min.min_d) AS max_gap
        FROM customers c
        JOIN (SELECT customer_id, MIN(days_ago) AS min_d FROM transactions WHERE is_simulated = 0 GROUP BY customer_id) t_min
          ON c.customer_id = t_min.customer_id
        WHERE c.archetype = 'at_risk_regular' AND c.dpdp_consent = 1 AND c.last_promo_days_ago >= ?
        """,
        (settings.cooldown_days,),
    ).fetchone()

    cmp_row = cur.execute("SELECT * FROM campaigns WHERE campaign_id = 'CMP-WINBACK-01'").fetchone()
    conn.close()

    min_gap = int(gap_stats["min_gap"] or 16)
    max_gap = int(gap_stats["max_gap"] or 38)

    brief = render_closing_briefing(
        lang=lang if lang in ("en", "kn", "hi") else "en",
        owner_first_name="Ramesh",
        store_short_name="Sri Krishna Darshini",
        recent_day_txns=int(recent_day_txns or 112),
        eligible_lapsed=int(cmp_row["eligible_count"]),
        treatment_count=int(cmp_row["treatment_count"]),
        control_count=int(cmp_row["holdout_count"]),
        min_silent_days=min_gap,
        max_silent_days=max_gap,
        offer_rupees=int(cmp_row["offer_rupees"]),
        min_bill_rupees=int(cmp_row["min_bill"]),
        max_cap_rupees=int(cmp_row["max_budget"]),
        extra_milk_liters=18,
    )

    provider = SarvamProvider(settings=settings)
    tts_res = provider.synthesize(brief["script"], lang_code=brief["lang_code"], strict=False)
    brief["tts_provider"] = tts_res.provider
    brief["tts_mode"] = tts_res.mode
    brief["audio_base64"] = tts_res.audio_base64
    brief["audio_mime_type"] = tts_res.mime_type
    brief["audio_cached"] = tts_res.cached
    return brief


def approve_campaign(
    campaign_id: str,
    via: str = "1-Tap Soundbox",
    custom_max_budget: Optional[int] = None,
) -> Dict[str, Any]:
    settings = get_settings()
    lock = get_db_lock()
    with lock:
        conn = get_conn()
        cur = conn.cursor()
        _ensure_pending_table(cur)
        cmp_row = cur.execute("SELECT * FROM campaigns WHERE campaign_id = ?", (campaign_id,)).fetchone()
        if not cmp_row:
            conn.close()
            raise ValueError("Campaign not found")

        max_budget = int(custom_max_budget) if custom_max_budget is not None else int(cmp_row["max_budget"])
        if custom_max_budget is not None and custom_max_budget > 0:
            cur.execute("UPDATE campaigns SET max_budget = ? WHERE campaign_id = ?", (max_budget, campaign_id))
            cmp_row = cur.execute("SELECT * FROM campaigns WHERE campaign_id = ?", (campaign_id,)).fetchone()

        assumed_p = _get_campaign_assumed_rate(campaign_id)
        cap_risk = compute_cap_binding_risk(
            treatment_count=cmp_row["treatment_count"],
            offer_rupees=cmp_row["offer_rupees"],
            max_budget=max_budget,
            assumed_redemption_rate=assumed_p,
            warn_threshold=settings.cap_overrun_warn_threshold,
        )

        if cmp_row["status"] == "PENDING_APPROVAL":
            treat_cids, holdout_cids = _partition_eligible_customers(
                cur, cmp_row["segment_key"], cmp_row["treatment_count"], cmp_row["holdout_count"]
            )
            ts = now_label()

            cur.execute("DELETE FROM campaign_passes WHERE campaign_id = ?", (campaign_id,))
            pass_rows = []
            for idx, cid in enumerate(treat_cids, start=1):
                pass_rows.append(
                    (
                        f"PASS-{campaign_id[-2:]}-T{idx:02d}",
                        campaign_id,
                        cid,
                        "TREATMENT",
                        int(cmp_row["offer_rupees"]),
                        "ISSUED",
                        0,
                        0,
                        ts,
                    )
                )
            for idx, cid in enumerate(holdout_cids, start=1):
                pass_rows.append(
                    (
                        f"PASS-{campaign_id[-2:]}-C{idx:02d}",
                        campaign_id,
                        cid,
                        "CONTROL",
                        0,
                        "HOLDOUT_NO_PASS",
                        0,
                        0,
                        ts,
                    )
                )
            cur.executemany(
                "INSERT INTO campaign_passes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                pass_rows,
            )

            cur.execute(
                "UPDATE campaigns SET status = 'LIVE_DISPATCHED', approved_via = ? WHERE campaign_id = ?",
                (via, campaign_id),
            )

            warn_note = (
                f" Cap-overrun probability is {cap_risk['prob_exceeds_cap_pct']}% (>10% threshold; suggested cap Rs {cap_risk['suggested_cap_inr']})."
                if cap_risk["warn_above_threshold"]
                else " Cap-overrun probability <=10%."
            )
            cur.execute(
                "INSERT INTO audit_logs (ts, actor, event_type, detail) VALUES (?, ?, ?, ?)",
                (
                    ts,
                    f"Merchant ({via})",
                    "CAMPAIGN_APPROVED",
                    f"Approved {campaign_id}: Issued Rs {cmp_row['offer_rupees']} passes to all {len(treat_cids)} nudged customers "
                    f"(Rs {cap_risk['face_exposure_inr']} face exposure) with Rs {max_budget} hard spend stop; "
                    f"held {len(holdout_cids)} in silent control.{warn_note}",
                ),
            )
            conn.commit()

        raw_updated = dict(cur.execute("SELECT * FROM campaigns WHERE campaign_id = ?", (campaign_id,)).fetchone())
        enriched = _enrich_campaign_dict(cur, raw_updated)
        conn.close()
        return enriched


def redeem_single_pass_atomic(campaign_id: str, customer_id: str, bill_amount: int) -> Dict[str, Any]:
    """
    Thread-safe, SQLite-serialized pass redemption enforcing both Stop-Loss and hard spend cap.
    """
    lock = get_db_lock()
    with lock:
        conn = get_conn()
        conn.isolation_level = None
        cur = conn.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")
            cmp_row = cur.execute(
                "SELECT * FROM campaigns WHERE campaign_id = ?", (campaign_id,)
            ).fetchone()
            if not cmp_row:
                raise ValueError(f"Campaign {campaign_id} not found")

            if cmp_row["status"] == "PAUSED_STOP_LOSS":
                cur.execute("COMMIT")
                return {
                    "already_processed": False,
                    "status": "BLOCKED_STOP_LOSS",
                    "cashback_paid_inr": 0,
                    "budget_spent_inr": int(cmp_row["budget_spent"]),
                    "cap_reached": bool(cmp_row["cap_reached"]),
                }

            pass_row = cur.execute(
                """
                SELECT * FROM campaign_passes
                WHERE campaign_id = ? AND customer_id = ? AND arm = 'TREATMENT'
                """,
                (campaign_id, customer_id),
            ).fetchone()
            if not pass_row:
                raise ValueError(f"No treatment pass issued for {customer_id} on {campaign_id}")

            if pass_row["status"] != "ISSUED":
                cur.execute("COMMIT")
                return {
                    "already_processed": True,
                    "status": pass_row["status"],
                    "cashback_paid_inr": pass_row["cashback_paid_inr"],
                }

            spent_so_far = int(
                cur.execute(
                    "SELECT COALESCE(SUM(cashback_paid_inr), 0) AS s FROM campaign_passes WHERE campaign_id = ?",
                    (campaign_id,),
                ).fetchone()["s"]
            )
            offer = int(cmp_row["offer_rupees"])
            max_budget = int(cmp_row["max_budget"])
            ts = now_label()

            if spent_so_far + offer <= max_budget:
                new_status = "REDEEMED_FUNDED"
                paid = offer
                new_spent = spent_so_far + offer
            else:
                new_status = "REDEEMED_CAP_REFUSED"
                paid = 0
                new_spent = spent_so_far

            cur.execute(
                """
                UPDATE campaign_passes
                SET status = ?, redeemed_bill_inr = ?, cashback_paid_inr = ?, updated_at = ?
                WHERE pass_id = ?
                """,
                (new_status, int(bill_amount), paid, ts, pass_row["pass_id"]),
            )

            agg = cur.execute(
                """
                SELECT
                    SUM(CASE WHEN status IN ('REDEEMED_FUNDED', 'REDEEMED_CAP_REFUSED') THEN 1 ELSE 0 END) AS itt_ret,
                    SUM(CASE WHEN status = 'REDEEMED_FUNDED' THEN 1 ELSE 0 END) AS funded_cnt,
                    SUM(CASE WHEN status = 'REDEEMED_CAP_REFUSED' THEN 1 ELSE 0 END) AS refused_cnt,
                    COALESCE(SUM(redeemed_bill_inr), 0) AS gross_sales,
                    COALESCE(SUM(cashback_paid_inr), 0) AS spent
                FROM campaign_passes
                WHERE campaign_id = ? AND arm = 'TREATMENT'
                """,
                (campaign_id,),
            ).fetchone()

            cap_reached = 1 if (int(agg["spent"]) >= max_budget and max_budget > 0) or int(agg["refused_cnt"]) > 0 else 0
            cur.execute(
                """
                UPDATE campaigns
                SET treatment_returned = ?,
                    funded_redemptions = ?,
                    refused_redemptions = ?,
                    cap_reached = ?,
                    gross_treatment_sales = ?,
                    budget_spent = ?
                WHERE campaign_id = ?
                """,
                (
                    int(agg["itt_ret"] or 0),
                    int(agg["funded_cnt"] or 0),
                    int(agg["refused_cnt"] or 0),
                    cap_reached,
                    int(agg["gross_sales"] or 0),
                    int(agg["spent"] or 0),
                    campaign_id,
                ),
            )
            cur.execute("COMMIT")
            return {
                "already_processed": False,
                "status": new_status,
                "cashback_paid_inr": paid,
                "budget_spent_inr": new_spent,
                "cap_reached": bool(cap_reached),
            }
        except Exception:
            cur.execute("ROLLBACK")
            raise
        finally:
            conn.close()


def _draw_independent_outcomes(
    treat_cids: List[str],
    holdout_cids: List[str],
    campaign_id: str,
    offer_rupees: int,
    mode: str = "canonical",
    seed: int = 20261025,
) -> Tuple[List[Tuple[str, int]], int, str, int]:
    if campaign_id == "CMP-WINBACK-01":
        avg_spend = 210
        cat = "Fresh Provisions & Dairy"
        sim_hr = 19
        canonical_t_ret = 12
        canonical_h_ret = 1
    else:
        avg_spend = 155
        cat = "Evening Snacks & Tea"
        sim_hr = 16
        canonical_t_ret = 11
        canonical_h_ret = 1

    if mode == "canonical":
        returning_treat = []
        for idx, cid in enumerate(treat_cids[:canonical_t_ret]):
            bill = avg_spend + ((idx % 4) * 15) - 15
            returning_treat.append((cid, bill))
        return returning_treat, canonical_h_ret, cat, sim_hr

    rng = random.Random(f"{campaign_id}:{seed}:{offer_rupees}")
    p_base = 0.125 if campaign_id == "CMP-WINBACK-01" else 0.143
    p_treat = p_base if offer_rupees <= 0 else p_base + (0.50 - p_base) * (1.0 - math.exp(-offer_rupees / 22.0))

    returning_treat = []
    for cid in treat_cids:
        if rng.random() < p_treat:
            bill = avg_spend + rng.choice([-15, 0, 15, 30])
            returning_treat.append((cid, bill))

    h_ret = sum(1 for _ in holdout_cids if rng.random() < p_base)
    return returning_treat, h_ret, cat, sim_hr


def step_live_campaign_scans(
    campaign_id: str,
    step_size: int = 4,
) -> Dict[str, Any]:
    """
    Task 9 Live Interim Wave Monitor: processes a partial batch of returning customer QR scans
    while keeping the campaign in LIVE_DISPATCHED interim mode (until all scans complete).
    """
    lock = get_db_lock()
    with lock:
        conn = get_conn()
        cur = conn.cursor()
        cmp_row = cur.execute("SELECT * FROM campaigns WHERE campaign_id = ?", (campaign_id,)).fetchone()
        if not cmp_row:
            conn.close()
            raise ValueError("Campaign not found")
        if cmp_row["status"] == "PAUSED_STOP_LOSS":
            conn.close()
            raise ValueError("Campaign is paused by Stop-Loss; resume before processing live scans.")
        if cmp_row["status"] == "SIMULATED_48H":
            enriched = _enrich_campaign_dict(cur, dict(cmp_row))
            conn.close()
            return enriched

        if cmp_row["status"] == "PENDING_APPROVAL":
            conn.close()
            approve_campaign(campaign_id, via="Live Wave Monitor")
            conn = get_conn()
            cur = conn.cursor()
            cmp_row = cur.execute("SELECT * FROM campaigns WHERE campaign_id = ?", (campaign_id,)).fetchone()

        treat_cids, holdout_cids = _partition_eligible_customers(
            cur, cmp_row["segment_key"], cmp_row["treatment_count"], cmp_row["holdout_count"]
        )
        offer_rupees = int(cmp_row["offer_rupees"])
        already_done = {
            r["customer_id"]
            for r in cur.execute(
                "SELECT customer_id FROM campaign_passes WHERE campaign_id = ? AND status != 'ISSUED' AND arm = 'TREATMENT'",
                (campaign_id,),
            ).fetchall()
        }
        conn.close()

        returning_treat, h_ret, cat, sim_hr = _draw_independent_outcomes(
            treat_cids=treat_cids,
            holdout_cids=holdout_cids,
            campaign_id=campaign_id,
            offer_rupees=offer_rupees,
            mode="canonical",
        )
        pending_scans = [(cid, bill) for (cid, bill) in returning_treat if cid not in already_done]
        batch = pending_scans[: max(1, int(step_size))]

        for cid, bill in batch:
            redeem_single_pass_atomic(campaign_id, cid, bill)

        conn = get_conn()
        cur = conn.cursor()
        cmp_after = cur.execute("SELECT * FROM campaigns WHERE campaign_id = ?", (campaign_id,)).fetchone()
        done_cnt = int(cmp_after["treatment_returned"])
        interim_h_ret = h_ret if done_cnt >= max(4, len(returning_treat) // 2) else 0

        for idx, (cid, bill) in enumerate(returning_treat[:done_cnt]):
            txn_id = f"UPI-SIM-{campaign_id[-2:]}-{idx+1:02d}"
            cur.execute(
                """
                INSERT OR REPLACE INTO transactions
                (txn_id, customer_id, amount, days_ago, hour_of_day, category, campaign_id, is_simulated)
                VALUES (?, ?, ?, 0, ?, ?, ?, 1)
                """,
                (txn_id, cid, bill, sim_hr, cat, campaign_id),
            )

        gross_sales = int(cmp_after["gross_treatment_sales"])
        budget_spent = int(cmp_after["budget_spent"])
        organic_expected = (interim_h_ret / max(1, cmp_after["holdout_count"])) * cmp_after["treatment_count"]
        net_inc_visits = max(0.0, done_cnt - organic_expected)
        avg_bill = gross_sales / max(1, done_cnt) if done_cnt > 0 else 0.0
        inc_sales = int(round(net_inc_visits * avg_bill))
        roi_mult = round(inc_sales / max(1, budget_spent), 1) if budget_spent > 0 else 0.0

        final_status = "SIMULATED_48H" if done_cnt >= len(returning_treat) else "LIVE_DISPATCHED"
        cur.execute(
            """
            UPDATE campaigns
            SET status = ?, holdout_returned = ?, incremental_sales = ?, roi_multiple = ?
            WHERE campaign_id = ?
            """,
            (final_status, interim_h_ret, inc_sales, roi_mult, campaign_id),
        )
        cur.execute(
            "INSERT INTO audit_logs (ts, actor, event_type, detail) VALUES (?, ?, ?, ?)",
            (
                now_label(),
                "Live Wave Monitor",
                "LIVE_INTERIM_STEP",
                f"{campaign_id}: Processed +{len(batch)} live QR scans ({done_cnt}/{len(returning_treat)} wave scans so far; "
                f"spent Rs {budget_spent} / Rs {cmp_after['max_budget']}; status={final_status}).",
            ),
        )
        conn.commit()
        raw_final = dict(cur.execute("SELECT * FROM campaigns WHERE campaign_id = ?", (campaign_id,)).fetchone())
        enriched = _enrich_campaign_dict(cur, raw_final)
        conn.close()
        return enriched


def simulate_campaign_48h(
    campaign_id: str,
    mode: str = "canonical",
    seed: int = 20261025,
    override_max_budget: Optional[int] = None,
) -> Dict[str, Any]:
    lock = get_db_lock()
    with lock:
        conn = get_conn()
        cur = conn.cursor()
        cmp_row = cur.execute("SELECT * FROM campaigns WHERE campaign_id = ?", (campaign_id,)).fetchone()
        if not cmp_row:
            conn.close()
            raise ValueError("Campaign not found")

        if cmp_row["status"] == "PAUSED_STOP_LOSS" and override_max_budget is None:
            conn.close()
            raise ValueError("Campaign is paused by Stop-Loss; resume before running 48h completion.")

        if cmp_row["status"] == "SIMULATED_48H" and override_max_budget is None and mode == "canonical":
            enriched_existing = _enrich_campaign_dict(cur, dict(cmp_row))
            conn.close()
            return enriched_existing

        if cmp_row["status"] == "PENDING_APPROVAL" or override_max_budget is not None:
            conn.close()
            if override_max_budget is not None:
                c_tmp = get_conn()
                c_tmp.execute("UPDATE campaigns SET status = 'PENDING_APPROVAL' WHERE campaign_id = ?", (campaign_id,))
                c_tmp.execute("DELETE FROM transactions WHERE campaign_id = ? AND is_simulated = 1", (campaign_id,))
                c_tmp.commit()
                c_tmp.close()
            approve_campaign(campaign_id, via="1-Tap Fast-Track", custom_max_budget=override_max_budget)
            conn = get_conn()
            cur = conn.cursor()
            cmp_row = cur.execute("SELECT * FROM campaigns WHERE campaign_id = ?", (campaign_id,)).fetchone()

        treat_cids, holdout_cids = _partition_eligible_customers(
            cur, cmp_row["segment_key"], cmp_row["treatment_count"], cmp_row["holdout_count"]
        )
        offer_rupees = int(cmp_row["offer_rupees"])
        conn.close()

        returning_treat, h_ret, cat, sim_hr = _draw_independent_outcomes(
            treat_cids=treat_cids,
            holdout_cids=holdout_cids,
            campaign_id=campaign_id,
            offer_rupees=offer_rupees,
            mode=mode,
            seed=seed,
        )

        for cid, bill in returning_treat:
            redeem_single_pass_atomic(campaign_id, cid, bill)

        conn = get_conn()
        cur = conn.cursor()
        cmp_after = cur.execute("SELECT * FROM campaigns WHERE campaign_id = ?", (campaign_id,)).fetchone()

        for idx, (cid, bill) in enumerate(returning_treat):
            txn_id = f"UPI-SIM-{campaign_id[-2:]}-{idx+1:02d}"
            cur.execute(
                """
                INSERT OR REPLACE INTO transactions
                (txn_id, customer_id, amount, days_ago, hour_of_day, category, campaign_id, is_simulated)
                VALUES (?, ?, ?, 0, ?, ?, ?, 1)
                """,
                (txn_id, cid, bill, sim_hr, cat, campaign_id),
            )

        itt_t_ret = int(cmp_after["treatment_returned"])
        gross_sales = int(cmp_after["gross_treatment_sales"])
        budget_spent = int(cmp_after["budget_spent"])
        funded_cnt = int(cmp_after["funded_redemptions"])
        refused_cnt = int(cmp_after["refused_redemptions"])
        cap_hit = int(cmp_after["cap_reached"])

        organic_expected_returns = (h_ret / max(1, cmp_after["holdout_count"])) * cmp_after["treatment_count"]
        net_incremental_visits = max(0.0, itt_t_ret - organic_expected_returns)
        avg_actual_bill = gross_sales / max(1, itt_t_ret) if itt_t_ret > 0 else 0.0
        incremental_sales = int(round(net_incremental_visits * avg_actual_bill))
        roi_mult = round(incremental_sales / max(1, budget_spent), 1) if budget_spent > 0 else 0.0

        cur.execute(
            """
            UPDATE campaigns
            SET status = 'SIMULATED_48H',
                holdout_returned = ?,
                incremental_sales = ?,
                roi_multiple = ?
            WHERE campaign_id = ?
            """,
            (h_ret, incremental_sales, roi_mult, campaign_id),
        )

        cur.execute(
            "INSERT INTO audit_logs (ts, actor, event_type, detail) VALUES (?, ?, ?, ?)",
            (
                now_label(),
                "ITT Holdout Engine",
                "48H_ITT_SIMULATION",
                f"{campaign_id}: ITT {itt_t_ret}/{cmp_after['treatment_count']} Nudged ({round(itt_t_ret/cmp_after['treatment_count']*100,1)}%) "
                f"vs {h_ret}/{cmp_after['holdout_count']} Control ({round(h_ret/cmp_after['holdout_count']*100,1)}%). "
                f"Funded={funded_cnt}, Refused={refused_cnt}, CapReached={bool(cap_hit)}. "
                f"Incremental sales: +Rs {incremental_sales} on Rs {budget_spent} spend ({roi_mult}x gross sales multiple).",
            ),
        )

        conn.commit()
        raw_final = dict(cur.execute("SELECT * FROM campaigns WHERE campaign_id = ?", (campaign_id,)).fetchone())
        enriched = _enrich_campaign_dict(cur, raw_final)
        conn.close()
        return enriched


def execute_ops_action(action_id: str) -> Dict[str, Any]:
    lock = get_db_lock()
    with lock:
        conn = get_conn()
        cur = conn.cursor()
        row = cur.execute("SELECT * FROM ops_actions WHERE action_id = ?", (action_id,)).fetchone()
        if not row:
            conn.close()
            raise ValueError("Ops action not found")

        note = (
            "WhatsApp PO #BLR-904 dispatched to Sri Vinayaka Dairy (+18L Milk, +12kg Batter) for 6:00 AM delivery."
            if action_id == "OPS-STOCK-01"
            else "Sent merchant-signed bilingual apology + Rs 30 Filter Coffee QR voucher to Karthik and Divya."
        )
        cur.execute(
            "UPDATE ops_actions SET status = 'EXECUTED', executed_note = ? WHERE action_id = ?",
            (note, action_id),
        )
        cur.execute(
            "INSERT INTO audit_logs (ts, actor, event_type, detail) VALUES (?, ?, ?, ?)",
            (now_label(), "VyaparVoice Ops Copilot", "OPS_ACTION_EXECUTED", f"{action_id}: {note}"),
        )
        conn.commit()
        updated = dict(cur.execute("SELECT * FROM ops_actions WHERE action_id = ?", (action_id,)).fetchone())
        updated["why_explanation"] = render_why_explanation(action_id, updated)
        conn.close()
        return updated


def handle_voice_command(utterance: str, lang: str = "en") -> Dict[str, Any]:
    text = (utterance or "").lower().strip()
    action_taken = None

    # 1. Check two-step pending cap confirmation / cancellation first
    if any(p in text for p in ["confirm limit", "confirm cap", "confirm spending", "yes confirm"]):
        try:
            conn = get_conn()
            cur = conn.cursor()
            _ensure_pending_table(cur)
            pend = cur.execute(
                "SELECT * FROM pending_confirmations WHERE campaign_id = 'CMP-WINBACK-01'"
            ).fetchone()
            conn.close()
            old_cap = int(pend["previous_cap_inr"]) if pend else 300
            updated = resolve_pending_cap_change(
                "CMP-WINBACK-01", confirm=True, actor=f"Voice Confirmed ({lang.upper()})"
            )
            action_taken = "CAP_CONFIRMED_CMP_WINBACK_01"
            reply = render_voice_cap_confirmed_reply(
                old_cap=old_cap,
                new_cap=int(updated["max_budget"]),
                offer_rupees=int(updated["offer_rupees"]),
            )
            return {"utterance": utterance, "reply": reply, "action_taken": action_taken}
        except ValueError:
            reply = "There is no pending spending limit change waiting for confirmation right now."
            return {"utterance": utterance, "reply": assert_valid_merchant_copy(reply), "action_taken": "NO_PENDING_CAP"}

    if any(p in text for p in ["cancel limit", "cancel cap", "discard limit"]):
        try:
            updated = resolve_pending_cap_change(
                "CMP-WINBACK-01", confirm=False, actor=f"Voice Cancelled ({lang.upper()})"
            )
            reply = f"Cancelled! Your spending limit stays unchanged at {updated['max_budget']} rupees."
            return {
                "utterance": utterance,
                "reply": assert_valid_merchant_copy(reply),
                "action_taken": "CAP_CANCELLED_CMP_WINBACK_01",
            }
        except ValueError:
            reply = "No pending spending limit change was active, so your current limit remains unchanged."
            return {"utterance": utterance, "reply": assert_valid_merchant_copy(reply), "action_taken": "NO_PENDING_CAP"}

    # 2. Voice cap change request -> two-step confirmation (never mutates without confirmation)
    cap_voice_match = re.search(
        r"(?:set|change|raise|lower|update|make)\s+(?:my\s+)?(?:spending\s+)?(?:limit|cap|budget)\s*(?:to|at)?\s*(?:rs\.?|inr)?\s*(-?\d+)",
        text,
    )
    if cap_voice_match:
        req_cap = int(cap_voice_match.group(1))
        try:
            res = update_campaign_cap(
                "CMP-WINBACK-01",
                new_cap_inr=req_cap,
                actor=f"Voice Request ({lang.upper()})",
                confirmed=False,
            )
            return {
                "utterance": utterance,
                "reply": res["confirmation_prompt"],
                "action_taken": "CAP_CONFIRMATION_PENDING",
                "requested_cap_inr": req_cap,
            }
        except ValueError as exc:
            settings = get_settings()
            msg = (
                f"Cannot set that limit. Please pick a spending limit between {settings.min_cap_inr} rupees "
                f"and {settings.max_cap_inr} rupees."
            )
            return {
                "utterance": utterance,
                "reply": assert_valid_merchant_copy(msg),
                "action_taken": "CAP_CHANGE_REJECTED",
                "error": str(exc),
            }

    # 3. Adversarial / off-policy discount or prompt-injection attempts via voice
    if any(
        k in text
        for k in [
            "ignore previous",
            "ignore all",
            "bypass",
            "override",
            "without consent",
            "unconsented",
            "no holdout",
            "every day",
            "free cashback",
            "100%",
            "80 rupees off",
            "50 rupees off",
        ]
    ) or re.search(r"(\d+)\s*(?:rupees?|rs\.?)\s*(?:off|cashback)", text):
        gr = evaluate_guardrail_attack(utterance, record_audit=True)
        if not gr["passed"]:
            return {
                "utterance": utterance,
                "reply": gr["merchant_safe_reply"],
                "action_taken": "GUARDRAIL_ATTACK_BLOCKED",
                "guardrail": gr,
            }

    # 4. Stop-loss / resume voice commands
    if any(p in text for p in ["stop loss", "stop-loss", "pause campaign", "stop offer", "halt offer"]):
        updated = set_campaign_stop_loss("CMP-WINBACK-01", pause=True, actor=f"Voice ({lang.upper()})")
        reply = (
            f"Stop-loss activated! Pass redemptions are paused immediately with {updated['budget_spent']} rupees spent "
            f"out of your {updated['max_budget']} rupee limit."
        )
        return {
            "utterance": utterance,
            "reply": assert_valid_merchant_copy(reply),
            "action_taken": "STOP_LOSS_TRIGGERED",
        }

    # 5. Task 14 Merchant Question Chips (deterministic SQLite-grounded plain answers)
    ov_ctx = get_dashboard_overview()
    winback = ov_ctx["campaigns"][0]
    qa_ctx = {
        "max_budget": winback["max_budget"],
        "offer_rupees": winback["offer_rupees"],
        "suggested_cap_inr": winback["cap_risk"]["suggested_cap_inr"],
    }
    if any(p in text for p in ["why these 40", "why 40", "why did you pick", "which 40"]):
        return {
            "utterance": utterance,
            "reply": render_merchant_question_answer("why_40", qa_ctx),
            "action_taken": "MERCHANT_QA_WHY_40",
        }
    if any(p in text for p in ["lose more than", "cross 300", "spend more than", "maximum loss"]):
        return {
            "utterance": utterance,
            "reply": render_merchant_question_answer("max_loss", qa_ctx),
            "action_taken": "MERCHANT_QA_MAX_LOSS",
        }
    if any(p in text for p in ["13th customer", "after the cap", "after limit", "budget runs out", "late customer"]):
        return {
            "utterance": utterance,
            "reply": render_merchant_question_answer("after_cap", qa_ctx),
            "action_taken": "MERCHANT_QA_AFTER_CAP",
        }
    if any(p in text for p in ["come anyway", "normal visits", "8 aside", "without an offer", "compare normal"]):
        return {
            "utterance": utterance,
            "reply": render_merchant_question_answer("normal_visits", qa_ctx),
            "action_taken": "MERCHANT_QA_NORMAL_VISITS",
        }
    if any(p in text for p in ["why order 18", "why 18 liters", "why extra milk"]):
        return {
            "utterance": utterance,
            "reply": render_merchant_question_answer("milk_why", qa_ctx),
            "action_taken": "MERCHANT_QA_MILK_WHY",
        }

    # 6. Core operational & campaign execution commands
    approve_keywords = ["approve", "haan", "bhej", "haudu", "kaluhisi", "yes", "send", "ಹೌದು", "हाँ"]
    stock_keywords = ["milk", "dairy", "stock", "batter", "reorder", "supplier"]
    simulate_keywords = ["48", "fast forward", "simulate", "result", "outcome"]

    if any(k in text for k in stock_keywords):
        execute_ops_action("OPS-STOCK-01")
        action_taken = "EXECUTED_OPS_STOCK_01"
        reply = (
            "Done Ramesh avare! I have sent the WhatsApp reorder for 18 liters extra milk and 12 kg idli-dosa batter "
            "to Sri Vinayaka Dairy for 6 AM delivery tomorrow."
        )
    elif any(k in text for k in simulate_keywords):
        res = simulate_campaign_48h("CMP-WINBACK-01")
        action_taken = "SIMULATED_CMP_WINBACK_01"
        pw = res["evaluation"]["profit_waterfall"]
        reply = (
            f"Early 48-hour check is ready. {res['treatment_returned']} out of {res['treatment_count']} customers with an offer came back, "
            f"compared to {res['holdout_returned']} of {res['holdout_count']} kept without an offer. "
            f"Your {res['max_budget']} rupee cashback limit stopped spending at {res['budget_spent']} rupees, "
            f"leaving an estimated {pw['net_profit_pre_fee_inr']:.0f} rupees profit before fee."
        )
    elif any(k in text for k in approve_keywords):
        cmp_res = approve_campaign("CMP-WINBACK-01", via=f"Voice ({lang.upper()})")
        action_taken = "APPROVED_CMP_WINBACK_01"
        cr = cmp_res["cap_risk"]
        reply = (
            f"Approved! Sent 25 rupee passes to all {cmp_res['treatment_count']} regular customers while keeping "
            f"{cmp_res['holdout_count']} aside without an offer to compare normal visits. "
            f"Your cashback payout stops strictly at {cmp_res['max_budget']} rupees "
            f"(note: {cr['prob_exceeds_cap_pct']:.0f} percent chance more than {cr['max_funded_redemptions']} buyers return)."
        )
    else:
        facts = build_sanitized_store_facts(ov_ctx)
        qa_res = get_groq_qa().answer_question(utterance, facts, lang=lang)
        reply = qa_res.answer
        action_taken = "GROQ_GROUNDED_QA" if qa_res.mode == "groq_grounded" else None

    assert_valid_merchant_copy(reply, check_sentence_length=True)
    return {
        "utterance": utterance,
        "reply": reply,
        "action_taken": action_taken,
    }


def build_sanitized_store_facts(ov_ctx: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Build strictly aggregate store-level facts with zero customer IDs, hashes, or PII."""
    ov = ov_ctx or get_dashboard_overview()
    k = ov["kpis"]
    winback = ov["campaigns"][0]
    cr = winback.get("cap_risk", {})
    facts: Dict[str, Any] = {
        "store_name": "Sri Krishna Darshini",
        "txn_count_30d": int(k["txn_count_30d"]),
        "total_60d_txns": int(k["total_60d_txns"]),
        "gmv_30d": int(round(float(k["gmv_30d"]))),
        "avg_ticket": float(k["avg_ticket"]),
        "avg_returning_bill": 217.5,
        "total_customers": int(k["total_customers"]),
        "repeat_rate_pct": float(k["repeat_rate_pct"]),
        "lapsed_total": int(winback.get("total_segment_count", 48)),
        "eligible_lapsed": int(winback["treatment_count"] + winback["holdout_count"]),
        "treatment_count": int(winback["treatment_count"]),
        "holdout_count": int(winback["holdout_count"]),
        "offer_rupees": int(winback["offer_rupees"]),
        "min_bill": int(winback["min_bill"]),
        "max_budget": int(winback["max_budget"]),
        "budget_spent": int(winback["budget_spent"]),
        "suggested_cap_inr": int(cr.get("suggested_cap_inr", 400)),
        "dead_hour_drop_pct": 70,
        "extra_milk_liters": 18,
        "extra_batter_kg": 12,
    }
    ev = winback.get("evaluation")
    if isinstance(ev, dict):
        pw = ev.get("profit_waterfall", {})
        facts["treatment_returned"] = int(winback.get("treatment_returned", 0))
        facts["holdout_returned"] = int(winback.get("holdout_returned", 0))
        facts["net_profit_pre_fee_inr"] = round(float(pw.get("net_profit_pre_fee_inr", 0.0)), 1)
        facts["net_profit_post_fee_inr"] = round(float(pw.get("net_profit_post_fee_inr", 0.0)), 1)
    return facts


def answer_merchant_question(question: str, lang: str = "en") -> Dict[str, Any]:
    """
    Task 15 grounded English Q&A endpoint handler:
    - Intercepts prompt-injection / off-policy discount attempts BEFORE touching any LLM.
    - Answers canonical Task 14 question chips deterministically.
    - Routes open-ended English store questions through GroqGroundedQA (when enabled locally)
      with strict zero-PII enforcement, numeric grounding verification, copy-lint check,
      and deterministic SQLite fallback.
    """
    raw = (question or "").strip()
    text = raw.lower()
    if not raw:
        raise ValueError("Question cannot be empty.")

    # 1. Intercept adversarial / off-policy override attempts before any LLM call
    if any(
        k in text
        for k in [
            "ignore previous",
            "ignore all",
            "system prompt",
            "developer mode",
            "bypass",
            "override",
            "without consent",
            "unconsented",
            "no holdout",
            "every day",
            "free cashback",
            "100%",
        ]
    ) or re.search(r"(\d+)\s*(?:rupees?|rs\.?)\s*(?:off|cashback)", text):
        gr = evaluate_guardrail_attack(raw, record_audit=True)
        if not gr["passed"]:
            return {
                "question": raw,
                "answer": gr["merchant_safe_reply"],
                "mode": "guardrail_blocked",
                "provider": "deterministic_guardrail",
                "grounded_verified": True,
                "guardrail": gr,
            }

    ov_ctx = get_dashboard_overview()
    winback = ov_ctx["campaigns"][0]
    qa_ctx = {
        "max_budget": winback["max_budget"],
        "offer_rupees": winback["offer_rupees"],
        "suggested_cap_inr": winback["cap_risk"]["suggested_cap_inr"],
    }

    # 2. Canonical Task 14 merchant question chips (instant deterministic SQLite answers)
    chip_map = [
        (["why these 40", "why 40", "why did you pick", "which 40"], "why_40"),
        (["lose more than", "cross 300", "spend more than", "maximum loss"], "max_loss"),
        (["13th customer", "after the cap", "after limit", "budget runs out", "late customer"], "after_cap"),
        (["come anyway", "normal visits", "8 aside", "without an offer", "compare normal"], "normal_visits"),
        (["why order 18", "why 18 liters", "why extra milk"], "milk_why"),
    ]
    for triggers, q_key in chip_map:
        if any(t in text for t in triggers):
            return {
                "question": raw,
                "answer": render_merchant_question_answer(q_key, qa_ctx),
                "mode": "deterministic_chip",
                "provider": "deterministic_sqlite",
                "grounded_verified": True,
                "chip_key": q_key,
            }

    # 3. Open-ended store Q&A via optional keyless GroqGroundedQA (with deterministic fallback)
    facts = build_sanitized_store_facts(ov_ctx)
    res = get_groq_qa().answer_question(raw, facts, lang=lang)
    return {
        "question": res.question,
        "answer": res.answer,
        "mode": res.mode,
        "provider": res.provider,
        "grounded_verified": res.grounded_verified,
        "fallback_reason": res.fallback_reason,
        "ungrounded_numbers": res.ungrounded_numbers,
        "lint_violations": res.lint_violations,
    }

