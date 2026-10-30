# PaytmAI VyaparVoice - Timed Pitch Scripts & Fallback Variants

- **Team Name:** SemiTechnical
- **Member Name:** Kevin Joseph
- **Track:** Track 1 - Merchant Growth AI (Paytm Build for India AI Hackathon, Bengaluru Finals, 31 Oct 2026)
- **Canonical Numbers Source:** `results/slide_numbers.md` and `AUDIT.md`
- **Live Demo URL:** `https://paytmai-vyaparvoice.onrender.com`

---

## Pre-Pitch Operational Rules

1. **Synthetic Data Transparency:** State in the first 30 seconds of any demo or metric discussion that the store ledger (`Sri Krishna Darshini & Provisions, Indiranagar`) is a deterministic 60-day synthetic UPI dataset (`1,613` transactions across `240` unique UPI payer profiles; `917` scans and `Rs 1,74,685` GMV in the last 30 days).
2. **Paytm Attribution Discipline:** Use `"Reported in Paytm's Q2 FY27 earnings release (26 Oct 2026)"` for `1.64 crore` subscription-paying merchants, `Rs 7.1 lakh crore` GMV, and `Rs 2,648 crore` operating revenue. Label `~7%` merchant loan penetration and `Rs 90 to 100/month` Soundbox rental as assumptions benchmarked to historical Paytm IR disclosures.
3. **Sarvam AI Honesty Toggle:**
   - **Default Line (Web Speech API / Cached Audio):** *"Today our voice loop runs on deterministic templates with browser speech synthesis, while our keyless Sarvam Bulbul TTS and Saaras STT adapter is mock-verified and gated behind a strict 30 percent credit cap."*
   - **Saturday Swap-In Line (USE ONLY IF `make activate-sarvam` and `make sarvam-selftest` succeeded between 11:00 AM and 1:00 PM):** *"For Kannada and Hindi voice delivery, we are running through Sarvam Bulbul TTS and Saaras STT behind a fail-closed credit ledger capped at 30 percent of our hackathon allocation, with cached audio fallback."*
4. **Statistical & Cap Discipline:**
   - Issue passes to all `32` nudged regulars (`Rs 800` face exposure) and enforce `Rs 300` (`12` redemptions) as a hard stop on actual spend, recording `cap_reached` and any `refused_redemptions`. Warn at approval whenever cap-binding probability exceeds `10%`.
   - Analyse the holdout strictly as **Intention-to-Treat (ITT)** (`12/32 = 37.5%` vs `1/8 = 12.5%`, Fisher exact `p = 0.24`), noting explicitly that simulated `12` returning buyers equals the `Rs 300` cap (`12 x Rs 25`).
   - State power accurately: at our `80/20` split (`40` eligible per wave), reaching `80%` power requires about `31` control and `124` nudged buyers (`155` total, roughly `4` waves), or `46` per arm at an even `50/50` split.

---

## Format 1: 60-Second Elevator / Triage Script (~150 words)

**[0:00 - 0:15 | Hook & Problem - Slide 1]**
Good morning. I am Kevin Joseph from Team SemiTechnical, building PaytmAI VyaparVoice for Track 1. In its Q2 FY27 release this week, Paytm reported `1.64 crore` subscription-paying merchants and `Rs 7.1 lakh crore` in quarterly GMV, yet Soundbox remains a passive payment speaker. When repeat customers quietly stop visiting, a busy counter merchant hears isolated scan alerts rather than retention trends.

**[0:15 - 0:40 | Product Mechanism - Slide 2 & Live App Glance]**
VyaparVoice turns Soundbox into a 20-second 8:30 PM closing voice workflow. On our 60-day synthetic Indiranagar darshini ledger (`1,613` scans, `240` payers), our deterministic SQL engine flags `48` lapsed regulars, filters to `40` DPDP-consented and 14-day cooldown-clear buyers, holds back `8` (`20%`) as silent controls, and sends passes to all `32` nudged buyers with a `Rs 300` hard stop on actual spend.

**[0:40 - 1:00 | Honest Economics & Close - Slides 4 & 5]**
In simulation (`12/32` vs `1/8` ITT, where `12` hits the `Rs 300` cap; `p = 0.24`, needing `~4` waves at `80/20` for `80%` power), a `30%`-margin shop nets `+Rs 222` pre-fee (`+Rs 91.50` post-fee). At `5%` of Paytm's `1.64 crore` devices (`8.20 lakh` shops), even the `Rs 79` SaaS tier alone represents `Rs 77.7 crore` ARR (`Rs 253.9 crore` full base case). Thank you.

---

## Format 2: 3-Minute Round-1 Table Judging Script (~430 words)

**[0:00 - 0:30 | Slide 1 & Slide 2: Real Merchant Bottleneck]**
Hello judges, I am Kevin Joseph, Team SemiTechnical. Paytm reported `1.64 crore` subscription-paying merchants and `Rs 2,648 crore` quarterly operating revenue in its Q2 FY27 release on 26 October 2026. Yet single-counter food and kirana owners cannot write prompts or study CRM tables. When repeat buyers drift away or 3-to-5 PM traffic drops `70%` below peak, high-margin repeat sales disappear silently. VyaparVoice solves this with a zero-typing 8:30 PM closing voice brief and one-command campaign execution.

**[0:30 - 1:55 | Live Demo: Sri Krishna Darshini & Provisions (Synthetic 60-Day Store)]**
*(Switch to live browser tab; keep Deck Slide 3 ready behind it)*
Let me show the live FastAPI and SQLite app on our synthetic 60-day UPI ledger (`1,613` scans across `240` payers; `917` scans and `Rs 1,74,685` GMV in 30 days):
1. **8:30 PM Closing Brief (Merchant vs Technical View):** I play the brief in English or Kannada (`[DRAFT - UNREVIEWED]`). Merchant View speaks plain rupee and customer counts with zero statistical jargon, backed by Grade A SQLite counts: `48` lapsed regulars (`16 to 38` days silent), a `3 to 5 PM` dead-hour trough, and a `+18L` milk restock PO.
2. **ITT Cap-vs-Holdout & Approval Warning:** Look at `CMP-WINBACK-01`. Five guardrails filter `48` regulars down to `40` (`43` DPDP opted-in, `40` clear of the 14-day cooldown) and split `32` nudged versus `8` silent control. Every one of the `32` nudged customers gets a `Rs 25` pass (`Rs 800` face exposure), while `Rs 300` (`12` redemptions) acts as a hard stop on actual spend. At approval, our engine computes the binomial probability that demand exceeds `12` redemptions (`42.2%` at a `37.5%` assumed rate, `16.3%` at `30%`) and warns the merchant because it exceeds `10%`, suggesting a `Rs 325` to `Rs 400` cap if they want zero late-redeemer refusals.
3. **48-Hour Settlement:** After voice approval (`"Haan, bhej do"`), our simulator draws customer return outcomes independently of the cap first, then applies the `Rs 300` spend stop and records `cap_reached = True` with `0` refused redemptions (`12` simulated returners equals the `12`-redemption cap).

**[1:55 - 2:35 | Slide 4: Intention-to-Treat Stats & Profit Reconciliation]**
*(Switch to Slide 4)*
Analysed as Intention-to-Treat, `12 of 32` nudged buyers return (`37.5%`, 95% Wilson CI `22.9% to 54.8%`) versus `1 of 8` holdout (`12.5%`, CI `2.2% to 47.1%`), with Fisher exact `p = 0.24`. At our `80/20` split (`40` per wave), `80%` statistical power requires about `31` control and `124` nudged buyers (`155` total, roughly `4` waves), or `46` per arm at an even split. Deducting `4` expected organic returners leaves `8` incremental visits (`Rs 1,740` incremental sales). At `30%` store margin, `Rs 522` gross profit minus `Rs 300` cashback yields `+Rs 222` net profit pre-fee, and `+Rs 91.50` after Paytm's `5%` fee (`Rs 130.50`, charged on all `Rs 2,610` redeemed bills including organic returners).

**[2:35 - 3:00 | Slide 5: Paytm Scale Economics]**
*(Switch to Slide 5)*
With phrase caching (`~88%` hit rate), monthly AI cost is `Rs 5.00` (`Rs 48.00` total COGS cached, `Rs 71.80` uncached). Across `5%` of Paytm's `1.64 crore` Q2 FY27 device base (`8.20 lakh` shops), ARR is `Rs 77.7 crore` on `Rs 79` SaaS alone, `Rs 178.1 crore` adding steady-state `Rs 102/month` promo fees (`~0.78` full waves/month), and `Rs 253.9 crore` in our full base case. Thank you.

---

## Format 3: 5-Minute Top-10 Stage Finale Script (~700 words)

**[0:00 - 0:45 | Slide 1: From Passive Payment Alerts to Counter Retention]**
Good evening judges. I am Kevin Joseph from Team SemiTechnical, presenting PaytmAI VyaparVoice for Track 1: Merchant Growth AI.
In its Q2 FY27 earnings release on 26 October 2026, Paytm reported `1.64 crore` subscription-paying merchant deployments, `Rs 7.1 lakh crore` in quarterly merchant GMV, and `Rs 2,648 crore` in operating revenue. Soundbox earned counter space across India because audio requires zero screen time during a rush. Yet once a payment clears, intelligence stops. When regular customers quietly stop visiting a darshini or kirana, the shopkeeper hears isolated daily totals rather than customer-level churn, and single-counter operators rarely open analytics dashboards or write CRM prompts.

**[0:45 - 1:30 | Slide 2: Deterministic Voice Workflow & Live Demo Link]**
*(Advance to Slide 2; judges may scan QR to `https://paytmai-vyaparvoice.onrender.com`)*
VyaparVoice turns Soundbox plus Paytm for Business into a 20-second 8:30 PM closing workflow. A deterministic SQL engine scans hashed UPI histories for lapsed regulars, afternoon dead hours, and weekend rush spikes, rendering plain-language templates in Kannada, Hindi, or English. No LLM ever touches payer identifiers or writes financial numbers. Public cloud visitors run inside isolated per-session SQLite sandboxes with paid API calls locked off, while merchants approve every action explicitly by voice or 1-tap button.

**[1:30 - 3:15 | Live Product Walkthrough (1m 45s)]**
*(Switch to live application window)*
Let us run our live MVP on a seeded 60-day synthetic ledger for Sri Krishna Darshini & Provisions in Indiranagar (`1,613` transactions, `240` payers, `Rs 1,74,685` 30-day GMV):
- **Moment 1 - Plain-Language Brief vs Technical View:** I play the 8:30 PM brief. *[Use Default or Saturday Sarvam Swap-In Line per Rule 3.]* Merchant View strips all statistical jargon (`cohort`, `p-value`, `holdout`) and tags claims with Evidence Grades A, B, and C, while Kannada and Hindi carry an explicit `Draft - Unreviewed` badge pending native teach-back.
- **Moment 2 - ITT Cap-vs-Holdout & Overrun Warning (`CMP-WINBACK-01`):** Out of `48` lapsed regulars, `43` pass DPDP opt-in and `40` clear the 14-day cooldown (`32` nudged, `8` silent control). Rather than restricting passes to `12` buyers, we issue `Rs 25` passes to all `32` nudged regulars (`Rs 800` face exposure) and enforce `Rs 300` (`12` redemptions) as an atomic hard stop on actual cashback spend. At approval, the engine calculates that `P(Binomial(32, p) > 12)` exceeds `10%` (`42.2%` at `p = 37.5%`, `16.3%` at `30%`) and warns the merchant, suggesting `Rs 325` to `Rs 400` if they want `<=10%` refusal risk.
- **Moment 3 - Independent Outcome Draw & Hard Spend Stop:** I approve by voice (`"Haudu, approve"`) and trigger the 48-hour settlement simulator. Customer return visits are drawn independently of the cap first; then the `Rs 300` spend ceiling stops funded payouts at redemption #12, recording `cap_reached = True` and `refused_redemptions = 0` (`12` simulated returners equals our `12`-redemption cap).

**[3:15 - 4:15 | Slide 4: Intention-to-Treat Evaluation & Real Merchant Profit]**
*(Switch to Slide 4)*
Because outcomes are analysed as Intention-to-Treat across all `32` nudged buyers versus `8` holdout buyers, the causal holdout comparison remains unbiased even when a cap binds:
- **Power & CIs:** `12/32` (`37.5%`, Wilson 95% CI `22.9% to 54.8%`) versus `1/8` (`12.5%`, CI `2.2% to 47.1%`) gives two-sided Fisher exact `p = 0.24`. At our `80/20` split (`40` buyers/wave), `80%` power at `alpha = 0.05` requires about `31` control and `124` nudged buyers (`155` total, roughly `4` waves), or `46` per arm at an even `50/50` split.
- **Merchant Net Profit:** `12` returning bills (`Rs 2,610` at `Rs 217.50` mean) include `4` expected organic returners (`Rs 100` cashback subsidy), leaving `8` incremental visits (`Rs 1,740` incremental sales, `5.8x` promo spend). At a `30%` store gross margin, `Rs 522` gross profit (`1.74x` promo) minus `Rs 300` cashback leaves **`+Rs 222` net profit pre-fee (`+74%` ROI)**, and **`+Rs 91.50` net profit (`+30.5%`)** after Paytm's `5%` fee (`Rs 130.50` across all `Rs 2,610` redeemed bills, including organic returners). Any store above `24.7%` margin profits post-fee.

**[4:15 - 5:00 | Slide 5: Reconciled Unit Economics & Q2 FY27 Scale]**
*(Advance to Slide 5)*
In steady state, assuming `~0.78` win-back-equivalent campaigns per month (`Rs 2,040/month` redeemed promo bills as the 14-day cooldown pool replenishes), Paytm earns `Rs 102/month` in promo fees alongside `Rs 79/month` SaaS against `Rs 48.00/month` cached COGS (`Rs 5.00` AI + `Rs 43.00` messaging; `Rs 71.80` uncached). Across `5%` of Paytm's `1.64 crore` Q2 FY27 subscription merchants (`8.20 lakh` shops):
1. **SaaS-Only Floor (`Rs 79/mo`):** `Rs 77.7 crore` ARR.
2. **Core Excl. Credit (`Rs 181/mo`):** `Rs 178.1 crore` ARR.
3. **Full Base Case (`Rs 258/mo`):** `Rs 253.9 crore` ARR.
Thank you, and I welcome your questions.

---

## Format 4: 7-Minute Extended Deep-Dive Script (~940 words)

- **0:00 - 1:00 (Slide 1 + Appendix A2):** Cite Paytm's Q2 FY27 earnings release (`26 Oct 2026`: `1.64 Cr` subscription merchants, `Rs 7.1L Cr` GMV, `Rs 2,648 Cr` operating revenue, `>50%` repeat merchant loan disbursements) while explicitly tagging `~7%` merchant loan penetration and `Rs 90-100/mo` Soundbox rental as assumptions benchmarked to FY24/FY25 Paytm IR disclosures. Show the synthetic store's `-70%` 3-to-5 PM scan trough (`30` vs `101`).
- **1:00 - 2:00 (Slide 2 + Appendix A4/A5):** Walk through the 4-layer architecture (`Config -> Render/Session Safeguards -> Keyless Provider & 30% Credit Cap -> Deterministic SQL + Templates`) and explain the disclosed trade-off between issuing `32` passes (`Rs 800` face exposure) and enforcing a `Rs 300` hard stop on actual spend.
- **2:00 - 4:15 (Live Full-Cycle Demo):**
  1. Toggle **Merchant View** (jargon-free plain language + Evidence Grades A/B/C) vs **Technical View** (Fisher `p`, Wilson CIs, ITT counts, cap-binding binomial math).
  2. Inspect the approval warning on `CMP-WINBACK-01` (`P(X > 12) = 42.2%` at `p = 37.5%`, suggesting `Rs 400` cap for `<=10%` refusal risk), approve by voice, and run the 48h simulator (`12/32` vs `1/8`, `cap_reached = True`, `refused_redemptions = 0`).
  3. Trigger `OPS-STOCK-01` (`+18L milk, +12kg batter` PO) and `OPS-CARE-02` (`Rs 30` queue-delay coffee pass), then show the immutable audit log.
- **4:15 - 5:45 (Slide 4 + Appendix A7):** Detail why Intention-to-Treat (`32` denominator) preserves valid causal inference even when a cap truncates payouts, verify the two power regimes (`31` control + `124` nudged = `155` across `~4` waves at `80/20`, vs `46/arm` at `50/50`), and walk through the `+Rs 222` pre-fee / `+Rs 91.50` post-fee waterfall (`17.2%` / `24.7%` break-even margins).
- **5:45 - 7:00 (Slide 5 + Appendix A8/A9):** Reconcile `Rs 130.50` single-wave fee (`5%` of `Rs 2,610` total redeemed bills including organic returners) with `Rs 102/mo` steady-state ARPU (`~0.78` waves/mo = `Rs 2,040/mo` redeemed bills), review the three Q2 FY27 ARR cases (`Rs 77.7 Cr`, `Rs 178.1 Cr`, `Rs 253.9 Cr`), and close with the 4-week Bengaluru randomized pilot protocol.

---

## Emergency Deck-Only Fallback Variant (Zero Network / Zero Browser / Audio Failure)

1. **Immediate Bridge Sentence:** *"To stay strictly on time without stage-audio latency, let us walk directly through the exact SQLite state, ITT cap-vs-holdout ledger, and audit outputs captured on Slide 3 and Appendix A4."*
2. **Slide 3 & Appendix A4 Walkthrough (60 seconds):**
   - Point to `1,613` synthetic scans across `240` payers (`917` scans / `Rs 1,74,685` in 30d) -> `48` lapsed -> `40` policy-eligible (`32` nudged, `8` silent control).
   - Highlight the disclosed cap design: all `32` nudged buyers receive passes (`Rs 800` face exposure), `Rs 300` (`12` redemptions) hard-stops actual spend (`>10%` overrun warning shown at approval), and simulated `12` returners equals the `Rs 300` cap (`cap_reached = True`, `0` refused).
   - Transition straight to Slide 4 (`12/32` vs `1/8` ITT, `p = 0.24`, `31` control + `124` nudged across `~4` waves for `80%` power, `+Rs 222` pre-fee / `+Rs 91.50` post-fee).
