# Canonical Slide and Documentation Numbers Ledger (results/slide_numbers.md)

Last Updated: 30 October 2026 (Step 0 Baseline Audit; updated automatically after Stage 2)
Rule: Every quantitative figure in Deck v1, Deck v2, SCRIPTS.md, and QA_SHEET.md must match this ledger and carry its designated status tag (`VERIFIED SOURCE`, `BUILT SYNTHETIC`, `SIMULATED`, `ASSUMPTION`, `PILOT TARGET`, or `PENDING`).

---

## 1. Paytm Ecosystem Market Figures (`VERIFIED SOURCE`)
| Metric | Value | Source & Date |
| :--- | :--- | :--- |
| Merchant device subscriptions | `1.57 crore` (+27 lakh YoY) | One97 Communications (Paytm) Q1 FY27 Earnings Release, July 2026 |
| Quarterly Merchant GMV | `Rs 7.1 lakh crore` (+31% YoY) | One97 Communications (Paytm) Q1 FY27 Earnings Release, July 2026 |
| Quarterly Operating Revenue | `Rs 2,448 crore` (+28% YoY) | One97 Communications (Paytm) Q1 FY27 Earnings Release, July 2026 |
| Merchant loan penetration | `~7%` of subscribed devices | One97 Communications (Paytm) Q4 FY26 Earnings Call, May 2026 |
| Repeat merchant borrowers | `>50%` of disbursements | One97 Communications (Paytm) Q1 FY27 Earnings Release, July 2026 |
| Typical Soundbox rental | `Rs 90 to Rs 100 / month` | One97 Communications (Paytm) FY25 Annual Report / Investor Filings |

---

## 2. Synthetic Store Dataset (`BUILT SYNTHETIC` - `app/database.py`, Seed `20261025`)
| Metric | Value | Notes |
| :--- | :--- | :--- |
| Store Persona | Sri Krishna Darshini & Provisions | Indiranagar, Bengaluru (`PYTM-BLR-88412`, synthetic) |
| Total unique UPI payers (60d) | `240` | Seeded across 4 behavioral cohorts |
| Total UPI transactions (60d) | `1,613` | `917` scans in last 30 days |
| 30-day UPI GMV | `Rs 1,74,685` | Mean 30d basket: `Rs 190` |
| Repeat payer share (3+ scans) | `72.9%` | `175 / 240` payers |
| Afternoon dead-hour window | `3:00 PM to 5:00 PM` | Hour 15 (`30` scans in 30d) vs Peak Hour (`101` scans) = `-70.3%` vs peak (`-68%` typical chart illustration) |
| Lapsed evening regulars detected | `48` | Silent `16+` days (range `16 to 38` days, median `19` days, mean `20.8` days) |
| DPDP consent filter pass | `43 / 48` | `5` unconsented payers excluded |
| 14-day cooldown filter pass | `40 / 43` | `3` recently messaged payers excluded; `40` policy-eligible |

---

## 3. Win-Back Campaign & Honest Holdout Statistics (`SIMULATED` - `CMP-WINBACK-01`)
| Metric | Value | Status / Derivation |
| :--- | :--- | :--- |
| Offer terms | `Rs 25` cashback on `Rs 150+` bill | Effective max discount `16.7%` (store floor `<=22.0%`) |
| Experimental split (80/20) | `32` Treatment / `8` Control | Randomized split of `40` eligible payers |
| Nominal cashback cap | `Rs 300` (`12` redemptions max) | Note: `32` passes = `Rs 800` face value unless wave-capped at `12` active passes |
| Simulated 48h returns | `12 / 32` (`37.5%`) vs `1 / 8` (`12.5%`) | `SIMULATED` (`simulate_campaign_48h`) |
| Wilson 95% CI (Treatment) | `22.9% to 54.8%` | Exact Wilson score interval (`12/32`) |
| Wilson 95% CI (Control) | `2.2% to 47.1%` | Exact Wilson score interval (`1/8`) |
| Fisher exact p-value | `p = 0.24` two-sided (`0.18` one-sided) | Not statistically significant (`p > 0.05`); pilot validation required |
| Pilot sample size for 80% power | `46` per arm (`54` continuity-adj.) | Two-sided `alpha = 0.05` for `12.5%` vs `37.5%` (`1:1` split) |
| Gross sales from 12 redeemers | `Rs 2,610` | Assumed mean redeemed bill `Rs 217.50` (`SIMULATED`) |
| Organic redeemer subsidy | `4` buyers (`Rs 100` cashback) | `12.5% x 32 = 4.0` buyers would have returned without offer |
| Net incremental visits & sales | `8` visits / `Rs 1,740` sales | `8 x Rs 217.50 = Rs 1,740` (`SIMULATED`) |
| Incremental sales per Re 1 promo | `5.8x` (`Rs 1,740 / Rs 300`) | Gross sales multiple, NOT profit ROI (`SIMULATED`) |
| Merchant gross profit (30% margin) | `Rs 522` (`1.74x` cashback) | `ASSUMPTION`: `30%` QSR/provisions gross margin |
| Merchant net profit (pre-fee) | `+Rs 222` (`+74%` net profit ROI) | `Rs 522` gross profit minus `Rs 300` cashback (`SIMULATED` + `ASSUMPTION`) |
| Merchant net profit (post 5% fee) | `+Rs 91.50` (`+30.5%` net return) | After `5%` Paytm fee on `Rs 2,610` redeemed bills (`Rs 130.50`) |
| Break-even merchant gross margin | `17.2%` pre-fee / `24.7%` post-fee | Minimum store margin for positive net rupee profit |

---

## 4. Unit Economics, TTS Cost, and Revenue Cases (`ASSUMPTION` / `MODELLED`)
| Metric | Value | Assumptions & Notes |
| :--- | :--- | :--- |
| Pro SaaS add-on price | `Rs 79 / month` | `ASSUMPTION`: bundled with Soundbox billing after 2 free trial campaigns |
| Promo fee revenue (ARPU) | `Rs 102 / month` | `ASSUMPTION`: `5%` fee on `~Rs 2,040/mo` redeemed promo bills (~1 campaign/wk) |
| Partner credit fee uplift (ARPU) | `Rs 77 / month` | `ASSUMPTION`: amortized `1.5% to 2.5%` origination fee on incremental loan conversion |
| Blended ARPU (all 3 streams) | `Rs 258 / month` | `Rs 181 / month` excluding credit uplift; `Rs 79 / month` SaaS only |
| SLM intent/planning cost | `Rs 1.80 / shop / month` | `ASSUMPTION`: structured prompts on small/open-weight models |
| Indic TTS cost (cached vs uncached) | `Rs 3.20` cached / `Rs 27.00` uncached | Sarvam Bulbul v3 (`Rs 30 / 10k chars`, `9k chars/mo`); `Rs 3.20` requires `~88%` template cache hit (`Rs 13.50` uncached on v2) |
| Messaging / push delivery COGS | `Rs 43.00 / shop / month` | `ASSUMPTION`: mix of free Paytm app push + paid WhatsApp utility/marketing messages |
| Total monthly COGS per shop | `Rs 48.00` cached / `Rs 71.80` uncached | `Rs 1.80 + Rs 3.20 + Rs 43.00` (or `+ Rs 27.00` uncached TTS) |
| Software gross margin | `81.4%` cached / `72.2%` uncached | `Rs 210 / Rs 258` cached; `Rs 186.20 / Rs 258` uncached |
| Target base (5% device adoption) | `7.85 lakh` merchants | `5%` of `1.57 crore` Paytm device subscribers |
| **Revenue Case C (SaaS Only)** | **`Rs 74.4 crore ARR`** | `7.85L x Rs 79 x 12` (`MODELLED`) |
| **Revenue Case B (Excl. Credit)** | **`Rs 170.5 crore ARR`** | `7.85L x Rs 181 x 12` (`MODELLED`) |
| **Revenue Case A (Full Base Case)** | **`Rs 243.0 crore ARR`** | `7.85L x Rs 258 x 12` (`MODELLED`) |

---

## 5. Sponsor & External Integrations Status
- **Sarvam AI:** `PENDING` live verification during Saturday 11:00 AM - 1:00 PM sponsor build window (500 sponsor credits). Zero live Sarvam claims permitted in Deck v1.
- **Groq API:** `OPTIONAL` keyless free-tier adapter (no card required; English grounded Q&A only).
- **Kannada & Hindi Merchant Strings:** `UNREVIEWED DRAFT` pending native-speaker check via `docs/COPY_REVIEW.md`.
