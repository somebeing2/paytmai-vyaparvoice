# Canonical Slide and Documentation Numbers Ledger (results/slide_numbers.md)

Last Updated: 30 October 2026 (Stage 1 Reconciled Ledger: Paytm Q2 FY27 Release + ITT Cap + 80/20 Power + Fee Reconciliation)
Rule: Every quantitative figure in Deck v1/v2, SCRIPTS.md, QA_SHEET.md, and UI scorecards must match this ledger and carry its designated status tag (`Reported (Paytm Q2 FY27 release)`, `BUILT SYNTHETIC`, `SIMULATED`, `ASSUMPTION`, `PILOT TARGET`, or `PENDING`).

---

## 1. Paytm Ecosystem Market Figures (Updated to Latest Reported Quarter: Q2 FY27)

Primary Sources:
- **Paytm Q2 FY27 Earnings Release PDF (26 Oct 2026):** `https://paytm.com/document/ir/financial-results/fy2026-27/Paytm_Q2-FY27_Earnings_Release.pdf`
- **Paytm Investor Relations Financial Results Portal:** `https://ir.paytm.com/financial-results`
- **Paytm Official IR Summary Blog (26-27 Oct 2026):** `https://paytm.com/blog/investor-relations/paytm-q2-fy27-results-pat-225-crore-ebitda-rises-90-to-270-crore/`
- **Historical Device Rental & Penetration Benchmarks (Paytm IR Filings):**
  - May 2023 Investor Presentation (`https://paytm.com/document/ir/financial-results/presentation/Paytm_Investor_Presentation_May_2023_INR.pdf`, Subscription Charges: Rs 100/mo per active device)
  - Q2 FY24 Earnings Release, 20 Oct 2023 (`https://paytm.com/document/ir/financial-results/Paytm_Q2_FY24_Earnings_Release_INR.pdf`, Merchant Loan penetration: 6.4% of device merchants; 4.4% in Q1 FY25 release dated 19 Jul 2024: `https://paytm.com/document/ir/press-release/fy2024-25/jul/Paytm-Q1-FY25-Earnings-Release.pdf`)

| Metric | Value | Status Tag & Exact Attribution |
| :--- | :--- | :--- |
| Subscription-paying merchant deployments (Soundbox & devices) | `1.64 crore` (+27 lakh YoY) | `Reported (Paytm Q2 FY27 release, 26 Oct 2026)` (up from `1.57 crore` in Q1 FY27) |
| Quarterly Merchant GMV | `Rs 7.1 lakh crore` (+26% YoY) | `Reported (Paytm Q2 FY27 release, 26 Oct 2026)` |
| Quarterly Operating Revenue | `Rs 2,648 crore` (+28% YoY, +8% QoQ) | `Reported (Paytm Q2 FY27 release, 26 Oct 2026)` (`Rs 2,636 Cr` comparable ex-PIDF, +33% YoY) |
| Quarterly EBITDA & Margin | `Rs 270 crore` (+90% YoY, `10%` margin) | `Reported (Paytm Q2 FY27 release, 26 Oct 2026)` |
| Quarterly Profit After Tax (PAT) | `Rs 225 crore` | `Reported (Paytm Q2 FY27 release, 26 Oct 2026)` |
| Financial Services Distribution Revenue | `Rs 912 crore` (+49% YoY) | `Reported (Paytm Q2 FY27 release, 26 Oct 2026)` |
| Key Financial Services Customers (Consumer + Merchant) | `8.8 lakh` (+35% YoY) | `Reported (Paytm Q2 FY27 release, 26 Oct 2026)` |
| Repeat Merchant Borrower Share | `>50%` of merchant loan disbursements | `Reported (Paytm Q2 FY27 release, 26 Oct 2026)` |
| Monthly Transacting Users (MTUs) | `8.5 crore` (+1.0 crore YoY) | `Reported (Paytm Q2 FY27 release, 26 Oct 2026)` |
| Merchant-only device loan penetration (`~7%`) | `~7%` | `ASSUMPTION` (Q2 FY27 reports `"low and increasing loan penetration"` and `8.8 lakh` combined consumer+merchant financial customers; historical Paytm IR reported `6.4%` in Q2 FY24 and `4.4%` in Q1 FY25) |
| Typical Soundbox monthly rental (`Rs 90 to Rs 100/mo`) | `Rs 90 to Rs 100 / month` | `ASSUMPTION` (Q2 FY27 does not isolate per-Soundbox ARPU; benchmarked to Paytm May 2023 IR presentation `Rs 100/mo` and Q2 FY24 call `~Rs 100 net of GST`) |

---

## 2. Synthetic Store Dataset (`BUILT SYNTHETIC` - `app/database.py`, Seed `20261025`, Evidence Grade A in Store Context)

| Metric | Value | Notes |
| :--- | :--- | :--- |
| Store Persona | Sri Krishna Darshini & Provisions | Indiranagar, Bengaluru (`PYTM-BLR-88412`, synthetic) |
| Total unique UPI payers (60d) | `240` | Seeded across 4 behavioral archetypes |
| Total UPI transactions (60d) | `1,613` | `917` scans in last 30 days |
| 30-day UPI GMV | `Rs 1,74,685` | Mean 30d basket: `Rs 190` |
| Repeat payer share (3+ scans) | `72.9%` | `175 / 240` payers |
| Afternoon dead-hour window | `3:00 PM to 5:00 PM` | Hour 15 (`30` scans in 30d) vs Peak Hour (`101` scans) = `-70.3%` vs peak |
| Lapsed evening regulars detected | `48` | Silent `16+` days (range `16 to 38` days, median `19` days, mean `20.8` days) |
| DPDP consent filter pass | `43 / 48` | `5` unconsented payers excluded |
| 14-day cooldown filter pass | `40 / 43` | `3` recently messaged payers excluded; `40` policy-eligible |

---

## 3. Win-Back Campaign, ITT Cap-vs-Holdout & Power (`SIMULATED` - `CMP-WINBACK-01`, Evidence Grade B)

| Metric | Value | Status / Derivation |
| :--- | :--- | :--- |
| Offer terms | `Rs 25` cashback on `Rs 150+` bill | Effective max discount `16.7%` (store floor `<=22.0%`) |
| Experimental split (80/20) | `32` Nudged (Treatment) / `8` Control | Randomized split of `40` eligible payers per wave |
| Passes issued vs Hard spend stop | `32` passes (`Rs 800` face exposure) vs `Rs 300` hard stop (`12` funded max) | Disclosed trade-off: every nudged customer receives a pass; cap stops cashback spend at `Rs 300` (`12` redemptions) and records `cap_reached` + `refused_redemptions` |
| Pre-approval cap-binding probability | `42.2%` at `p = 37.5%` (`16.3%` at `p = 30.0%`) | `P(Binomial(32, p) > 12) > 10%` triggers merchant warning; suggested cap for `<=10%` overrun risk is `Rs 400` (`16` redemptions) at `p = 37.5%` or `Rs 325` (`13` redemptions) at `p = 30.0%` |
| Simulated 48h ITT returns | `12 / 32` (`37.5%`) vs `1 / 8` (`12.5%`) | `SIMULATED`: note explicitly on slides that **simulated `12` returning nudged buyers equals the `Rs 300` cap (`12 x Rs 25`, `cap_reached = True`, `refused_redemptions = 0`)**; holdout analysis is Intention-to-Treat (ITT), unchanged if cap binds |
| Wilson 95% CI (Treatment ITT) | `22.9% to 54.8%` | Exact Wilson score interval (`12/32`) |
| Wilson 95% CI (Control) | `2.2% to 47.1%` | Exact Wilson score interval (`1/8`) |
| Fisher exact p-value (ITT) | `p = 0.24` two-sided (`0.18` one-sided) | Interim directional readout (`p > 0.05`); single wave (`N = 40`) is underpowered |
| **Power @ 80/20 split (`r = 4.0`)** | **`31` control + `124` nudged = `155` total (`~4` waves of `40`)** | Two-sided `alpha = 0.05`, `80%` power for `12.5%` vs `37.5%` at actual `80/20` campaign split |
| **Power @ 50/50 even split (`r = 1.0`)** | **`46` per arm (`92` total)** | Two-sided `alpha = 0.05`, `80%` power for `12.5%` vs `37.5%` at `1:1` split (`54/arm` continuity-adjusted) |
| Gross sales from 12 redeemers | `Rs 2,610` | Simulated mean redeemed bill `Rs 217.50` (`[195, 210, 225, 240]`) |
| Organic redeemer subsidy | `4` buyers (`Rs 100` cashback) | `12.5% x 32 = 4.0` nudged buyers expected to return organically (`Rs 870` baseline sales) |
| Net incremental visits & sales | `8` visits / `Rs 1,740` sales | `8 x Rs 217.50 = Rs 1,740` (`5.8x` gross incremental sales per Re 1 cashback) |
| Merchant gross profit (`30%` margin) | `Rs 522` (`1.74x` cashback) | `ASSUMPTION`: `30%` darshini/provisions gross margin (Evidence Grade C) |
| Merchant net profit (pre-fee) | `+Rs 222` (`+74.0%` net profit ROI) | `Rs 522` gross profit minus `Rs 300` cashback (`SIMULATED` + `ASSUMPTION`) |
| Paytm `5%` promo fee on this campaign | `Rs 130.50` | `5%` of **all `Rs 2,610` redeemed bills (`12` bills, including the `4` organic returners)** |
| Merchant net profit (post `5%` fee) | `+Rs 91.50` (`+30.5%` net return) | `Rs 222.00 - Rs 130.50 = +Rs 91.50` |
| Break-even merchant gross margin | `17.2%` pre-fee / `24.7%` post-fee | Minimum store gross margin for positive net rupee profit |

---

## 4. Unit Economics, Fee Reconciliation & ARR Cases (`ASSUMPTION` / `MODELLED`, Evidence Grade C)

### Fee Reconciliation (`Rs 130.50` Single Campaign vs `Rs 102 / month` Steady-State ARPU)
- **Fee Base Definition:** Paytm charges a `5%` success fee on **total gross value of QR-redeemed campaign bills (including organic returners who redeem a pass)**, because scan-time settlement observes individual pass redemptions rather than counterfactual identity.
- **Single Launch Wave (`CMP-WINBACK-01`):** `12` redeemed bills x `Rs 217.50` = `Rs 2,610` redeemed bill volume -> `5%` fee = **`Rs 130.50`** on that campaign.
- **Monthly Steady-State ARPU (`Rs 102 / month`):** Assumes **`Rs 2,040 / month`** in redeemed campaign bills (`5% x Rs 2,040 = Rs 102/mo`), equivalent to **`~0.78` full win-back waves per month** (`~9.4` redeemed bills/month across 1-2 smaller biweekly campaigns, reflecting gradual replenishment of a neighborhood store's 14-day cooldown-eligible lapsed pool after the initial backlog wave).

### Per-Merchant Monthly Unit Economics & 5% Adoption ARR (Updated to Q2 FY27 `1.64 Crore` Base)
| Metric | Value (Q2 FY27 `1.64 Cr` Base) | Notes & Assumptions |
| :--- | :--- | :--- |
| Pro SaaS add-on price | `Rs 79 / month` | `ASSUMPTION`: Soundbox voice copilot add-on after 2 free trial campaigns |
| Promo fee ARPU (steady-state) | `Rs 102 / month` | `ASSUMPTION`: `5%` fee on `Rs 2,040/mo` total redeemed promo bills (`~0.78` full waves/mo; includes organic redeemers) |
| Partner credit referral uplift | `Rs 77 / month` | `ASSUMPTION`: amortized `1.5% to 2.5%` partner origination fee on incremental loan conversion |
| Blended ARPU | `Rs 258 / month` | `Rs 181 / month` excluding credit; `Rs 79 / month` SaaS-only |
| SLM intent/planning cost | `Rs 1.80 / shop / month` | `ASSUMPTION`: structured prompts on compact models |
| Indic TTS cost | `Rs 3.20` cached / `Rs 27.00` uncached | Sarvam Bulbul v3 (`Rs 30 / 10k chars`, `9k chars/mo`); `Rs 3.20` assumes `~88%` phrase-cache hit (`Rs 13.50` uncached on v2) |
| Messaging / push delivery COGS | `Rs 43.00 / shop / month` | `ASSUMPTION`: Paytm app push + WhatsApp utility/marketing notifications |
| Total monthly COGS per shop | `Rs 48.00` cached / `Rs 71.80` uncached | Software gross margin on `Rs 258` ARPU: `81.4%` cached / `72.2%` uncached |
| **Target Base (`5%` of `1.64 Cr` Q2 FY27 devices)** | **`8.20 lakh` merchants** | `5% x 1,64,00,000 = 8,20,000` shops *(Note: Deck v1 used Q1 FY27 `1.57 Cr` -> `7.85L` shops = `Rs 74.4 Cr / Rs 170.5 Cr / Rs 243.0 Cr`)* |
| **Revenue Case C (SaaS Only, `Rs 79/mo`)** | **`Rs 77.7 crore ARR`** | `8.20L x Rs 79 x 12` (`39.2%` cached gross margin; zero campaign or credit fees) |
| **Revenue Case B (Excl. Credit, `Rs 181/mo`)** | **`Rs 178.1 crore ARR`** | `8.20L x Rs 181 x 12` (`73.5%` cached gross margin; zero credit assumptions) |
| **Revenue Case A (Full Base Case, `Rs 258/mo`)** | **`Rs 253.9 crore ARR`** | `8.20L x Rs 258 x 12` (`81.4%` cached gross margin / `72.2%` uncached) |

---

## 5. Sponsor & Copy Review Status
- **Sarvam AI:** Keyless adapter + mock server + `15%/15%` (`30%` max) universal credit cap built in Stage 1 (`Task 7`); live voice calls remain `PENDING` Saturday 11:00 AM - 1:00 PM sponsor window.
- **Kannada & Hindi Merchant Strings:** `DRAFT - UNREVIEWED BY NATIVE SPEAKER` (`docs/COPY_REVIEW.md`).
- **Live Demo URL:** `https://paytmai-vyaparvoice.onrender.com`
