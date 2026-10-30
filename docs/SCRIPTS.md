# PaytmAI VyaparVoice - Timed Pitch Scripts & Fallback Variants

- **Team Name:** SemiTechnical
- **Member Name:** Kevin Joseph
- **Track:** Track 1 - Merchant Growth AI (Paytm Build for India AI Hackathon, Bengaluru Finals, 31 Oct 2026)
- **Canonical Numbers Source:** `results/slide_numbers.md`, `results/unit_economics.md`, and `AUDIT.md`
- **Presentation File:** `deck/v3/PaytmAI_VyaparVoice_v3.pptx` / `.pdf` (`Main 1..5` + `Appendix A1..A13`)
- **Live Demo URL:** `https://paytmai-vyaparvoice.onrender.com` (Offline Zero-Network Replay: `app/static/demo_replay.html` / `/replay`)

---

## Pre-Pitch Operational Rules

1. **Synthetic Data Transparency:** State in the first 30 seconds of any demo or metric discussion that the store ledger (`Sri Krishna Darshini & Provisions, Indiranagar`) is a deterministic 60-day synthetic UPI dataset (`1,613` transactions across `240` unique UPI payer profiles; `917` scans and `Rs 1,74,685` GMV in the last 30 days).
2. **Paytm Attribution Discipline:** Use `"Reported in Paytm's Q2 FY27 earnings release (26 Oct 2026)"` for `1.64 crore` subscription-paying merchants, `Rs 7.1 lakh crore` GMV, and `Rs 2,648 crore` operating revenue. Label `~7%` merchant loan penetration and `Rs 90 to 100/month` Soundbox rental as assumptions benchmarked to historical Paytm IR disclosures.
3. **Copy & Sarvam AI Honesty:**
   - State English merchant copy as `EN author-checked, native review pending`, and Kannada/Hindi as `DRAFT - UNREVIEWED BY NATIVE SPEAKER`.
   - **Default Voice Line (Web Speech API / Cached Audio):** *"Today our voice loop runs on deterministic templates with browser speech synthesis, while our keyless Sarvam Bulbul TTS and Saaras STT adapter is mock-verified and gated behind a strict 30 percent credit cap."*
   - **Saturday Swap-In Line (USE ONLY IF `make activate-sarvam` and `make sarvam-selftest` succeeded between 11:00 AM and 1:00 PM):** *"For Kannada and Hindi voice delivery, we are running through Sarvam Bulbul TTS and Saaras STT behind a fail-closed credit ledger capped at 30 percent of our hackathon allocation, with cached audio fallback."*
4. **Statistical, Cap & Pooled Pilot Discipline:**
   - Issue passes (`valid while the shop's offer budget lasts`) to all `32` nudged regulars (`Rs 800` face exposure) and enforce `Rs 300` (`12` redemptions) as a hard stop on actual spend, recording `cap_reached` and `refused_redemptions`, with a pre-approval alert whenever overrun probability exceeds `10%`.
   - Define and use **Intention-to-Treat (ITT)** (`12/32 = 37.5%` vs `1/8 = 12.5%`, Fisher exact `p = 0.24`), noting explicitly that simulated `12` returning buyers equals the `Rs 300` cap (`12 x Rs 25`).
   - Never claim a single shop yields four full waves in four weeks (which would conflict with our 14-day cooldown and `~0.78` steady-state waves/month). Instead, specify our **pooled 50-shop x 1-wave stratified pilot** (`~400` control and `~1,600` nudged, randomized within each shop and stratified by shop: `83.3%` power at `+6 pp` lift, `97.2%` at `+8 pp`, `99.8%` at `+10 pp` above `12.5%` baseline), advancing only if the lower 95% bound of post-5%-fee net profit per nudged customer is above zero and observed lift exceeds the `+15.3 pp` post-fee break-even lift.

---

## Format 1: 60-Second Elevator / Triage Script (~155 words)

**[0:00 - 0:15 | Hook & Problem - Slide 1]**
Good morning. I am Kevin Joseph from Team SemiTechnical, building PaytmAI VyaparVoice for Track 1. In its Q2 FY27 release on 26 October 2026, Paytm reported `1.64 crore` subscription-paying merchants and `Rs 7.1 lakh crore` in quarterly GMV, yet Soundbox stays silent after checkout. Busy counter merchants hear isolated payment alerts rather than repeat-customer churn.

**[0:15 - 0:40 | Product Mechanism - Slide 2 & Live App Glance]**
VyaparVoice turns Soundbox into a 20-second 8:30 PM closing voice brief. On our 60-day synthetic Indiranagar darshini ledger (`1,613` scans, `240` payers), deterministic SQL flags `48` lapsed regulars, filters to `40` DPDP-consented and 14-day cooldown-clear buyers, holds `8` in silent control, and issues `Rs 25` passes to all `32` nudged buyers with an atomic `Rs 300` stop on actual spend.

**[0:40 - 1:00 | Honest Economics & Pooled Pilot - Slides 4 & 5]**
In simulation (`12/32` vs `1/8` Intention-to-Treat, where `12` hits the `Rs 300` cap; `p = 0.24`), a `30%`-margin shop nets `+Rs 222` pre-fee (`+Rs 91.50` post-5%-fee). Rather than over-messaging one store, our pilot pools one wave across `50` stores (`~400` control, `~1,600` nudged; `83.3%` power at `+6 pp` lift). At `5%` of Paytm's `1.64 crore` devices (`8.20 lakh` shops), SaaS alone is `Rs 77.7 crore` ARR (`Rs 253.9 crore` full base). Thank you.

---

## Format 2: 3-Minute Round-1 Table Judging Script (~435 words)

**[0:00 - 0:30 | Slide 1 & Slide 2: Real Merchant Bottleneck]**
Hello judges, I am Kevin Joseph, Team SemiTechnical. Paytm reported `1.64 crore` subscription-paying merchants and `Rs 2,648 crore` quarterly operating revenue in its Q2 FY27 release on 26 October 2026. Yet single-counter food and kirana owners cannot write prompts or study CRM tables. When repeat buyers drift away or 3-to-5 PM traffic drops `70%` below peak, high-margin repeat sales disappear silently. VyaparVoice delivers a zero-typing 8:30 PM closing voice brief and one-command campaign execution.

**[0:30 - 1:55 | Live Demo: Sri Krishna Darshini & Provisions (Synthetic 60-Day Store)]**
*(Switch to live browser tab; keep Deck Slide 3 ready behind it)*
Let me show the live FastAPI and SQLite app on our synthetic 60-day UPI ledger (`1,613` scans across `240` payers; `917` scans and `Rs 1,74,685` GMV in 30 days):
1. **8:30 PM Closing Brief (Merchant vs Technical View):** I play the brief in English (`EN author-checked, native review pending`) or Kannada (`DRAFT - UNREVIEWED BY NATIVE SPEAKER`). Merchant View speaks plain rupee and customer counts with zero statistical jargon, backed by Grade A SQLite counts: `48` lapsed regulars (`16 to 38` days silent), a `3 to 5 PM` slow-hour trough, and a `+18L` milk restock PO.
2. **ITT Cap-vs-Holdout, Bounded Cap Editor & Two-Step Voice Confirm:** Six guardrails filter `48` regulars down to `40` (`43` DPDP opted-in, `40` clear of the 14-day cooldown) and split `32` nudged versus `8` silent control. All `32` nudged buyers receive a `Rs 25` pass (`valid while shop offer budget lasts`, `Rs 800` face exposure), while `Rs 300` (`12` redemptions) hard-stops actual spend. At approval, our engine warns that `P(Binomial(32, 0.375) > 12) = 42.2%` exceeds `10%`, and our Cap Editor (`Rs 50 to Rs 2,500`) plus two-step voice confirmation (`"Set my limit to 400 rupees"` -> `"Confirm limit"`) lowers refusal risk to `5.2%` at `Rs 400`.
3. **Live Interim Step, 1-Tap Stop-Loss & Bayesian Scorecard:** Stepping live scans shows an explicit `INTERIM LIVE READOUT` banner with 1-tap atomic `Stop-Loss` pause. At 48 hours (`12/32` vs `1/8`, `cap_reached = True`, `0` refused at `Rs 300`), our conjugate `Beta(1,1)` posterior (`88.8%` `P(lift>0)`, `67.0%` `P(pre-fee>0)`, `52.1%` `P(post-fee>0)`, `95%` CrI `[-Rs 19.97, +Rs 14.73]`/buyer) proves why one shop cannot auto-scale without pooling `50` stores.

**[1:55 - 2:35 | Slide 4: Intention-to-Treat Stats & Profit Reconciliation]**
*(Switch to Slide 4)*
Intention-to-Treat compares every assigned customer (`12 of 32` nudged vs `1 of 8` silent control) regardless of cap stops, yielding `37.5%` versus `12.5%` (`p = 0.24`). Subtracting `4` expected organic returners leaves `8` incremental visits (`Rs 1,740` sales). At `30%` shop margin, `Rs 522` gross profit minus `Rs 300` cashback leaves `+Rs 222` pre-fee, and `+Rs 91.50` after Paytm's `5%` fee (`Rs 130.50` across all `Rs 2,610` redeemed bills including organic returners; post-fee break-even lift is `+15.3 pp`).

**[2:35 - 3:00 | Slide 5: Pooled 50-Shop Pilot & Paytm Scale]**
*(Switch to Slide 5)*
Because our 14-day cooldown and `~0.78` waves/month cadence preclude 4 weekly waves in one shop, our pilot pools **one wave across `50` Bengaluru shops** (`~400` control, `~1,600` nudged, stratified by shop: `83.3%` power at `+6 pp`, `97.2%` at `+8 pp`, `99.8%` at `+10 pp`). Across `5%` of Paytm's `1.64 crore` Q2 FY27 base (`8.20 lakh` shops), ARR is `Rs 77.7 crore` on `Rs 79` SaaS alone, `Rs 178.1 crore` with `Rs 102/mo` steady promo fees, and `Rs 253.9 crore` full base. Thank you.

---

## Format 3: 5-Minute Top-10 Stage Finale Script (~710 words)

**[0:00 - 0:45 | Slide 1: From Passive Payment Alerts to Counter Retention]**
Good evening judges. I am Kevin Joseph from Team SemiTechnical, presenting PaytmAI VyaparVoice for Track 1: Merchant Growth AI.
In its Q2 FY27 earnings release on 26 October 2026, Paytm reported `1.64 crore` subscription-paying merchant deployments, `Rs 7.1 lakh crore` in quarterly merchant GMV, and `Rs 2,648 crore` in operating revenue. Soundbox earned counter space across India because audio requires zero screen time during a rush. Yet once a payment clears, intelligence stops. When regular customers quietly stop visiting a darshini or kirana, the shopkeeper hears isolated daily totals rather than customer-level churn, and single-counter operators rarely open analytics dashboards or write CRM prompts.

**[0:45 - 1:30 | Slide 2: Deterministic Voice Workflow & Isolated Cloud Demo]**
*(Advance to Slide 2; judges may scan QR to `https://paytmai-vyaparvoice.onrender.com`)*
VyaparVoice turns Soundbox plus Paytm for Business into a 20-second 8:30 PM closing workflow. A deterministic SQL engine scans hashed UPI histories for lapsed regulars, afternoon slow hours, and weekend rush spikes, rendering plain-language templates in English (`EN author-checked, native review pending`), Kannada, or Hindi (`DRAFT - UNREVIEWED`). No LLM ever touches payer identifiers or writes financial numbers. Public cloud visitors run inside isolated per-session SQLite sandboxes bounded by TTL, count, and byte caps with paid API calls disabled.

**[1:30 - 3:15 | Live Product Walkthrough (1m 45s)]**
*(Switch to live application window)*
Let us run our live MVP on a seeded 60-day synthetic ledger for Sri Krishna Darshini & Provisions in Indiranagar (`1,613` transactions, `240` payers, `Rs 1,74,685` 30-day GMV):
- **Moment 1 - Plain-Language Brief vs Technical View:** I play the 8:30 PM brief. *[Use Default or Saturday Sarvam Swap-In Line per Rule 3.]* Merchant View strips all statistical jargon (`cohort`, `p-value`, `holdout`) and grades claims A, B, and C, while keeping full statistical audit metrics one click away in Technical View.
- **Moment 2 - ITT Cap-vs-Holdout & Overrun Warning (`CMP-WINBACK-01`):** Out of `48` lapsed regulars, `43` pass DPDP opt-in and `40` clear the 14-day cooldown (`32` nudged, `8` silent control). Rather than restricting passes to `12` buyers, we issue `Rs 25` passes (`valid while the shop's offer budget lasts`) to all `32` nudged regulars (`Rs 800` face exposure) and enforce `Rs 300` (`12` redemptions) as an atomic hard stop on actual cashback spend. At approval, the engine warns that `P(Binomial(32, 0.375) > 12) = 42.2%` exceeds `10%`, suggesting a `Rs 400` cap to minimize counter refusals.
- **Moment 3 - Independent Outcome Draw & Hard Spend Stop:** I approve by voice (`"Haudu, approve"`) and trigger the 48-hour settlement simulator. Customer return visits are drawn independently of the cap first; then the `Rs 300` spend ceiling stops funded payouts at redemption #12, recording `cap_reached = True` and `refused_redemptions = 0` (`12` simulated returners equals our `12`-redemption cap).

**[3:15 - 4:15 | Slide 4: Intention-to-Treat Definition & Real Merchant Profit]**
*(Switch to Slide 4)*
Intention-to-Treat means we compare all `32` customers assigned to receive an offer against all `8` customers assigned to silent control regardless of whether they redeem or hit the spend stop, keeping the causal comparison unbiased even when a cap binds:
- **Single-Wave Readout:** `12/32` (`37.5%`, Wilson 95% CI `22.9% to 54.8%`) versus `1/8` (`12.5%`, CI `2.2% to 47.1%`) gives two-sided Fisher exact `p = 0.24` (requiring `31` control + `124` nudged = `155` pooled buyers at `80/20`, or `46/arm` at `50/50`, to power a `25 pp` lift).
- **Merchant Net Profit:** Subtracting `4` expected organic returners (`Rs 100` subsidy) from `12` bills (`Rs 2,610`) leaves `8` incremental visits (`Rs 1,740` sales, `5.8x` promo). At `30%` margin, `Rs 522` gross profit minus `Rs 300` cashback leaves **`+Rs 222` pre-fee (`+74%`)**, and **`+Rs 91.50` (`+30.5%`)** after Paytm's `5%` fee (`Rs 130.50` across all `Rs 2,610` redeemed bills including organic returners; break-even lift is `+7.8 pp` pre-fee and `+15.3 pp` post-fee).

**[4:15 - 5:00 | Slide 5: Pooled 50-Store Stratified Pilot & Q2 FY27 ARR]**
*(Advance to Slide 5)*
Because a single shop's 14-day cooldown pool refills at `~0.78` waves/month (`Rs 102/mo` steady promo fee vs `Rs 130.50` initial wave), our pilot pools **one wave across `50` Bengaluru shops** (`~400` control + `~1,600` nudged, stratified by shop: `83.3%` power at `+6 pp`, `97.2%` at `+8 pp`, `99.8%` at `+10 pp`), advancing only if the lower 95% bound of post-fee net profit per nudged customer exceeds zero and lift exceeds `+15.3 pp`. Across `5%` of Paytm's `1.64 crore` Q2 FY27 base (`8.20 lakh` shops), ARR is `Rs 77.7 crore` (SaaS-only), `Rs 178.1 crore` (excl. credit), and `Rs 253.9 crore` (full base). Thank you.

---

## Format 4: 7-Minute Extended Deep-Dive Script (~950 words)

- **0:00 - 1:00 (Slide 1 + Appendix A2):** Cite Paytm's Q2 FY27 earnings release (`26 Oct 2026`: `1.64 Cr` subscription merchants, `Rs 7.1L Cr` GMV, `Rs 2,648 Cr` operating revenue) while tagging `~7%` merchant loan penetration and `Rs 90-100/mo` Soundbox rental as assumptions benchmarked to FY24/FY25 Paytm IR disclosures. Show the synthetic store's `-70%` 3-to-5 PM scan trough (`30` vs `101`).
- **1:00 - 2:00 (Slide 2 + Appendix A4/A5):** Walk through the built architecture (`Config -> Render TTL/Count/Byte Session Bounds -> Keyless Provider & 30% Credit Cap -> Deterministic SQL + Templates`) and explain customer pass terms (`valid while shop offer budget lasts`), `>10%` overrun warning, 80%-cap merchant top-up prompt, and counter brand risk if late redeemers are declined.
- **2:00 - 4:15 (Live Full-Cycle Demo):**
  1. Toggle **Merchant View** (`EN author-checked, native review pending`; `KN/HI` `DRAFT - UNREVIEWED`; Grade A/B/C badges) vs **Technical View** (Fisher `p`, Wilson CIs, ITT invariance, cap-binding binomial math).
  2. Inspect the `42.2%` overrun warning on `CMP-WINBACK-01` (suggesting `Rs 400` cap), approve by voice, run the 48h simulator (`12/32` vs `1/8`, `cap_reached = True`, `refused_redemptions = 0`), and run the `Rs 150` tight-cap test (`6` paid, `6` refused, ITT unchanged).
  3. Trigger `OPS-STOCK-01` (`+18L milk, +12kg batter` PO) and `OPS-CARE-02` (`Rs 30` queue-delay coffee pass).
- **4:15 - 5:45 (Slide 4 + Appendix A7):** Define Intention-to-Treat, walk through the `+Rs 222` pre-fee / `+Rs 91.50` post-fee waterfall (`17.2%` / `24.7%` break-even margins; `+7.8 pp` / `+15.3 pp` break-even lifts), and show the pooled 50-shop power curve (`50.3%, 68.8%, 83.3%, 92.5%, 97.2%, 99.8%` across `+4, +5, +6, +7, +8, +10 pp`).
- **5:45 - 7:00 (Slide 5 + Appendix A8/A9):** Reconcile `Rs 130.50` single-wave fee with `Rs 102/mo` steady-state ARPU (`~0.78` waves/mo), review the three Q2 FY27 ARR cases (`Rs 77.7 Cr`, `Rs 178.1 Cr`, `Rs 253.9 Cr`), and close with the exact A9 go/no-go decision rule (lower 95% bound of post-5%-fee net profit per nudged customer `> Rs 0` and observed lift `>` break-even lift).

---

## Emergency Deck-Only Fallback Variant (Zero Network / Zero Browser / Audio Failure)

1. **Immediate Bridge Sentence:** *"To stay strictly on time without stage-audio latency, let us walk directly through the exact SQLite state, ITT cap-vs-holdout ledger, and pooled pilot math captured on Slide 3, Slide 4, and Appendix A4."*
2. **Slide 3 & Appendix A4 Walkthrough (60 seconds):**
   - Point to `1,613` synthetic scans across `240` payers (`917` scans / `Rs 1,74,685` in 30d) -> `48` lapsed -> `40` policy-eligible (`32` nudged, `8` silent control).
   - Highlight the disclosed cap design: all `32` nudged buyers receive passes (`valid while shop offer budget lasts`, `Rs 800` face exposure), `Rs 300` (`12` redemptions) hard-stops actual spend (`42.2%` overrun warning shown at approval), and simulated `12` returners equals the `Rs 300` cap (`cap_reached = True`, `0` refused).
   - Transition straight to Slide 4 (`12/32` vs `1/8` ITT, `+Rs 222` pre-fee / `+Rs 91.50` post-fee) and Slide 5 (`50` shops x `1` wave = `400C + 1,600T`, `83.3%` power at `+6 pp`).
