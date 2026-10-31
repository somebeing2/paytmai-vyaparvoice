# PaytmAI VyaparVoice: 5-Minute Elevator Pitch & Demo Script

- **Presenter:** Kevin Joseph, Team SemiTechnical (Track 1: Merchant Growth AI)
- **Target Total Runtime:** 4:40 (`280` seconds = `204` seconds spoken at `150` wpm + `46` seconds cached app audio + `30` seconds clean UI cuts; leaves `20` seconds buffer inside the `5:00` cap)
- **Total Spoken Word Count:** 510 words (verified inside the `500` to `540` word target)
- **Live Demo URL:** https://paytmai-vyaparvoice.onrender.com/
- **Repository:** https://github.com/somebeing2/paytmai-vyaparvoice

---

## Pre-Recording Checklist

1. **Wake Render Container:** Open `https://paytmai-vyaparvoice.onrender.com/health` 3 minutes before recording (`status: "ok"`, `version: "1.5.0"`).
2. **Unlock & Pre-Warm Off-Camera:** Open `Technical & Audit View`, enter `DEMO_PIN` off-screen (never show any PIN or key on camera), click `Pre-warm` once so Kannada, Hindi, and English audio clips sit in the SQLite cache (`0` network delay during takes), then click `Reset` so all campaigns start at `Rs 0` spent with a `Rs 300` cap.
3. **Framing & Audio Check:** Switch to `Merchant View` in `Kannada`, set browser zoom to `100%`, mute OS notifications, and verify both microphone input and desktop loopback audio before rolling.
4. **Separate Takes:** Record Segments 1 and 6 face-to-camera, and record Demo Takes `3A` through `3F` as separate screen-capture clips for clean editing.

---

## Segment Timing & Word-Budget Summary (at 150 WPM)

| Segment | Window | Target Duration | Spoken Words | Speech @ 150 WPM | Cached Audio + UI Pause | Est. Segment Total |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Hook (Face to Camera)** | `0:00 - 0:30` | `30s` | `71` words | `28.4s` | `1.6s` pause | `30s` |
| **2. Solution** | `0:30 - 1:00` | `30s` | `67` words | `26.8s` | `3.2s` cut | `30s` |
| **3. Six-Take Live Demo** | `1:00 - 3:00` | `120s` | `152` words | `60.8s` | `46.0s` audio + `13.2s` UI | `120s` |
| **4. Why Numbers Are Trusted** | `3:00 - 3:25` | `25s` | `56` words | `22.4s` | `2.6s` cut | `25s` |
| **5. Business Case** | `3:25 - 4:05` | `40s` | `82` words | `32.8s` | `7.2s` cut | `40s` |
| **6. Honest Close (Face to Camera)** | `4:05 - 4:40` | `35s` | `82` words | `32.8s` | `2.2s` end hold | `35s` |
| **Total** | **`0:00 - 4:40`** | **`280s` (`4:40`)** | **`510` words** | **`204.0s`** | **`76.0s`** | **`280s` (`4:40`)** |

---

## Script & Take-by-Take Choreography

### Segment 1 (`0:00` to `0:30`) - Hook (Face to Camera)

- **Shot:** Kevin Joseph face to camera. *(First 42 words = 16.8 seconds land both synthetic customer-loss figures inside the first 20 seconds.)*

> **KEVIN (Spoken - 71 words | 28.4s @ 150 wpm):**
> On our sixty-day synthetic darshini ledger, forty-eight out of one hundred seventy-five repeat regulars quietly stopped visiting, and just two delayed morning regulars put four thousand nine hundred twenty rupees of monthly spend at risk. Neighbourhood shops rarely lose business overnight. Because QR payment alerts stream in as raw rupee amounts, owners notice churn late, miss the cause, and avoid discounts because an uncapped cashback offer can wipe out thin margins.

---

### Segment 2 (`0:30` to `1:00`) - The Solution

- **Shot:** Cut to clean overview of `Merchant View` showing `Closing-Time Soundbox` and `Bring Back Regulars`.

> **KEVIN (Spoken - 67 words | 26.8s @ 150 wpm):**
> PaytmAI VyaparVoice is a voice-delivered customer win-back copilot built around four steps: detect silent regulars from QR scan gaps, propose a targeted cashback pass, enforce a hard rupee cap, and measure return visits against an eighty-twenty non-offer holdout. To our knowledge the standard Paytm Soundbox is speaker-based with no microphone; this is to be validated with Paytm, so Soundbox speaks briefings while the Paytm app takes replies.

---

### Segment 3 (`1:00` to `3:00`) - Six-Action Live Demo (Recorded as Separate Takes)

#### Take 3A (`1:00` to `1:14`) - Action 1: Whole-Screen Language Switch
- **On-Screen Action:** Toggle the header language buttons from `Kannada` to `Hindi` to `English` and back to `Kannada` (`2s` UI pause).

> **KEVIN (Spoken - 20 words | 8.0s):**
> Every label, card, and spoken template switches cleanly across Kannada, Hindi, and English, while marking Hindi and Kannada as drafts.

#### Take 3B (`1:14` to `1:36`) - Action 2: Play Cached Kannada Closing Briefing
- **On-Screen Action:** Click `Speak` (`ಧ್ವನಿಯಲ್ಲಿ ಕೇಳಿ`) on the Soundbox panel. Let the cached Kannada 3-sentence briefing play (`11.0s` audio clip).
- **English Subtitle Cue (Burned On-Screen During Kannada Audio):**
  `[Kannada Audio Subtitle]: "Hello Ramesh, today Sri Krishna Darshini recorded 111 UPI payments. A Rs 25 cashback offer is ready for 32 regulars within a Rs 300 cap. Say Yes to send the offer."`

> **KEVIN (Spoken - 18 words | 7.2s):**
> At closing time, Ramesh hears a cached three-sentence Kannada briefing covering recent payments, eligible regulars, and his cap.

#### Take 3C (`1:36` to `1:58`) - Action 3: Set Budget by Voice to Rs 300 + Readback Confirmation
- **On-Screen Action:** Switch to `English` (for clear voice command capture, or stay in `Kannada` with subtitle), use the browser microphone (standing in for the Paytm for Business app) to speak `"Set my offer budget to 300 rupees for this week"`, play the cached readback (`5.0s` audio), and confirm `"Yes"` so the active cap stays at `Rs 300`.
- **English Subtitle Cue (If Readback Is Played in Kannada or Hindi):**
  `[Kannada/Hindi Audio Subtitle]: "Offer budget of Rs 300 for this week. Say Yes to confirm or say a different amount."`

> **KEVIN (Spoken - 28 words | 11.2s):**
> Using the browser microphone as our stand-in for the Paytm app, I set the offer budget to three hundred rupees, hear the exact readback, and confirm before launch.

#### Take 3D (`1:58` to `2:25`) - Action 4: Simulate Spend to 80% Alert and 100% Auto-Pause
- **On-Screen Action:** Trigger `Simulate spend` to `80%` (`Rs 250` used across `10` bills, firing the `50%` / `Rs 150` and `80%` / `Rs 250` alerts; play `80%` cached clip `7.5s`), then trigger `100%` (`Rs 300` across `12` bills, firing the `100%` pause alert `6.5s` and locking status to `CAP_PAUSED`).
- **English Subtitle Cues (If Alerts Play in Hindi or Kannada):**
  `[80% Alert Subtitle]: "80 percent budget alert. Rs 250 of your Rs 300 cap is used, leaving Rs 50. Say extend to raise budget or stop to pause now."`
  `[100% Alert Subtitle]: "100 percent cap reached. Rs 300 of your Rs 300 cap is used. Cashback is paused automatically and later customers pay regular price."`

> **KEVIN (Spoken - 27 words | 10.8s):**
> As passes redeem, spoken alerts fire at Rs 150 and at eighty percent, Rs 250. At Rs 300, cashback pauses automatically and later customers pay regular price.

#### Take 3E (`2:25` to `2:48`) - Action 5: Simulate 48h Return & Explain Simply
- **On-Screen Action:** Click `Complete 48h Run` (`Simulate 48h Return`), then open `Explain Simply` and play its cached readout (`16.0s` audio clip, which speaks `Rs 222` before fee and `Rs 92` after fee).
- **English Subtitle Cue (If Explain Simply Plays in Kannada or Hindi):**
  `[Explain Simply Subtitle]: "You spent Rs 300 of your Rs 300 budget across 12 bills. 12 of 32 customers with the offer visited versus 1 of 8 without an offer, adding 8 extra visits and Rs 1,740 extra sales. At 30 percent margin, profit is Rs 222 before fee, or Rs 92 after fee."`

> **KEVIN (Spoken - 31 words | 12.4s):**
> Next, in our simulation of forty-eight-hour returns, Explain Simply reads the outcome without statistical jargon: twelve of thirty-two nudged regulars returned versus one of eight, leaving about ninety-two rupees after fee.

#### Take 3F (`2:48` to `3:00`) - Action 6: Delayed-Regulars Card & Why? Panel
- **On-Screen Action:** Open the `Stock & Care` tab, show the `Delayed Regulars` card (`2` regulars, `Monthly spend at risk: Rs 4,920`, `possibly after a busy rush`), and click `Why?` (`2 x Rs 205 x 12`).

> **KEVIN (Spoken - 28 words | 11.2s):**
> Finally, the delayed-regulars card flags two regulars silent eight days, possibly after a busy rush, and its Why panel shows two times two hundred five times twelve visits.

---

### Segment 4 (`3:00` to `3:25`) - Why Every Number Can Be Trusted

- **On-Screen Action:** Switch to `Technical & Audit View` showing `Provider in use`, `Sarvam calls`, `Cached items`, `DEMO_PIN` session lock, and the audit log.

> **KEVIN (Spoken - 56 words | 22.4s @ 150 wpm):**
> In Technical View, every figure is computed by Python code, never by an AI model. Sarvam runs primary voice and chat, backed up by Groq and browser speech with templates. A digit gate checks English, Hindi, and Kannada numbers on every AI sentence, while an audit log, call caps, and PIN gating protect our public link.

---

### Segment 5 (`3:25` to `4:05`) - Business Case & Margin Reality

- **On-Screen Action:** Show the `What-If & Sensitivity` margin-by-fee table in `Technical & Audit View` (`+Rs 91.50` at `30%` margin and `5%` fee vs `-Rs 82.50` at `20%` margin).

> **KEVIN (Spoken - 82 words | 32.8s @ 150 wpm):**
> Our business case stays strictly grounded in unit incentives. Merchants get capped, holdout-measured win-back in their own language. As an assumption to verify with Paytm, Paytm gains deeper Soundbox and QR engagement with measurable offers. Who pays remains an open assumption, modelling a five percent promo fee only as an assumption alongside a modelled forty-eight rupee monthly cached cost per merchant. Crucially, this offer is post-fee positive near thirty percent food margins, suiting darshinis first, while low-margin kiranas need smaller category presets.

---

### Segment 6 (`4:05` to `4:40`) - Honest Close (Face to Camera)

- **Shot:** Cut back to Kevin Joseph face to camera, with lower-third text showing `paytmai-vyaparvoice.onrender.com` and `github.com/somebeing2/paytmai-vyaparvoice`.

> **KEVIN (Spoken - 82 words | 32.8s @ 150 wpm):**
> Let me close with our honest boundaries. Our sixty-day ledger and forty-eight-hour returns are synthetic simulations, Hindi and Kannada strings are drafts awaiting native review, single-wave results are directional only, and the spoken input channel must be validated with Paytm. Our proposed next step is an opt-in multi-shop darshini pilot with randomized holdouts and clear stop rules. I am Kevin Joseph from Team SemiTechnical. Try the live app on Render and inspect every test and line of code on GitHub. Thank you.
