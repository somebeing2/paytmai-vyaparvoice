"""
Grounded Store Q&A & Chat Router (Sarvam Primary -> Groq Secondary -> Static Templates Tertiary).

Design guarantees:
1. Primary LLM: Sarvam (`sarvam-105b-conversations` on POST /v1/chat/completions with `api-subscription-key`)
   when `SARVAM_API_KEY` is set and within call/credit caps.
2. Secondary LLM: Groq (`openai/gpt-oss-20b` on POST /chat/completions with `Authorization: Bearer`)
   when `GROQ_API_KEY` is set.
3. Tertiary: Deterministic SQLite templates in English (`en`), Hindi (`hi`), and Kannada (`kn`).
4. Zero secrets in code/logs; zero PII outbound (`assert_zero_pii`); strict numeric grounding
   (`verify_grounded_numbers` across ASCII, Devanagari, and Kannada digits) + merchant copy-lint
   on every model output. Numbers are never produced or altered by any model.
"""
from dataclasses import dataclass, field
import json
import re
from typing import Any, Dict, List, Optional, Set
import httpx

from ..config import Settings, get_settings
from ..copy_lint import assert_valid_merchant_copy, lint_merchant_copy
from ..security import assert_paid_calls_permitted, get_current_request_session, is_session_demo_unlocked
from .persistent_cache import PersistentProviderCache
from .sarvam import SarvamProvider, SarvamProviderError, set_fallback_notice

PII_PATTERNS = [
    re.compile(r"\bCUST-[A-Za-z0-9_-]+\b", re.IGNORECASE),
    re.compile(r"\bpayer_hash\b", re.IGNORECASE),
    re.compile(r"\b[0-9a-f]{32,64}\b", re.IGNORECASE),
    re.compile(r"(?:\+91[\-\s]?)?[6-9]\d{9}\b"),
]

ALLOWED_CONTEXT_CONSTANTS = {
    0.0, 1.0, 2.0, 3.0, 5.0, 6.0, 8.0, 12.0, 14.0, 16.0, 18.0,
    20.0, 22.0, 24.0, 25.0, 30.0, 32.0, 38.0, 40.0, 48.0, 70.0, 80.0, 100.0,
}

INDIC_DIGIT_MAP = str.maketrans(
    "०१२३४५६७८९೦೧೨೩೪೫೬೭೮೯",
    "01234567890123456789",
)
NUMBER_TOKEN_RE = re.compile(r"(?<![A-Za-z])(\d[\d,]*(?:\.\d+)?)(?![A-Za-z])")


@dataclass
class GroqQAResult:
    question: str
    answer: str
    mode: str  # "sarvam_grounded" | "groq_grounded" | "deterministic_fallback"
    provider: str  # "sarvam" | "groq" | "deterministic_sqlite"
    grounded_verified: bool
    cached: bool = False
    fallback_reason: Optional[str] = None
    ungrounded_numbers: List[str] = field(default_factory=list)
    lint_violations: List[str] = field(default_factory=list)


def assert_zero_pii(payload_json: str) -> None:
    """Verify no customer identifiers, hashes, or phone numbers appear in outbound payload."""
    for pat in PII_PATTERNS:
        m = pat.search(payload_json)
        if m:
            raise ValueError(f"Outbound PII / identifier guard blocked payload matching '{m.group(0)}'.")


def extract_allowed_numbers(store_facts: Dict[str, Any]) -> Set[float]:
    """Collect all numeric values (and rounded integer equivalents) from sanitized store facts."""
    allowed: Set[float] = set(ALLOWED_CONTEXT_CONSTANTS)

    def _walk(obj: Any) -> None:
        if isinstance(obj, bool) or obj is None:
            return
        if isinstance(obj, (int, float)):
            fval = float(obj)
            allowed.add(round(fval, 4))
            allowed.add(float(round(fval)))
            allowed.add(float(int(fval)))
        elif isinstance(obj, dict):
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, (list, tuple)):
            for item in obj:
                _walk(item)

    _walk(store_facts)
    return allowed


def verify_grounded_numbers(draft_text: str, allowed_numbers: Set[float]) -> List[str]:
    """Return any numeric token in draft_text (including Indic digits) not matching SQLite facts."""
    normalized = draft_text.translate(INDIC_DIGIT_MAP)
    ungrounded: List[str] = []
    for match in NUMBER_TOKEN_RE.finditer(normalized):
        raw_tok = match.group(1)
        clean_tok = raw_tok.replace(",", "")
        try:
            val = float(clean_tok)
        except ValueError:
            continue
        matched = any(abs(val - a) < 1e-3 for a in allowed_numbers)
        if not matched:
            ungrounded.append(raw_tok)
    return ungrounded


def render_deterministic_voice_intent(
    intent_key: str, store_facts: Dict[str, Any], lang: str = "en"
) -> str:
    """
    Task E & C.3: Keyless deterministic answers in English, Hindi, and Kannada for:
      - customers_today (explicitly defining 'today' as latest day in synthetic ledger)
      - profit (stating the 30% gross margin and 5% fee assumptions in plain words)
      - repeat_or_total_customers
      - sales_summary / why_40 / max_loss / after_cap
    """
    lg = "hi" if str(lang).startswith("hi") else ("kn" if str(lang).startswith("kn") else "en")
    date_en = str(store_facts.get("latest_date_en", "")).strip()
    date_hi = str(store_facts.get("latest_date_hi", "")).strip()
    date_kn = str(store_facts.get("latest_date_kn", "")).strip()
    if not date_en:
        raw_iso = str(store_facts.get("latest_ledger_date", ""))
        date_en = raw_iso
        date_hi = raw_iso
        date_kn = raw_iso

    today_custs = int(store_facts.get("today_customers", 9))
    today_txns = int(store_facts.get("today_txns", 9))
    today_gmv = int(store_facts.get("today_gmv", 1750))
    total_custs = int(store_facts.get("total_customers", 240))
    repeat_custs = int(store_facts.get("repeat_customers", 175))
    margin_pct = int(round(float(store_facts.get("assumed_margin_pct", 30))))
    fee_pct = int(round(float(store_facts.get("assumed_fee_pct", 5))))
    profit_state = str(store_facts.get("profit_state", "NO_OFFER_RUN_YET"))
    pre_fee = float(store_facts.get("net_profit_pre_fee_inr", 0.0))
    post_fee = float(store_facts.get("net_profit_post_fee_inr", 0.0))
    spent_inr = int(store_facts.get("total_cashback_spent_inr", store_facts.get("budget_spent", 0)))
    extra_sales = int(store_facts.get("incremental_sales", 0))
    gross_prof = float(store_facts.get("gross_profit_inr", round(extra_sales * (margin_pct / 100.0), 2)))
    txn_30d = int(store_facts.get("txn_count_30d", 917))
    gmv_30d = int(round(float(store_facts.get("gmv_30d", 174685))))
    avg_bill = float(store_facts.get("avg_ticket", 190.0))
    cap_inr = int(store_facts.get("max_budget", 300))
    offer_inr = int(store_facts.get("offer_rupees", 25))
    max_paid = cap_inr // max(1, offer_inr)

    if intent_key == "customers_today":
        if lg == "hi":
            return (
                f"यह संख्या {date_hi}, नमूना डेटा के सबसे नए दिन से संबंधित है, आज की वास्तविक तारीख से नहीं: "
                f"उस दिन {today_custs} ग्राहकों ने {today_txns} QR भुगतान किए जिनसे कुल {today_gmv} रुपये मिले।"
            )
        if lg == "kn":
            return (
                f"ಈ ಸಂಖ್ಯೆಯು {date_kn}, ಮಾದರಿ ಡೇಟಾದ ಕೊನೆಯ ದಿನಕ್ಕೆ ಸಂಬಂಧಿಸಿದೆ, ಇಂದಿನ ನಿಜವಾದ ದಿನಾಂಕಕ್ಕಲ್ಲ: "
                f"ಆ ದಿನ {today_custs} ಗ್ರಾಹಕರು {today_txns} QR ಪೇಮೆಂಟ್ ಮೂಲಕ ಒಟ್ಟು {today_gmv} ರೂಪಾಯಿ ಪಾವತಿಸಿದ್ದಾರೆ."
            )
        return (
            f"This count refers to {date_en}, the latest day in the sample data, not the live calendar date: "
            f"{today_custs} unique customers made {today_txns} QR payments worth {today_gmv} rupees."
        )

    if intent_key == "profit":
        pre_disp = int(round(pre_fee)) if abs(pre_fee - round(pre_fee)) < 0.05 else round(pre_fee, 2)
        post_disp = int(round(post_fee)) if abs(post_fee - round(post_fee)) < 0.05 else round(post_fee, 2)
        gp_disp = int(round(gross_prof)) if abs(gross_prof - round(gross_prof)) < 0.05 else round(gross_prof, 2)
        if profit_state == "NO_OFFER_RUN_YET":
            if lg == "hi":
                return (
                    f"अभी कोई ऑफर नहीं चला है, इसलिए {fee_pct} प्रतिशत Paytm प्रोमो शुल्क से पहले और बाद में अनुमानित लाभ 0 रुपये है (0 रुपये खर्च)। "
                    f"ऑफर चलने पर हम हर 100 रुपये की अतिरिक्त बिक्री पर {margin_pct} रुपये दुकान मार्जिन मानकर कैशबैक और {fee_pct} प्रतिशत प्रोमो शुल्क घटाते हैं।"
                )
            if lg == "kn":
                return (
                    f"ಇನ್ನೂ ಯಾವುದೇ ಆಫರ್ ನಡೆದಿಲ್ಲದ ಕಾರಣ ಶೇಕಡಾ {fee_pct} Paytm ಪ್ರೊಮೊ ಶುಲ್ಕಕ್ಕೆ ಮುನ್ನ ಮತ್ತು ನಂತರ ಅಂದಾಜು ಲಾಭ 0 ರೂಪಾಯಿ ಇದೆ (0 ರೂಪಾಯಿ ಖರ್ಚು). "
                    f"ಆಫರ್ ನಡೆದಾಗ ಪ್ರತಿ 100 ರೂಪಾಯಿ ಹೆಚ್ಚುವರಿ ಮಾರಾಟದಲ್ಲಿ {margin_pct} ರೂಪಾಯಿ ಮಾರ್ಜಿನ್ ಹಿಡಿದು ಕ್ಯಾಶ್‌ಬ್ಯಾಕ್ ಮತ್ತು ಶೇಕಡಾ {fee_pct} ಶುಲ್ಕ ಕಳೆಯಲಾಗುತ್ತದೆ."
                )
            return (
                f"No offer has run yet, so estimated profit is 0 rupees both before and after the {fee_pct} percent Paytm promo fee (0 rupees spent). "
                f"When an offer runs, we assume {margin_pct} rupees shop margin per 100 rupees of extra sales and report profit before and after the {fee_pct} percent Paytm promo fee."
            )
        if lg == "hi":
            return (
                f"हर 100 रुपये की अतिरिक्त बिक्री पर {margin_pct} रुपये मार्जिन मानकर ({extra_sales} रुपये अतिरिक्त बिक्री से {gp_disp} रुपये मार्जिन घटाव {spent_inr} रुपये कैशबैक), {fee_pct} प्रतिशत Paytm प्रोमो शुल्क से पहले लाभ {pre_disp} रुपये है "
                f"और {fee_pct} प्रतिशत प्रोमो शुल्क घटाने के बाद लाभ {post_disp} रुपये है।"
            )
        if lg == "kn":
            return (
                f"ಪ್ರತಿ 100 ರೂಪಾಯಿ ಹೆಚ್ಚುವರಿ ಮಾರಾಟದಲ್ಲಿ {margin_pct} ರೂಪಾಯಿ ಮಾರ್ಜಿನ್ ಅಂದಾಜಿನ ಮೇಲೆ ({extra_sales} ರೂಪಾಯಿ ಹೆಚ್ಚುವರಿ ಮಾರಾಟದಿಂದ {gp_disp} ರೂಪಾಯಿ ಮಾರ್ಜಿನ್ ಕಳೆಯಿರಿ {spent_inr} ರೂಪಾಯಿ ಕ್ಯಾಶ್‌ಬ್ಯಾಕ್), ಶೇಕಡಾ {fee_pct} Paytm ಪ್ರೊಮೊ ಶುಲ್ಕಕ್ಕೆ ಮುನ್ನ ಲಾಭ {pre_disp} ರೂಪಾಯಿ "
                f"ಮತ್ತು ಶೇಕಡಾ {fee_pct} ಪ್ರೊಮೊ ಶುಲ್ಕದ ನಂತರ ಲಾಭ {post_disp} ರೂಪಾಯಿ ಆಗಿದೆ."
            )
        return (
            f"At {margin_pct} rupees shop margin per 100 rupees of extra sales, {extra_sales} rupees extra sales minus {spent_inr} rupees cashback gives {pre_disp} rupees before the {fee_pct} percent Paytm promo fee. "
            f"After subtracting that {fee_pct} percent Paytm promo fee on redeemed bills, estimated profit is {post_disp} rupees."
        )

    if intent_key == "repeat_or_total_customers":
        one_time = max(0, total_custs - repeat_custs)
        if lg == "hi":
            return (
                f"पिछले 60 दिनों के सिंथेटिक खाते में आपकी दुकान के कुल {total_custs} ग्राहक हैं। "
                f"इनमें से {repeat_custs} नियमित ग्राहक हैं जो 3 या अधिक बार आए हैं, और {one_time} नए या कभी-कभार आने वाले ग्राहक हैं।"
            )
        if lg == "kn":
            return (
                f"ಕಳೆದ 60 ದಿನಗಳ ಸಿಂಥೆಟಿಕ್ ಲೆಡ್ಜರ್‌ನಲ್ಲಿ ನಿಮ್ಮ ಅಂಗಡಿಗೆ ಒಟ್ಟು {total_custs} ಗ್ರಾಹಕರಿದ್ದಾರೆ. "
                f"ಇವರಲ್ಲಿ {repeat_custs} ಮಂದಿ 3 ಅಥವಾ ಹೆಚ್ಚು ಬಾರಿ ಬಂದ ಖಾಯಂ ಗ್ರಾಹಕರು ಮತ್ತು {one_time} ಮಂದಿ ಹೊಸ ಅಥವಾ ಸಾಂದರ್ಭಿಕ ಗ್ರಾಹಕರು."
            )
        return (
            f"Across the 60 day synthetic ledger, your shop has {total_custs} total unique customers. "
            f"Out of those {total_custs} buyers, {repeat_custs} are repeat customers with 3 or more visits and {one_time} visited once or twice."
        )

    if intent_key == "sales_summary":
        if lg == "hi":
            return (
                f"पिछले 30 दिनों में आपकी दुकान में {txn_30d} QR भुगतान से कुल {gmv_30d} रुपये आए। "
                f"ग्राहकों का औसत बिल {avg_bill:.1f} रुपये रहा।"
            )
        if lg == "kn":
            return (
                f"ಕಳೆದ 30 ದಿನಗಳಲ್ಲಿ ನಿಮ್ಮ ಅಂಗಡಿಯಲ್ಲಿ {txn_30d} QR ಪೇಮೆಂಟ್ ಮೂಲಕ ಒಟ್ಟು {gmv_30d} ರೂಪಾಯಿ ಬಂದಿದೆ. "
                f"ಗ್ರಾಹಕರ ಸರಾಸರಿ ಬಿಲ್ {avg_bill:.1f} ರೂಪಾಯಿ ಆಗಿದೆ."
            )
        return (
            f"In the last 30 days, your shop recorded {txn_30d} Paytm QR payments worth {gmv_30d} rupees. "
            f"Your average customer bill is {avg_bill:.1f} rupees."
        )

    if intent_key == "why_40":
        if lg == "hi":
            return (
                "48 शांत नियमित ग्राहकों में से 5 ने प्रचार संदेश की अनुमति नहीं दी और 3 को पिछले 14 दिनों में संदेश जा चुका है। "
                "इसलिए आज रात 40 सुरक्षित ग्राहक चुने गए हैं।"
            )
        if lg == "kn":
            return (
                "48 ಖಾಯಂ ಗ್ರಾಹಕರಲ್ಲಿ 5 ಮಂದಿ ಆಫರ್ ಸಂದೇಶಕ್ಕೆ ಒಪ್ಪಿಗೆ ನೀಡಿಲ್ಲ ಮತ್ತು 3 ಮಂದಿಗೆ ಕಳೆದ 14 ದಿನಗಳಲ್ಲಿ ಸಂದೇಶ ಹೋಗಿದೆ. "
                "ಹಾಗಾಗಿ ಇಂದು ರಾತ್ರಿ 40 ಅರ್ಹ ಗ್ರಾಹಕರನ್ನು ಮಾತ್ರ ಸೇರಿಸಲಾಗಿದೆ."
            )
        return (
            "Out of 48 regular evening buyers silent for 16 to 38 days, 5 did not agree to shop offers and 3 received a message within 14 days. "
            "That leaves 40 buyers safe to include tonight."
        )

    if intent_key == "max_loss":
        if lg == "hi":
            return (
                f"नहीं, आपका कैशबैक खर्च {cap_inr} रुपये से ऊपर नहीं जा सकता। "
                f"{max_paid} बिल पूरे होते ही स्वचालित रोक लग जाती है।"
            )
        if lg == "kn":
            return (
                f"ಇಲ್ಲ, ನಿಮ್ಮ ಕ್ಯಾಶ್‌ಬ್ಯಾಕ್ ಖರ್ಚು {cap_inr} ರೂಪಾಯಿ ಮೀರಲು ಸಾಧ್ಯವಿಲ್ಲ. "
                f"{max_paid} ಬಿಲ್ ಪೂರ್ಣಗೊಂಡ ತಕ್ಷಣ ಸ್ವಯಂಚಾಲಿತವಾಗಿ ನಿಲ್ಲುತ್ತದೆ."
            )
        return (
            f"No, your cashback payout cannot cross {cap_inr} rupees. "
            f"Automatic payout stops strictly after {max_paid} paid bills at {offer_inr} rupees each."
        )

    if intent_key == "after_cap":
        if lg == "hi":
            return (
                f"जब {cap_inr} रुपये की सीमा पूरी हो जाती है तो ऑफर अपने आप रुक जाता है और आपको तुरंत संदेश मिलता है। "
                "बाद में आने वाले ग्राहक सामान्य बिल चुकाते हैं।"
            )
        if lg == "kn":
            return (
                f"{cap_inr} ರೂಪಾಯಿ ಮಿತಿ ತಲುಪಿದ ತಕ್ಷಣ ಆಫರ್ ತಾನಾಗಿಯೇ ನಿಲ್ಲುತ್ತದೆ ಮತ್ತು ನಿಮಗೆ ಸೂಚನೆ ಬರುತ್ತದೆ. "
                "ನಂತರ ಬಂದ ಗ್ರಾಹಕರು ಸಾಮಾನ್ಯ ಬಿಲ್ ಪಾವತಿಸುತ್ತಾರೆ."
            )
        return (
            f"Once {cap_inr} rupees is reached, the offer pauses automatically and alerts you right away. "
            "Any later buyer pays normal price with zero extra cashback charged to you."
        )

    return build_deterministic_store_answer("", store_facts, lang=lg)


def detect_common_qa_intent(question: str) -> Optional[str]:
    """
    Task C.3 & E: Match common questions deterministically before touching any LLM.
    Carefully scoped so open-ended phrasing (e.g. 'Summarize my 30 day store sales.')
    still exercises the LLM path when keys are enabled.
    """
    q = " ".join((question or "").strip().lower().split())
    if not q:
        return "sales_summary"

    # 1. Customers today (EN / HI / KN)
    if any(
        p in q
        for p in (
            "customers today",
            "customer today",
            "today's customers",
            "todays customers",
            "how many came today",
            "visitors today",
            "aaj kitne grahak",
            "aaj ke grahak",
            "आज कितने ग्राहक",
            "आज के ग्राहक",
            "आज ग्राहक",
            "ಇಂದು ಎಷ್ಟು ಗ್ರಾಹಕರು",
            "ಇಂದಿನ ಗ್ರಾಹಕರು",
            "ivattu eshtu grahakaru",
            "indu eshtu grahakaru",
        )
    ):
        return "customers_today"

    # 2. Profit (EN / HI / KN)
    if any(
        p in q
        for p in (
            "profit",
            "my profit",
            "net profit",
            "kitna munafa",
            "kitna fayda",
            "munafa",
            "मुनाफा",
            "लाभ",
            "फायदा",
            "ಲಾಭ",
            "ನಿವ್ವಳ ಲಾಭ",
            "eshtu labha",
            "labha",
        )
    ):
        return "profit"

    # 3. Repeat or total customers (EN / HI / KN)
    if any(
        p in q
        for p in (
            "repeat customer",
            "repeat buyers",
            "total customer",
            "total buyers",
            "how many customers do we have",
            "how many regulars",
            "regular customers count",
            "kul grahak",
            "niyamit grahak",
            "कुल ग्राहक",
            "नियमित ग्राहक",
            "रिपीट ग्राहक",
            "ಒಟ್ಟು ಗ್ರಾಹಕರು",
            "ಖಾಯಂ ಗ್ರಾಹಕರು",
            "ottu grahakaru",
        )
    ):
        return "repeat_or_total_customers"

    # 4. Exact short common Soundbox chips
    if q in ("sales summary", "salessummary", "बिक्री सारांश", "ಮಾರಾಟ ವಿವರ", "ಮಾರಾಟ ಸಾರಾಂಶ"):
        return "sales_summary"
    if any(p in q for p in ("why only 40", "why 40", "40 क्यों", "40 ಏಕೆ")):
        return "why_40"
    if any(p in q for p in ("maximum loss", "max loss", "अधिकतम नुकसान", "ಗರಿಷ್ಠ ನಷ್ಟ")):
        return "max_loss"
    if any(p in q for p in ("after cap", "once cap is reached", "बजट पूरा होने पर", "ಮಿತಿ ಮುಗಿದ ಮೇಲೆ")):
        return "after_cap"

    return None


def build_deterministic_store_answer(
    question: str, store_facts: Dict[str, Any], lang: str = "en"
) -> str:
    """Deterministic SQLite-grounded fallback answer in English, Hindi, or Kannada."""
    lg = "hi" if str(lang).startswith("hi") else ("kn" if str(lang).startswith("kn") else "en")
    matched = detect_common_qa_intent(question)
    if matched is not None:
        ans = render_deterministic_voice_intent(matched, store_facts, lang=lg)
        return assert_valid_merchant_copy(ans, check_sentence_length=(lg == "en"))

    q = (question or "").strip().lower()
    txn_30d = int(store_facts.get("txn_count_30d", 917))
    gmv_30d = int(round(float(store_facts.get("gmv_30d", 174685))))
    avg_bill = float(store_facts.get("avg_ticket", 190.0))
    offer_inr = int(store_facts.get("offer_rupees", 25))
    min_bill = int(store_facts.get("min_bill", 150))
    cap_inr = int(store_facts.get("max_budget", 300))
    spent_inr = int(store_facts.get("budget_spent", 0))
    treat_n = int(store_facts.get("treatment_count", 32))
    ctrl_n = int(store_facts.get("holdout_count", 8))
    drop_pct = int(store_facts.get("dead_hour_drop_pct", 70))
    milk_l = int(store_facts.get("extra_milk_liters", 18))

    if any(w in q for w in ["afternoon", "slow", "3 pm", "dead", "quiet", "tea", "combo", "दोपहर", "ಮಧ್ಯಾಹ್ನ"]):
        if lg == "hi":
            ans = (
                f"दोपहर 3 बजे से 5 बजे के बीच दुकान के QR भुगतान व्यस्त समय से {drop_pct} प्रतिशत कम हो जाते हैं। "
                f"आप अपने बजट के भीतर दोपहर कॉफी कॉम्बो आज़मा सकते हैं।"
            )
        elif lg == "kn":
            ans = (
                f"ಮಧ್ಯಾಹ್ನ 3 ರಿಂದ 5 ಗಂಟೆಯ ನಡುವೆ QR ಪೇಮೆಂಟ್‌ಗಳು ರಶ್ ಸಮಯಕ್ಕಿಂತ ಶೇಕಡಾ {drop_pct} ಕಡಿಮೆಯಾಗುತ್ತವೆ. "
                f"ನಿಮ್ಮ ಬಜೆಟ್ ಒಳಗೆ ಮಧ್ಯಾಹ್ನ ಕಾಫಿ ಕಾಂಬೊ ಆಫರ್ ಪರೀಕ್ಷಿಸಬಹುದು."
            )
        else:
            ans = (
                f"Between 3 PM and 5 PM, shop QR scans drop {drop_pct} percent below peak hour. "
                f"You can test an afternoon filter-coffee combo for regular buyers within your spending limit."
            )
    elif any(w in q for w in ["sales", "revenue", "gmv", "average bill", "ticket", "many payment", "transactions", "बिक्री", "ಮಾರಾಟ"]):
        ans = render_deterministic_voice_intent("sales_summary", store_facts, lang=lg)
    elif any(w in q for w in ["spent", "remaining", "budget", "limit", "cap", "बजट", "ಬಜೆಟ್", "ಮಿತಿ"]):
        rem = max(0, cap_inr - spent_inr)
        if lg == "hi":
            ans = (
                f"आपकी वर्तमान कैशबैक सीमा {cap_inr} रुपये है, जिसमें {spent_inr} रुपये खर्च हुए और {rem} रुपये बाकी हैं। "
                f"{cap_inr} रुपये पूरे होते ही कैशबैक अपने आप रुक जाता है।"
            )
        elif lg == "kn":
            ans = (
                f"ನಿಮ್ಮ ಪ್ರಸ್ತುತ ಕ್ಯಾಶ್‌ಬ್ಯಾಕ್ ಮಿತಿ {cap_inr} ರೂಪಾಯಿ ಆಗಿದ್ದು, {spent_inr} ರೂಪಾಯಿ ಬಳಕೆಯಾಗಿದೆ ಮತ್ತು {rem} ರೂಪಾಯಿ ಉಳಿದಿದೆ. "
                f"{cap_inr} ರೂಪಾಯಿ ತಲುಪಿದ ತಕ್ಷಣ ಕ್ಯಾಶ್‌ಬ್ಯಾಕ್ ತಾನಾಗಿಯೇ ನಿಲ್ಲುತ್ತದೆ."
            )
        else:
            ans = (
                f"Your current cashback limit is {cap_inr} rupees, with {spent_inr} rupees spent and {rem} rupees remaining. "
                f"Cashback stops automatically once {cap_inr} rupees is reached."
            )
    elif any(w in q for w in ["milk", "batter", "morning", "saturday", "stock", "dairy", "दूध", "ಹಾಲು", "ಹಿಟ್ಟು"]):
        if lg == "hi":
            ans = (
                f"शनिवार सुबह भीड़ सामान्य दिनों से अधिक रहती है। "
                f"आज रात {milk_l} लीटर अतिरिक्त दूध और 12 किलो बैटर मंगवाने से सुबह कमी नहीं होगी।"
            )
        elif lg == "kn":
            ans = (
                f"ಶನಿವಾರ ಬೆಳಿಗ್ಗೆ ಗ್ರಾಹಕರ ದಟ್ಟಣೆ ಸಾಮಾನ್ಯ ದಿನಗಳಿಗಿಂತ ಹೆಚ್ಚಿರುತ್ತದೆ. "
                f"ಇಂದು ರಾತ್ರಿ {milk_l} ಲೀಟರ್ ಹೆಚ್ಚುವರಿ ಹಾಲು ಮತ್ತು 12 ಕಿ.ಗ್ರಾಂ ಹಿಟ್ಟು ತರಿಸಿದರೆ ಬೆಳಿಗ್ಗೆ ಕೊರತೆಯಾಗುವುದಿಲ್ಲ."
            )
        else:
            ans = (
                f"Saturday morning traffic runs higher than normal weekdays. "
                f"Ordering {milk_l} liters extra milk and 12 kg batter by tonight prevents early stockouts."
            )
    else:
        if lg == "hi":
            ans = (
                f"पिछले 30 दिनों में श्री कृष्णा दर्शिनी में {txn_30d} QR भुगतान से {gmv_30d} रुपये आए। "
                f"आज रात आप {cap_inr} रुपये की सीमा में {treat_n} ग्राहकों को {min_bill} रुपये बिल पर {offer_inr} रुपये ऑफर भेज सकते हैं और {ctrl_n} को तुलना हेतु अलग रख सकते हैं।"
            )
        elif lg == "kn":
            ans = (
                f"ಕಳೆದ 30 ದಿನಗಳಲ್ಲಿ ಶ್ರೀ ಕೃಷ್ಣ ದರ್ಶಿನಿಯಲ್ಲಿ {txn_30d} QR ಪೇಮೆಂಟ್ ಮೂಲಕ {gmv_30d} ರೂಪಾಯಿ ಬಂದಿದೆ. "
                f"ಇಂದು ರಾತ್ರಿ {cap_inr} ರೂಪಾಯಿ ಮಿತಿಯಲ್ಲಿ {treat_n} ಗ್ರಾಹಕರಿಗೆ {min_bill} ರೂಪಾಯಿ ಬಿಲ್ ಮೇಲೆ {offer_inr} ರೂಪಾಯಿ ಆಫರ್ ಕಳುಹಿಸಿ {ctrl_n} ಮಂದಿಯನ್ನು ಹೋಲಿಕೆಗೆ ಇಡಬಹುದು."
            )
        else:
            ans = (
                f"In the last 30 days, Sri Krishna Darshini recorded {txn_30d} QR payments worth {gmv_30d} rupees. "
                f"Tonight you can send {treat_n} silent regulars a {offer_inr} rupee offer on {min_bill} rupee bills "
                f"within a {cap_inr} rupee limit while keeping {ctrl_n} aside."
            )
    return assert_valid_merchant_copy(ans, check_sentence_length=(lg == "en"))


class GroqGroundedQA:
    """
    Unified Grounded Store Q&A Router:
      1. Common deterministic intents (0 API calls).
      2. Primary LLM: Sarvam (`sarvam-105b-conversations`) across EN/HI/KN + persistent cache.
      3. Secondary LLM: Groq (`openai/gpt-oss-20b` / `GROQ_MODEL`) across EN/HI/KN + persistent cache.
      4. Tertiary: Deterministic SQLite templates across EN/HI/KN.
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.persistent_cache = PersistentProviderCache(
            self.settings.provider_cache_db_path,
            prewarmed_dir=self.settings.prewarmed_assets_dir,
        )
        self._calls_made: int = 0
        self._circuit_open: bool = False
        self._circuit_reason: Optional[str] = None

    def status_dict(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        unlocked = is_session_demo_unlocked(session_id)
        return {
            "groq_enabled": self.settings.groq_enabled,
            "public_deploy": self.settings.public_deploy,
            "demo_unlocked": unlocked,
            "api_key_configured": len(self.settings.groq_api_key.strip()) > 0,
            "live_allowed": self.settings.is_groq_live_allowed(demo_unlocked=unlocked) and not self._circuit_open,
            "model": self.settings.groq_model,
            "calls_made": self._calls_made,
            "max_calls_per_session": self.settings.groq_max_calls_per_session,
            "circuit_open": self._circuit_open,
            "circuit_reason": self._circuit_reason,
        }

    def _validate_candidate(
        self,
        raw_draft: str,
        allowed_nums: Set[float],
        fallback_ans: str,
        question: str,
        lg: str,
    ) -> GroqQAResult:
        cleaned = raw_draft.replace("\u2014", ",").replace("\u2013", " to ").strip()
        ungrounded = verify_grounded_numbers(cleaned, allowed_nums)
        if ungrounded:
            return GroqQAResult(
                question=question,
                answer=fallback_ans,
                mode="deterministic_fallback",
                provider="deterministic_sqlite",
                grounded_verified=False,
                fallback_reason=f"Rejected ungrounded LLM numbers: {ungrounded}",
                ungrounded_numbers=ungrounded,
            )

        lint_res = lint_merchant_copy(cleaned, check_sentence_length=(lg == "en"), max_words_per_sentence=26)
        violations = list(lint_res.get("issues", []))  # type: ignore[arg-type]
        if violations:
            return GroqQAResult(
                question=question,
                answer=fallback_ans,
                mode="deterministic_fallback",
                provider="deterministic_sqlite",
                grounded_verified=False,
                fallback_reason=f"Rejected LLM copy-lint violations: {violations}",
                lint_violations=violations,
            )

        return GroqQAResult(
            question=question,
            answer=cleaned,
            mode="validated",
            provider="validated",
            grounded_verified=True,
        )

    def answer_question(
        self,
        question: str,
        store_facts: Dict[str, Any],
        lang: str = "en",
        session_id: Optional[str] = None,
    ) -> GroqQAResult:
        norm_lang = (lang or "en").strip().lower()
        lg = "hi" if norm_lang.startswith("hi") else ("kn" if norm_lang.startswith("kn") else "en")
        lang_code = "hi-IN" if lg == "hi" else ("kn-IN" if lg == "kn" else "en-IN")
        lang_label = "Hindi" if lg == "hi" else ("Kannada" if lg == "kn" else "Indian English")
        fallback_ans = build_deterministic_store_answer(question, store_facts, lang=lg)

        # 1. Task C.3 & E: Route common questions through deterministic intents first (0 API calls)
        matched_intent = detect_common_qa_intent(question)
        if matched_intent is not None:
            return GroqQAResult(
                question=question,
                answer=fallback_ans,
                mode="deterministic_fallback",
                provider="deterministic_sqlite",
                grounded_verified=True,
                fallback_reason=f"Matched deterministic intent '{matched_intent}' (0 API calls).",
            )

        sid = session_id if session_id is not None else get_current_request_session()
        unlocked = is_session_demo_unlocked(sid)

        # Compact facts payload (minimum tokens needed, strictly zero PII)
        facts_json = json.dumps(store_facts, sort_keys=True, separators=(",", ":"))
        assert_zero_pii(facts_json)
        assert_zero_pii(question)
        allowed_nums = extract_allowed_numbers(store_facts)

        sys_prompt = (
            f"You are VyaparVoice, a closing-time shop assistant. Reply in {lang_label} in at most 2 short sentences "
            "(<= 22 words per sentence). Copy ONLY exact numbers from FACTS. Never invent or alter numbers. "
            "No dashes, no emojis, no statistical jargon (forbidden: cohort, holdout, p-value, Fisher, Wilson, "
            "confidence interval, uplift, incremental, ROI, ROAS, ARPU, DPDP, ITT, RFM). Read-only.\n"
            f"FACTS:{facts_json}"
        )
        q_trim = question.strip()[:240]
        cache_key_payload = f"{lg}|{q_trim}|{facts_json}"
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": q_trim},
        ]

        # 2. Enforce PUBLIC_DEPLOY paid/external API lock (still serve cached LLM answers if already cached!)
        sarvam_cached = self.persistent_cache.get_llm(
            "sarvam", lang_code, self.settings.sarvam_chat_model, cache_key_payload
        )
        if sarvam_cached is not None:
            val_res = self._validate_candidate(sarvam_cached, allowed_nums, fallback_ans, question, lg)
            if val_res.grounded_verified:
                val_res.mode = "sarvam_grounded"
                val_res.provider = "sarvam"
                val_res.cached = True
                return val_res

        groq_cached = self.persistent_cache.get_llm(
            "groq", lang_code, self.settings.groq_model, cache_key_payload
        )
        if groq_cached is not None:
            val_res = self._validate_candidate(groq_cached, allowed_nums, fallback_ans, question, lg)
            if val_res.grounded_verified:
                val_res.mode = "groq_grounded"
                val_res.provider = "groq"
                val_res.cached = True
                return val_res

        try:
            assert_paid_calls_permitted("live LLM", demo_unlocked=unlocked)
        except PermissionError as exc:
            return GroqQAResult(
                question=question,
                answer=fallback_ans,
                mode="deterministic_fallback",
                provider="deterministic_sqlite",
                grounded_verified=True,
                fallback_reason=str(exc),
            )

        sarvam_fail_note: Optional[str] = None

        # 3. PRIMARY PROVIDER: Sarvam (`sarvam-105b-conversations` on /v1/chat/completions)
        if self.settings.is_sarvam_live_allowed(demo_unlocked=unlocked) and self.settings.llm_provider in ("auto", "sarvam"):
            sarvam_client = SarvamProvider(settings=self.settings, persistent_cache=self.persistent_cache)
            try:
                s_draft, s_was_cached = sarvam_client.chat_complete(
                    messages=messages,
                    lang_code=lang_code,
                    cache_key_text=cache_key_payload,
                    max_tokens=110,
                    session_id=sid,
                )
                s_val = self._validate_candidate(s_draft, allowed_nums, fallback_ans, question, lg)
                if s_val.grounded_verified:
                    s_val.mode = "sarvam_grounded"
                    s_val.provider = "sarvam_cached" if s_was_cached else "sarvam"
                    s_val.cached = s_was_cached
                    return s_val
                # Grounding or lint rejection from Sarvam: record notice and try Groq if configured, else return rejection details
                sarvam_fail_note = s_val.fallback_reason or "Sarvam completion failed numeric/lint gate."
                set_fallback_notice(f"Sarvam Chat output rejected by grounding gate; switched to fallback.")
                if not self.settings.is_groq_live_allowed(demo_unlocked=unlocked):
                    return s_val
            except SarvamProviderError as exc:
                sarvam_fail_note = str(exc)

        # 4. SECONDARY PROVIDER: Groq (`/chat/completions`)
        if not self.settings.is_groq_live_allowed(demo_unlocked=unlocked):
            reason_out = sarvam_fail_note or "Live LLM disabled (set SARVAM_API_KEY or GROQ_API_KEY in .env)."
            return GroqQAResult(
                question=question,
                answer=fallback_ans,
                mode="deterministic_fallback",
                provider="deterministic_sqlite",
                grounded_verified=True,
                fallback_reason=reason_out,
            )

        if self._circuit_open:
            return GroqQAResult(
                question=question,
                answer=fallback_ans,
                mode="deterministic_fallback",
                provider="deterministic_sqlite",
                grounded_verified=True,
                fallback_reason=f"Groq circuit breaker open: {self._circuit_reason}",
            )

        if self._calls_made >= self.settings.groq_max_calls_per_session:
            return GroqQAResult(
                question=question,
                answer=fallback_ans,
                mode="deterministic_fallback",
                provider="deterministic_sqlite",
                grounded_verified=True,
                fallback_reason=f"Session Groq call limit ({self.settings.groq_max_calls_per_session}) reached.",
            )

        req_body = {
            "model": self.settings.groq_model,
            "temperature": 0.0,
            "max_tokens": 110,
            "messages": messages,
        }
        headers = {
            "Authorization": f"Bearer {self.settings.groq_api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.settings.groq_base_url}/chat/completions"

        try:
            self._calls_made += 1
            with httpx.Client(timeout=self.settings.groq_timeout_seconds) as client:
                resp = client.post(url, json=req_body, headers=headers)
            if resp.status_code in (401, 402, 403, 429) or resp.status_code >= 500:
                self._circuit_open = True
                self._circuit_reason = f"HTTP {resp.status_code}"
                return GroqQAResult(
                    question=question,
                    answer=fallback_ans,
                    mode="deterministic_fallback",
                    provider="deterministic_sqlite",
                    grounded_verified=True,
                    fallback_reason=f"Groq HTTP {resp.status_code} tripped fail-closed circuit breaker.",
                )
            resp.raise_for_status()
            data = resp.json()
            raw_draft = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )
        except Exception as exc:
            self._circuit_open = True
            self._circuit_reason = type(exc).__name__
            return GroqQAResult(
                question=question,
                answer=fallback_ans,
                mode="deterministic_fallback",
                provider="deterministic_sqlite",
                grounded_verified=True,
                fallback_reason=f"Groq network/parse error ({type(exc).__name__}); served deterministic SQLite answer.",
            )

        if not raw_draft:
            return GroqQAResult(
                question=question,
                answer=fallback_ans,
                mode="deterministic_fallback",
                provider="deterministic_sqlite",
                grounded_verified=True,
                fallback_reason="Empty Groq completion; served deterministic SQLite answer.",
            )

        g_val = self._validate_candidate(raw_draft, allowed_nums, fallback_ans, question, lg)
        if not g_val.grounded_verified:
            return g_val

        self.persistent_cache.put_llm("groq", lang_code, self.settings.groq_model, cache_key_payload, g_val.answer)
        g_val.mode = "groq_grounded"
        g_val.provider = "groq"
        g_val.fallback_reason = sarvam_fail_note
        return g_val


_GROQ_SINGLETON: Optional[GroqGroundedQA] = None


def get_groq_qa(reset: bool = False) -> GroqGroundedQA:
    global _GROQ_SINGLETON
    if _GROQ_SINGLETON is None or reset:
        _GROQ_SINGLETON = GroqGroundedQA()
    return _GROQ_SINGLETON
