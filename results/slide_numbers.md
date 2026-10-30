# Canonical Slide and Documentation Numbers Ledger (results/slide_numbers.md)

Last Updated: 30 October 2026 (Deck v2.1 Ledger: Pooled 50-Shop Stratified Power + Break-Even Lift + Paytm Q2 FY27 + ITT Cap + Fee Reconciliation)
Rule: Every quantitative figure in Deck v2.1, SCRIPTS.md, QA_SHEET.md, and UI scorecards must match this ledger and carry its designated status tag (`Reported (Paytm Q2 FY27 release)`, `BUILT SYNTHETIC`, `SIMULATED`, `ASSUMPTION`, `PILOT TARGET`, or `PENDING`).

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
| Merchant-only device loan penetration (`~7%`) | `~7%` | `ASSUMPTION` (Q2 FY27 states `"low and increasing loan penetration"` without a merchant-only `%`; historical Paytm IR reported `6.4%` in Q2 FY24 and `4.4%` in Q1 FY25. Slide A2 omits combined FS customer counts to avoid conflation.) |
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
| Afternoon slow-hour window | `3:00 PM to 5:00 PM` | Hour 15 (`30` scans in 30d) vs Peak Hour (`101` scans) = `-70.3%` vs peak |
| Lapsed evening regulars detected | `48` | Silent `16+` days (range `16 to 38` days, median `19` days, mean `20.8` days) |
| DPDP consent filter pass | `43 / 48` | `5` unconsented payers excluded |
| 14-day cooldown filter pass | `40 / 43` | `3` recently messaged payers excluded; `40` policy-eligible |

---

## 3. Win-Back Campaign, ITT Cap-vs-Holdout, Power & Pooled Pilot Design (`SIMULATED`, Evidence Grade B)

### 3.1 Single-Wave ITT Readout (`CMP-WINBACK-01`)
| Metric | Value | Status / Derivation |
| :--- | :--- | :--- |
| Offer terms | `Rs 25` cashback on `Rs 150+` bill | Effective max discount `16.7%` (store floor `<=22.0%`) |
| Experimental split (80/20) | `32` Nudged (Treatment) / `8` Control | Randomized split of `40` eligible payers per store wave |
| Passes issued vs Hard spend stop | `32` passes (`Rs 800` face exposure) vs `Rs 300` hard stop (`12` funded max) | Every nudged customer gets a pass (`valid while shop offer budget lasts`); cap stops cashback spend at `Rs 300` (`12` redemptions) and records `cap_reached` + `refused_redemptions` |
| Pre-approval cap-binding probability | `42.2%` at `p = 37.5%` (`16.3%` at `p = 30.0%`) | `P(Binomial(32, p) > 12) > 10%` triggers merchant warning; suggested cap for `<=10%` overrun risk is `Rs 400` (`16` redemptions) at `p = 37.5%` |
| Intention-to-Treat (ITT) definition | All `32` assigned nudged vs all `8` assigned control | Compares every assigned customer regardless of redemption or cap stop, preventing selection bias |
| Simulated 48h ITT returns | `12 / 32` (`37.5%`) vs `1 / 8` (`12.5%`) | `SIMULATED`: **simulated `12` returning nudged buyers equals the `Rs 300` cap (`12 x Rs 25`, `cap_reached = True`, `refused_redemptions = 0`)**; ITT comparison is invariant if cap binds |
| Wilson 95% CI (Treatment vs Control) | `22.9% to 54.8%` vs `2.2% to 47.1%` | Exact Wilson score intervals (`12/32` vs `1/8`) |
| Fisher exact p-value (ITT) | `p = 0.24` two-sided (`0.18` one-sided) | Single store wave (`N = 40`) is an interim directional readout (`p > 0.05`) |
| Sample size for `25 pp` lift (`12.5%` vs `37.5%`) | `31` control + `124` nudged = `155` (`80/20`) or `46/arm` (`50/50`) | Two-sided `alpha = 0.05`, `80%` power (`~4` pooled store-waves of `40`; note a single store does NOT yield 4 full waves in 4 weeks due to the 14-day cooldown and `~0.78` waves/mo replenishment) |
| Gross sales & organic subsidy | `Rs 2,610` gross; `4` organic (`Rs 100` subsidy) | `12 x Rs 217.50 = Rs 2,610`; `8` net incremental visits = `Rs 1,740` incremental sales (`5.8x` promo spend) |
| Merchant net profit (`30%` margin) | `+Rs 222` pre-fee (`+74%`) / `+Rs 91.50` post-5%-fee (`+30.5%`) | `Rs 522` gross profit (`1.74x` promo) minus `Rs 300` cashback minus `Rs 130.50` (`5%` fee on all `Rs 2,610` redeemed bills) |
| Break-even merchant gross margin | `17.2%` pre-fee / `24.7%` post-fee | Minimum shop gross margin for positive net rupee profit at `+25 pp` simulated lift |
| **Break-even lift at `30%` shop margin** | **`+7.8 pp` pre-fee (`20.3%`) / `+15.3 pp` post-5%-fee (`27.8%`)** | Minimum percentage-point lift above `12.5%` baseline (`Rs 217.50` bill, `Rs 25` pass) for expected net profit per nudged customer `> Rs 0` |

### 3.2 Pooled 50-Shop Stratified Pilot Design & Power Table (`app/stats.py: compute_pooled_pilot_power_table`)
- **Design:** Pool **one wave across `50` Bengaluru shops** (`~40` eligible regulars per shop = **`~400` silent control and `~1,600` nudged**, `N = 2,000` total), randomized `80/20` within each shop, analysed **stratified by shop** (Cochran-Mantel-Haenszel / shop fixed effects). This avoids running multiple back-to-back waves inside one shop, staying consistent with the 14-day per-customer cooldown and the `~0.78` waves/month steady-state replenishment assumption.
- **Two-Sided Power (`alpha = 0.05`) at `12.5%` Baseline (`400` Control vs `1,600` Nudged):**

| True Lift Above `12.5%` Baseline | Nudged Return Rate | Statistical Power (Two-Sided `alpha = 0.05`) | Economic Context (`30%` Margin, `Rs 217.50` Bill) |
| :--- | :--- | :--- | :--- |
| **`+4` percentage points** | `16.5%` | **`50.3%`** | Below pre-fee break-even (`+7.8 pp`) |
| **`+5` percentage points** | `17.5%` | **`68.8%`** | Below pre-fee break-even (`+7.8 pp`) |
| **`+6` percentage points** | `18.5%` | **`83.3%`** | Crosses `80%` power threshold |
| **`+7` percentage points** | `19.5%` | **`92.5%`** | Near pre-fee break-even (`+7.8 pp`) |
| **`+8` percentage points** | `20.5%` | **`97.2%`** | Above pre-fee break-even (`+7.8 pp`) |
| **`+10` percentage points** | `22.5%` | **`99.8%`** | High power (`>99.9%` at `+15.3 pp` post-fee break-even) |

- **Pilot Advancement Decision Rule (Appendix A9):** Advance to citywide rollout **only if the lower 95% confidence bound of net profit per nudged customer after the 5% fee is above zero AND the observed lift exceeds the break-even lift (`+15.3 pp` post-fee at `30%` shop margin)**.

---

## 4. Unit Economics, Fee Reconciliation & ARR Cases (`ASSUMPTION` / `MODELLED`, Evidence Grade C)

### Fee Reconciliation (`Rs 130.50` Single Campaign vs `Rs 102 / month` Steady-State ARPU)
- **Fee Base Definition:** Paytm charges a `5%` success fee on **total gross value of QR-redeemed campaign bills (including organic returners who redeem a pass)**.
- **Single Launch Wave (`CMP-WINBACK-01`):** `12` redeemed bills x `Rs 217.50` = `Rs 2,610` redeemed bill volume -> `5%` fee = **`Rs 130.50`**.
- **Monthly Steady-State ARPU (`Rs 102 / month`):** Assumes **`Rs 2,040 / month`** in redeemed campaign bills (`5% x Rs 2,040 = Rs 102/mo`), equivalent to **`~0.78` full win-back-equivalent waves per month** as a shop's 14-day cooldown-eligible lapsed pool replenishes gradually after the initial backlog wave.

### Per-Merchant Monthly Unit Economics & 5% Adoption ARR (Q2 FY27 `1.64 Crore` Base -> `8.20 Lakh` Shops)
| Metric | Value (Q2 FY27 `1.64 Cr` Base) | Notes & Assumptions |
| :--- | :--- | :--- |
| Pro SaaS add-on price | `Rs 79 / month` | `ASSUMPTION`: Soundbox voice copilot add-on after 2 free trial campaigns |
| Promo fee ARPU (steady-state) | `Rs 102 / month` | `ASSUMPTION`: `5%` fee on `Rs 2,040/mo` total redeemed promo bills (`~0.78` full waves/mo; includes organic redeemers) |
| Partner credit referral uplift | `Rs 77 / month` | `ASSUMPTION`: amortized `1.5% to 2.5%` partner origination fee on incremental loan conversion |
| Blended ARPU & Monthly COGS | `Rs 258 / month` ARPU; `Rs 48.00` cached COGS (`Rs 71.80` uncached) | `Rs 1.80` SLM + `Rs 3.20` cached Bulbul v3 TTS (`~88%` hit rate; `Rs 27.00` uncached) + `Rs 43.00` messaging -> `81.4%` cached margin (`72.2%` uncached) |
| **Revenue Case C (SaaS Only, `Rs 79/mo`)** | **`Rs 77.7 crore ARR`** | `8.20L x Rs 79 x 12` (`39.2%` cached gross margin; zero campaign or credit fees) |
| **Revenue Case B (Excl. Credit, `Rs 181/mo`)** | **`Rs 178.1 crore ARR`** | `8.20L x Rs 181 x 12` (`73.5%` cached gross margin; zero credit assumptions) |
| **Revenue Case A (Full Base Case, `Rs 258/mo`)** | **`Rs 253.9 crore ARR`** | `8.20L x Rs 258 x 12` (`81.4%` cached gross margin / `72.2%` uncached) |

---

## 5. Sponsor, Copy Review & Render Resource Bounds
- **Sarvam AI:** Keyless adapter + mock server + `15%/15%` (`30%` max) universal credit cap built (`stage1-ok`); live voice calls remain `PENDING` Saturday 11:00 AM - 1:00 PM sponsor window.
- **Merchant Copy Review Status:** English (`en-IN`): `EN author-checked, native review pending`. Kannada (`kn-IN`) & Hindi (`hi-IN`): `DRAFT - UNREVIEWED BY NATIVE SPEAKER`.
- **Render Session Bounds (`stage1-ok`):** Per-visitor SQLite DBs (`204.0 KB` each) bounded by `1,800s` (`30m`) idle TTL, `64` max active sessions (LRU eviction of oldest), `2 MB` per-DB cap, and `32 MB` total session disk cap (`~55.4 MB` peak worker RSS on `512 MB` Render Free tier).
