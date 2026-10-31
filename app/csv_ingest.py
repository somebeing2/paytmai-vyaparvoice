"""
Portfolio v1.6 Upgrades:
1. Store Category & Gross Margin Presets (Darshini 30%, Grocery Kirana 18%, Bakery/Salon 35%)
   using break-even lift math so thin-margin kiranas stay post-fee profitable.
2. Zero-PII Merchant UPI Statement CSV Uploader & Live RFM Re-Segmentation Engine.
   Hashes all raw payer handles/phones with SHA-256 in memory before SQLite storage.
"""
import csv
from datetime import date, datetime, timedelta
import hashlib
import io
import random
import re
from typing import Any, Dict, List, Optional, Tuple

from .config import get_settings
from .database import get_conn, get_db_lock

STORE_CATEGORY_PRESETS: Dict[str, Dict[str, Any]] = {
    "darshini_30": {
        "preset_key": "darshini_30",
        "label_en": "Darshini / Cafe (30% Margin)",
        "label_hi": "दरशिनी / कैफे (30% मार्जिन)",
        "label_kn": "ದರ್ಶಿನಿ / ಕೆಫೆ (30% ಮಾರ್ಜಿನ್)",
        "gross_margin_pct": 30.0,
        "winback_offer_inr": 25,
        "winback_min_bill_inr": 150,
        "winback_cap_inr": 300,
        "avg_return_bill_inr": 210,
        "deadhour_offer_inr": 20,
        "deadhour_min_bill_inr": 110,
        "deadhour_cap_inr": 240,
        "summary_en": "30% food/cafe margin: Rs 25 off Rs 150+ with Rs 300 cap (16.7% max discount; post-fee break-even at 27.8% return rate).",
    },
    "kirana_18": {
        "preset_key": "kirana_18",
        "label_en": "Grocery Kirana (18% Thin Margin)",
        "label_hi": "किराना जनरल स्टोर (18% कम मार्जिन)",
        "label_kn": "ಕಿರಾಣಿ ಅಂಗಡಿ (18% ಕಡಿಮೆ ಮಾರ್ಜಿನ್)",
        "gross_margin_pct": 18.0,
        "winback_offer_inr": 10,
        "winback_min_bill_inr": 220,
        "winback_cap_inr": 160,
        "avg_return_bill_inr": 260,
        "deadhour_offer_inr": 10,
        "deadhour_min_bill_inr": 180,
        "deadhour_cap_inr": 140,
        "summary_en": "18% thin grocery margin: lowers offer to Rs 10 off Rs 220+ (4.5% discount, Rs 160 cap) so kirana stores stay profitable after fee.",
    },
    "bakery_35": {
        "preset_key": "bakery_35",
        "label_en": "Bakery / Sweet Shop (35% Margin)",
        "label_hi": "बेकरी / मिठाई दुकान (35% मार्जिन)",
        "label_kn": "ಬೇಕರಿ / ಸಿಹಿ ಅಂಗಡಿ (35% ಮಾರ್ಜಿನ್)",
        "gross_margin_pct": 35.0,
        "winback_offer_inr": 30,
        "winback_min_bill_inr": 180,
        "winback_cap_inr": 360,
        "avg_return_bill_inr": 235,
        "deadhour_offer_inr": 25,
        "deadhour_min_bill_inr": 140,
        "deadhour_cap_inr": 275,
        "summary_en": "35% bakery/specialty margin: supports Rs 30 off Rs 180+ with Rs 360 cap while keeping strong post-fee margin headroom.",
    },
}


def get_ledger_meta_map(cur=None) -> Dict[str, str]:
    own_conn = None
    try:
        if cur is None:
            own_conn = get_conn()
            cur = own_conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS ledger_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        rows = cur.execute("SELECT key, value FROM ledger_meta").fetchall()
        return {str(r["key"]): str(r["value"]) for r in rows}
    except Exception:
        return {}
    finally:
        if own_conn is not None:
            own_conn.close()


def get_active_store_margin_pct(cur=None) -> float:
    meta = get_ledger_meta_map(cur)
    raw = meta.get("store_gross_margin_pct")
    if raw is not None:
        try:
            val = float(raw)
            if 5.0 <= val <= 80.0:
                return val
        except ValueError:
            pass
    return float(get_settings().default_gross_margin_pct)


def get_active_preset_info(cur=None) -> Dict[str, Any]:
    meta = get_ledger_meta_map(cur)
    pkey = meta.get("store_preset_key", "darshini_30")
    if pkey not in STORE_CATEGORY_PRESETS:
        pkey = "darshini_30"
    margin = get_active_store_margin_pct(cur)
    dataset_source = meta.get("dataset_source", "SYNTHETIC_60D_LEDGER")
    custom_store_name = meta.get("custom_store_name", "").strip()
    return {
        "active_preset_key": pkey,
        "gross_margin_pct": margin,
        "dataset_source": dataset_source,
        "custom_store_name": custom_store_name,
        "presets": list(STORE_CATEGORY_PRESETS.values()),
    }


def apply_store_category_preset(preset_key: str) -> Dict[str, Any]:
    pkey = (preset_key or "").strip().lower()
    if pkey not in STORE_CATEGORY_PRESETS:
        raise ValueError(f"Unknown store preset '{preset_key}'. Allowed: {', '.join(STORE_CATEGORY_PRESETS)}")

    preset = STORE_CATEGORY_PRESETS[pkey]
    lock = get_db_lock()
    with lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS ledger_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        cur.execute(
            "INSERT OR REPLACE INTO ledger_meta (key, value) VALUES ('store_preset_key', ?)",
            (pkey,),
        )
        cur.execute(
            "INSERT OR REPLACE INTO ledger_meta (key, value) VALUES ('store_gross_margin_pct', ?)",
            (str(preset["gross_margin_pct"]),),
        )
        cur.execute(
            "INSERT OR REPLACE INTO ledger_meta (key, value) VALUES ('store_avg_return_bill_inr', ?)",
            (str(preset["avg_return_bill_inr"]),),
        )

        # Clear any prior simulated campaign redemptions so merchant can run fresh with the new preset
        cur.execute("DELETE FROM transactions WHERE is_simulated = 1")
        cur.execute("DELETE FROM campaign_passes")
        cur.execute("DELETE FROM pending_confirmations")
        try:
            cur.execute("DELETE FROM campaign_threshold_alerts")
        except Exception:
            pass
        try:
            cur.execute("DELETE FROM campaign_cap_pause_logs")
        except Exception:
            pass

        cur.execute(
            """
            UPDATE campaigns
            SET offer_rupees = ?, min_bill = ?, max_budget = ?,
                status = 'PENDING_APPROVAL', approved_via = NULL,
                treatment_returned = 0, holdout_returned = 0,
                funded_redemptions = 0, cap_reached = 0, refused_redemptions = 0,
                gross_treatment_sales = 0, incremental_sales = 0,
                budget_spent = 0, roi_multiple = 0.0
            WHERE campaign_id = 'CMP-WINBACK-01'
            """,
            (preset["winback_offer_inr"], preset["winback_min_bill_inr"], preset["winback_cap_inr"]),
        )
        cur.execute(
            """
            UPDATE campaigns
            SET offer_rupees = ?, min_bill = ?, max_budget = ?,
                status = 'PENDING_APPROVAL', approved_via = NULL,
                treatment_returned = 0, holdout_returned = 0,
                funded_redemptions = 0, cap_reached = 0, refused_redemptions = 0,
                gross_treatment_sales = 0, incremental_sales = 0,
                budget_spent = 0, roi_multiple = 0.0
            WHERE campaign_id = 'CMP-DEADHOUR-02'
            """,
            (preset["deadhour_offer_inr"], preset["deadhour_min_bill_inr"], preset["deadhour_cap_inr"]),
        )

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            "INSERT INTO audit_logs (ts, actor, event_type, detail) VALUES (?, ?, ?, ?)",
            (
                now_str,
                "Merchant Dashboard",
                "STORE_PRESET_APPLIED",
                f"Applied preset '{preset['label_en']}' ({preset['gross_margin_pct']:.0f}% margin): "
                f"Win-back set to Rs {preset['winback_offer_inr']} off Rs {preset['winback_min_bill_inr']}+ "
                f"with Rs {preset['winback_cap_inr']} cap.",
            ),
        )
        conn.commit()
        info = get_active_preset_info(cur)
        conn.close()
        return info


def _normalize_col(col: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (col or "").strip().lower()).strip("_")


def _parse_datetime_and_hour(raw_dt: str, raw_hour: Optional[str]) -> Optional[Tuple[date, int]]:
    s = (raw_dt or "").strip()
    if not s:
        return None
    parsed_dt: Optional[datetime] = None
    formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
    )
    clean_s = s.rstrip("Z")
    for fmt in formats:
        try:
            parsed_dt = datetime.strptime(clean_s, fmt)
            break
        except ValueError:
            continue
    if parsed_dt is None:
        try:
            parsed_dt = datetime.fromisoformat(clean_s)
        except ValueError:
            return None

    hr = parsed_dt.hour
    if raw_hour is not None and str(raw_hour).strip() != "":
        try:
            hr_cand = int(float(str(raw_hour).strip()))
            if 0 <= hr_cand <= 23:
                hr = hr_cand
        except ValueError:
            pass
    elif len(clean_s) <= 10:
        hr = 19
    return parsed_dt.date(), hr


def _hash_payer_zero_pii(raw_payer: str, idx: int) -> Tuple[str, str, str, str]:
    digest = hashlib.sha256(f"vyaparvoice-zero-pii:{raw_payer}".encode("utf-8")).hexdigest()[:8]
    cid = f"CUST-U{idx:03d}"
    name_hint = f"Shopper #{idx:03d}"
    masked_phone = f"+91 9X-HASH-{digest[:4].upper()}"
    upi_handle = f"anon_{digest}@upi"
    return cid, name_hint, masked_phone, upi_handle


def ingest_merchant_upi_csv(csv_text: str, store_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Parse a merchant UPI QR transaction CSV, strip/hash all payer identifiers in memory
    (zero PII written to SQLite), recompute RFM customer archetypes, and rebuild campaigns.
    """
    if not csv_text or not csv_text.strip():
        raise ValueError("Uploaded CSV is empty.")
    if len(csv_text) > 1_500_000:
        raise ValueError("CSV file exceeds the 1.5 MB upload limit.")

    clean_text = csv_text.lstrip("\ufeff")
    reader = csv.DictReader(io.StringIO(clean_text))
    if not reader.fieldnames:
        raise ValueError("CSV header row is missing.")

    col_map = {_normalize_col(f): f for f in reader.fieldnames if f}

    def pick_col(candidates: Tuple[str, ...]) -> Optional[str]:
        for c in candidates:
            if c in col_map:
                return col_map[c]
        return None

    amt_col = pick_col(("amount", "amount_inr", "bill_amount", "paid_amount", "inr", "rupees", "total", "value"))
    payer_col = pick_col(("payer_ref", "payer", "payer_id", "customer_id", "upi_id", "vpa", "customer", "phone", "masked_phone"))
    dt_col = pick_col(("timestamp", "date", "txn_date", "datetime", "payment_time", "created_at"))
    days_col = pick_col(("days_ago", "days_since"))
    hour_col = pick_col(("hour_of_day", "hour"))
    cat_col = pick_col(("category", "item", "items", "department", "notes"))
    consent_col = pick_col(("dpdp_consent", "consent", "opt_in", "marketing_consent"))
    promo_col = pick_col(("last_promo_days_ago", "cooldown_days_ago"))

    if not amt_col:
        raise ValueError("CSV must contain an amount column (for example: amount or amount_inr).")
    if not payer_col:
        raise ValueError("CSV must contain a payer column (for example: payer_ref, customer_id, or upi_id).")
    if not dt_col and not days_col:
        raise ValueError("CSV must contain either a date/timestamp column or a days_ago column.")

    parsed_rows: List[Dict[str, Any]] = []
    max_date_seen: Optional[date] = None

    for row_idx, row in enumerate(reader, start=1):
        if row_idx > 10_000:
            raise ValueError("CSV exceeds maximum allowed 10,000 transactions.")
        raw_amt = str(row.get(amt_col) or "").replace(",", "").replace("Rs", "").replace("INR", "").replace("\u20b9", "").strip()
        if not raw_amt:
            continue
        try:
            amt_val = int(round(float(raw_amt)))
        except ValueError:
            continue
        if amt_val <= 0:
            continue

        raw_payer = str(row.get(payer_col) or "").strip()
        if not raw_payer:
            continue

        row_date: Optional[date] = None
        days_ago_val: Optional[int] = None
        hr_val = 19

        if days_col and str(row.get(days_col) or "").strip() != "":
            try:
                days_ago_val = max(0, int(round(float(str(row.get(days_col)).strip()))))
            except ValueError:
                days_ago_val = None
            if hour_col and str(row.get(hour_col) or "").strip() != "":
                try:
                    h_c = int(float(str(row.get(hour_col)).strip()))
                    if 0 <= h_c <= 23:
                        hr_val = h_c
                except ValueError:
                    pass

        if days_ago_val is None and dt_col:
            dt_parsed = _parse_datetime_and_hour(str(row.get(dt_col) or ""), str(row.get(hour_col) or "") if hour_col else None)
            if dt_parsed is None:
                continue
            row_date, hr_val = dt_parsed
            if max_date_seen is None or row_date > max_date_seen:
                max_date_seen = row_date

        if days_ago_val is None and row_date is None:
            continue

        cat_val = str(row.get(cat_col) or "Store QR Purchase").strip()[:60] or "Store QR Purchase"

        consent_val = 1
        if consent_col and str(row.get(consent_col) or "").strip() != "":
            c_raw = str(row.get(consent_col)).strip().lower()
            consent_val = 0 if c_raw in ("0", "false", "no", "n") else 1

        promo_days = 30
        if promo_col and str(row.get(promo_col) or "").strip() != "":
            try:
                promo_days = max(0, int(round(float(str(row.get(promo_col)).strip()))))
            except ValueError:
                promo_days = 30

        parsed_rows.append(
            {
                "raw_payer": raw_payer,
                "amount": amt_val,
                "row_date": row_date,
                "days_ago": days_ago_val,
                "hour_of_day": hr_val,
                "category": cat_val,
                "dpdp_consent": consent_val,
                "last_promo_days_ago": promo_days,
            }
        )

    if len(parsed_rows) < 10:
        raise ValueError("CSV needs at least 10 valid payment rows to compute RFM customer groups.")

    anchor_date = max_date_seen or date(2026, 10, 30)
    for r in parsed_rows:
        if r["days_ago"] is None:
            r["days_ago"] = max(0, (anchor_date - r["row_date"]).days)

    # Group by payer and hash immediately so zero raw PII leaves this function
    by_payer: Dict[str, List[Dict[str, Any]]] = {}
    for r in parsed_rows:
        by_payer.setdefault(r["raw_payer"], []).append(r)

    if len(by_payer) < 5:
        raise ValueError("CSV needs at least 5 unique payers to form holdout and offer groups.")

    customers_rows = []
    txns_rows = []
    txn_counter = 20000

    for p_idx, (raw_payer, plist) in enumerate(sorted(by_payer.items(), key=lambda kv: kv[0]), start=1):
        cid, name_hint, masked_phone, upi_handle = _hash_payer_zero_pii(raw_payer, p_idx)
        recency = min(int(x["days_ago"]) for x in plist)
        first_seen = max(int(x["days_ago"]) for x in plist)
        freq = len(plist)
        consent = min(int(x["dpdp_consent"]) for x in plist)
        promo_days = min(int(x["last_promo_days_ago"]) for x in plist)

        afternoon_scans = sum(1 for x in plist if 15 <= int(x["hour_of_day"]) <= 17)
        morning_scans = sum(1 for x in plist if int(x["hour_of_day"]) < 11)
        if afternoon_scans >= max(1, freq // 2):
            pref_slot = "Afternoon (3-5 PM)"
        elif morning_scans >= max(1, freq // 2):
            pref_slot = "Morning (8-10 AM)"
        else:
            pref_slot = "Evening (6-9 PM)"

        if freq >= 3 and recency >= 14:
            archetype = "at_risk_regular"
        elif afternoon_scans >= 2 and recency < 14:
            archetype = "afternoon_snack"
        elif freq >= 3 and recency < 14:
            archetype = "loyal_champion"
        else:
            archetype = "new_or_casual"

        customers_rows.append(
            (cid, name_hint, masked_phone, upi_handle, consent, pref_slot, first_seen, promo_days, archetype)
        )
        for x in plist:
            txn_counter += 1
            txns_rows.append(
                (
                    f"UPI-CSV-{txn_counter}",
                    cid,
                    int(x["amount"]),
                    int(x["days_ago"]),
                    int(x["hour_of_day"]),
                    str(x["category"]),
                    None,
                    0,
                )
            )

    settings = get_settings()
    cooldown = int(settings.cooldown_days)

    def segment_counts(seg_key: str) -> Tuple[int, int, int, int]:
        det = sum(1 for c in customers_rows if c[8] == seg_key)
        elig = sum(1 for c in customers_rows if c[8] == seg_key and c[4] == 1 and c[7] >= cooldown)
        if elig <= 1:
            treat = elig
            hold = 0
        else:
            hold = max(1, int(round(elig * 0.20)))
            treat = max(1, elig - hold)
        return det, elig, treat, hold

    wb_det, wb_elig, wb_treat, wb_hold = segment_counts("at_risk_regular")
    dh_det, dh_elig, dh_treat, dh_hold = segment_counts("afternoon_snack")

    lock = get_db_lock()
    with lock:
        conn = get_conn()
        cur = conn.cursor()
        preset_info = get_active_preset_info(cur)
        preset = STORE_CATEGORY_PRESETS[preset_info["active_preset_key"]]

        cur.execute("DELETE FROM campaign_passes")
        cur.execute("DELETE FROM pending_confirmations")
        cur.execute("DELETE FROM transactions")
        cur.execute("DELETE FROM customers")
        cur.execute("DELETE FROM campaigns")
        try:
            cur.execute("DELETE FROM campaign_threshold_alerts")
        except Exception:
            pass
        try:
            cur.execute("DELETE FROM campaign_cap_pause_logs")
        except Exception:
            pass

        cur.executemany("INSERT INTO customers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", customers_rows)
        cur.executemany("INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?, ?, ?)", txns_rows)

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        wb_cap = max(
            int(settings.min_cap_inr),
            min(int(settings.max_cap_inr), max(preset["winback_offer_inr"] * 2, int(round(wb_treat * 0.38)) * preset["winback_offer_inr"])),
        )
        dh_cap = max(
            int(settings.min_cap_inr),
            min(int(settings.max_cap_inr), max(preset["deadhour_offer_inr"] * 2, int(round(dh_treat * 0.40)) * preset["deadhour_offer_inr"])),
        )

        campaigns_rows = [
            (
                "CMP-WINBACK-01",
                f"Win-Back {wb_elig} Lapsed Regulars",
                "Grow Business - Retention",
                "at_risk_regular",
                wb_det,
                wb_elig,
                wb_treat,
                wb_hold,
                preset["winback_offer_inr"],
                preset["winback_min_bill_inr"],
                wb_cap,
                "PENDING_APPROVAL",
                None,
                0, 0, 0, 0, 0, 0, 0, 0, 0.0,
                now_str,
            ),
            (
                "CMP-DEADHOUR-02",
                "3 to 5 PM Slow-Hour Footfall Boost",
                "Grow Business - Footfall",
                "afternoon_snack",
                dh_det,
                dh_elig,
                dh_treat,
                dh_hold,
                preset["deadhour_offer_inr"],
                preset["deadhour_min_bill_inr"],
                dh_cap,
                "PENDING_APPROVAL",
                None,
                0, 0, 0, 0, 0, 0, 0, 0, 0.0,
                now_str,
            ),
        ]
        cur.executemany(
            "INSERT INTO campaigns VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            campaigns_rows,
        )

        clean_store_name = (store_name or "").strip()[:70] or "Uploaded Merchant UPI Statement"
        cur.execute("CREATE TABLE IF NOT EXISTS ledger_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        cur.execute("INSERT OR REPLACE INTO ledger_meta (key, value) VALUES ('dataset_source', 'CSV_UPLOAD')")
        cur.execute("INSERT OR REPLACE INTO ledger_meta (key, value) VALUES ('custom_store_name', ?)", (clean_store_name,))
        cur.execute("INSERT OR REPLACE INTO ledger_meta (key, value) VALUES ('ledger_end_date', ?)", (anchor_date.isoformat(),))

        cur.execute(
            "INSERT INTO audit_logs (ts, actor, event_type, detail) VALUES (?, ?, ?, ?)",
            (
                now_str,
                "Zero-PII CSV Ingest",
                "CSV_LEDGER_INGESTED",
                f"Ingested {len(txns_rows)} QR payments across {len(customers_rows)} SHA-256 anonymized payers "
                f"for '{clean_store_name}'. Detected {wb_det} silent regulars ({wb_elig} eligible: {wb_treat} offer / {wb_hold} holdout).",
            ),
        )
        conn.commit()
        conn.close()

    return {
        "ok": True,
        "store_name": clean_store_name,
        "transactions_ingested": len(txns_rows),
        "unique_payers_hashed": len(customers_rows),
        "zero_pii_hashed": True,
        "winback_detected": wb_det,
        "winback_eligible": wb_elig,
        "winback_split": {"treatment": wb_treat, "holdout": wb_hold, "cap_inr": wb_cap},
    }


def generate_sample_merchant_csv() -> str:
    """
    Generate a clean 280-row sample merchant UPI QR export CSV so recruiters and merchants
    can download, inspect/edit in Excel, and upload right back to test live RFM ingestion.
    """
    rng = random.Random(20261031)
    anchor = date(2026, 10, 30)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["txn_id", "timestamp", "payer_ref", "amount_inr", "category", "dpdp_consent", "last_promo_days_ago"])

    t_idx = 1
    # 22 silent regulars (3 to 6 visits, last seen 16 to 34 days ago)
    for i in range(1, 23):
        payer = f"payer_regular_{i:02d}@okaxis"
        consent = 1 if i <= 20 else 0
        promo_d = 25 if i <= 18 else 6
        for _ in range(rng.randint(4, 7)):
            d_ago = rng.randint(16, 54)
            dt = anchor - timedelta(days=d_ago)
            hr = rng.choice([18, 19, 20])
            amt = rng.choice([165, 185, 210, 240, 275])
            writer.writerow([f"TXN-{t_idx:04d}", f"{dt.isoformat()} {hr:02d}:{rng.randint(10,55):02d}:00", payer, amt, "Evening Snacks & Filter Coffee", consent, promo_d])
            t_idx += 1

    # 24 active loyal regulars (visited within last 7 days)
    for i in range(1, 25):
        payer = f"payer_loyal_{i:02d}@ybl"
        for v in range(rng.randint(5, 9)):
            d_ago = rng.randint(0, 4) if v == 0 else rng.randint(2, 48)
            dt = anchor - timedelta(days=d_ago)
            hr = rng.choice([8, 9, 19, 20])
            amt = rng.choice([150, 195, 225, 290])
            writer.writerow([f"TXN-{t_idx:04d}", f"{dt.isoformat()} {hr:02d}:{rng.randint(10,55):02d}:00", payer, amt, "Fresh Provisions & Bakery", 1, 28])
            t_idx += 1

    # 15 afternoon 3 to 5 PM snack buyers
    for i in range(1, 16):
        payer = f"payer_afternoon_{i:02d}@paytm"
        for _ in range(rng.randint(3, 5)):
            d_ago = rng.randint(1, 28)
            dt = anchor - timedelta(days=d_ago)
            hr = rng.choice([15, 16])
            amt = rng.choice([95, 120, 145, 175])
            writer.writerow([f"TXN-{t_idx:04d}", f"{dt.isoformat()} {hr:02d}:{rng.randint(10,55):02d}:00", payer, amt, "Afternoon Tea & Bun", 1, 22])
            t_idx += 1

    # 18 casual visitors (1 to 2 visits)
    for i in range(1, 19):
        payer = f"payer_casual_{i:02d}@ibl"
        d_ago = rng.randint(0, 25)
        dt = anchor - timedelta(days=d_ago)
        writer.writerow([f"TXN-{t_idx:04d}", f"{dt.isoformat()} 13:{rng.randint(10,55):02d}:00", payer, rng.choice([110, 160, 220]), "Quick Counter Purchase", 1, 30])
        t_idx += 1

    return buf.getvalue()
