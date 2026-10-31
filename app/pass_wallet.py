"""
Portfolio v1.7 Capabilities:
1. Customer QR Pass Wallet, Counter Pass Scanner (with Minimum Bill & Atomic Cap Guardrails),
   and Optional PIN-Gated Twilio WhatsApp Sandbox Preview Dispatch.
2. Multi-Shop / Multi-Wave Pooled Pilot Simulator (showing why 1 shop = directional vs 50 shops = powered).
3. Self-Contained Printable 1-Page Merchant Closing & Holdout Profit Report (HTML/Print-to-PDF).
"""
from datetime import datetime
import html
import math
import os
import random
from typing import Any, Dict, List, Optional
import httpx

from .audit_qr import render_pass_qr_svg
from .database import get_conn, get_db_lock
from .engine import (
    _check_and_fire_thresholds,
    _enrich_campaign_dict,
    _partition_eligible_customers,
    _record_cap_reached_audit_if_needed,
    approve_campaign,
    get_dashboard_overview,
    redeem_single_pass_atomic,
)
from .security import assert_paid_calls_permitted, is_session_demo_unlocked
from .stats import compute_power_two_prop, fisher_exact_2x2, wilson_ci_95


def render_whatsapp_pass_message(
    store_name: str,
    pass_id: str,
    offer_inr: int,
    min_bill_inr: int,
    lang: str = "en",
) -> str:
    lg = lang if lang in ("en", "hi", "kn") else "en"
    if lg == "kn":
        return (
            f"{store_name}: ನಿಮಗಾಗಿ ರೂ {offer_inr} ಕ್ಯಾಶ್‌ಬ್ಯಾಕ್ ಪಾಸ್ ಸಿದ್ಧವಾಗಿದೆ "
            f"(ರೂ {min_bill_inr}+ QR ಬಿಲ್ ಮೇಲೆ, ಮುಂದಿನ 48 ಗಂಟೆಗಳವರೆಗೆ ಮಾನ್ಯ). "
            f"ಕೌಂಟರ್ ಬಳಿ ಪಾಸ್ ಕೋಡ್ ತೋರಿಸಿ: {pass_id}. ಸಂದೇಶ ನಿಲ್ಲಿಸಲು STOP ಎಂದು ಕಳುಹಿಸಿ."
        )
    if lg == "hi":
        return (
            f"{store_name}: आपके लिए रु {offer_inr} कैशबैक पास तैयार है "
            f"(रु {min_bill_inr}+ QR बिल पर अगले 48 घंटे तक मान्य)। "
            f"काउंटर पर पास कोड दिखाएं: {pass_id}। संदेश बंद करने हेतु STOP लिखें।"
        )
    return (
        f"{store_name}: Your Rs {offer_inr} cashback pass is ready on Paytm QR bills of "
        f"Rs {min_bill_inr} or more for the next 48 hours. "
        f"Pass code at counter: {pass_id}. Reply STOP anytime to opt out."
    )


def _normalize_pass_row(raw: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "pass_id": str(raw["pass_id"]),
        "campaign_id": str(raw["campaign_id"]),
        "customer_id": str(raw["customer_id"]),
        "display_name": str(raw.get("name_hint") or raw["customer_id"]),
        "upi_handle": str(raw.get("upi_handle") or ""),
        "arm": str(raw["arm"]),
        "face_value_inr": int(raw.get("face_value_inr") or 0),
        "status": str(raw["status"]),
        "bill_amount": int(raw.get("redeemed_bill_inr") or 0),
        "cashback_paid": int(raw.get("cashback_paid_inr") or 0),
        "updated_at": str(raw.get("updated_at") or ""),
    }


def get_campaign_passes_wallet(campaign_id: str, lang: str = "en") -> Dict[str, Any]:
    conn = get_conn()
    cur = conn.cursor()
    cmp_row = cur.execute("SELECT * FROM campaigns WHERE campaign_id = ?", (campaign_id,)).fetchone()
    if not cmp_row:
        conn.close()
        raise ValueError(f"Campaign '{campaign_id}' not found.")

    cmp_dict = dict(cmp_row)
    rows = cur.execute(
        """
        SELECT p.pass_id, p.campaign_id, p.customer_id, p.arm, p.face_value_inr,
               p.status, p.redeemed_bill_inr, p.cashback_paid_inr, p.updated_at,
               c.name_hint, c.upi_handle
        FROM campaign_passes p
        JOIN customers c ON p.customer_id = c.customer_id
        WHERE p.campaign_id = ?
        ORDER BY CASE WHEN p.arm = 'TREATMENT' THEN 0 ELSE 1 END, p.customer_id ASC
        """,
        (campaign_id,),
    ).fetchall()

    if rows:
        passes = [_normalize_pass_row(dict(r)) for r in rows]
    else:
        # Read-only deterministic preview when campaign is still PENDING_APPROVAL
        treat_cids, holdout_cids = _partition_eligible_customers(
            cur,
            cmp_dict["segment_key"],
            int(cmp_dict["treatment_count"]),
            int(cmp_dict["holdout_count"]),
        )
        all_cids = list(treat_cids) + list(holdout_cids)
        cust_map: Dict[str, Dict[str, Any]] = {}
        if all_cids:
            placeholders = ",".join("?" for _ in all_cids)
            c_rows = cur.execute(
                f"SELECT customer_id, name_hint, upi_handle FROM customers WHERE customer_id IN ({placeholders})",
                tuple(all_cids),
            ).fetchall()
            cust_map = {str(r["customer_id"]): dict(r) for r in c_rows}

        passes = []
        for idx, cid in enumerate(treat_cids, start=1):
            cinfo = cust_map.get(cid, {})
            passes.append(
                _normalize_pass_row(
                    {
                        "pass_id": f"PASS-{campaign_id[-2:]}-T{idx:02d}",
                        "campaign_id": campaign_id,
                        "customer_id": cid,
                        "name_hint": cinfo.get("name_hint", cid),
                        "upi_handle": cinfo.get("upi_handle", ""),
                        "arm": "TREATMENT",
                        "face_value_inr": int(cmp_dict["offer_rupees"]),
                        "status": "ISSUED",
                        "redeemed_bill_inr": 0,
                        "cashback_paid_inr": 0,
                        "updated_at": "Pending Approval Preview",
                    }
                )
            )
        for idx, cid in enumerate(holdout_cids, start=1):
            cinfo = cust_map.get(cid, {})
            passes.append(
                _normalize_pass_row(
                    {
                        "pass_id": f"PASS-{campaign_id[-2:]}-C{idx:02d}",
                        "campaign_id": campaign_id,
                        "customer_id": cid,
                        "name_hint": cinfo.get("name_hint", cid),
                        "upi_handle": cinfo.get("upi_handle", ""),
                        "arm": "CONTROL",
                        "face_value_inr": 0,
                        "status": "HOLDOUT_NO_PASS",
                        "redeemed_bill_inr": 0,
                        "cashback_paid_inr": 0,
                        "updated_at": "Holdout Control",
                    }
                )
            )

    meta_store = None
    try:
        meta_store = cur.execute("SELECT value FROM ledger_meta WHERE key = 'custom_store_name'").fetchone()
    except Exception:
        meta_store = None
    if meta_store and meta_store["value"]:
        store_name = str(meta_store["value"])
    else:
        store_name = "Sri Krishna Darshini & Provisions"
        try:
            st_row = cur.execute("SELECT store_name FROM store_settings LIMIT 1").fetchone()
            if st_row and st_row["store_name"]:
                store_name = str(st_row["store_name"])
        except Exception:
            pass
    conn.close()

    treat_passes = [p for p in passes if p["arm"] == "TREATMENT"]
    holdout_entries = [p for p in passes if p["arm"] in ("CONTROL", "HOLDOUT")]

    sample_pass_id = treat_passes[0]["pass_id"] if treat_passes else f"PASS-{campaign_id[-2:]}-T01"
    qr_payload = f"VYAPAR|{campaign_id}|{sample_pass_id}|RS{int(cmp_dict['offer_rupees'])}|MIN{int(cmp_dict['min_bill'])}"
    qr_svg = render_pass_qr_svg(qr_payload, size_px=120)
    preview_msg = render_whatsapp_pass_message(
        store_name=store_name,
        pass_id=sample_pass_id,
        offer_inr=int(cmp_dict["offer_rupees"]),
        min_bill_inr=int(cmp_dict["min_bill"]),
        lang=lang,
    )
    twilio_ready = all(
        bool(os.environ.get(k, "").strip())
        for k in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_WHATSAPP_FROM", "DEMO_WHATSAPP_TO")
    )
    max_b = int(cmp_dict["max_budget"])
    spent_b = int(cmp_dict["budget_spent"])
    summary = {
        "total_treatment_passes": len(treat_passes),
        "total_holdout_customers": len(holdout_entries),
        "issued_unredeemed": sum(1 for p in treat_passes if p["status"] == "ISSUED"),
        "redeemed_funded": sum(1 for p in treat_passes if p["status"] == "REDEEMED_FUNDED"),
        "redeemed_cap_refused": sum(1 for p in treat_passes if p["status"] == "REDEEMED_CAP_REFUSED"),
        "remaining_budget_inr": max(0, max_b - spent_b),
    }
    return {
        "campaign_id": campaign_id,
        "campaign_status": cmp_dict["status"],
        "offer_rupees": int(cmp_dict["offer_rupees"]),
        "min_bill": int(cmp_dict["min_bill"]),
        "max_budget": max_b,
        "budget_spent": spent_b,
        "sample_pass_id": sample_pass_id,
        "sample_pass_qr_payload": qr_payload,
        "sample_pass_qr_svg": qr_svg,
        "summary": summary,
        "total_passes": len(passes),
        "treatment_passes": treat_passes,
        "holdout_entries": holdout_entries,
        "whatsapp_preview_text": preview_msg,
        "twilio_sandbox_configured": twilio_ready,
    }


def scan_customer_pass_at_counter(
    campaign_id: str,
    customer_id: Optional[str] = None,
    bill_amount: int = 195,
) -> Dict[str, Any]:
    """
    Interactive counter QR pass redemption:
    - Auto-approves campaign if still PENDING_APPROVAL so merchant can test immediately.
    - Enforces min_bill guardrail (bills below min_bill get Rs 0 cashback and pass stays ISSUED).
    - Otherwise executes atomic BEGIN IMMEDIATE pass redemption and fires 50%/80%/100% alerts.
    """
    if int(bill_amount) <= 0 or int(bill_amount) > 25000:
        raise ValueError("Counter bill amount must be between Rs 1 and Rs 25,000.")

    conn0 = get_conn()
    cur0 = conn0.cursor()
    cmp0 = cur0.execute("SELECT * FROM campaigns WHERE campaign_id = ?", (campaign_id,)).fetchone()
    if not cmp0:
        conn0.close()
        raise ValueError(f"Campaign '{campaign_id}' not found.")
    if cmp0["status"] == "PAUSED_STOP_LOSS":
        conn0.close()
        raise ValueError("Campaign is paused by Stop-Loss; resume before scanning passes.")
    need_approve = cmp0["status"] == "PENDING_APPROVAL"
    conn0.close()

    if need_approve:
        approve_campaign(campaign_id, via="Counter Pass Scanner")

    conn1 = get_conn()
    cur1 = conn1.cursor()
    cmp_row = cur1.execute("SELECT * FROM campaigns WHERE campaign_id = ?", (campaign_id,)).fetchone()
    min_bill = int(cmp_row["min_bill"])
    cur_spent = int(cmp_row["budget_spent"])

    if customer_id:
        p_row = cur1.execute(
            "SELECT * FROM campaign_passes WHERE campaign_id = ? AND customer_id = ? AND arm = 'TREATMENT'",
            (campaign_id, customer_id),
        ).fetchone()
    else:
        p_row = cur1.execute(
            "SELECT * FROM campaign_passes WHERE campaign_id = ? AND arm = 'TREATMENT' AND status = 'ISSUED' ORDER BY customer_id ASC LIMIT 1",
            (campaign_id,),
        ).fetchone()

    if not p_row:
        conn1.close()
        raise ValueError("No unredeemed treatment passes remain in this campaign.")

    chosen_cid = str(p_row["customer_id"])
    pass_id = str(p_row["pass_id"])

    if int(bill_amount) < min_bill:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur1.execute(
            "INSERT INTO audit_logs (ts, actor, event_type, detail) VALUES (?, ?, ?, ?)",
            (
                now_str,
                "Counter QR Guardrail",
                "PASS_BELOW_MIN_BILL",
                f"{pass_id} ({chosen_cid}): Bill Rs {int(bill_amount)} is below minimum Rs {min_bill}. "
                "Charged regular price (Rs 0 cashback); pass kept ISSUED for next qualifying visit.",
            ),
        )
        conn1.commit()
        enriched = _enrich_campaign_dict(cur1, dict(cmp_row))
        conn1.close()
        return {
            "ok": True,
            "min_bill_met": False,
            "min_bill_rejected": True,
            "pass_id": pass_id,
            "customer_id": chosen_cid,
            "bill_amount_inr": int(bill_amount),
            "cashback_paid_inr": 0,
            "pass_status": "ISSUED",
            "status": "BELOW_MIN_BILL",
            "budget_spent_inr": cur_spent,
            "message": f"Bill Rs {int(bill_amount)} is below the Rs {min_bill} minimum bill rule. Rs 0 cashback paid; pass stays active.",
            "campaign": enriched,
            "threshold_alerts_fired": [],
            "newly_fired_alerts": [],
        }
    conn1.close()

    red_res = redeem_single_pass_atomic(campaign_id, chosen_cid, int(bill_amount))

    lock = get_db_lock()
    with lock:
        conn2 = get_conn()
        cur2 = conn2.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        txn_id = f"UPI-SCAN-{pass_id[-7:]}"
        cur2.execute(
            """
            INSERT OR REPLACE INTO transactions
            (txn_id, customer_id, amount, days_ago, hour_of_day, category, campaign_id, is_simulated)
            VALUES (?, ?, ?, 0, 19, 'Counter Pass Scan', ?, 1)
            """,
            (txn_id, chosen_cid, int(bill_amount), campaign_id),
        )
        cmp_after = cur2.execute("SELECT * FROM campaigns WHERE campaign_id = ?", (campaign_id,)).fetchone()
        if cmp_after["status"] == "PENDING_APPROVAL":
            cur2.execute("UPDATE campaigns SET status = 'LIVE_DISPATCHED' WHERE campaign_id = ?", (campaign_id,))

        cur2.execute(
            "INSERT INTO audit_logs (ts, actor, event_type, detail) VALUES (?, ?, ?, ?)",
            (
                now_str,
                "Counter QR Scanner",
                "PASS_SCANNED_ATOMIC",
                f"{pass_id} ({chosen_cid}): Scanned Rs {int(bill_amount)} bill -> status={red_res['status']}, "
                f"cashback=Rs {red_res['cashback_paid_inr']} (spent Rs {cmp_after['budget_spent']} / Rs {cmp_after['max_budget']}).",
            ),
        )
        newly_fired = _check_and_fire_thresholds(cur2, campaign_id)
        _record_cap_reached_audit_if_needed(cur2, campaign_id)
        conn2.commit()
        raw_final = dict(cur2.execute("SELECT * FROM campaigns WHERE campaign_id = ?", (campaign_id,)).fetchone())
        enriched = _enrich_campaign_dict(cur2, raw_final)
        conn2.close()

    paid = int(red_res["cashback_paid_inr"])
    final_spent = int(raw_final["budget_spent"])
    msg = (
        f"Scanned {pass_id} on Rs {int(bill_amount)} bill: Rs {paid} cashback applied (Spent Rs {final_spent} / Rs {raw_final['max_budget']})."
        if paid > 0
        else f"Scanned {pass_id} on Rs {int(bill_amount)} bill: 100% budget cap reached, so customer paid regular price (Rs 0 cashback)."
    )
    return {
        "ok": True,
        "min_bill_met": True,
        "min_bill_rejected": False,
        "pass_id": pass_id,
        "customer_id": chosen_cid,
        "bill_amount_inr": int(bill_amount),
        "cashback_paid_inr": paid,
        "pass_status": str(red_res["status"]),
        "status": str(red_res["status"]),
        "budget_spent_inr": final_spent,
        "message": msg,
        "campaign": enriched,
        "threshold_alerts_fired": newly_fired,
        "newly_fired_alerts": newly_fired,
    }


def send_whatsapp_sandbox_preview(
    campaign_id: str,
    lang: str = "en",
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generates a DPDP-compliant WhatsApp pass preview message and, ONLY if Twilio Sandbox
    env vars are configured and DEMO_PIN is unlocked on public deploys, dispatches a live
    preview to DEMO_WHATSAPP_TO without ever logging or returning phone numbers or tokens.
    """
    wallet = get_campaign_passes_wallet(campaign_id, lang=lang)
    body_text = wallet["whatsapp_preview_text"]
    pass_id = wallet["sample_pass_id"]

    sid = os.environ.get("TWILIO_ACCOUNT_SID", "").strip()
    tok = os.environ.get("TWILIO_AUTH_TOKEN", "").strip()
    w_from = os.environ.get("TWILIO_WHATSAPP_FROM", "").strip()
    w_to = os.environ.get("DEMO_WHATSAPP_TO", "").strip()

    if not (sid and tok and w_from and w_to):
        return {
            "ok": True,
            "dispatched_live": False,
            "delivery_mode": "local_preview",
            "mode": "local_preview",
            "pass_id": pass_id,
            "message_text": body_text,
            "preview_message": body_text,
            "note": "Rendered locally with DPDP STOP opt-out (configure Twilio Sandbox env vars on server for live WhatsApp delivery).",
        }

    unlocked = is_session_demo_unlocked(session_id)
    try:
        assert_paid_calls_permitted("Twilio WhatsApp Sandbox", demo_unlocked=unlocked)
    except PermissionError as exc:
        return {
            "ok": True,
            "dispatched_live": False,
            "delivery_mode": "pin_locked_preview",
            "mode": "pin_locked_preview",
            "pass_id": pass_id,
            "message_text": body_text,
            "preview_message": body_text,
            "note": str(exc),
        }

    from_fmt = w_from if w_from.startswith("whatsapp:") else f"whatsapp:{w_from}"
    to_fmt = w_to if w_to.startswith("whatsapp:") else f"whatsapp:{w_to}"
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    try:
        with httpx.Client(timeout=8.0) as client:
            resp = client.post(
                url,
                auth=(sid, tok),
                data={"From": from_fmt, "To": to_fmt, "Body": body_text},
            )
        if 200 <= resp.status_code < 300:
            return {
                "ok": True,
                "dispatched_live": True,
                "delivery_mode": "twilio_whatsapp_live",
                "mode": "twilio_whatsapp_live",
                "pass_id": pass_id,
                "message_text": body_text,
                "preview_message": body_text,
                "note": "Live WhatsApp preview sent to configured presenter phone.",
            }
        return {
            "ok": True,
            "dispatched_live": False,
            "delivery_mode": "twilio_http_fallback",
            "mode": "twilio_http_fallback",
            "pass_id": pass_id,
            "message_text": body_text,
            "preview_message": body_text,
            "note": f"Twilio returned HTTP {resp.status_code}; showing local preview safely.",
        }
    except Exception as exc:
        return {
            "ok": True,
            "dispatched_live": False,
            "delivery_mode": "twilio_network_fallback",
            "mode": "twilio_network_fallback",
            "pass_id": pass_id,
            "message_text": body_text,
            "preview_message": body_text,
            "note": f"Network fallback ({type(exc).__name__}); showing local preview safely.",
        }


def simulate_multi_shop_pilot(
    n_shops: int = 50,
    waves_per_shop: int = 1,
    offer_rupees: int = 25,
    avg_bill_inr: float = 217.50,
    gross_margin_pct: float = 30.0,
    paytm_fee_pct: float = 5.0,
    baseline_return_pct: float = 12.5,
    true_lift_pp: float = 18.0,
    max_cap_per_wave_inr: int = 300,
    seed: int = 20261031,
) -> Dict[str, Any]:
    """
    Deterministic multi-shop x multi-wave stratified holdout simulator (32 offer vs 8 holdout per shop-wave).
    Demonstrates why 1 shop (n=40) is directional noise whereas 50+ shop-waves achieve >=80% statistical power.
    """
    shops = max(1, min(200, int(n_shops)))
    waves = max(1, min(12, int(waves_per_shop)))
    p_c = max(0.01, min(0.80, float(baseline_return_pct) / 100.0))
    p_t = max(p_c, min(0.95, p_c + float(true_lift_pp) / 100.0))
    offer = max(0, int(offer_rupees))
    cap = max(max(1, offer), int(max_cap_per_wave_inr))
    max_funded_per_wave = (cap // offer) if offer > 0 else 32

    rng = random.Random(f"pilot:{shops}:{waves}:{offer}:{true_lift_pp:.2f}:{seed}")
    total_waves = shops * waves
    n_treat = total_waves * 32
    n_hold = total_waves * 8
    total_elig = n_treat + n_hold

    obs_t_ret = 0
    obs_h_ret = 0
    total_funded_redemptions = 0
    total_cashback_spent = 0

    for _ in range(total_waves):
        w_t = sum(1 for _ in range(32) if rng.random() < p_t)
        w_h = sum(1 for _ in range(8) if rng.random() < p_c)
        funded = min(w_t, max_funded_per_wave)
        obs_t_ret += w_t
        obs_h_ret += w_h
        total_funded_redemptions += funded
        total_cashback_spent += funded * offer

    obs_t_rate = obs_t_ret / max(1, n_treat)
    obs_h_rate = obs_h_ret / max(1, n_hold)
    obs_lift_pp = round((obs_t_rate - obs_h_rate) * 100.0, 2)

    ci_t = wilson_ci_95(obs_t_ret, n_treat)
    ci_h = wilson_ci_95(obs_h_ret, n_hold)

    if total_elig <= 400:
        f_res = fisher_exact_2x2(obs_t_ret, n_treat - obs_t_ret, obs_h_ret, n_hold - obs_h_ret)
        p_val = float(f_res["p_two_sided"])
    else:
        p_pool = (obs_t_ret + obs_h_ret) / max(1, total_elig)
        se = math.sqrt(max(1e-12, p_pool * (1.0 - p_pool) * (1.0 / n_treat + 1.0 / n_hold)))
        z = abs(obs_t_rate - obs_h_rate) / se
        p_val = round(math.erfc(z / math.sqrt(2.0)), 6)

    pow_info = compute_power_two_prop(n_hold, n_treat, p_c, p_t, alpha=0.05)
    power_pct = float(pow_info["power_pct"])
    is_powered = power_pct >= 80.0
    is_sig = p_val < 0.05

    organic_expected = obs_h_rate * n_treat
    net_extra_visits = max(0.0, obs_t_ret - organic_expected)
    extra_sales = round(net_extra_visits * float(avg_bill_inr), 2)
    inc_gp = round(extra_sales * (float(gross_margin_pct) / 100.0), 2)
    redeemed_gmv = round(total_funded_redemptions * float(avg_bill_inr), 2)
    paytm_fee = round(redeemed_gmv * (float(paytm_fee_pct) / 100.0), 2)
    net_pre_fee = round(inc_gp - total_cashback_spent, 2)
    net_post_fee = round(net_pre_fee - paytm_fee, 2)
    per_shop_post_fee = round(net_post_fee / shops, 2)

    verdict_label = (
        "STATISTICALLY POWERED PILOT (>=80% POWER)"
        if is_powered
        else "DIRECTIONAL ONLY (INCREASE SHOPS OR WAVES FOR >=80% POWER)"
    )
    plain_summary = (
        f"Across {shops} shop(s) and {waves} wave(s) ({total_elig} eligible buyers), design power for a +{true_lift_pp:.1f} pp true lift "
        f"is {power_pct:.1f}% (two-sided alpha=0.05). Simulated observed lift is +{obs_lift_pp:.2f} pp (p = {p_val:.4f}), "
        f"generating Rs {net_post_fee:,.2f} estimated fleet net profit after assumed {paytm_fee_pct:.1f}% Paytm fee."
    )

    return {
        "n_shops": shops,
        "waves_per_shop": waves,
        "total_shop_waves": total_waves,
        "total_eligible_customers": total_elig,
        "total_eligible_buyers": total_elig,
        "treatment_n": n_treat,
        "holdout_n": n_hold,
        "treatment_return_pct": round(obs_t_rate * 100.0, 2),
        "holdout_return_pct": round(obs_h_rate * 100.0, 2),
        "treatment_ci_95": [ci_t[0], ci_t[1]],
        "holdout_ci_95": [ci_h[0], ci_h[1]],
        "observed_lift_pp": obs_lift_pp,
        "true_lift_pp": round(float(true_lift_pp), 2),
        "p_value_two_sided": round(float(p_val), 4),
        "statistical_power_pct": round(power_pct, 1),
        "is_powered_80": is_powered,
        "statistically_significant_95": is_sig,
        "paytm_fee_pct": round(float(paytm_fee_pct), 2),
        "total_cashback_spent_inr": total_cashback_spent,
        "net_extra_visits": round(net_extra_visits, 1),
        "extra_sales_inr": extra_sales,
        "fleet_net_before_fee_inr": net_pre_fee,
        "fleet_net_after_fee_inr": net_post_fee,
        "per_shop_net_after_fee_inr": per_shop_post_fee,
        "verdict_label": verdict_label,
        "plain_summary": plain_summary,
    }


def render_printable_closing_report_html(overview: Optional[Dict[str, Any]] = None) -> str:
    ov = overview or get_dashboard_overview()
    st = ov["store"]
    k = ov["kpis"]
    sp = ov.get("store_preset", {})
    margin_pct = float(sp.get("gross_margin_pct", 30.0))

    cmp_rows_html = []
    for c in ov.get("campaigns", []):
        pw = (c.get("evaluation") or {}).get("profit_waterfall") or {}
        pre_p = float(pw.get("net_profit_pre_fee_inr", 0.0))
        post_p = float(pw.get("net_profit_post_fee_inr", 0.0))
        cmp_rows_html.append(
            f"<tr>"
            f"<td><strong>{html.escape(str(c['title']))}</strong><br/><span style='color:#475569;font-size:11px;'>{html.escape(str(c['status']))}</span></td>"
            f"<td>Rs {int(c['offer_rupees'])} off Rs {int(c['min_bill'])}+</td>"
            f"<td>Rs {int(c['budget_spent'])} / Rs {int(c['max_budget'])}</td>"
            f"<td>{int(c['treatment_returned'])}/{int(c['treatment_count'])} vs {int(c['holdout_returned'])}/{int(c['holdout_count'])}</td>"
            f"<td>Rs {pre_p:.2f}</td>"
            f"<td><strong>Rs {post_p:.2f}</strong></td>"
            f"</tr>"
        )

    seg_rows_html = [
        f"<tr><td>{html.escape(str(s['name']))}</td><td>{int(s['customer_count'])}</td><td>Rs {int(s.get('historical_gmv', 0)):,}</td><td>{html.escape(str(s['action_hint']))}</td></tr>"
        for s in ov.get("segments", [])
    ]

    audit_rows_html = [
        f"<tr><td>{html.escape(str(a['ts']))}</td><td>{html.escape(str(a['actor']))}</td><td><code>{html.escape(str(a['event_type']))}</code></td><td>{html.escape(str(a['detail']))}</td></tr>"
        for a in (ov.get("audit_logs") or [])[:8]
    ]

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>PaytmAI VyaparVoice - Closing Profit & Holdout Report</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #0f172a; margin: 24px auto; max-width: 900px; padding: 0 18px; line-height: 1.45; }}
  .hdr {{ display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2.5px solid #002970; padding-bottom: 12px; margin-bottom: 16px; }}
  .hdr h1 {{ margin: 0; font-size: 20px; color: #002970; }}
  .sub {{ font-size: 12.5px; color: #475569; margin-top: 3px; }}
  .btn-print {{ background: #002970; color: #fff; border: none; padding: 8px 14px; border-radius: 7px; font-weight: 700; cursor: pointer; font-size: 12.5px; }}
  .kpis {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 18px; }}
  .kpi {{ border: 1px solid #cbd5e1; border-radius: 9px; padding: 10px 12px; background: #f8fafc; }}
  .kpi span {{ display: block; font-size: 11px; color: #475569; font-weight: 700; text-transform: uppercase; }}
  .kpi strong {{ font-size: 18px; color: #002970; }}
  h2 {{ font-size: 14.5px; color: #002970; margin: 16px 0 7px; border-left: 4px solid #00baf2; padding-left: 8px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 14px; }}
  th, td {{ border: 1px solid #cbd5e1; padding: 7px 9px; text-align: left; vertical-align: top; }}
  th {{ background: #eff6ff; color: #002970; font-weight: 700; }}
  .note {{ font-size: 11.5px; color: #334155; background: #fef3c7; border: 1px solid #fcd34d; padding: 8px 11px; border-radius: 7px; margin-top: 10px; }}
  @media print {{ .no-print {{ display: none !important; }} body {{ margin: 0; }} }}
</style>
</head>
<body>
  <div class="hdr">
    <div>
      <h1>PaytmAI VyaparVoice | Closing Profit & Holdout Report</h1>
      <div class="sub">{html.escape(str(st['store_name']))} ({html.escape(str(st.get('area', 'Bengaluru')) )}) | Dataset: {html.escape(str(ov['runtime_mode']['dataset_status']))} | Assumed Margin: {margin_pct:.0f}%</div>
    </div>
    <button class="btn-print no-print" onclick="window.print()">Print / Save as PDF</button>
  </div>

  <div class="kpis">
    <div class="kpi"><span>30-Day QR Sales (Grade A)</span><strong>Rs {int(k['gmv_30d']):,}</strong><div class="sub">{int(k['txn_count_30d'])} scans (30d)</div></div>
    <div class="kpi"><span>Unique QR Buyers (Grade A)</span><strong>{int(k['total_customers'])}</strong><div class="sub">{k['repeat_rate_pct']}% repeat visitors</div></div>
    <div class="kpi"><span>Cashback Spent</span><strong>Rs {int(k['total_cashback_spent_inr']):,}</strong><div class="sub">Zero cap overrun</div></div>
    <div class="kpi"><span>Est. Profit After 5% Fee (Grade C)</span><strong>Rs {float(k['estimated_net_profit_post_fee_inr']):.2f}</strong><div class="sub">Pre-fee: Rs {float(k['estimated_net_profit_pre_fee_inr']):.2f}</div></div>
  </div>

  <h2>1. Win-Back &amp; Slow-Hour Campaigns (80/20 Holdout Comparison)</h2>
  <table>
    <thead><tr><th>Campaign</th><th>Offer Terms</th><th>Cap Spent</th><th>Offer vs No-Offer Returns</th><th>Est. Pre-Fee Profit</th><th>Est. Post-5%-Fee Profit</th></tr></thead>
    <tbody>{''.join(cmp_rows_html)}</tbody>
  </table>

  <h2>2. RFM Customer Groups (60-Day QR History)</h2>
  <table>
    <thead><tr><th>Customer Group</th><th>Buyers</th><th>60-Day Sales</th><th>Recommended Action</th></tr></thead>
    <tbody>{''.join(seg_rows_html)}</tbody>
  </table>

  <h2>3. Recent Guardrail &amp; Counter Activity Log</h2>
  <table>
    <thead><tr><th>Timestamp</th><th>Actor</th><th>Event</th><th>Detail</th></tr></thead>
    <tbody>{''.join(audit_rows_html)}</tbody>
  </table>

  <div class="note">
    <strong>Methodology &amp; Hardware Disclosure:</strong> All figures are computed deterministically in SQLite and Python (zero LLM arithmetic, zero outbound customer PII). Store gross margin ({margin_pct:.0f}%) and Paytm promotional fee (5% on redeemed bills) are explicit Grade C assumptions to validate with Paytm; to our knowledge the standard Paytm Soundbox is speaker-based with no microphone; this is to be validated with Paytm. Single-wave 40-buyer outcomes are directional; pooled multi-shop validation is recommended before scale rollout.
  </div>
</body>
</html>"""
