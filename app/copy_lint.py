import re
from typing import Dict, List

BANNED_MERCHANT_JARGON = [
    r"\bcohort(s)?\b",
    r"\bholdout(s)?\b",
    r"\bcontrol\s+group\b",
    r"\btreatment\s+arm\b",
    r"\bp-value(s)?\b",
    r"\bfisher\b",
    r"\bwilson\b",
    r"\bconfidence\s+interval(s)?\b",
    r"\bstatistically\s+significant\b",
    r"\bunderpowered\b",
    r"\buplift\b",
    r"\bincremental\b",
    r"\broi\b",
    r"\broas\b",
    r"\barpu\b",
    r"\bdpdp\b",
    r"\bsha-256\b",
    r"\bopt-in\b",
    r"\battribution\b",
    r"\bconversion\s+rate\b",
    r"\banomal(y|ies)\b",
    r"\bheuristic(s)?\b",
    r"\brfm\b",
    r"\bitt\b",
    r"\bintention-to-treat\b",
]

_EMOJI_RE = re.compile(
    "["
    "\U0001F1E0-\U0001F1FF"
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FAFF"
    "\U00002600-\U000027BF"
    "]+"
)


def find_formatting_violations(text: str) -> List[str]:
    issues: List[str] = []
    if "\u2014" in text:
        issues.append("Contains forbidden em dash (U+2014).")
    if "\u2013" in text:
        issues.append("Contains forbidden en dash (U+2013).")
    if _EMOJI_RE.search(text):
        issues.append("Contains forbidden Unicode emoji/dingbat symbol.")
    return issues


def lint_merchant_copy(text: str, check_sentence_length: bool = True, max_words_per_sentence: int = 34) -> Dict[str, object]:
    """
    Validates merchant-facing text against banned statistical/technical jargon,
    banned formatting characters (em/en dashes, emojis), and sentence length.
    """
    issues = find_formatting_violations(text)
    for pattern in BANNED_MERCHANT_JARGON:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            issues.append(f"Contains banned merchant jargon: '{match.group(0)}'")

    if check_sentence_length:
        sentences = [s.strip() for s in re.split(r"[.!?।]+", text) if s.strip()]
        for sent in sentences:
            words = sent.split()
            if len(words) > max_words_per_sentence:
                issues.append(
                    f"Sentence exceeds {max_words_per_sentence} words ({len(words)} words): '{sent[:50]}...'"
                )

    return {
        "passed": len(issues) == 0,
        "issues": issues,
    }


def assert_valid_merchant_copy(text: str, check_sentence_length: bool = True) -> str:
    res = lint_merchant_copy(text, check_sentence_length=check_sentence_length)
    if not res["passed"]:
        raise ValueError("Merchant copy failed lint: " + "; ".join(res["issues"]))  # type: ignore[arg-type]
    return text
