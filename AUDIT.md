# Codebase, Statistical, and Presentation Audit (AUDIT.md)

Date: 30 October 2026
Project: PaytmAI VyaparVoice (Track 1: Merchant Growth AI)
Team: SemiTechnical (Kevin Joseph)
Baseline Commit Audited: `ddd1379` on `https://github.com/somebeing2/paytmai-vyaparvoice` (branch `main`)

---

## 1. Environment, Repository, and Deployment Baseline

### 1.1 Runtime and Git Status
- Sandbox Python version: `Python 3.13.16`
- Production target Python version (`render.yaml`): `3.11.9` (`Dockerfile`: `python:3.11-slim`)
- Git remote (`git remote -v`):
  - `origin https://github.com/somebeing2/paytmai-vyaparvoice.git (fetch)`
  - `origin https://github.com/somebeing2/paytmai-vyaparvoice.git (push)`
- Push credentials in sandbox: Not present (`fatal: could not read Username for 'https://github.com'`). All work will execute on local Git branches, merge to local `main` only at verified stage gates (`stage1-ok`, `stage2-ok`, `stage3-ok`), and export via `make export` (generating a clean Git bundle and zip archive for local push).
- Active working branch: `work/step0-and-deck-v1` (created from `ddd1379`, tagged `baseline-pre-audit`).

### 1.2 Current `render.yaml` Contents
```yaml
services:
  - type: web
    name: paytmai-vyaparvoice
    runtime: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.9
```

### 1.3 Evaluation of `autoDeploy: false` on Render Free Plan
Source verified: Render Blueprint YAML Specification (`https://render.com/docs/blueprint-spec`) and Render Free Instances Documentation (`https://render.com/docs/free`), retrieved 30 October 2026.

1. **Support and Deprecation Status:** Setting `autoDeploy: false` is supported on all compute plans, including `plan: free`, but `autoDeploy` is officially deprecated in Render's Blueprint specification. The current field is `autoDeployTrigger: 'off'` (must be quoted as `'off'` in YAML so YAML 1.1 parsers do not cast it to boolean `false`).
2. **Operational Behavior:**
   - Adding `autoDeployTrigger: 'off'` to `render.yaml` and pushing to `main` triggers one Blueprint sync to apply the setting; subsequent pushes to `main` will not auto-deploy until triggered manually in the Render Dashboard.
   - Alternative without editing `render.yaml`: Including `[skip render]` or `[render skip]` in a Git commit message prevents Render from auto-deploying that push.
3. **Verified Free-Plan Constraints:**
   - Compute: `0.1 CPU`, `512 MB RAM`, 750 free instance hours/month.
   - Spin-down: Spins down after 15 minutes of zero inbound traffic; cold start takes roughly 60 seconds. Warming `https://paytmai-vyaparvoice.onrender.com/api/health` 2 minutes before any demo slot is mandatory.
   - Ephemeral disk: Local SQLite (`app/vyaparvoice.db`) resets whenever the container spins down or redeploys, then re-seeds on FastAPI startup.
   - Rollbacks: Dashboard one-click rollbacks on the free plan retain only the 2 most recent deploys, whereas "Manual Deploy -> Deploy a specific commit" works for any historical commit SHA (such as `release-final`).
4. **Action Taken:** Per instructions, `render.yaml` has NOT been modified.

---

## 2. Inventory of Built vs Unbuilt Capabilities

| Component / Claim | Status in `ddd1379` | Evidence / File Location | Required Slide Label |
| :--- | :--- | :--- | :--- |
| Synthetic store ledger (240 payers, 1,613 scans) | BUILT (SYNTHETIC) | `app/database.py` (`random.Random(20261025)`) | Built in MVP (Synthetic Data) |
| SQL RFM cohort & hourly scan aggregation | BUILT | `app/engine.py` (`get_dashboard_overview`) | Built in MVP |
| 5-rule deterministic policy check | PARTIAL (see Sec. 3.4) | `app/engine.py` (`compute_guardrails_for_campaign`) | Built in MVP |
| Scripted briefings (English, Kannada, Hindi) | BUILT (UNREVIEWED) | `app/engine.py` (`get_voice_briefing`) | Built in MVP (Draft Copy) |
| Browser TTS / Mic speech recognition UI | BUILT (BROWSER API) | `app/static/index.html` (`speechSynthesis` / `SpeechRecognition`) | Built in MVP |
| 48-hour redemption & holdout simulator | BUILT (SIMULATED) | `app/engine.py` (`simulate_campaign_48h`) | Simulated in MVP |
| Ops action toggles (Dairy PO & Apology note) | BUILT (MOCKED STATE) | `app/engine.py` (`execute_ops_action`) | Simulated in MVP |
| QA test battery (21 assertions) | BUILT | `tests/qa_battery.py` | Built in MVP |
| Honest statistics (Fisher p, Wilson CI, profit ROI) | NOT BUILT | Scheduled for Stage 1 | Stage 1 Target |
| Commitment-based cashback cap ledger | NOT BUILT | Scheduled for Stage 1 | Stage 1 Target |
| Public deploy lock (`PUBLIC_DEPLOY`, `ADMIN_TOKEN`) | NOT BUILT | Scheduled for Stage 1 | Stage 1 Target |
| Sarvam AI Bulbul TTS / Saarika ASR adapters | NOT BUILT | Keyless adapter in Stage 2; live test `PENDING` tomorrow 11 AM | Pending Live Verification |
| Groq free-tier grounded Q&A / safety validator | NOT BUILT | Optional keyless adapter in Stage 2 | Pending / Optional |
| Paytm QR Offer Ledger / WhatsApp Cloud dispatch | NOT BUILT | External ecosystem integration | Production Plan |
| PostgreSQL, Redis atomic counters, n8n, Cognee | NOT BUILT | Architectural target only | Production Plan |

---

## 3. Forensic Audit of Numbers, Statistics, and Deck Discrepancies

### 3.1 Synthetic Dataset Disclosure
- **Finding:** Slide 4 previously carried the banner `"REAL FASTAPI + SQLITE COMPUTATION (ZERO HARDCODED MOCK NUMBERS)"`.
- **Fact:** While SQL queries run dynamically against SQLite, `app/database.py` seeds a synthetic dataset (`random.Random(20261025)`), and `simulate_campaign_48h()` inserts deterministic return counts (`t_ret = 12`, `h_ret = 1` for `CMP-WINBACK-01`; `t_ret = 11`, `h_ret = 1` for `CMP-DEADHOUR-02`) with deterministic basket amounts (`[195, 210, 225, 240]`, mean `Rs 217.50`).
- **Correction:** Remove the misleading banner and explicitly label all store and campaign outputs as **Synthetic Dataset** and **Simulated**.

### 3.2 Holdout Statistics and Sample Power (`CMP-WINBACK-01`)
- **Simulated Observations:**
  - Eligible cohort: `N = 40` (`32` Treatment, `8` Control; 80/20 split).
  - Simulated 48h returns: Treatment `12 / 32 = 37.5%`; Control `1 / 8 = 12.5%`.
- **Exact Hypothesis Test & Intervals:**
  - Fisher's exact test: two-sided `p = 0.2364` (approx `0.24`), one-sided `p = 0.1790` (approx `0.18`).
  - Wilson 95% confidence intervals: Treatment `22.9% to 54.8%`; Control `2.2% to 47.1%`.
  - Statistical verdict: **Directional simulation only; NOT statistically significant** (`p > 0.05`). Words such as `"proven"` and `"verified"` must be replaced with `"simulated; to be validated in pilot"`.
- **Required Pilot Sample Size (`12.5%` vs `37.5%`, `80%` power, two-sided `alpha = 0.05`):**
  - Equal `1:1` allocation: `46` payers per arm unadjusted (`92` total), or `54` per arm with continuity correction (`108` total); arcsine approximation gives `44` per arm. This requires pooling across roughly 3 to 5 weekly store waves or multiple pilot stores.

### 3.3 Sales Multiple vs Profit-Based Merchant ROI (`CMP-WINBACK-01`)
- **Bill Size Assumption:** Simulated redeemers spend `Rs 2,610` total across `12` scans (`Rs 217.50` mean bill vs `Rs 190` 30-day store average, reflecting upward basket shift from the `Rs 150` minimum bill condition).
- **Subsidy to Organic Returners:** At `12.5%` control return rate, `4.0` of the `32` treatment payers (`0.125 x 32`) would have returned organically without an incentive, consuming `4 x Rs 25 = Rs 100` (`33.3%` of cashback spend).
- **Incremental Gross Sales:** `(12 - 4) = 8` net incremental visits x `Rs 217.50` = `Rs 1,740`.
- **5.8x Clarification:** `Rs 1,740 / Rs 300 = 5.80x` is **incremental gross sales per rupee of cashback**, NOT merchant profit ROI.
- **Merchant Profit Accounting (at 30% gross margin assumption for QSR/Darshini):**
  - Incremental gross profit: `30% x Rs 1,740 = Rs 522.00` (**Gross-profit multiple: `1.74x`**).
  - Less merchant-funded cashback (`12 x Rs 25`): `-Rs 300.00`.
  - Merchant net profit before platform fee: **`+Rs 222.00`** (**Net profit ROI: `+74.0%`**, or `0.74x` net profit per rupee of cashback).
  - Less Paytm `5%` promo fee on redeemed promo bills (`5% x Rs 2,610 = Rs 130.50`): Merchant net profit after fee = **`+Rs 91.50`** (**`+30.5%` net return**). *(If Paytm charges 5% only on incremental sales, fee is `Rs 87.00` and merchant net profit is `+Rs 135.00`.)*
  - Break-even merchant gross margin: **`17.24%`** before platform fee (`Rs 300 / Rs 1,740`); **`24.74%`** after a 5% redeemed-bill fee (`Rs 430.50 / Rs 1,740`).

### 3.4 Spending Cap Commitment Accounting Gap
- **Finding:** `CMP-WINBACK-01` dispatches `32` passes at `Rs 25` (`Rs 800` total face value) while advertising a `Rs 300` max budget (`12` redemptions). Relying solely on scan-time cutoff means customer #13 could be denied cashback at the counter.
- **Remediation (Stage 1/2):** Introduce commitment-based accounting where issued-but-unredeemed passes count against the cap (`12` active passes per wave for a `Rs 300` cap, releasing expired unredeemed passes to the next wave) alongside scan-time hard cutoff.

### 3.5 Internal Slide Inconsistencies Fixed
1. **Inactivity Window:** Slide 3 stated `15-30 days`, Slide 4/UI stated `16-28 days`, voice script stated `18 days`, while `app/database.py` actually yields `MIN(days_ago)` from **`16 to 38 days`** (`median 19 days`, `mean 20.8 days`). Standardized to: **`16+ days silent (range 16 to 38 days, median 19 days in synthetic ledger)`**.
2. **Cohort Funnel Counts:** Standardized everywhere to: **`48 lapsed regulars detected -> 43 DPDP opted-in -> 40 cooldown-eligible (32 treatment, 8 control)`**.
3. **AI & TTS Cost Consistency:**
   - Removed conflicting `< Rs 2 / shop / month` tile from Slide 7.
   - Standardized AI cost to **`Rs 5.00 / shop / month`** (`Rs 1.80` SLM inference + `Rs 3.20` cached TTS) in the cached case, and documented uncached sensitivity: at Sarvam Bulbul v3 listed rate (`Rs 30 per 10,000 chars`), `300 chars/day x 30 days = 9,000 chars/month` costs **`Rs 27.00/month` uncached** (`Rs 13.50/month` on Bulbul v2 at `Rs 15 per 10,000 chars`). Achieving `Rs 3.20/month` requires an **`~88%` phrase/template cache hit rate** on v3 (`~76%` on v2).
4. **Gross Margin Consistency:**
   - Replaced mixed `>78%` vs `~81%` labels with exact figures: **`81.4%`** (`Rs 210 / Rs 258` at `Rs 48` cached COGS) and **`72.2%`** (`Rs 186.20 / Rs 258` at `Rs 71.80` uncached Bulbul v3 COGS).
5. **Latency Claim:** Removed unmeasured `<400 ms` latency claim.

### 3.6 Revenue Cases (at 5% of 1.57 Cr Device Base = 7.85 Lakh Merchants)
1. **SaaS-Only Conservative Case (`Rs 79/mo`):** `7,85,000 x Rs 79 x 12` = **`Rs 74.4 Cr ARR`**.
2. **Core Product Case, Excluding Credit Uplift (`Rs 79 SaaS + Rs 102 Promo Fee = Rs 181/mo`):** `7,85,000 x Rs 181 x 12` = **`Rs 170.5 Cr ARR`**.
3. **Full Ecosystem Base Case (`+ Rs 77 Partner Credit Fee = Rs 258/mo`):** `7,85,000 x Rs 258 x 12` = **`Rs 243.0 Cr ARR`**.

### 3.7 Source Verification for Market vs Assumed Figures
- **Verified Primary Disclosures (One97 Communications Ltd / Paytm):**
  - `1.57 crore` merchant device subscriptions (+27 lakh YoY): Paytm Q1 FY27 Earnings Release (July 2026).
  - `Rs 7.1 lakh crore` quarterly Merchant GMV (+31% YoY): Paytm Q1 FY27 Earnings Release (July 2026).
  - `~7%` merchant lending penetration of subscribed device base: Paytm Q4 FY26 Earnings Call (May 2026).
  - `~Rs 90 to Rs 100/month` average Soundbox subscription rental: Paytm FY25 Annual Report / Investor Presentations.
- **Unverified Figures Relabelled as `ASSUMPTION` or `PILOT TARGET`:**
  - `25% to 35%` annual SMB repeat-buyer attrition: **`ASSUMPTION (to measure in pilot)`**.
  - `<8%` weekly active usage of SMB BI dashboards: **`ASSUMPTION`**.
  - `+14% to 22%` repeat visits, `-18%` perishable waste, `-35%` device churn, `+12% to 15%` store GMV, `7% to 15%` loan funnel: **`PILOT TARGETS (unvalidated)`**.
