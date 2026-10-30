"""
Reproducible Unit-Economics, Store ROI Sensitivity, Sarvam Credit Cap, and Paytm Q2 FY27 ARR Generator (Task 8).
Reads canonical configuration from config/default.yaml and config/sarvam.yaml plus app/stats.py,
and writes results/unit_economics.md.

Run: python3 scripts/unit_economics.py
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yaml
from app.copy_lint import find_formatting_violations
from app.stats import (
    compute_bayesian_profit_posterior,
    compute_breakeven_lift,
    compute_cap_binding_risk,
    compute_margin_fee_sensitivity_table,
    compute_pooled_pilot_power_table,
    evaluate_itt_holdout_and_profit,
)


def generate_unit_economics_markdown() -> str:
    d_cfg = yaml.safe_load((ROOT / "config" / "default.yaml").read_text(encoding="utf-8"))
    s_cfg = yaml.safe_load((ROOT / "config" / "sarvam.yaml").read_text(encoding="utf-8"))

    econ = d_cfg["economics"]
    saas_inr = float(econ["saas_addon_monthly_inr"])  # 79.0
    fee_pct = float(econ["paytm_promo_fee_pct"])  # 5.0
    steady_waves = float(econ["steady_state_campaigns_per_month"])  # 0.782
    steady_redeemed_gmv = float(econ["steady_state_redeemed_gmv_monthly_inr"])  # 2040.0
    promo_arpu_inr = round(steady_redeemed_gmv * (fee_pct / 100.0), 2)  # 102.0
    credit_arpu_inr = float(econ["credit_referral_monthly_inr"])  # 77.0

    slm_cogs = float(econ["slm_monthly_cogs_inr"])  # 1.80
    tts_cached_cogs = float(econ["tts_cached_monthly_cogs_inr"])  # 3.20
    tts_uncached_cogs = float(econ["tts_uncached_monthly_cogs_inr"])  # 27.00
    msg_cogs = float(econ["messaging_monthly_cogs_inr"])  # 43.00

    cogs_cached = round(slm_cogs + tts_cached_cogs + msg_cogs, 2)  # 48.00
    cogs_uncached = round(slm_cogs + tts_uncached_cogs + msg_cogs, 2)  # 71.80
    tts_cache_hit_pct = round((1.0 - (tts_cached_cogs / tts_uncached_cogs)) * 100.0, 1)  # 88.1%

    arpu_case_c = saas_inr  # 79.0
    arpu_case_b = round(saas_inr + promo_arpu_inr, 2)  # 181.0
    arpu_case_a = round(arpu_case_b + credit_arpu_inr, 2)  # 258.0

    gm_c_cached = round(((arpu_case_c - cogs_cached) / arpu_case_c) * 100.0, 1)
    gm_b_cached = round(((arpu_case_b - cogs_cached) / arpu_case_b) * 100.0, 1)
    gm_a_cached = round(((arpu_case_a - cogs_cached) / arpu_case_a) * 100.0, 1)
    gm_a_uncached = round(((arpu_case_a - cogs_uncached) / arpu_case_a) * 100.0, 1)

    merchants_cr = float(econ["paytm_merchant_subscriptions_cr"])  # 1.64 Cr (Paytm Q2 FY27, 26 Oct 2026)
    total_merchants = int(round(merchants_cr * 10_000_000))  # 16,400,000

    # Canonical CMP-WINBACK-01 single-wave readout
    ev_single = evaluate_itt_holdout_and_profit(
        treatment_count=32,
        itt_treatment_returned=12,
        holdout_count=8,
        holdout_returned=1,
        funded_redemptions=12,
        refused_redemptions=0,
        cap_reached=True,
        offer_rupees=25,
        max_budget=300,
        gross_returning_sales_inr=2610.0,
        funded_redeemed_sales_inr=2610.0,
        gross_margin_pct=30.0,
        paytm_fee_pct=5.0,
    )
    pw = ev_single["profit_waterfall"]
    be_lift = compute_breakeven_lift(0.125, 217.50, 30.0, 25.0, 5.0)
    cap_risk_300 = compute_cap_binding_risk(32, 25, 300, 0.375, 0.10)
    bayes_single = compute_bayesian_profit_posterior(32, 12, 8, 1, 25, 300, 217.50, 30.0, 5.0)
    sens = compute_margin_fee_sensitivity_table(
        incremental_sales_inr=pw["incremental_sales_inr"],
        budget_spent_inr=300.0,
        funded_redeemed_sales_inr=2610.0,
    )
    pooled = compute_pooled_pilot_power_table()

    # Portfolio penetration rows
    pen_rates = [0.01, 0.025, 0.05, 0.10]
    pen_rows = []
    for p in pen_rates:
        shops = int(round(total_merchants * p))
        shops_lakh = shops / 100_000.0
        arr_c_cr = (shops * arpu_case_c * 12.0) / 10_000_000.0
        arr_b_cr = (shops * arpu_case_b * 12.0) / 10_000_000.0
        arr_a_cr = (shops * arpu_case_a * 12.0) / 10_000_000.0
        net_gp_b_cr = (shops * (arpu_case_b - cogs_cached) * 12.0) / 10_000_000.0
        net_gp_a_cr = (shops * (arpu_case_a - cogs_cached) * 12.0) / 10_000_000.0
        pen_rows.append(
            f"| `{p*100:.1f}%` | `{shops_lakh:.2f} lakh` | `Rs {arr_c_cr:.1f} Cr` | "
            f"`Rs {arr_b_cr:.1f} Cr` (`Rs {net_gp_b_cr:.1f} Cr` GP) | "
            f"`Rs {arr_a_cr:.1f} Cr` (`Rs {net_gp_a_cr:.1f} Cr` GP) |"
        )

    # Sensitivity markdown rows
    sens_md_rows = []
    for r in sens["rows"]:
        m = int(r["gross_margin_pct"])
        c_map = {c["fee_pct"]: c["net_profit_inr"] for c in r["cells"]}
        sens_md_rows.append(
            f"| `{m}%` {'**(Base)**' if m == 30 else ''} | `Rs {r['incremental_gross_profit_inr']:.2f}` | "
            f"`{c_map[0.0]:+.2f}` | `{c_map[3.0]:+.2f}` | **`{c_map[5.0]:+.2f}`** | `{c_map[7.0]:+.2f}` |"
        )

    # Sarvam Saturday 500-credit budget proof
    tts_rate = float(s_cfg["tts"]["cost_per_10k_chars_inr"])  # 30.0
    stt_rate = float(s_cfg["stt"]["cost_per_hour_inr"])  # 30.0
    tts_cap_pct = float(s_cfg["credit_caps"]["tts_max_share_pct"])  # 15.0
    stt_cap_pct = float(s_cfg["credit_caps"]["stt_max_share_pct"])  # 15.0
    tot_cap_pct = float(s_cfg["credit_caps"]["total_max_share_pct"])  # 30.0
    sponsor_credits = 500.0
    tts_cap_cr = sponsor_credits * (tts_cap_pct / 100.0)
    stt_cap_cr = sponsor_credits * (stt_cap_pct / 100.0)
    tot_cap_cr = sponsor_credits * (tot_cap_pct / 100.0)
    max_tts_chars = int((tts_cap_cr / tts_rate) * 10_000)
    max_stt_hours = round(stt_cap_cr / stt_rate, 2)

    lines = [
        "# Reproducible Unit Economics, Store ROI & Portfolio ARR Report (results/unit_economics.md)",
        "",
        "Generated by: `python3 scripts/unit_economics.py`",
        "Config Sources: `config/default.yaml`, `config/sarvam.yaml`, `app/stats.py`",
        "Primary Ecosystem Anchor: Paytm Q2 FY27 Earnings Release (26 October 2026, `1.64 crore` subscription-paying merchant devices; `https://paytm.com/document/ir/financial-results/fy2026-27/Paytm_Q2-FY27_Earnings_Release.pdf`)",
        "",
        "---",
        "",
        "## 1. Per-Merchant Monthly Revenue & Cost Waterfall (`MODELLED` / `ASSUMPTION`, Evidence Grade C)",
        "",
        "### 1.1 Fee Reconciliation (`Rs 130.50` Single Wave vs `Rs 102.00 / month` Steady-State)",
        f"- **Fee Base Rule:** Paytm's `{fee_pct:.1f}%` promotional take-rate applies to **all funded QR-redeemed campaign bills, including organic returners who redeem an offer pass**.",
        f"- **Single Launch Wave (`CMP-WINBACK-01`):** `12` funded redemptions x `Rs 217.50` average bill = `Rs 2,610.00` redeemed bill volume -> `{fee_pct:.1f}%` fee = **`Rs {pw['paytm_fee_on_all_redeemed_bills_inr']:.2f}`**.",
        f"- **Monthly Steady-State (`Rs {promo_arpu_inr:.2f} / month`):** Under the `{econ['cooldown_days']}-day` per-customer anti-spam cooldown, an individual store's lapsed regular pool replenishes gradually after the first backlog wave at **`~{steady_waves:.2f}` full win-back-equivalent waves/month** (`Rs {steady_redeemed_gmv:.0f}/mo` redeemed promo bills x `{fee_pct:.1f}%` = **`Rs {promo_arpu_inr:.2f}/mo`**).",
        "",
        "### 1.2 Monthly Per-Merchant ARPU & AI/Messaging COGS Stack",
        "| Line Item | Monthly Rupee Value | Status & Basis |",
        "| :--- | :--- | :--- |",
        f"| **Pro Voice Copilot SaaS Add-on** | `Rs {saas_inr:.2f}` | `ASSUMPTION`: Soundbox add-on (vs `ASSUMPTION Rs 90 to Rs 100/mo` base Soundbox rental) |",
        f"| **Steady-State Promo Fee (`5%` of `Rs {steady_redeemed_gmv:.0f}`)** | `Rs {promo_arpu_inr:.2f}` | `MODELLED`: `~{steady_waves:.2f}` waves/mo on all redeemed campaign bills |",
        f"| **Partner Working-Capital Referral Uplift** | `Rs {credit_arpu_inr:.2f}` | `ASSUMPTION`: amortized origination share (`~7%` merchant loan penetration assumption) |",
        f"| **SLM / Intent & Ledger Compute COGS** | `-Rs {slm_cogs:.2f}` | Deterministic SQLite engine + zero-PII intent classification |",
        f"| **Sarvam Bulbul v3 TTS COGS (Cached vs Uncached)** | `-Rs {tts_cached_cogs:.2f}` (`-Rs {tts_uncached_cogs:.2f}` uncached) | `~{tts_cache_hit_pct}%` SHA-256 phrase-cache hit rate at `Rs {tts_rate:.0f} / 10k chars` |",
        f"| **WhatsApp / Paytm App Nudge Delivery COGS** | `-Rs {msg_cogs:.2f}` | Utility/offer pass push & WhatsApp dispatch |",
        f"| **Total Monthly COGS (Cached / Uncached)** | **`Rs {cogs_cached:.2f}` / `Rs {cogs_uncached:.2f}`** | Saving `Rs {tts_uncached_cogs - tts_cached_cogs:.2f}/merchant/mo` via phrase caching |",
        "",
        "### 1.3 Three Revenue Scenarios (Separating Core SaaS+Promo from Credit Assumptions)",
        "| Scenario | Monthly ARPU | Cached COGS | Monthly Gross Profit | Cached Gross Margin | Uncached Gross Margin |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
        f"| **Case C: SaaS Add-on Only** | `Rs {arpu_case_c:.2f}` | `Rs {cogs_cached:.2f}` | `Rs {arpu_case_c - cogs_cached:.2f}` | `{gm_c_cached}%` | `{round(((arpu_case_c - cogs_uncached)/arpu_case_c)*100,1)}%` |",
        f"| **Case B: SaaS + Promo Fee (Excl. Credit)** | `Rs {arpu_case_b:.2f}` | `Rs {cogs_cached:.2f}` | `Rs {arpu_case_b - cogs_cached:.2f}` | **`{gm_b_cached}%`** | `{round(((arpu_case_b - cogs_uncached)/arpu_case_b)*100,1)}%` |",
        f"| **Case A: Full Base Case (Incl. Credit)** | `Rs {arpu_case_a:.2f}` | `Rs {cogs_cached:.2f}` | `Rs {arpu_case_a - cogs_cached:.2f}` | **`{gm_a_cached}%`** | `{gm_a_uncached}%` |",
        "",
        "---",
        "",
        "## 2. Store-Level Win-Back Economics, Cap Risk & Margin Sensitivity (`CMP-WINBACK-01`)",
        "",
        f"- **Cap-Binding Risk (`Rs 300` stop on `32` passes = `Rs 800` face exposure):** `P(Binomial(32, 0.375) > 12) = {cap_risk_300['prob_exceeds_cap_pct']}%` (`>10%` alert threshold -> suggests `Rs {cap_risk_300['suggested_cap_inr']}` cap for `<=10%` refusal probability).",
        f"- **Canonical 48h ITT Waterfall (`12/32` vs `1/8`, `Rs 217.50` avg bill):** Gross returning sales `Rs {pw['gross_returning_sales_inr']:.2f}`, organic expected `4.0` visits (`Rs {pw['organic_subsidy_inr']:.2f}` organic cashback subsidy), net incremental sales **`Rs {pw['incremental_sales_inr']:.2f}`** (`{pw['gross_sales_multiple']}x` spend), gross profit at `30%` margin **`Rs {pw['incremental_gross_profit_inr']:.2f}`**, net profit **`+Rs {pw['net_profit_pre_fee_inr']:.2f}` pre-fee** / **`+Rs {pw['net_profit_post_fee_inr']:.2f}` post-5%-fee**.",
        f"- **Break-Even Thresholds:** Minimum shop gross margin at `+25 pp` lift is **`{pw['breakeven_margin_pre_fee_pct']}%` pre-fee** and **`{pw['breakeven_margin_post_fee_pct']}%` post-5%-fee**. At `30%` shop margin, minimum required lift above `12.5%` baseline is **`+{be_lift['breakeven_lift_pre_fee_pp']} pp` pre-fee (`{be_lift['breakeven_rate_pre_fee_pct']}%`)** and **`+{be_lift['breakeven_lift_post_fee_pp']} pp` post-5%-fee (`{be_lift['breakeven_rate_post_fee_pct']}%`)**.",
        f"- **Bayesian Single-Wave Posterior (`Beta(1,1)` uniform prior, `10,000` draws):** `P(Lift > 0) = {bayes_single['prob_lift_positive_pct']}%`, `P(Pre-Fee Profit > Rs 0) = {bayes_single['prob_profit_pre_fee_pct']}%`, `P(Post-Fee Profit > Rs 0) = {bayes_single['prob_profit_post_fee_pct']}%`, 95% credible interval per nudged buyer **`[Rs {bayes_single['posterior_profit_per_nudged_ci_95_inr'][0]}, Rs {bayes_single['posterior_profit_per_nudged_ci_95_inr'][1]}]`** (confirming why a 50-shop pooled pilot of `{pooled['total_n']}` buyers with `{pooled['rows'][2]['power_pct']}%` power at `+6 pp` lift is required before rollout).",
        "",
        "### Store Net Profit Sensitivity Matrix (Rs) Across Shop Gross Margin x Paytm Promo Fee",
        "| Shop Gross Margin | Incremental GP (`Rs 1,740` Sales) | `0%` Fee (SaaS Only) | `3%` Redeemed Fee | **`5%` Base Fee (`Rs 130.50`)** | `7%` Redeemed Fee |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
        *sens_md_rows,
        "",
        "*Takeaway for Low-Margin Kiranas (`15% to 20%` gross margin):* A `Rs 25` cashback on `Rs 150+` bills loses money (`-Rs 82.50` at `20%` margin post-fee). For low-margin grocery counters, VyaparVoice lowers the offer to `Rs 10 to Rs 15` on `Rs 250+` bills (`4% to 6%` discount).",
        "",
        "---",
        "",
        "## 3. Paytm Portfolio ARR Sensitivity (Anchored to Q2 FY27 `1.64 Crore` Subscription Merchants)",
        "",
        "| Adoption % of `1.64 Cr` Base | Active Shops | Case C ARR (`Rs 79` SaaS) | Case B ARR (`Rs 181` Excl. Credit) | Case A ARR (`Rs 258` Full Base) |",
        "| :--- | :--- | :--- | :--- | :--- |",
        *pen_rows,
        "",
        "---",
        "",
        "## 4. Saturday Live Demo Sponsor Credit Safeguard (`500` Sarvam Credits)",
        "",
        f"- **Hard Ledger Caps (`app/ledger.py`):** TTS `<= {tts_cap_pct:.0f}%` (**`{tts_cap_cr:.0f}` credits** = `{max_tts_chars:,}` Bulbul v3 chars), STT `<= {stt_cap_pct:.0f}%` (**`{stt_cap_cr:.0f}` credits** = `{max_stt_hours}` hours Saaras v3 audio), Universal Total `<= {tot_cap_pct:.0f}%` (**`{tot_cap_cr:.0f}` credits** max; **`{sponsor_credits - tot_cap_cr:.0f}` credits** untouched safety reserve).",
        "- **Public Render Deployment (`PUBLIC_DEPLOY=true`):** `0` credits consumed (`paid_calls_blocked=true`; deterministic Web Speech + cached audio only).",
        "",
    ]

    md = "\n".join(lines)
    issues = find_formatting_violations(md)
    if issues:
        raise RuntimeError(f"Generated unit_economics.md violated formatting rules: {issues}")
    return md


def main() -> int:
    out_path = ROOT / "results" / "unit_economics.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    md = generate_unit_economics_markdown()
    out_path.write_text(md, encoding="utf-8")
    print(f"[OK] Wrote reproducible unit economics report to {out_path} ({len(md)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
