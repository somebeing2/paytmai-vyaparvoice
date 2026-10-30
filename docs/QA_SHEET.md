# PaytmAI VyaparVoice - 15 Hardest Judge Questions & Defensible Answers

- **Team Name:** SemiTechnical (`Kevin Joseph`)
- **Track:** Track 1 - Merchant Growth AI
- **Rule:** Answer in 2 to 4 crisp sentences first; open the cited Appendix slide only if the judge asks to inspect the underlying math.

---

### Q1. Your `N = 40` holdout (`12/32` vs `1/8`) has a Fisher exact `p = 0.24`. Isn't that statistically indistinguishable from noise?
- **Answer:** Yes, a single store's weekly wave of `40` eligible regulars (`32` nudged, `8` control) is underpowered on its own: `37.5%` (`95%` Wilson CI `22.9% to 54.8%`) versus `12.5%` (`2.2% to 47.1%`) yields two-sided Fisher exact `p = 0.24`. That is why our UI and Slide 4 explicitly classify one wave as an interim directional readout and suppress significance claims. At our `80/20` allocation (`40` customers per wave), reaching `80%` statistical power at `alpha = 0.05` requires about `31` control and `124` nudged customers (`155` total, roughly `4` waves), or `46` per arm (`92` total) if run at an even `50/50` split.
- **Slide Backup:** Main Slide 4, Main Slide 5 & Appendix A7, A9.

### Q2. Your original submission claimed `5.8x ROI`, which divides gross sales (`Rs 1,740`) by cashback (`Rs 300`). What happens when you account for food cost, organic returners, and Paytm's fee?
- **Answer:** Slide 4 separates gross sales multiple from true merchant net profit. Out of `12` returning bills (`Rs 2,610` at `Rs 217.50` mean), `4` visits (`12.5% x 32`) are expected organic returners who still redeem `Rs 100` in cashback, leaving `8` incremental visits (`Rs 1,740` incremental sales, or `5.8x` gross sales per rupee of cashback). At a `30%` darshini gross margin, incremental gross profit is `Rs 522` (`1.74x` promo spend), leaving **`+Rs 222` net profit pre-fee (`+74.0%` net ROI)** and **`+Rs 91.50` net profit (`+30.5%`)** after Paytm's `5%` fee (`Rs 130.50`, charged on all `Rs 2,610` redeemed bills including organic returners). Store break-even gross margin is `17.2%` pre-fee and `24.7%` post-fee.
- **Slide Backup:** Main Slide 4 & Appendix A7.

### Q3. You issue `Rs 25` passes to all `32` nudged customers (`Rs 800` face exposure) against a `Rs 300` merchant cap (`12` redemptions). What happens if a 13th customer tries to redeem, and doesn't capping corrupt the holdout experiment?
- **Answer:** We deliberately issue passes to all `32` nudged customers rather than starving reach to `12`, and treat `Rs 300` as an atomic hard stop on actual cashback spend (`actual_spend <= Rs 300`), explicitly disclosing the `Rs 800` face exposure versus `Rs 300` spend stop trade-off. First, at approval our engine computes the exact binomial probability that redemptions exceed `12` (`42.2%` at a `37.5%` rate; `16.3%` at `30%`) and warns the merchant whenever overrun risk exceeds `10%`, suggesting a higher cap (`Rs 325` to `Rs 400`). Second, our simulator draws customer return visits independently of the cap first and then applies the spend stop (recording `cap_reached` and `refused_redemptions`; in our canonical run, simulated `12` returners equals the `12`-redemption cap), while analysing holdout lift strictly as **Intention-to-Treat (ITT)** across all `32` nudged buyers so the causal comparison is mathematically unchanged even when the cap binds.
- **Slide Backup:** Main Slide 4 & Appendix A4.

### Q4. On Slide 4, Paytm's `5%` promo fee on one campaign is `Rs 130.50`, yet Appendix A8 models `Rs 102 / month` in promo fee ARPU. Why is the monthly number lower than a single campaign?
- **Answer:** Both figures use the exact same fee rule: `5%` of **all QR-redeemed campaign bills, including organic returners** (`5% x Rs 2,610 = Rs 130.50` on the initial `40`-customer backlog wave). Once a neighborhood shop clears its initial backlog of lapsed regulars, the 14-day cooldown-eligible lapsed pool replenishes gradually rather than regenerating `40` fresh lapsed regulars every week. Our steady-state ARPU therefore assumes **`Rs 2,040 / month`** in redeemed promo bills (`~0.78` full win-back-equivalent waves per month, or two smaller biweekly runs), yielding `5% x Rs 2,040 = Rs 102 / month`.
- **Slide Backup:** Main Slide 4, Main Slide 5 & Appendix A8.

### Q5. Why wouldn't Paytm just add a "Retention" tab inside the Paytm for Business app? Why Soundbox voice?
- **Answer:** Counter-operated kiranas, darshinis, and pharmacies already have Paytm for Business installed, yet busy single-operator merchants rarely navigate multi-screen analytics tables or configure CRM segments during service hours. Soundbox succeeded across `1.64 crore` subscription-paying merchants (Reported in Paytm's Q2 FY27 release, 26 Oct 2026) because audio requires zero screen navigation and zero typing. VyaparVoice meets the merchant in that exact habit at 8:30 PM closing time with a 20-second voice brief and one spoken confirmation, using the companion screen only for visual audit and fallback.
- **Slide Backup:** Main Slide 1 & Appendix A3.

### Q6. How do you know a "lapsed regular" actually stopped visiting the store and didn't just pay cash or scan a competitor's QR code?
- **Answer:** Our SQL detector measures **Paytm QR scan silence**, not guaranteed physical absence, and we state that boundary explicitly. Requiring `5 to 10` historical Paytm scans before a `16 to 38` day gap filters out one-time passersby. Even when a regular switched to cash or a rival QR at the same counter, a targeted Paytm QR cashback pass shifts checkout share back onto Paytm's rails while still being evaluated against our `20%` silent holdout.
- **Slide Backup:** Main Slide 2 & Appendix A4.

### Q7. Are you running on real merchant UPI data today?
- **Answer:** No. Everything shown today runs on a deterministic, seeded 60-day synthetic SQLite dataset (`seed = 20261025`) modeling a single Bengaluru store (`Sri Krishna Darshini & Provisions`, `1,613` transactions across `240` unique UPI payer profiles). Using synthetic data guarantees zero consumer PII exposure while allowing any judge to reproduce every SQL count, Wilson confidence interval, ITT holdout test, and rupee ledger entry deterministically.
- **Slide Backup:** Main Slide 3 & Appendix A4.

### Q8. How do you comply with India's DPDP Act 2023 when a customer simply scans a UPI QR to buy breakfast?
- **Answer:** Paying via UPI QR does not grant promotional messaging consent. In production on Paytm's stack, promotional eligibility binds strictly to explicit consumer opt-in inside the Paytm app or WhatsApp opt-in registry with instant `STOP` revocation. Our engine enforces `dpdp_consent = 1` at the SQL layer before segmentation (`excluding 5 of 48` lapsed regulars), enforces a 14-day anti-spam cooldown (`excluding 3 more`), and masks payer handles so raw phone numbers never reach the voice or LLM layers.
- **Slide Backup:** Main Slide 2 & Appendix A4.

### Q9. Does an LLM touch customer phone numbers, UPI IDs, or compute the merchant's financial numbers?
- **Answer:** Never. All RFM segmentation, hourly anomaly math, holdout splits, cap-binding probabilities, and profit calculations execute in deterministic Python and SQLite. Merchant-facing voice briefs and scorecards are rendered through locked string templates checked by an automated banned-jargon linter. Even when an optional small language model handles English store Q&A in Stage 2, it receives only aggregated store summary totals with zero customer rows and strict output validation.
- **Slide Backup:** Main Slide 2 & Appendix A5.

### Q10. What happens if a noisy street environment corrupts speech recognition or a merchant says `"Haan"` without realizing the rupee commitment?
- **Answer:** Confirmation binds strictly to the pending campaign ID, warns upfront if cap-overrun risk exceeds `10%`, and reads back the exact `Rs 300` hard spend ceiling with a cancellation window. In addition, our Kannada and Hindi merchant strings are marked `[DRAFT - UNREVIEWED BY NATIVE SPEAKER]` in both the UI and `docs/COPY_REVIEW.md`, and must pass a 3-merchant native teach-back check verifying comprehension of the `Rs 300` max spend before any live pilot.
- **Slide Backup:** Appendix A4 & `docs/COPY_REVIEW.md`.

### Q11. What is Sarvam AI's exact role in your stack today, and doesn't Indian-language voice synthesis destroy unit economics on a Rs 79 subscription?
- **Answer:** Our Stage 1 provider layer includes a keyless Sarvam Bulbul TTS and Saaras STT adapter tested against a local mock HTTP server, gated behind dual feature flags and a fail-closed credit ledger capped at `15%` TTS + `15%` STT (`30%` max of hackathon credits), with zero-cost browser Web Speech API and cached audio fallback. On unit economics, uncached Bulbul v3 TTS (`Rs 30 per 10k chars`, `9,000 chars/month`) costs `Rs 27.00/month`, and `~88%` phrase-template caching lowers TTS cost to `Rs 3.20/month` (`Rs 48.00` total COGS cached, `Rs 71.80` uncached, leaving positive gross margin even on the `Rs 79` SaaS-only tier).
- **Slide Backup:** Main Slide 5 & Appendix A8.

### Q12. Nearly a third of your `Rs 253.9 Crore` ARR comes from merchant loan referral commissions (`Rs 77/month`, using an assumed `~7%` baseline loan penetration). What if zero merchants take loans?
- **Answer:** First, we explicitly label `~7%` merchant loan penetration and `Rs 90 to 100/month` Soundbox rental as assumptions (noting Paytm's Q2 FY27 release on 26 Oct 2026 reports `8.8 lakh` total key financial services customers and `>50%` repeat merchant loan disbursements). Second, Slide 5 breaks revenue into three standalone cases across `5%` of Paytm's `1.64 crore` subscription merchants (`8.20 lakh` shops): **`Rs 77.7 Crore` ARR** on `Rs 79/month` SaaS alone (zero promo or credit fees), **`Rs 178.1 Crore` ARR** adding steady-state promo fees (`Rs 181/month`, still zero credit), and **`Rs 253.9 Crore` ARR** in the full base case.
- **Slide Backup:** Main Slide 5 & Appendix A8.

### Q13. Can prompt injection, such as a crafted voice transcript, trick VyaparVoice into issuing `Rs 500` cashback or clobbering another visitor's live Render demo?
- **Answer:** No on both counts. Offer amounts (`offer_rupees`), caps (`max_budget`), and recipient lists are pre-computed in SQLite and cannot be parameterized by voice or LLM output; voice commands resolve only to a closed enum of allowlisted actions. On our public Render URL (`PUBLIC_DEPLOY=true`), live paid provider calls are disabled in code, global admin endpoints require `X-Admin-Token`, and each browser visitor runs inside an isolated per-session SQLite sandbox so concurrent judges never overwrite one another.
- **Slide Backup:** Appendix A5 & Stage 1 Safeguards (`app/sessions.py`, `app/security.py`).

### Q14. Soundbox devices have constrained hardware and intermittent 4G connectivity. How does this deploy in production?
- **Answer:** Soundbox does not run SQL or speech models locally on-device. Just as Paytm Soundbox already receives pre-rendered audio payloads over 4G for payment confirmations, VyaparVoice pre-generates and caches the store's 20-second closing audio brief off-peak before 8:30 PM. Two-way approval uses either the Paytm for Business companion mic or button-triggered short audio capture (`<= 4 seconds`), with instant 1-tap fallback in Paytm for Business if 4G drops.
- **Slide Backup:** Main Slide 2 & Appendix A5.

### Q15. If Paytm greenlights a pilot on Monday, what is your exact 4-week validation protocol before scaling?
- **Answer:** Run a 4-week randomized Intention-to-Treat holdout pilot across `500` opted-in Bengaluru food and kirana Soundbox merchants (`Appendix A9`). First, complete native Kannada and Hindi merchant teach-back testing (`docs/COPY_REVIEW.md`). Second, pool `4` weekly `80/20` waves per store (`~160` eligible observations per store, exceeding the `31` control + `124` nudged = `155` sample needed for `80%` power at `alpha = 0.05`) and advance to citywide rollout only if net merchant profit after COGS, refused-redemption goodwill rules, and Paytm fees is statistically positive at `p < 0.05`.
- **Slide Backup:** Main Slide 4 & Appendix A9.
