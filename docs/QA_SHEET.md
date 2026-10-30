# PaytmAI VyaparVoice - 16 Hardest Judge Questions & Defensible Answers

- **Team Name:** SemiTechnical (`Kevin Joseph`)
- **Track:** Track 1 - Merchant Growth AI
- **Rule:** Answer in 2 to 4 crisp sentences first; open the cited Appendix slide only if the judge asks to inspect the underlying math.

---

### Q1. Your `N = 40` holdout (`12/32` vs `1/8`) has a Fisher exact `p = 0.24`. Isn't that statistically indistinguishable from noise, and how do you power a pilot without violating the 14-day cooldown?
- **Answer:** Yes, a single store wave (`32` nudged, `8` control) is directional only (`37.5%` [CI `22.9%-54.8%`] vs `12.5%` [`2.2%-47.1%`], two-sided Fisher `p = 0.24`; conjugate `Beta(1,1)` posterior gives `88.8%` `P(lift>0)`, `67.0%` `P(pre-fee profit>0)`, `52.1%` `P(post-fee profit>0)`, and `95%` CrI `[-Rs 19.97, +Rs 14.73]` per nudged buyer), so our UI explicitly fails the auto-scale gate on one wave. Because a 14-day per-customer cooldown and `~0.78` steady-state waves/month mean one store cannot run four independent full waves in four weeks, our pilot **pools one wave across `50` Bengaluru shops** (`~40` eligible each = **`~400` silent control and `~1,600` nudged**), randomized within each shop and analysed stratified by shop (`50.3%, 68.8%, 83.3%, 92.5%, 97.2%, 99.8%` power at `+4, +5, +6, +7, +8, +10 pp`).
- **Slide Backup:** Main Slide 4, Main Slide 5 & Appendix A7, A9, A13.

### Q2. Your original submission claimed `5.8x ROI`, which divides gross sales (`Rs 1,740`) by cashback (`Rs 300`). What happens when you account for food cost, organic returners, and Paytm's fee?
- **Answer:** Slide 4 separates gross sales multiple from true merchant net profit. Out of `12` returning bills (`Rs 2,610` at `Rs 217.50` mean), `4` visits (`12.5% x 32`) are expected organic returners who still redeem `Rs 100` in cashback, leaving `8` incremental visits (`Rs 1,740` incremental sales, or `5.8x` gross sales per rupee of cashback). At a `30%` darshini gross margin, incremental gross profit is `Rs 522` (`1.74x` promo spend), leaving **`+Rs 222` net profit pre-fee (`+74.0%` net ROI)** and **`+Rs 91.50` net profit (`+30.5%`)** after Paytm's `5%` fee (`Rs 130.50`, charged on all `Rs 2,610` redeemed bills including organic returners). Store break-even margin is `17.2%` pre-fee / `24.7%` post-fee, and break-even lift at `30%` margin is `+7.8 pp` pre-fee / `+15.3 pp` post-fee.
- **Slide Backup:** Main Slide 4 & Appendix A7.

### Q3. Why do you issue passes to all `32` nudged customers (`Rs 800` face exposure) against a `Rs 300` merchant cap (`12` redemptions), and doesn't capping corrupt the holdout experiment?
- **Answer:** Limiting pass issuance to `12` buyers would starve campaign reach; instead, we issue passes to all `32` nudged customers and enforce `Rs 300` as an atomic SQLite hard stop on actual cashback spend, warning at approval whenever `P(Binomial(32, p) > 12) > 10%` (`42.2%` at `p = 37.5%`, suggesting `Rs 400`). Crucially, our simulator draws customer return visits independently of the cap first and then applies the spend stop (in the base run, simulated `12` returners equals the `Rs 300` cap). Because we evaluate holdout lift strictly as **Intention-to-Treat (ITT)** across all `32` assigned nudged customers versus all `8` assigned controls regardless of cap stops, causal lift is mathematically unchanged when the cap binds (verified by automated multi-seed tests).
- **Slide Backup:** Main Slide 4 & Appendix A4.

### Q4. What happens to a customer who arrives at the counter after the `Rs 300` cap is reached?
- **Answer:** Four explicit safeguards govern late arrivals: first, **pass terms** state upfront *"Valid on Paytm QR bills of Rs 150+ while the shop's campaign offer budget lasts."* Second, **merchant top-up prompt**: in addition to the pre-approval `>10%` overrun alert, crossing `80%` of the cap (`10 of 12` redemptions) triggers a 1-tap Soundbox/App prompt letting the merchant top up `+Rs 100` (`4` extra passes) before exhaustion. Third, **declines logged**: if the merchant does not top up and a 13th regular scans QR, normal UPI payment completes cleanly, the `Rs 25` cashback is withheld with an in-app *"Shop offer budget ended for this round"* notice, and SQLite increments `refused_redemptions` plus an immutable `audit_log` row. Fourth, **brand risk named**: turning away a returning regular at checkout creates real merchant goodwill and Paytm brand friction, which is why `refused_redemptions` is tracked as a primary guardrail metric in our pilot.
- **Slide Backup:** Appendix A4 & Appendix A11.

### Q5. On Slide 4, Paytm's `5%` promo fee on one campaign is `Rs 130.50`, yet Appendix A8 models `Rs 102 / month` in promo fee ARPU. Why is the monthly number lower than a single campaign?
- **Answer:** Both figures use the exact same fee rule: `5%` of **all QR-redeemed campaign bills, including organic returners** (`5% x Rs 2,610 = Rs 130.50` on the initial `40`-customer backlog wave). Once a neighborhood shop clears its initial backlog of lapsed regulars, the 14-day cooldown-eligible lapsed pool replenishes gradually rather than regenerating `40` fresh lapsed regulars every week. Steady-state ARPU therefore assumes **`Rs 2,040 / month`** in redeemed promo bills (`~0.78` full win-back-equivalent waves per month), yielding `5% x Rs 2,040 = Rs 102 / month`.
- **Slide Backup:** Main Slide 4, Main Slide 5 & Appendix A8.

### Q6. Why wouldn't Paytm just add a "Retention" tab inside the Paytm for Business app? Why Soundbox voice?
- **Answer:** Counter-operated kiranas, darshinis, and pharmacies already have Paytm for Business installed, yet busy single-operator merchants rarely navigate multi-screen analytics tables or configure CRM segments during service hours. Soundbox succeeded across `1.64 crore` subscription-paying merchants (Reported in Paytm's Q2 FY27 release, 26 Oct 2026) because audio requires zero screen navigation and zero typing. VyaparVoice meets the merchant in that exact habit at 8:30 PM closing time with a 20-second voice brief and one spoken confirmation, using the companion screen only for visual audit and fallback.
- **Slide Backup:** Main Slide 1 & Appendix A3.

### Q7. How do you know a "lapsed regular" actually stopped visiting the store and didn't just pay cash or scan a competitor's QR code?
- **Answer:** Our SQL detector measures **Paytm QR scan silence**, not guaranteed physical absence, and we state that boundary explicitly. Requiring `5 to 10` historical Paytm scans before a `16 to 38` day gap filters out one-time passersby. Even when a regular switched to cash or a rival QR at the same counter, a targeted Paytm QR cashback pass shifts checkout share back onto Paytm's rails while still being evaluated against our `20%` silent holdout.
- **Slide Backup:** Main Slide 2 & Appendix A4.

### Q8. Are you running on real merchant UPI data today?
- **Answer:** No. Everything shown today runs on a deterministic, seeded 60-day synthetic SQLite dataset (`seed = 20261025`) modeling a single Bengaluru store (`Sri Krishna Darshini & Provisions`, `1,613` transactions across `240` unique UPI payer profiles). Using synthetic data guarantees zero consumer PII exposure while allowing any judge to reproduce every SQL count, Wilson confidence interval, ITT holdout test, and rupee ledger entry deterministically.
- **Slide Backup:** Main Slide 3 & Appendix A4.

### Q9. How do you comply with India's DPDP Act 2023 when a customer simply scans a UPI QR to buy breakfast?
- **Answer:** Paying via UPI QR does not grant promotional messaging consent. In production on Paytm's stack, promotional eligibility binds strictly to explicit consumer opt-in inside the Paytm app or WhatsApp opt-in registry with instant `STOP` revocation. Our engine enforces `dpdp_consent = 1` at the SQL layer before segmentation (`excluding 5 of 48` lapsed regulars), enforces a 14-day anti-spam cooldown (`excluding 3 more`), and masks payer handles so raw phone numbers never reach the voice or LLM layers.
- **Slide Backup:** Main Slide 2 & Appendix A4.

### Q10. Does an LLM touch customer phone numbers, UPI IDs, or compute the merchant's financial numbers?
- **Answer:** Never. All segmentation, hourly slow-window math, holdout splits, cap-binding probabilities, and profit calculations execute in deterministic Python and SQLite. Merchant-facing voice briefs and scorecards are rendered through locked string templates checked by an automated banned-jargon linter. Our optional Stage 2 Groq English Q&A adapter (`app/providers/groq_qa.py`, disabled by default and hard-blocked on `PUBLIC_DEPLOY=true`) enforces an outbound zero-PII regex filter (`assert_zero_pii`), verifies every emitted number against the SQLite fact whitelist (`verify_grounded_numbers`), runs `copy_lint`, and falls back automatically to deterministic SQLite answers on any mismatch.
- **Slide Backup:** Main Slide 2, Appendix A3 & Appendix A5.

### Q11. What happens if street noise corrupts speech recognition or a merchant says `"Haan"` without realizing the rupee commitment?
- **Answer:** Confirmation binds strictly to the pending campaign ID, warns upfront if cap-overrun risk exceeds `10%`, and reads back the exact `Rs 300` hard spend ceiling with a cancellation window. Furthermore, we disclose honest copy status everywhere: English is marked `EN author-checked, native review pending`, and Kannada and Hindi are marked `[DRAFT - UNREVIEWED BY NATIVE SPEAKER]`, requiring a 3-merchant counter teach-back sign-off on the `Rs 300` cap before any live store pilot.
- **Slide Backup:** Appendix A4, Appendix A10 & `docs/COPY_REVIEW.md`.

### Q12. What is Sarvam AI's exact role in your stack today, and doesn't Indian-language voice synthesis destroy unit economics on a Rs 79 subscription?
- **Answer:** Our Stage 1 provider layer includes a keyless Sarvam Bulbul TTS and Saaras STT adapter verified against a local mock HTTP server, gated behind dual feature flags and a fail-closed credit ledger capped at `15%` TTS + `15%` STT (`30%` max of hackathon credits), with zero-cost browser Web Speech API and SHA-256 cached audio fallback. On unit economics, uncached Bulbul v3 TTS (`Rs 30 per 10k chars`, `9,000 chars/month`) costs `Rs 27.00/month`, and `~88%` phrase-template caching lowers TTS cost to `Rs 3.20/month` (`Rs 48.00` total COGS cached, `Rs 71.80` uncached, leaving positive gross margin even on the `Rs 79` SaaS-only tier).
- **Slide Backup:** Main Slide 5 & Appendix A8.

### Q13. Nearly a third of your `Rs 253.9 Crore` ARR comes from merchant loan referral commissions (`Rs 77/month`, using an assumed `~7%` baseline loan penetration). What if zero merchants take loans?
- **Answer:** First, we explicitly label `~7%` merchant loan penetration and `Rs 90 to 100/month` Soundbox rental as assumptions benchmarked to historical Paytm IR disclosures. Second, Slide 5 breaks revenue into three standalone cases across `5%` of Paytm's `1.64 crore` Q2 FY27 subscription merchants (`8.20 lakh` shops): **`Rs 77.7 Crore` ARR** on `Rs 79/month` SaaS alone (zero promo or credit fees), **`Rs 178.1 Crore` ARR** adding steady-state promo fees (`Rs 181/month`, still zero credit), and **`Rs 253.9 Crore` ARR** in the full base case.
- **Slide Backup:** Main Slide 5 & Appendix A8.

### Q14. Can prompt injection trick VyaparVoice into issuing `Rs 500` cashback, or can heavy traffic crash your Render Free deployment?
- **Answer:** Offer amounts (`offer_rupees`), caps (`max_budget`), and recipient lists live in SQLite and cannot be parameterized by voice or LLM output. On Render (`PUBLIC_DEPLOY=true`), paid provider calls are disabled in code, admin endpoints require `X-Admin-Token`, and per-visitor SQLite sandboxes (`204 KB` each) enforce a `30`-minute idle TTL, a `64`-session LRU cap, a `2 MB` per-DB cap, and a `32 MB` total session disk cap (`~55 MB` worker RSS out of `512 MB` RAM).
- **Slide Backup:** Main Slide 2, Main Slide 3 & Appendix A5.

### Q15. Soundbox devices have constrained hardware and intermittent 4G connectivity. How does this deploy in production?
- **Answer:** Soundbox does not run SQL or speech models locally on-device. Just as Paytm Soundbox already receives pre-rendered audio payloads over 4G for payment confirmations, VyaparVoice pre-generates and caches the store's 20-second closing audio brief off-peak before 8:30 PM. Two-way approval uses either the Paytm for Business companion mic or button-triggered short audio capture (`<= 4 seconds`), with instant 1-tap fallback in Paytm for Business if 4G drops.
- **Slide Backup:** Main Slide 2 & Appendix A5.

### Q16. If Paytm greenlights a pilot on Monday, what is your exact experimental design and go/no-go decision rule?
- **Answer:** Run a **pooled 50-shop x 1-wave stratified Intention-to-Treat pilot** across opted-in Bengaluru food and kirana merchants (`~40` eligible regulars per shop = `~400` silent control and `~1,600` nudged), randomized `80/20` within each shop and analysed stratified by shop (`83.3%` power at `+6 pp` lift, `97.2%` at `+8 pp`, `99.8%` at `+10 pp`), after completing 3-merchant native teach-back sign-off across EN, KN, and HI. Our strict go/no-go gate (`Appendix A9`) is: **advance to citywide rollout only if the lower 95% confidence bound of net profit per nudged customer after the 5% fee is above zero AND the observed lift exceeds the break-even lift (`+15.3 pp` post-fee at `30%` margin)**.
- **Slide Backup:** Main Slide 5, Appendix A7 & Appendix A9.
