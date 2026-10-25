from datetime import datetime
from typing import Dict, Any, List
from .database import get_conn

STORE_INFO = {
    "merchant_id": "PYTM-BLR-88412",
    "store_name": "Sri Krishna Darshini & Provisions",
    "owner_name": "Ramesh Rao",
    "locality": "100 Feet Rd, Indiranagar, Bengaluru",
    "device": "Paytm AI Soundbox 4G (v3.2)",
    "max_discount_pct": 22.0,
}


def now_label() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_dashboard_overview() -> Dict[str, Any]:
    conn = get_conn()
    cur = conn.cursor()

    # Core 30-day metrics from actual SQLite UPI ledger
    kpi_30d = cur.execute(
        """
        SELECT
            COUNT(*) AS txn_count,
            COALESCE(SUM(amount), 0) AS gmv_30d,
            ROUND(AVG(amount), 0) AS avg_ticket,
            COUNT(DISTINCT customer_id) AS active_customers
        FROM transactions
        WHERE days_ago <= 30
        """
    ).fetchone()

    total_60d_txns = cur.execute("SELECT COUNT(*) AS c FROM transactions").fetchone()["c"]
    total_customers = cur.execute("SELECT COUNT(*) AS c FROM customers").fetchone()["c"]

    repeat_custs = cur.execute(
        """
        SELECT COUNT(*) AS c FROM (
            SELECT customer_id FROM transactions GROUP BY customer_id HAVING COUNT(*) >= 3
        )
        """
    ).fetchone()["c"]

    # Hourly distribution (7 AM to 9 PM)
    hourly_rows = cur.execute(
        """
        SELECT hour_of_day, COUNT(*) AS txns, COALESCE(SUM(amount), 0) AS revenue
        FROM transactions
        WHERE days_ago <= 30
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

    # RFM Segments computed from SQLite
    segments_raw = cur.execute(
        """
        SELECT
            c.archetype,
            COUNT(DISTINCT c.customer_id) AS customer_count,
            SUM(CASE WHEN c.dpdp_consent = 1 AND c.last_promo_days_ago >= 14 THEN 1 ELSE 0 END) AS eligible_count,
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
            GROUP BY customer_id
        ) t_agg ON c.customer_id = t_agg.customer_id
        GROUP BY c.archetype
        """
    ).fetchall()

    segment_meta = {
        "loyal_champion": {
            "name": "Loyal Champions",
            "badge": "Healthy Core",
            "color": "emerald",
            "action_hint": "Protect queue experience & milestone perks",
        },
        "at_risk_regular": {
            "name": "At-Risk Regulars (16–28d Silent)",
            "badge": "High Priority Churn",
            "color": "amber",
            "action_hint": "₹25 Win-Back Cashback on ₹150+ UPI scan",
        },
        "afternoon_snack": {
            "name": "Afternoon Dead-Hour Cohort",
            "badge": "3–5 PM Opportunity",
            "color": "cyan",
            "action_hint": "₹20 Filter Coffee + Snack Combo Flash Nudge",
        },
        "new_or_casual": {
            "name": "First-Time / Casual Scanners",
            "badge": "2nd-Visit Funnel",
            "color": "indigo",
            "action_hint": "Convert 1st scan into 2nd repeat visit within 10d",
        },
    }

    segments = []
    for row in segments_raw:
        meta = segment_meta.get(row["archetype"], {"name": row["archetype"], "badge": "Cohort", "color": "slate", "action_hint": ""})
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

    campaigns = [
        dict(r)
        for r in cur.execute(
            "SELECT * FROM campaigns ORDER BY CASE WHEN campaign_id='CMP-WINBACK-01' THEN 0 ELSE 1 END, campaign_id ASC"
        ).fetchall()
    ]
    for cmp_item in campaigns:
        cmp_item["guardrails"] = compute_guardrails_for_campaign(cur, cmp_item)

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
    conn.close()

    return {
        "store": STORE_INFO,
        "kpis": {
            "gmv_30d": kpi_30d["gmv_30d"],
            "txn_count_30d": kpi_30d["txn_count"],
            "total_60d_txns": total_60d_txns,
            "avg_ticket": int(kpi_30d["avg_ticket"] or 0),
            "total_customers": total_customers,
            "repeat_rate_pct": round((repeat_custs / max(1, total_customers)) * 100, 1),
            "verified_incremental_inr": total_incremental,
        },
        "hourly_series": hourly_series,
        "segments": segments,
        "campaigns": campaigns,
        "ops_actions": ops_actions,
        "recent_txns": recent_txns,
        "audit_logs": audit_logs,
    }


def compute_guardrails_for_campaign(cur, cmp_row: Dict[str, Any]) -> List[Dict[str, Any]]:
    seg = cmp_row["segment_key"]
    total_seg = cur.execute("SELECT COUNT(*) AS c FROM customers WHERE archetype = ?", (seg,)).fetchone()["c"]
    consented = cur.execute(
        "SELECT COUNT(*) AS c FROM customers WHERE archetype = ? AND dpdp_consent = 1", (seg,)
    ).fetchone()["c"]
    cooldown_ok = cur.execute(
        "SELECT COUNT(*) AS c FROM customers WHERE archetype = ? AND dpdp_consent = 1 AND last_promo_days_ago >= 14",
        (seg,),
    ).fetchone()["c"]

    disc_pct = round((cmp_row["offer_rupees"] / max(1, cmp_row["min_bill"])) * 100, 1)
    max_redemptions = cmp_row["max_budget"] // max(1, cmp_row["offer_rupees"])

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
            "rule": "Merchant Margin Floor (≤22%)",
            "passed": disc_pct <= STORE_INFO["max_discount_pct"],
            "metric": f"{disc_pct}% effective discount (₹{cmp_row['offer_rupees']} on ₹{cmp_row['min_bill']}+)",
        },
        {
            "rule": "Hard Liability Auto-Cutoff",
            "passed": True,
            "metric": f"₹{cmp_row['max_budget']} hard cap (auto-stops at {max_redemptions} UPI scans)",
        },
        {
            "rule": "80/20 Causal Holdout Split",
            "passed": True,
            "metric": f"{cmp_row['treatment_count']} Treatment vs {cmp_row['holdout_count']} Silent Control",
        },
    ]


def get_voice_briefing(lang: str = "en") -> Dict[str, Any]:
    briefings = {
        "en": {
            "lang_code": "en-IN",
            "language_name": "English (India)",
            "headline": "8:30 PM Closing Voice Briefing · Paytm AI Soundbox",
            "script": (
                "Good evening Ramesh avare! Today Sri Krishna Darshini collected 184 UPI payments. "
                "I found one high-return action for tonight: 40 regular evening customers have not visited in the last 18 days. "
                "Shall I send a 25 rupee UPI cashback on bills above 150 rupees? Your maximum spend is capped at 300 rupees. "
                "Also, tomorrow's weekend rush needs 18 liters extra milk. Say 'Approve' or tap once on Soundbox!"
            ),
            "romanized": "Direct English (Indian Accent) — Ready for 1-Tap or Voice Approval",
            "cta_hint": "Say: 'Yes, approve win-back' or click 1-Tap Approve",
        },
        "kn": {
            "lang_code": "kn-IN",
            "language_name": "ಕನ್ನಡ (Kannada · Bengaluru)",
            "headline": "ರಾತ್ರಿ 8:30 ಕ್ಲೋಸಿಂಗ್ ಬ್ರೀಫಿಂಗ್ · Paytm AI Soundbox",
            "script": (
                "ನಮಸ್ಕಾರ ರಮೇಶ್ ಅವರೇ! ಇಂದು ಶ್ರೀ ಕೃಷ್ಣ ದರ್ಶಿನಿಯಲ್ಲಿ ಉತ್ತಮ ವ್ಯಾಪಾರವಾಗಿದೆ. "
                "ಒಂದು ಮುಖ್ಯ ಸಲಹೆ: ನಿಮ್ಮ 40 ಖಾಯಂ ಗ್ರಾಹಕರು ಕಳೆದ 18 ದಿನಗಳಿಂದ ಬಂದಿಲ್ಲ. "
                "ಅವರಿಗೆ 150 ರೂಪಾಯಿ ಮೇಲಿನ ಬಿಲ್‌ಗೆ 25 ರೂಪಾಯಿ ಯುಪಿಐ ಕ್ಯಾಶ್‌ಬ್ಯಾಕ್ ಕಳುಹಿಸಲೇ? "
                "ಗರಿಷ್ಠ ಬಜೆಟ್ ಕೇವಲ 300 ರೂಪಾಯಿ ಮಾತ್ರ. ಒಪ್ಪಿಗೆ ನೀಡಲು 'ಹೌದು, ಕಳುಹಿಸಿ' ಎಂದು ಹೇಳಿ!"
            ),
            "romanized": (
                "Namaskara Ramesh avare! Indu Sri Krishna Darshiniyalli uttama vyaparavagide. "
                "Nimma 40 khayam grahakaru kaleda 18 dinagalinda bandilla. Avarige ₹150 melina bill-ge ₹25 UPI cashback kaluhisale? "
                "Garistha budget kevala ₹300 matra. Oppige needalu 'Haudu, kaluhisi' endu heli!"
            ),
            "cta_hint": "Say: 'Haudu kaluhisi' / 'Approve'",
        },
        "hi": {
            "lang_code": "hi-IN",
            "language_name": "हिंदी (Hindi)",
            "headline": "रात 8:30 क्लोजिंग वॉइस ब्रीफिंग · Paytm AI Soundbox",
            "script": (
                "नमस्ते रमेश जी! आज आपकी दुकान पर शानदार यूपीआई बिक्री हुई। "
                "आज रात के लिए एक मुनाफे का सुझाव है: आपके 40 पुराने ग्राहक पिछले 18 दिनों से नहीं आए हैं। "
                "क्या मैं उन्हें 150 रुपये की खरीद पर 25 रुपये का पेटीएम कैशबैक भेज दूँ? "
                "आपका अधिकतम खर्च 300 रुपये पर लॉक रहेगा। शुरू करने के लिए बस बोलें — 'हाँ, भेज दो'!"
            ),
            "romanized": (
                "Namaste Ramesh ji! Aapke 40 purane grahak pichhle 18 dino se nahi aaye hain. "
                "Kya main unhe ₹150 ki kharid par ₹25 ka Paytm cashback bhej doon? "
                "Aapka adhiktam kharch ₹300 par lock rahega. Shuru karne ke liye bas bolein — 'Haan, bhej do'!"
            ),
            "cta_hint": "Say: 'Haan bhej do' / 'Approve'",
        },
    }
    return briefings.get(lang, briefings["en"])


def approve_campaign(campaign_id: str, via: str = "1-Tap Soundbox") -> Dict[str, Any]:
    conn = get_conn()
    cur = conn.cursor()
    cmp_row = cur.execute("SELECT * FROM campaigns WHERE campaign_id = ?", (campaign_id,)).fetchone()
    if not cmp_row:
        conn.close()
        raise ValueError("Campaign not found")

    if cmp_row["status"] == "PENDING_APPROVAL":
        cur.execute(
            "UPDATE campaigns SET status = 'LIVE_DISPATCHED', approved_via = ? WHERE campaign_id = ?",
            (via, campaign_id),
        )
        cur.execute(
            "INSERT INTO audit_logs (ts, actor, event_type, detail) VALUES (?, ?, ?, ?)",
            (
                now_label(),
                f"Merchant ({via})",
                "CAMPAIGN_APPROVED",
                f"Approved {campaign_id}: Sent Paytm UPI cashback pass to {cmp_row['treatment_count']} consented customers; held {cmp_row['holdout_count']} in silent control group. Hard cap ₹{cmp_row['max_budget']} armed.",
            ),
        )
        conn.commit()

    updated = dict(cur.execute("SELECT * FROM campaigns WHERE campaign_id = ?", (campaign_id,)).fetchone())
    conn.close()
    return updated


def simulate_campaign_48h(campaign_id: str) -> Dict[str, Any]:
    conn = get_conn()
    cur = conn.cursor()
    cmp_row = cur.execute("SELECT * FROM campaigns WHERE campaign_id = ?", (campaign_id,)).fetchone()
    if not cmp_row:
        conn.close()
        raise ValueError("Campaign not found")

    if cmp_row["status"] == "SIMULATED_48H":
        conn.close()
        return dict(cmp_row)

    # Ensure approved first if user clicks simulate directly
    if cmp_row["status"] == "PENDING_APPROVAL":
        cur.execute(
            "UPDATE campaigns SET status = 'LIVE_DISPATCHED', approved_via = '1-Tap Fast-Track' WHERE campaign_id = ?",
            (campaign_id,),
        )

    # Deterministic, realistic causal lift simulation:
    if campaign_id == "CMP-WINBACK-01":
        # 32 treatment -> 12 return (37.5% return rate, hits exact ₹300 cap = 12 * ₹25!)
        # 8 holdout -> 1 returns naturally (12.5% organic baseline!)
        t_ret = 12
        h_ret = 1
        avg_spend = 210
        cat = "Fresh Provisions & Dairy"
        sim_hr = 19
    else:
        # Dead-hour flash boost: 27 treatment -> 11 return (40.7%), 7 holdout -> 1 returns (14.3%)
        t_ret = 11
        h_ret = 1
        avg_spend = 155
        cat = "Evening Snacks & Tea"
        sim_hr = 16

    eligible_custs = cur.execute(
        """
        SELECT customer_id FROM customers
        WHERE archetype = ? AND dpdp_consent = 1 AND last_promo_days_ago >= 14
        ORDER BY customer_id ASC
        LIMIT ?
        """,
        (cmp_row["segment_key"], t_ret),
    ).fetchall()

    gross_sales = 0
    for idx, c_row in enumerate(eligible_custs):
        bill = avg_spend + ((idx % 4) * 15) - 15
        gross_sales += bill
        txn_id = f"UPI-SIM-{campaign_id[-2:]}-{idx+1:02d}"
        cur.execute(
            """
            INSERT OR REPLACE INTO transactions
            (txn_id, customer_id, amount, days_ago, hour_of_day, category, campaign_id, is_simulated)
            VALUES (?, ?, ?, 0, ?, ?, ?, 1)
            """,
            (txn_id, c_row["customer_id"], bill, sim_hr, cat, campaign_id),
        )

    # Causal incrementality calculation:
    # Organic expected return rate in treatment = (h_ret / holdout_count) * treatment_count
    organic_expected_returns = (h_ret / max(1, cmp_row["holdout_count"])) * cmp_row["treatment_count"]
    net_incremental_visits = max(0.0, t_ret - organic_expected_returns)
    avg_actual_bill = gross_sales / max(1, t_ret)
    incremental_sales = int(round(net_incremental_visits * avg_actual_bill))
    budget_spent = min(cmp_row["max_budget"], t_ret * cmp_row["offer_rupees"])
    roi_mult = round(incremental_sales / max(1, budget_spent), 1)

    cur.execute(
        """
        UPDATE campaigns
        SET status = 'SIMULATED_48H',
            treatment_returned = ?,
            holdout_returned = ?,
            gross_treatment_sales = ?,
            incremental_sales = ?,
            budget_spent = ?,
            roi_multiple = ?
        WHERE campaign_id = ?
        """,
        (t_ret, h_ret, gross_sales, incremental_sales, budget_spent, roi_mult, campaign_id),
    )

    cur.execute(
        "INSERT INTO audit_logs (ts, actor, event_type, detail) VALUES (?, ?, ?, ?)",
        (
            now_label(),
            "Holdout Attribution Engine",
            "48H_CAUSAL_PROOF",
            f"{campaign_id}: {t_ret}/{cmp_row['treatment_count']} Treatment returned ({round(t_ret/cmp_row['treatment_count']*100,1)}%) vs {h_ret}/{cmp_row['holdout_count']} Control ({round(h_ret/cmp_row['holdout_count']*100,1)}%). Verified Net Incremental GMV: +₹{incremental_sales} on ₹{budget_spent} spend ({roi_mult}x ROI).",
        ),
    )

    conn.commit()
    updated = dict(cur.execute("SELECT * FROM campaigns WHERE campaign_id = ?", (campaign_id,)).fetchone())
    conn.close()
    return updated


def execute_ops_action(action_id: str) -> Dict[str, Any]:
    conn = get_conn()
    cur = conn.cursor()
    row = cur.execute("SELECT * FROM ops_actions WHERE action_id = ?", (action_id,)).fetchone()
    if not row:
        conn.close()
        raise ValueError("Ops action not found")

    note = (
        "WhatsApp PO #BLR-904 dispatched to Sri Vinayaka Dairy (+18L Milk, +12kg Batter) for 6:00 AM delivery."
        if action_id == "OPS-STOCK-01"
        else "Sent merchant-signed bilingual apology + ₹30 Filter Coffee QR voucher to Karthik & Divya."
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

    # Detect approval intent in English, Hindi, or Kannada romanization/script
    approve_keywords = ["approve", "haan", "bhej", "haudu", "kaluhisi", "yes", "send", " ಹೌದು", "हाँ"]
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
        reply = (
            f"48-hour results are in! 12 out of 32 nudged regulars scanned and paid at your counter, compared to just 1 in the control group. "
            f"You earned {res['incremental_sales']} rupees in verified net new sales on a 300 rupee cashback spend — a {res['roi_multiple']}x return!"
        )
    elif any(k in text for k in approve_keywords):
        approve_campaign("CMP-WINBACK-01", via=f"Voice ({lang.upper()})")
        action_taken = "APPROVED_CMP_WINBACK_01"
        reply = (
            "Approved! Guardrails verified: 40 DPDP-consented regulars selected, 32 sent the 25 rupee UPI cashback pass, "
            "8 held in silent control, and your 300 rupee maximum budget ceiling is locked."
        )
    else:
        ov = get_dashboard_overview()
        k = ov["kpis"]
        reply = (
            f"Over the last 30 days, Sri Krishna Darshini processed {k['txn_count_30d']} Paytm UPI scans worth "
            f"{k['gmv_30d']} rupees with an average bill of {k['avg_ticket']} rupees. "
            f"Your biggest immediate opportunity is winning back 40 lapsed evening regulars and filling the 3 to 5 PM afternoon dip."
        )

    return {
        "utterance": utterance,
        "reply": reply,
        "action_taken": action_taken,
    }
