# PaytmAI VyaparVoice - Reproducible 60-Case Evaluation Benchmark

**Command:** `python3 scripts/eval_benchmark.py --assert-targets`
**Execution Environment:** Keyless deterministic engine + isolated SQLite sandbox (zero API keys, zero network calls)

## 1. Summary Scorecard

| Evaluation Suite | Cases | Passed | Accuracy | Target | Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Suite A: Multilingual Voice Intents & Verbal Caps (EN / HI / KN / Indic Digits)** | 24 | 24 | 100.0% | 100.0% | PASS |
| **Suite B: Adversarial Prompt-Injection & 6 Hard Policy Guardrails** | 18 | 18 | 100.0% | 100.0% | PASS |
| **Suite C: Numeric Grounding (ASCII + Devanagari + Kannada) & Zero-PII Firewall** | 18 | 18 | 100.0% | 100.0% | PASS |
| **Total Combined Benchmark** | **60** | **60** | **100.0%** | **100.0%** | **PASS** |

## 2. What Each Suite Verifies

1. **Suite A (24 Cases - Multilingual Voice & Readback State Machine):**
   - Verifies verbal rupee cap parsing across English, Hindi, and Kannada words and native digits (`400`, `450`, `350`, Devanagari `४००`, Kannada `೪೦೦`).
   - Enforces two-step readback confirmation (`CAP_CONFIRMATION_PENDING` -> `yes` / `हां` / `ಹೌದು` -> `CAP_CONFIRMED_CMP_WINBACK_01`, and `नहीं` / `ಬೇಡ` -> `CAP_CANCELLED_CMP_WINBACK_01`).
   - Rejects out-of-bounds caps (`Rs 20` below `Rs 50` floor; `Rs 5,000` above `Rs 2,500` ceiling).
   - Routes campaign approvals, supplier milk reorders, 48-hour simulations, immediate voice stop-loss (`ऑफर रोको` / `ಆಫರ್ ನಿಲ್ಲಿಸಿ`), and SQLite-grounded merchant Q&A.
2. **Suite B (18 Cases - Deterministic Policy Guardrail Engine):**
   - Verifies `0%` false-negative rate on adversarial prompt-injection attempts (`>22%` effective discount, `<Rs 50` or `>Rs 2,500` spend cap bounds, `<14-day` message spam, unconsented outreach, removing the `20%` holdout control group, and jailbreak/override directives) while permitting compliant merchant offers (`0%` false-positive rate).
3. **Suite C (18 Cases - Hallucination & Outbound PII Firewall):**
   - Normalizes ASCII, Devanagari (`०-९`), and Kannada (`೦-೯`) numerals via `verify_grounded_numbers` and rejects every ungrounded figure.
   - Blocks `CUST-*` IDs, Indian mobile numbers (`+91` / `10-digit`), and `SHA-256` payer hashes before any external LLM prompt leaves the server (`assert_zero_pii`).

## 3. Suite A Multilingual Utterance Matrix (24/24)

| # | Lang | Utterance | Expected Action | Observed Action | Result |
| :---: | :---: | :--- | :--- | :--- | :---: |
| 1 | `en` | `Set my spending limit to 400 rupees` | `CAP_CONFIRMATION_PENDING` | `CAP_CONFIRMATION_PENDING` | PASS |
| 2 | `en` | `yes` | `CAP_CONFIRMED_CMP_WINBACK_01` | `CAP_CONFIRMED_CMP_WINBACK_01` | PASS |
| 3 | `hi` | `मेरा बजट 450 रुपये कर दो` | `CAP_CONFIRMATION_PENDING` | `CAP_CONFIRMATION_PENDING` | PASS |
| 4 | `hi` | `हां` | `CAP_CONFIRMED_CMP_WINBACK_01` | `CAP_CONFIRMED_CMP_WINBACK_01` | PASS |
| 5 | `kn` | `ನನ್ನ ಬಜೆಟ್ 350 ರೂಪಾಯಿ ಮಾಡಿ` | `CAP_CONFIRMATION_PENDING` | `CAP_CONFIRMATION_PENDING` | PASS |
| 6 | `kn` | `ಹೌದು` | `CAP_CONFIRMED_CMP_WINBACK_01` | `CAP_CONFIRMED_CMP_WINBACK_01` | PASS |
| 7 | `hi` | `बजट ४०० रुपये रखो` | `CAP_CONFIRMATION_PENDING` | `CAP_CONFIRMATION_PENDING` | PASS |
| 8 | `hi` | `नहीं` | `CAP_CANCELLED_CMP_WINBACK_01` | `CAP_CANCELLED_CMP_WINBACK_01` | PASS |
| 9 | `kn` | `ಬಜೆಟ್ ೪೦೦ ರೂಪಾಯಿ ಇಡಿ` | `CAP_CONFIRMATION_PENDING` | `CAP_CONFIRMATION_PENDING` | PASS |
| 10 | `kn` | `ಬೇಡ` | `CAP_CANCELLED_CMP_WINBACK_01` | `CAP_CANCELLED_CMP_WINBACK_01` | PASS |
| 11 | `en` | `Set budget to 20 rupees` | `CAP_CHANGE_REJECTED` | `CAP_CHANGE_REJECTED` | PASS |
| 12 | `en` | `Set spending limit to 5000 rupees` | `CAP_CHANGE_REJECTED` | `CAP_CHANGE_REJECTED` | PASS |
| 13 | `en` | `Yes, approve and send offer` | `APPROVED_CMP_WINBACK_01` | `APPROVED_CMP_WINBACK_01` | PASS |
| 14 | `hi` | `हाँ ऑफर भेज दो` | `APPROVED_CMP_WINBACK_01` | `APPROVED_CMP_WINBACK_01` | PASS |
| 15 | `kn` | `ಹೌದು ಆಫರ್ ಕಳುಹಿಸಿ` | `APPROVED_CMP_WINBACK_01` | `APPROVED_CMP_WINBACK_01` | PASS |
| 16 | `en` | `Approve supplier milk reorder` | `EXECUTED_OPS_STOCK_01` | `EXECUTED_OPS_STOCK_01` | PASS |
| 17 | `en` | `Check 48 hours outcome` | `SIMULATED_CMP_WINBACK_01` | `SIMULATED_CMP_WINBACK_01` | PASS |
| 18 | `hi` | `ऑफर रोको` | `STOP_LOSS_TRIGGERED` | `STOP_LOSS_TRIGGERED` | PASS |
| 19 | `kn` | `ಆಫರ್ ನಿಲ್ಲಿಸಿ` | `STOP_LOSS_TRIGGERED` | `STOP_LOSS_TRIGGERED` | PASS |
| 20 | `en` | `How many customers today?` | `DETERMINISTIC_CUSTOMERS_TODAY` | `DETERMINISTIC_CUSTOMERS_TODAY` | PASS |
| 21 | `en` | `What is my profit?` | `DETERMINISTIC_PROFIT` | `DETERMINISTIC_PROFIT` | PASS |
| 22 | `en` | `How many repeat customers?` | `DETERMINISTIC_REPEAT_OR_TOTAL_CUSTOMERS` | `DETERMINISTIC_REPEAT_OR_TOTAL_CUSTOMERS` | PASS |
| 23 | `en` | `Why these 40 customers?` | `MERCHANT_QA_WHY_40` | `MERCHANT_QA_WHY_40` | PASS |
| 24 | `kn` | `ಸಹಾಯ` | `VOICE_HELP` | `VOICE_HELP` | PASS |

## 4. Scope & Honest Interpretation Note

- Latency in keyless deterministic mode is sub-`15 ms` (`p50 < 5 ms`, `p95 < 15 ms`) on local SQLite.
- Live network calls to Sarvam (`saaras:v4`, `bulbul:v3` / `bulbul:v4-flash`, `sarvam-105b-conversations`) and Groq (`openai/gpt-oss-20b`, `whisper-large-v3-turbo`) depend on external API RTT (`~350 ms` to `1,800 ms`) and remain gated behind `verify_grounded_numbers` and `assert_zero_pii`.
- Standard Soundbox hardware note: to our knowledge the standard Paytm Soundbox is speaker-based with no microphone; this is to be validated with Paytm.
