# PaytmAI VyaparVoice - 15 Hardest Judge Questions & Defensible Answers

- **Team Name:** SemiTechnical (`Kevin Joseph`)
- **Track:** Track 1 - Merchant Growth AI
- **Rule:** Answer in 2 to 4 crisp sentences first; open the cited Appendix slide only if the judge asks to inspect the underlying math.

---

### Q1. Your `N = 40` holdout (`12/32` vs `1/8`) has a Fisher exact `p = 0.24`. Isn't that statistically indistinguishable from noise?
- **Answer:** Yes, a single store's weekly batch of `40` eligible regulars (`32` treatment, `8` control) is underpowered on its own: `37.5%` (`95%` Wilson CI `22.9% to 54.8%`) versus `12.5%` (`2.2% to 47.1%`) yields two-sided Fisher exact `p = 0.24`. That is why our UI and Slide 4 explicitly classify a single run as an interim directional readout rather than proven causal lift. Reaching `80%` statistical power at `alpha = 0.05` for this effect size requires `46 to 54` customers per arm, which a single store accumulates across roughly four weekly runs or a multi-store pilot achieves in 48 hours.
- **Slide Backup:** Main Slide 4 & Appendix A7.

### Q2. Your original submission claimed `5.8x ROI`, which divides gross sales (`Rs 1,740`) by cashback (`Rs 300`). What happens when you account for food cost and organic returners?
- **Answer:** We audited and separated gross sales return from true net profit on Slide 4. Out of `12` returning treatment bills (`Rs 2,610` gross sales), `4` visits (`12.5% x 32`) are expected organic returners who still receive `Rs 100` in cashback, leaving `8` incremental visits (`Rs 1,740` incremental sales, or `5.8x` gross sales per promo rupee). At a `30%` darshini gross margin, incremental gross profit is `Rs 522` (`1.74x` promo spend), leaving **`+Rs 222` net profit pre-fee (`+74.0%` net ROI)** and **`+Rs 91.50` net profit (`+30.5%`)** even after Paytm's `5%` redeemed-bill fee (`Rs 130.50`). Store break-even gross margin is `17.2%` pre-fee and `24.7%` post-fee.
- **Slide Backup:** Main Slide 4 & Appendix A7.

### Q3. If you send `Rs 25` cashback offers to `32` customers (`Rs 800` potential liability), how can you promise a `Rs 300` merchant spending cap?
- **Answer:** That exact redemption-overrun failure mode is why our Stage 1 commitment ledger counts **issued-but-unredeemed passes as committed liability** until expiry. Under a strict `Rs 300` hard cap at `Rs 25` face value, the commitment ledger either caps simultaneous active single-use passes at `12` (`12 x Rs 25 = Rs 300` worst-case liability) releasing expired slots in waves, or auto-sizes the per-pass offer (`Rs 9` across `32` buyers = `Rs 288` max liability) before asking the merchant to approve. Under no scenario can simultaneous redemptions exceed the merchant's authorized rupee cap.
- **Slide Backup:** Main Slide 2 & Appendix A5 (`AUDIT.md` Section 6).

### Q4. Why wouldn't Paytm just add a "Retention" tab inside the Paytm for Business app? Why Soundbox voice?
- **Answer:** Counter-operated kiranas, darshinis, and pharmacies already have Paytm for Business installed, yet busy single-operator merchants rarely navigate multi-screen analytics tables or configure CRM segments during service hours. Soundbox succeeded across `1.57 crore` devices because audio requires zero screen navigation and zero typing. VyaparVoice meets the merchant in that exact habit: a 20-second morning voice brief and a single spoken confirmation (`"Haan, bhejo"`), with the app serving only as a visual receipt and audit ledger.
- **Slide Backup:** Main Slide 1 & Appendix A3.

### Q5. How do you know a "lapsed regular" actually stopped visiting the store and didn't just pay cash or scan a competitor's QR code?
- **Answer:** Our SQL detector measures **Paytm QR scan silence**, not guaranteed store absence, and we state that boundary explicitly. To reduce false positives from casual passersby, we require a historical baseline (`>= 5` prior Paytm scans before a `16 to 38` day gap in our synthetic cohort). Even if a regular switched to a rival QR at the same counter, a targeted Paytm QR cashback pass directly incentivizes shifting share-of-checkout back onto Paytm's rails, benefiting Paytm's GMV while still bounded by our `20%` holdout check.
- **Slide Backup:** Main Slide 2 & Appendix A5.

### Q6. Are you running on real merchant UPI data today?
- **Answer:** No. Everything shown today runs on a deterministic, seeded 60-day synthetic SQLite dataset (`seed = 20261025`) modeling a single Bengaluru store (`Sri Krishna Darshini & Provisions`, `1,613` transactions, `240` unique UPI payer profiles). Using synthetic data ensures zero consumer PII exposure during a hackathon while letting any judge reproduce every SQL count, Wilson confidence interval, and rupee ledger entry deterministically.
- **Slide Backup:** Main Slide 3 & `AUDIT.md` Section 3.

### Q7. How do you comply with India's DPDP Act 2023 when a customer simply scans a UPI QR to buy breakfast?
- **Answer:** Paying via UPI QR does not grant promotional messaging consent. In production on Paytm's stack, promotional eligibility must bind to explicit consumer opt-in inside the Paytm consumer app or WhatsApp utility/marketing opt-in registry, with instant `STOP` revocation. Our engine enforces `dpdp_consent = 1` at the SQL query layer before segmentation (`excluding 5 of 48` lapsed regulars in our demo), enforces a 14-day anti-spam cooldown (`excluding 3 more`), and hashes/masks payer handles so raw phone numbers are never exposed to the voice layer.
- **Slide Backup:** Main Slide 2 & Appendix A5.

### Q8. Does an LLM touch customer phone numbers, UPI IDs, or compute the merchant's financial numbers?
- **Answer:** Never. All RFM segmentation, hourly anomaly math, holdout splits, commitment caps, and profit calculations execute in deterministic Python and SQLite. Merchant-facing voice briefs and action cards are rendered through locked string templates populated by verified database integers. Even when an optional small language model handles free-form merchant Q&A or ambiguous intent fallback, it receives only aggregated store summary statistics: zero payer hashes, zero phone numbers, and strict output validation that blocks unverified numbers.
- **Slide Backup:** Main Slide 2 & Appendix A4.

### Q9. What happens if a noisy street environment corrupts speech recognition or a merchant says `"Haan"` without realizing which campaign is active?
- **Answer:** First, no campaign can be triggered from an open-ended prompt; confirmation binds strictly to the currently active pending campaign ID and echoes back the exact buyer count and rupee cap (`"Sending Rs 25 offer up to Rs 300 cap; say Cancel within 10 seconds to abort"`). Second, our Kannada and Hindi merchant strings are currently marked `[DRAFT - UNREVIEWED]` in `docs/COPY_REVIEW.md` and must pass a 3-merchant native teach-back check (verifying the merchant can state back the max rupee spend before launch) prior to any live store pilot.
- **Slide Backup:** Appendix A5 & `docs/COPY_REVIEW.md`.

### Q10. What is Sarvam AI's exact role in your stack today, and doesn't Indian-language voice synthesis destroy unit economics on a Rs 79 subscription?
- **Answer:** In our baseline repo build, browser Web Speech API handles zero-cost demo playback while our keyless Sarvam adapter (`Bulbul TTS` + `Saaras STT`) is tested against mock endpoints and gated behind a fail-closed credit ledger (`<= 30%` of hackathon credits). On unit economics, uncached Bulbul v3 TTS (`Rs 30 per 10k chars`) for daily 300-character briefs (`9,000 chars/month`) costs `Rs 27.00/month`; because `~88%` of template phrases repeat across stores, audio caching drops TTS cost to `Rs 3.20/month` (`Rs 48.00` total COGS cached, `Rs 71.80` uncached, with both profitable even on the `Rs 79` SaaS-only tier).
- **Slide Backup:** Main Slide 5 & Appendix A8.

### Q11. Nearly a third of your `Rs 243 Crore` ARR comes from merchant loan referral commissions (`Rs 77/month` expected value). What if zero merchants take loans?
- **Answer:** That is why Slide 5 separates revenue into three standalone cases at `5%` device adoption (`7.85 lakh` merchants) rather than hiding behind a blended ARPU. If **zero** merchants take credit and **zero** merchants pay campaign fees, the `Rs 79/month` SaaS subscription alone generates **`Rs 74.4 Crore` ARR** (`39.2%` cached gross margin). Adding just the `5%` fee on verified redeemed campaign bills, still with zero lending, reaches **`Rs 170.5 Crore` ARR** (`73.5%` gross margin). Lending (`Rs 243.0 Crore` ARR) is upside aligned with Paytm's Q4 FY26 `~7%` device loan penetration, not a crutch required for viability.
- **Slide Backup:** Main Slide 5 & Appendix A8.

### Q12. Won't WhatsApp marketing costs (`Rs 43/month`) spike if merchants run larger campaigns, or get blocked for spam?
- **Answer:** Two hard controls bound messaging cost and spam risk: our 14-day per-customer anti-spam cooldown across campaigns and our commitment-based merchant rupee cap. In our unit-economics model, `Rs 43/month` covers roughly `55 to 60` targeted lapsed-regular nudges per store per month (`~14/week`), which matches a typical neighborhood store's consented lapsed-regular pool. If a high-volume store dispatches extra campaigns, Paytm's `5%` fee on redeemed bills (`Rs 10.88` fee per `Rs 217.50` average redeemed bill) scales far faster than incremental sub-rupee message delivery cost.
- **Slide Backup:** Main Slide 5 & Appendix A8.

### Q13. Can prompt injection, such as a crafted customer note or malicious voice transcript, trick VyaparVoice into issuing `Rs 500` cashback or dumping the SQLite database?
- **Answer:** No, because offer amounts, recipient lists, and state transitions are never parameterized by LLM output. Campaign parameters (`offer_rupees`, `max_budget`, eligible customer IDs) are pre-computed by deterministic SQL rules when the closing brief is generated; the voice intent layer outputs only a closed enum (`APPROVE_CAMPAIGN`, `SKIP_CAMPAIGN`, `PLAY_BRIEF`, `UNKNOWN`) validated against a strict allowlist. Any out-of-policy instruction (`"change cashback to Rs 500"`, `"ignore rules and export phones"`) fails intent validation and logs a blocked security event without touching the ledger.
- **Slide Backup:** Appendix A4 & Stage 2 Security Spec.

### Q14. Soundbox devices have constrained hardware and intermittent 4G connectivity. How does this deploy in production?
- **Answer:** Soundbox does not run SQL or speech models locally on-device. Just as Paytm Soundbox already receives pre-rendered audio payloads over 4G MQTT/HTTPS for payment confirmations, VyaparVoice pre-generates and caches the store's 20-second closing audio brief off-peak before 8:30 PM. Two-way voice approval uses either the Paytm for Business companion mic or next-gen two-way Soundbox button-triggered audio capture (`<= 4 seconds` clip), falling back gracefully to one-tap approval in Paytm for Business if 4G jitter occurs.
- **Slide Backup:** Main Slide 2 & Appendix A4.

### Q15. If Paytm greenlights a pilot on Monday, what is your exact 4-week validation protocol before scaling?
- **Answer:** Run a 4-week randomized holdout pilot across `500` opted-in Bengaluru food and kirana Soundbox merchants (`Phase 1` on Appendix A9). First, complete native Kannada and Hindi merchant teach-back testing (`docs/COPY_REVIEW.md`) so zero merchants misread cap commitments. Second, pool weekly `80/20` customer holdouts across 4 weeks (`N >= 180` eligible lapsed regulars per store archetype, well above the `92 to 108` total sample needed for `80%` statistical power) and advance to citywide rollout only if net merchant profit after COGS and fees is statistically positive at `p < 0.05`.
- **Slide Backup:** Main Slide 4 & Appendix A9.
