from datetime import datetime
import math
import random
from typing import Any, Dict, List, Optional, Tuple

from .config import get_settings
from .copy_lint import assert_valid_merchant_copy
from .database import get_conn, get_db_lock
from .providers.sarvam import SarvamProvider
from .stats import (
    compute_cap_binding_risk,
    evaluate_itt_holdout_and_profit,
    simulate_dose_response_curve,
)
from .templates import (
    EVIDENCE_GRADES,
    render_cap_warning_merchant,
    render_closing_briefing,
    render_merchant_scorecard_summary,
)

STORE_INFO = {
    "merchant_id": "PYTM-BLR-88412",
    "store_name": "Sri Krishna Darshini & Provisions",
    "owner_name": "Ramesh Rao",
    "locality": "100 Feet Rd, Indiranagar, Bengaluru",
    "device": "Paytm AI Soundbox 4G (v3.2)",
    "max_discount_pct": 22.0,
    "dataset_disclosure": "SYNTHETIC_SEED_20261025",
}


def now_label() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


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
    item = dict(cmp_row)
    item["guardrails"] = compute_guardrails_for_campaign(cur, item)

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

    passes_count = cur.execute(
        "SELECT COUNT(*) AS c FROM campaign_passes WHERE campaign_id = ? AND arm = 'TREATMENT'",
        (item["campaign_id"],),
    ).fetchone()["c"]
    item["passes_issued_count"] = int(passes_count)

    if item["status"] == "SIMULATED_48H":
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
        item["evaluation"] = evaluation
        pw = evaluation["profit_waterfall"]
        pow_80 = evaluation["power"]["at_campaign_split_80_20"]
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
        item["merchant_scorecard"] = None

    return item


def get_dashboard_overview() -> Dict[str, Any]:
    settings = get_settings()
    conn = get_conn()
    cur = conn.cursor()

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

    ops_actions = [dict(r) for r in cur.execute("SELECT * FROM ops_actions ORDER BY action_id ASC").fetchall()]

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

    audit_logs = [dict(r) for r in cur.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 12").fetchall()]

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
            "passed": True,
            "metric": f"All {cmp_row['treatment_count']} passes issued (Rs {face_exposure} face); spend hard-stops at Rs {cmp_row['max_budget']} ({max_redemptions} paid)",
        },
        {
            "rule": "80/20 Intention-to-Treat Holdout",
            "passed": True,
            "metric": f"{cmp_row['treatment_count']} Nudged vs {cmp_row['holdout_count']} Silent Control",
        },
    ]


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

    # Attach cached or zero-cost provider audio metadata without ever making public paid calls
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

            # Decision 1: Issue passes to EVERY nudged customer (do not restrict to cap/offer)
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
    Thread-safe, SQLite-serialized pass redemption enforcing the merchant's hard spend cap.
    Never allows cumulative cashback_paid_inr to exceed max_budget; records refused redemptions
    while still counting the customer visit under Intention-to-Treat.
    """
    lock = get_db_lock()
    with lock:
        conn = get_conn()
        conn.isolation_level = None  # Manual transaction control for BEGIN IMMEDIATE
        cur = conn.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")
            cmp_row = cur.execute(
                "SELECT * FROM campaigns WHERE campaign_id = ?", (campaign_id,)
            ).fetchone()
            if not cmp_row:
                raise ValueError(f"Campaign {campaign_id} not found")

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
    """
    Draws customer return visits and bill sizes STRICTLY INDEPENDENTLY of max_budget (Decision 1).
    Changing max_budget never alters who returns or how many holdout/treatment buyers return.
    """
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

    # Stochastic mode: Bernoulli draws driven only by (seed, campaign_id, offer_rupees)
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

        if cmp_row["status"] == "SIMULATED_48H" and override_max_budget is None and mode == "canonical":
            enriched_existing = _enrich_campaign_dict(cur, dict(cmp_row))
            conn.close()
            return enriched_existing

        # Ensure campaign passes are issued to all nudged customers first
        if cmp_row["status"] == "PENDING_APPROVAL" or override_max_budget is not None:
            conn.close()
            if override_max_budget is not None:
                # Reset passes for fresh re-application of the cap stop against identical outcomes
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

        # Step 1: Draw customer return outcomes strictly independently of max_budget
        returning_treat, h_ret, cat, sim_hr = _draw_independent_outcomes(
            treat_cids=treat_cids,
            holdout_cids=holdout_cids,
            campaign_id=campaign_id,
            offer_rupees=offer_rupees,
            mode=mode,
            seed=seed,
        )

        # Step 2: Apply atomic spending-cap stop to returning treatment scans
        for cid, bill in returning_treat:
            redeem_single_pass_atomic(campaign_id, cid, bill)

        # Record simulated UPI transactions and finalize ITT causal attribution
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
        conn.close()
        return updated


def handle_voice_command(utterance: str, lang: str = "en") -> Dict[str, Any]:
    text = utterance.lower().strip()
    action_taken = None

    # Closed allowlist of merchant intents; offer amounts and caps are never parsed from utterances
    approve_keywords = ["approve", "haan", "bhej", "haudu", "kaluhisi", "yes", "send", "ಹೌದು", "हाँ"]
    stock_keywords = ["milk", "dairy", "stock", "batter", "reorder", "supplier"]
    simulate_keywords = ["48", "fast forward", "simulate", "result", "lift", "roi"]

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
            f"Your 300 rupee cashback limit stopped spending right on budget, leaving an estimated {pw['net_profit_pre_fee_inr']:.0f} rupees profit before fee."
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
        ov = get_dashboard_overview()
        k = ov["kpis"]
        reply = (
            f"Over the last 30 days, Sri Krishna Darshini recorded {k['txn_count_30d']} Paytm QR payments worth "
            f"{k['gmv_30d']} rupees with an average bill of {k['avg_ticket']} rupees. "
            f"Your top action tonight is sending a 25 rupee return offer to 32 silent regular customers within a 300 rupee limit."
        )

    assert_valid_merchant_copy(reply, check_sentence_length=True)
    return {
        "utterance": utterance,
        "reply": reply,
        "action_taken": action_taken,
    }
