import os
import random
import sqlite3
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "vyaparvoice.db")

FIRST_NAMES = [
    "Karthik", "Priya", "Arjun", "Divya", "Suresh", "Ananya", "Rohan", "Meera",
    "Naveen", "Lakshmi", "Vikram", "Sneha", "Prashanth", "Kavitha", "Deepak",
    "Pooja", "Manjunath", "rekha", "Harish", "Swathi", "Gaurav", "Nandini",
    "chetan", "Bhavana", "Santosh", "ashwini", "Rajesh", "Shruti", "Kiran", "uma"
]

CATEGORIES = [
    ("Breakfast & Filter Coffee", 85, 190),
    ("South Indian Thali / Lunch", 140, 310),
    ("Evening Snacks & Tea", 65, 160),
    ("Fresh Provisions & Dairy", 160, 480),
]


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_and_seed_db(force_reset: bool = False) -> None:
    if force_reset and os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = get_conn()
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS customers (
            customer_id TEXT PRIMARY KEY,
            name_hint TEXT NOT NULL,
            masked_phone TEXT NOT NULL,
            upi_handle TEXT NOT NULL,
            dpdp_consent INTEGER NOT NULL,
            preferred_slot TEXT NOT NULL,
            first_seen_days_ago INTEGER NOT NULL,
            last_promo_days_ago INTEGER NOT NULL,
            archetype TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS transactions (
            txn_id TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL,
            amount INTEGER NOT NULL,
            days_ago INTEGER NOT NULL,
            hour_of_day INTEGER NOT NULL,
            category TEXT NOT NULL,
            campaign_id TEXT DEFAULT NULL,
            is_simulated INTEGER DEFAULT 0,
            FOREIGN KEY(customer_id) REFERENCES customers(customer_id)
        );

        CREATE TABLE IF NOT EXISTS campaigns (
            campaign_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            pillar TEXT NOT NULL,
            segment_key TEXT NOT NULL,
            detected_count INTEGER NOT NULL,
            eligible_count INTEGER NOT NULL,
            treatment_count INTEGER NOT NULL,
            holdout_count INTEGER NOT NULL,
            offer_rupees INTEGER NOT NULL,
            min_bill INTEGER NOT NULL,
            max_budget INTEGER NOT NULL,
            status TEXT NOT NULL,
            approved_via TEXT DEFAULT NULL,
            treatment_returned INTEGER DEFAULT 0,
            holdout_returned INTEGER DEFAULT 0,
            gross_treatment_sales INTEGER DEFAULT 0,
            incremental_sales INTEGER DEFAULT 0,
            budget_spent INTEGER DEFAULT 0,
            roi_multiple REAL DEFAULT 0.0,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ops_actions (
            action_id TEXT PRIMARY KEY,
            pillar TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            voice_prompt_en TEXT NOT NULL,
            recommended_step TEXT NOT NULL,
            est_value_inr INTEGER NOT NULL,
            status TEXT NOT NULL,
            executed_note TEXT DEFAULT NULL
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            actor TEXT NOT NULL,
            event_type TEXT NOT NULL,
            detail TEXT NOT NULL
        );
        """
    )

    existing = cur.execute("SELECT COUNT(*) AS c FROM customers").fetchone()["c"]
    if existing > 0:
        conn.close()
        return

    rng = random.Random(20261025)

    # Seed 240 realistic Bengaluru store customers across 4 clear behavioral archetypes
    customers_rows = []
    txns_rows = []
    txn_counter = 10000

    # Archetypes:
    # 1. loyal_champion (72 customers): frequent & visited within last 0-6 days
    # 2. at_risk_regular (48 customers): 5-11 visits historically, NO visit in last 16-28 days!
    #    (40 have dpdp_consent=1 & last_promo_days_ago>=15 -> exact 40 eligible!)
    # 3. afternoon_snack (55 customers): occasional visitors, 42 consented for dead-hour flash deals
    # 4. new_or_casual (65 customers): 1-2 visits in last 30 days
    archetype_plan = (
        [("loyal_champion", 72)]
        + [("at_risk_regular", 48)]
        + [("afternoon_snack", 55)]
        + [("new_or_casual", 65)]
    )

    cust_idx = 1
    for archetype, count in archetype_plan:
        for i in range(count):
            cid = f"CUST-{cust_idx:03d}"
            fname = FIRST_NAMES[(cust_idx * 7 + i) % len(FIRST_NAMES)].capitalize()
            masked_phone = f"+91 98{rng.randint(10,99)}XXXXXX"
            upi_handle = f"{fname.lower()}{rng.randint(11,99)}@paytm"

            if archetype == "at_risk_regular":
                # Guarantee deterministic policy numbers:
                # Out of 48 at-risk regulars: 43 have DPDP consent, and 40 also pass 14-day cooldown
                dpdp_consent = 1 if i < 43 else 0
                last_promo_days_ago = 24 if i < 40 else 6
                preferred_slot = "Evening (6-9 PM)"
                first_seen = rng.randint(42, 60)
                num_visits = rng.randint(5, 10)
                visit_days = [rng.randint(16, 58) for _ in range(num_visits)]
            elif archetype == "loyal_champion":
                dpdp_consent = 1 if rng.random() < 0.88 else 0
                last_promo_days_ago = rng.randint(10, 40)
                preferred_slot = rng.choice(["Morning (8-10 AM)", "Evening (6-9 PM)"])
                first_seen = rng.randint(35, 60)
                num_visits = rng.randint(8, 16)
                visit_days = [rng.randint(0, 6)] + [rng.randint(1, 55) for _ in range(num_visits - 1)]
            elif archetype == "afternoon_snack":
                dpdp_consent = 1 if i < 36 else 0
                last_promo_days_ago = 20 if i < 34 else 5
                preferred_slot = "Afternoon (3-5 PM)"
                first_seen = rng.randint(25, 55)
                num_visits = rng.randint(3, 6)
                visit_days = [rng.randint(3, 45) for _ in range(num_visits)]
            else:
                dpdp_consent = 1 if rng.random() < 0.78 else 0
                last_promo_days_ago = 30
                preferred_slot = rng.choice(["Morning (8-10 AM)", "Lunch (12-2 PM)", "Evening (6-9 PM)"])
                first_seen = rng.randint(2, 25)
                num_visits = rng.randint(1, 2)
                visit_days = [rng.randint(1, max(2, first_seen)) for _ in range(num_visits)]

            customers_rows.append(
                (
                    cid,
                    fname,
                    masked_phone,
                    upi_handle,
                    dpdp_consent,
                    preferred_slot,
                    first_seen,
                    last_promo_days_ago,
                    archetype,
                )
            )

            for d_ago in visit_days:
                txn_counter += 1
                # Realistic hourly distribution creating a clear 15:00-17:00 dead-hour dip!
                r_hr = rng.random()
                if r_hr < 0.30:
                    hr = rng.choice([7, 8, 9, 10])
                    cat, lo, hi = CATEGORIES[0]
                elif r_hr < 0.56:
                    hr = rng.choice([12, 13, 14])
                    cat, lo, hi = CATEGORIES[1]
                elif r_hr < 0.62:
                    # Very sparse afternoon 15-16h -> clear dead-hour trough!
                    hr = rng.choice([15, 16])
                    cat, lo, hi = CATEGORIES[2]
                else:
                    hr = rng.choice([17, 18, 19, 20, 21])
                    cat, lo, hi = rng.choice([CATEGORIES[2], CATEGORIES[3]])

                amt = rng.randrange(lo, hi + 1, 5)
                txns_rows.append((f"UPI-{txn_counter}", cid, amt, d_ago, hr, cat, None, 0))

            cust_idx += 1

    cur.executemany(
        """
        INSERT INTO customers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        customers_rows,
    )
    cur.executemany(
        """
        INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        txns_rows,
    )

    now_str = "2026-10-25 20:30:00"
    # Seed 2 ready-to-approve Growth Campaigns computed from the cohort rules
    campaigns_seed = [
        (
            "CMP-WINBACK-01",
            "Win-Back 40 Lapsed Evening Regulars",
            "Grow Business · Retention",
            "at_risk_regular",
            48,
            40,
            32,
            8,
            25,
            150,
            300,
            "PENDING_APPROVAL",
            None,
            0,
            0,
            0,
            0,
            0,
            0.0,
            now_str,
        ),
        (
            "CMP-DEADHOUR-02",
            "3–5 PM Dead-Hour Filter Coffee & Snack Flash Boost",
            "Grow Business · Footfall",
            "afternoon_snack",
            55,
            34,
            27,
            7,
            20,
            110,
            240,
            "PENDING_APPROVAL",
            None,
            0,
            0,
            0,
            0,
            0,
            0.0,
            now_str,
        ),
    ]
    cur.executemany(
        """
        INSERT INTO campaigns VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        campaigns_seed,
    )

    ops_seed = [
        (
            "OPS-STOCK-01",
            "Manage Operations · Smart Inventory",
            "Weekend Payday Rush: Dairy & Idli-Dosa Batter Restock Alert",
            "8-week UPI item velocity shows +28% morning rush spike on last-weekend-of-month Saturdays. Current Nandini Milk & Fresh Batter standing order will stock out by 9:40 AM.",
            "Ramesh avare, tomorrow morning rush is projected 28% higher. Should I send a WhatsApp reorder to Sri Vinayaka Dairy for +18L milk and +12kg batter?",
            "Auto-dispatch WhatsApp Purchase Order to Supplier (Sri Vinayaka Dairy) & set 6:00 AM delivery confirmation reminder.",
            2450,
            "PENDING",
            None,
        ),
        (
            "OPS-CARE-02",
            "Serve Customers Better · Service Recovery",
            "Peak-Hour Queue Delay Recovery for 2 Loyal Champions",
            "2 top-decile regulars (Karthik & Divya, 12+ visits each) waited >18 mins during yesterday's 1:30 PM rush and left a 3-star Paytm payment feedback tag.",
            "Two loyal regulars faced a lunch queue delay yesterday. Approve a polite Kannada/English apology note with a complimentary Filter Coffee pass on next scan?",
            "Send personalized merchant-signed apology + complimentary ₹30 coffee QR pass (₹60 total cost to protect ₹4,200/mo repeat LTV).",
            4200,
            "PENDING",
            None,
        ),
    ]
    cur.executemany(
        """
        INSERT INTO ops_actions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ops_seed,
    )

    cur.execute(
        "INSERT INTO audit_logs (ts, actor, event_type, detail) VALUES (?, ?, ?, ?)",
        (
            now_str,
            "VyaparVoice Engine",
            "NIGHTLY_SCAN_COMPLETE",
            f"Scanned {len(txns_rows)} Paytm UPI transactions across 240 unique payers. Identified 48 churn-risk regulars (40 policy-eligible) & 3–5 PM dead-hour trough (-68% vs peak).",
        ),
    )

    conn.commit()
    conn.close()
