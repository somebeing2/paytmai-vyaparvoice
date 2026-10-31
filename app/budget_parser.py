"""
Task 3: Deterministic Multilingual Verbal Budget & Period Parser (en, hi, kn)
with strictly validated optional LLM parsing fallback (never alters numbers).
"""
import json
import re
from typing import Any, Dict, List, Optional, Tuple
import httpx

from .config import get_settings
from .copy_lint import assert_valid_merchant_copy
from .security import assert_paid_calls_permitted

# Translate Indic digits (Devanagari ०-९, Kannada ೦-೯) to ASCII 0-9
_INDIC_DIGIT_TABLE = str.maketrans(
    "०१२३४५६७८९೦೧೨೩೪೫೬೭೮೯",
    "01234567890123456789",
)

PERIOD_LABELS = {
    "today": {"en": "today", "hi": "आज", "kn": "ಇಂದು"},
    "48_hours": {"en": "48 hours", "hi": "48 घंटे", "kn": "48 ಗಂಟೆ"},
    "this_week": {"en": "this week", "hi": "इस हफ्ते", "kn": "ಈ ವಾರ"},
    "this_weekend": {"en": "this weekend", "hi": "इस वीकेंड", "kn": "ಈ ವಾರಾಂತ್ಯ"},
    "this_month": {"en": "this month", "hi": "इस महीने", "kn": "ಈ ತಿಂಗಳು"},
}

# Ordered longest-first compound phrases across English, Hindi (Devanagari + Roman), Kannada (script + Roman)
_EXACT_COMPOUND_AMOUNTS: List[Tuple[str, int]] = [
    ("two thousand five hundred", 2500),
    ("twenty five hundred", 2500),
    ("one thousand five hundred", 1500),
    ("fifteen hundred", 1500),
    ("twelve hundred", 1200),
    ("five thousand", 5000),
    ("four thousand", 4000),
    ("three thousand", 3000),
    ("two thousand", 2000),
    ("one thousand", 1000),
    ("nine hundred", 900),
    ("eight hundred", 800),
    ("seven hundred and fifty", 750),
    ("seven hundred fifty", 750),
    ("seven hundred", 700),
    ("six hundred", 600),
    ("five hundred", 500),
    ("four hundred and fifty", 450),
    ("four hundred fifty", 450),
    ("four hundred", 400),
    ("three hundred and fifty", 350),
    ("three hundred fifty", 350),
    ("three hundred", 300),
    ("two hundred and fifty", 250),
    ("two hundred fifty", 250),
    ("two hundred", 200),
    ("one hundred and fifty", 150),
    ("one hundred fifty", 150),
    ("one hundred", 100),
    ("seventy five", 75),
    ("fifty", 50),
    ("forty", 40),
    ("thirty", 30),
    ("twenty", 20),
    ("ten", 10),
    # Hindi Devanagari + Roman
    ("दो हज़ार पाँच सौ", 2500),
    ("दो हजार पांच सौ", 2500),
    ("ढाई हज़ार", 2500),
    ("ढाई हजार", 2500),
    ("dhai hazaar", 2500),
    ("dhai hazar", 2500),
    ("पाँच हज़ार", 5000),
    ("पांच हजार", 5000),
    ("panch hazaar", 5000),
    ("panch hazar", 5000),
    ("तीन हज़ार", 3000),
    ("teen hazaar", 3000),
    ("दो हज़ार", 2000),
    ("दो हजार", 2000),
    ("do hazaar", 2000),
    ("do hazar", 2000),
    ("डेढ़ हज़ार", 1500),
    ("डेढ़ हजार", 1500),
    ("पंद्रह सौ", 1500),
    ("dedh hazaar", 1500),
    ("pandrah sau", 1500),
    ("एक हज़ार", 1000),
    ("एक हजार", 1000),
    ("ek hazaar", 1000),
    ("ek hazar", 1000),
    ("हज़ार", 1000),
    ("हजार", 1000),
    ("hazaar", 1000),
    ("hazar", 1000),
    ("नौ सौ", 900),
    ("nau sau", 900),
    ("आठ सौ", 800),
    ("aath sau", 800),
    ("सात सौ", 700),
    ("saat sau", 700),
    ("छह सौ", 600),
    ("chhah sau", 600),
    ("पाँच सौ", 500),
    ("पांच सौ", 500),
    ("panch sau", 500),
    ("चार सौ", 400),
    ("char sau", 400),
    ("तीन सौ", 300),
    ("teen sau", 300),
    ("ढाई सौ", 250),
    ("dhai sau", 250),
    ("दो सौ", 200),
    ("do sau", 200),
    ("डेढ़ सौ", 150),
    ("dedh sau", 150),
    ("एक सौ", 100),
    ("ek sau", 100),
    ("पचास", 50),
    ("pachas", 50),
    ("दस", 10),
    # Kannada Script + Roman
    ("ಎರಡು ಸಾವಿರದ ಐದು ನೂರು", 2500),
    ("ಎರಡೂವರೆ ಸಾವಿರ", 2500),
    ("eradu savirada aidu nooru", 2500),
    ("ಐದು ಸಾವಿರ", 5000),
    ("aidu savira", 5000),
    ("ಮೂರು ಸಾವಿರ", 3000),
    ("mooru savira", 3000),
    ("ಎರಡು ಸಾವಿರ", 2000),
    ("eradu savira", 2000),
    ("eradu saavira", 2000),
    ("ಒಂದೂವರೆ ಸಾವಿರ", 1500),
    ("ಹದಿನೈದು ನೂರು", 1500),
    ("hadinaidu nooru", 1500),
    ("ಒಂದು ಸಾವಿರ", 1000),
    ("ondu savira", 1000),
    ("ondu saavira", 1000),
    ("ಸಾವಿರ", 1000),
    ("savira", 1000),
    ("saavira", 1000),
    ("ಒಂಬತ್ತು ನೂರು", 900),
    ("ombattu nooru", 900),
    ("ಎಂಟು ನೂರು", 800),
    ("entu nooru", 800),
    ("ಏಳು ನೂರು", 700),
    ("elu nooru", 700),
    ("ಆರು ನೂರು", 600),
    ("aaru nooru", 600),
    ("ಐದು ನೂರು", 500),
    ("ಐನೂರು", 500),
    ("aidu nooru", 500),
    ("ainooru", 500),
    ("ನಾಲ್ಕು ನೂರು", 400),
    ("ನಾನೂರು", 400),
    ("nalku nooru", 400),
    ("nanooru", 400),
    ("ಮುನ್ನೂರು", 300),
    ("ಮೂರು ನೂರು", 300),
    ("munnooru", 300),
    ("mooru nooru", 300),
    ("ಇನ್ನೂರ ಐವತ್ತು", 250),
    ("innoora aivattu", 250),
    ("ಇನ್ನೂರು", 200),
    ("ಎರಡು ನೂರು", 200),
    ("innooru", 200),
    ("eradu nooru", 200),
    ("ನೂರ ಐವತ್ತು", 150),
    ("noora aivattu", 150),
    ("ಒಂದು ನೂರು", 100),
    ("ನೂರು", 100),
    ("ondu nooru", 100),
    ("nooru", 100),
    ("ಐವತ್ತು", 50),
    ("aivattu", 50),
    ("ಹತ್ತು", 10),
    ("hattu", 10),
]

_EN_UNITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
}
_EN_TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}

BUDGET_INTENT_KEYWORDS = [
    "budget", "limit", "cap", "spending",
    "बजट", "सीमा", "खर्च", "bajat", "seema",
    "ಬಜೆಟ್", "ಮಿತಿ", "ಖರ್ಚು", "miti",
]

YES_TOKENS = {
    "yes", "confirm", "confirm limit", "confirm cap", "confirm budget", "yes confirm", "ok", "okay",
    "haan", "ha", "हाँ", "हां", "पक्का", "हाँ पक्का", "हां पक्का", "पुष्टि",
    "haudu", "ಹೌದು", "ಸರಿ", "ಖಚಿತ", "ಖಚಿತಪಡಿಸಿ", "ಹೌದು ಖಚಿತಪಡಿಸಿ",
}

NO_TOKENS = {
    "no", "cancel", "cancel limit", "cancel cap", "cancel budget", "discard", "discard limit",
    "nahi", "na", "नहीं", "रद्द", "मत करो",
    "beda", "illa", "ಬೇಡ", "ಇಲ್ಲ", "ರದ್ದು", "ರದ್ದುಮಾಡಿ",
}


def detect_confirmation_intent(utterance: str) -> Optional[bool]:
    """Return True for yes/confirm, False for no/cancel, None otherwise."""
    norm = re.sub(r"[.!?,।]+", " ", (utterance or "").lower()).strip()
    norm = re.sub(r"\s+", " ", norm)
    if norm in YES_TOKENS:
        return True
    if norm in NO_TOKENS:
        return False
    words = norm.split()
    if len(words) <= 4:
        if any(w in ("confirm", "पक्का", "पुष्टि", "ಖಚಿತಪಡಿಸಿ") for w in words) and not any(w in ("no", "not", "नहीं", "ಬೇಡ") for w in words):
            return True
        if any(w in ("yes", "haan", "हाँ", "हां", "haudu", "ಹೌದು") for w in words) and not any(w in ("approve", "send", "milk", "48") for w in words):
            return True
        if any(w in ("no", "cancel", "discard", "nahi", "नहीं", "रद्द", "ಬೇಡ", "ಇಲ್ಲ", "ರದ್ದು") for w in words):
            return False
    return None


def parse_period_deterministic(utterance: str) -> str:
    txt = (utterance or "").lower()
    if any(k in txt for k in ["this week", "for a week", "weekly", "इस हफ्ते", "इस सप्ताह", "हफ्ते", "is hafte", "ಈ ವಾರ", "ವಾರಕ್ಕೆ", "ee vaara"]):
        return "this_week"
    if any(k in txt for k in ["weekend", "वीकेंड", "सप्ताहांत", "ವಾರಾಂತ್ಯ"]):
        return "this_weekend"
    if any(k in txt for k in ["this month", "monthly", "इस महीने", "महीने", "is mahine", "ಈ ತಿಂಗಳು", "ee tingalu"]):
        return "this_month"
    if any(k in txt for k in ["today", "tonight", "आज", "आज रात", "aaj", "ಇಂದು", "ಇಂದು ರಾತ್ರಿ", "indu"]):
        return "today"
    if any(k in txt for k in ["48 hour", "48h", "two days", "2 days", "दो दिन", "48 घंटे", "ಎರಡು ದಿನ", "48 ಗಂಟೆ"]):
        return "48_hours"
    if "week" in txt or "ವಾರ" in txt:
        return "this_week"
    return "48_hours"


def _parse_english_number_words(text: str) -> Optional[int]:
    tokens = re.findall(r"[a-z]+", text.lower())
    total = 0
    current = 0
    matched = False
    for tok in tokens:
        if tok == "and":
            continue
        if tok in _EN_UNITS:
            current += _EN_UNITS[tok]
            matched = True
        elif tok in _EN_TENS:
            current += _EN_TENS[tok]
            matched = True
        elif tok == "hundred":
            current = (current or 1) * 100
            matched = True
        elif tok == "thousand":
            total += (current or 1) * 1000
            current = 0
            matched = True
        elif matched:
            break
    val = total + current
    return val if matched and val > 0 else None


def parse_amount_deterministic(utterance: str) -> Optional[int]:
    """
    Deterministically extract spoken or typed rupee amount from digits or words
    in English, Hindi (Devanagari/Roman), or Kannada (script/Roman).
    """
    norm = (utterance or "").translate(_INDIC_DIGIT_TABLE).lower()
    norm_nocomma = re.sub(r"(?<=\d),(?=\d)", "", norm)

    # Remove '48 hours' / '48h' / '14 days' tokens before scanning raw digits so period numbers aren't mistaken for budget
    cleaned_for_digits = re.sub(r"\b(?:48\s*(?:hours?|h|घंटे|ಗಂಟೆ)|14\s*days?)\b", " ", norm_nocomma)

    # 1. Explicit negative or positive digits near budget/rupee context or standalone
    digit_matches = re.findall(r"(-?\d+)", cleaned_for_digits)
    if digit_matches:
        return int(digit_matches[0])

    # 2. Compound phrase table (en / hi / kn)
    padded = " " + re.sub(r"[^\w\u0900-\u097F\u0C80-\u0CFF]+", " ", norm) + " "
    for phrase, val in _EXACT_COMPOUND_AMOUNTS:
        if f" {phrase} " in padded or ( any(ord(ch) > 127 for ch in phrase) and phrase in norm ):
            return val

    # 3. General compositional English number-word parser (e.g. 'one thousand two hundred fifty')
    en_val = _parse_english_number_words(norm)
    if en_val is not None:
        return en_val

    if re.search(r"\bhundred\b", norm):
        return 100
    if re.search(r"\bthousand\b", norm):
        return 1000
    return None


BUDGET_ACTION_VERBS = [
    "set", "change", "raise", "lower", "update", "make", "put", "keep", "increase", "decrease", "extend",
    "रखो", "रखें", "करो", "करें", "बढ़ाओ", "बढ़ाएं", "बदलो", "तय", "rakho", "karo", "badhao",
    "ಇಡಿ", "ಇಡು", "ಮಾಡಿ", "ಹೊಂದಿಸಿ", "ಹೆಚ್ಚಿಸಿ", "ಬದಲಿಸಿ", "idi", "maadi", "hechisi",
]


def has_verbal_budget_intent(utterance: str) -> bool:
    low = (utterance or "").lower().strip()
    if "?" in low or any(low.startswith(q) for q in ("what ", "why ", "how ", "can i ", "when ", "who ")):
        return False
    has_noun = any(k in low for k in BUDGET_INTENT_KEYWORDS)
    has_verb = any(v in low for v in BUDGET_ACTION_VERBS)
    return bool(has_noun and has_verb)


def _llm_fallback_parse(utterance: str) -> Optional[Tuple[int, str]]:
    """
    Optional LLM parser fallback used ONLY when deterministic parser found budget intent
    but could not extract an amount, and GROQ_API_KEY is enabled locally.
    Hard constraint: never lets the LLM invent a number; any returned integer must also be
    grounded in a recognized token or digit in the utterance.
    """
    settings = get_settings()
    try:
        assert_paid_calls_permitted("Groq Parser Fallback")
    except PermissionError:
        return None
    if not settings.groq_live_allowed:
        return None

    prompt = (
        "Extract the period from the merchant's budget command as JSON: "
        '{"period": "today"|"48_hours"|"this_week"|"this_weekend"|"this_month"}. '
        "Never invent numbers."
    )
    try:
        with httpx.Client(timeout=3.5) as client:
            resp = client.post(
                f"{settings.groq_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.groq_api_key}", "Content-Type": "application/json"},
                json={
                    "model": settings.groq_model,
                    "temperature": 0.0,
                    "max_tokens": 40,
                    "messages": [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": utterance[:220]},
                    ],
                },
            )
        if resp.status_code != 200:
            return None
        content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        m = re.search(r"\{.*\}", content, re.DOTALL)
        if not m:
            return None
        parsed = json.loads(m.group(0))
        amt = parse_amount_deterministic(utterance)
        period = str(parsed.get("period", "48_hours"))
        if period not in PERIOD_LABELS:
            period = "48_hours"
        if amt is not None:
            return amt, period
    except Exception:
        return None
    return None


def parse_verbal_budget_command(utterance: str) -> Dict[str, Any]:
    """
    Parse a spoken or typed budget command deterministically first.
    Returns {'matched': bool, 'amount_inr': Optional[int], 'period_key': str, 'parser_mode': str}.
    """
    if not has_verbal_budget_intent(utterance):
        return {"matched": False, "amount_inr": None, "period_key": "48_hours", "parser_mode": "none"}

    # Guardrail check: if utterance asks for discount off bill (e.g. '80 rupees off 100 bill'), do not treat as cap update
    low = (utterance or "").lower()
    if re.search(r"\d+\s*(?:rupees?|rs\.?)\s*off\b", low) or "ignore previous" in low or "without consent" in low:
        return {"matched": False, "amount_inr": None, "period_key": "48_hours", "parser_mode": "none"}

    amt = parse_amount_deterministic(utterance)
    period = parse_period_deterministic(utterance)
    if amt is not None:
        return {
            "matched": True,
            "amount_inr": amt,
            "period_key": period,
            "parser_mode": "deterministic",
        }

    fb = _llm_fallback_parse(utterance)
    if fb is not None:
        return {
            "matched": True,
            "amount_inr": fb[0],
            "period_key": fb[1],
            "parser_mode": "llm_period_fallback",
        }

    return {"matched": True, "amount_inr": None, "period_key": period, "parser_mode": "missing_amount"}


def format_period_label(period_key: str, lang: str) -> str:
    lg = lang if lang in ("en", "hi", "kn") else "en"
    return PERIOD_LABELS.get(period_key, PERIOD_LABELS["48_hours"])[lg]


def render_budget_readback_prompt(amount_inr: int, period_key: str, lang: str) -> str:
    lg = lang if lang in ("en", "hi", "kn") else "en"
    p_lbl = format_period_label(period_key, lg)
    if lg == "hi":
        msg = f"ऑफर बजट {p_lbl} के लिए {amount_inr} रुपये होगा। पुष्टि के लिए हां बोलें।"
        return assert_valid_merchant_copy(msg, check_sentence_length=False)
    if lg == "kn":
        msg = f"ಆಫರ್ ಬಜೆಟ್ {p_lbl} ಗಾಗಿ {amount_inr} ರೂಪಾಯಿ ಆಗಲಿದೆ. ಖಚಿತಪಡಿಸಲು ಹೌದು ಎಂದು ಹೇಳಿ."
        return assert_valid_merchant_copy(msg, check_sentence_length=False)
    msg = f"Offer budget of Rs {amount_inr} for {p_lbl}. Say yes to confirm."
    return assert_valid_merchant_copy(msg, check_sentence_length=True)


def render_budget_confirmed_message(old_cap: int, new_cap: int, period_key: str, lang: str) -> str:
    lg = lang if lang in ("en", "hi", "kn") else "en"
    p_lbl = format_period_label(period_key, lg)
    if lg == "hi":
        msg = f"पक्का हो गया। {p_lbl} के लिए आपका ऑफर बजट {old_cap} रुपये से बदलकर {new_cap} रुपये कर दिया गया है।"
        return assert_valid_merchant_copy(msg, check_sentence_length=False)
    if lg == "kn":
        msg = f"ಖಚಿತವಾಗಿದೆ. {p_lbl} ಗಾಗಿ ನಿಮ್ಮ ಆಫರ್ ಬಜೆಟ್ {old_cap} ರೂಪಾಯಿಯಿಂದ {new_cap} ರೂಪಾಯಿಗೆ ಬದಲಾಗಿದೆ."
        return assert_valid_merchant_copy(msg, check_sentence_length=False)
    msg = f"Confirmed. Your offer budget for {p_lbl} is updated from Rs {old_cap} to Rs {new_cap}."
    return assert_valid_merchant_copy(msg, check_sentence_length=True)


def render_budget_cancelled_message(current_cap: int, lang: str) -> str:
    lg = lang if lang in ("en", "hi", "kn") else "en"
    if lg == "hi":
        return assert_valid_merchant_copy(
            f"बदलाव रद्द किया गया। आपका ऑफर बजट {current_cap} रुपये पर अपरिवर्तित है।",
            check_sentence_length=False,
        )
    if lg == "kn":
        return assert_valid_merchant_copy(
            f"ಬದಲಾವಣೆ ರದ್ದಾಗಿದೆ. ನಿಮ್ಮ ಆಫರ್ ಬಜೆಟ್ {current_cap} ರೂಪಾಯಿಯಲ್ಲೇ ಉಳಿದಿದೆ.",
            check_sentence_length=False,
        )
    return assert_valid_merchant_copy(
        f"Cancelled. Your offer budget stays unchanged at Rs {current_cap}.",
        check_sentence_length=True,
    )


def render_budget_bounds_rejection(min_cap: int, max_cap: int, attempted: Optional[int], lang: str) -> str:
    lg = lang if lang in ("en", "hi", "kn") else "en"
    if lg == "hi":
        prefix = f"{attempted} रुपये मान्य नहीं है। " if attempted is not None else ""
        return assert_valid_merchant_copy(
            f"{prefix}कृपया अपना ऑफर बजट {min_cap} रुपये से {max_cap} रुपये के बीच रखें।",
            check_sentence_length=False,
        )
    if lg == "kn":
        prefix = f"{attempted} ರೂಪಾಯಿ ಮಾನ್ಯವಲ್ಲ. " if attempted is not None else ""
        return assert_valid_merchant_copy(
            f"{prefix}ದಯವಿಟ್ಟು ನಿಮ್ಮ ಆಫರ್ ಬಜೆಟ್ ಅನ್ನು {min_cap} ರೂಪಾಯಿಯಿಂದ {max_cap} ರೂಪಾಯಿ ಒಳಗೆ ಇಡಿ.",
            check_sentence_length=False,
        )
    prefix = f"Rs {attempted} is outside allowed bounds. " if attempted is not None else ""
    return assert_valid_merchant_copy(
        f"{prefix}Please choose an offer budget between Rs {min_cap} and Rs {max_cap}.",
        check_sentence_length=True,
    )
