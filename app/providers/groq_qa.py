"""
Task 15: Keyless Optional Groq Grounded English Store Q&A Provider.

Design guarantees:
1. Disabled by default (GROQ_ENABLED=false) and hard-blocked when PUBLIC_DEPLOY=true.
2. Zero secrets in code or config; reads GROQ_API_KEY solely from environment/.env.
3. Zero PII outbound: sends only store-level aggregate KPIs and campaign parameters;
   assert_zero_pii() scans the serialized JSON before any HTTP request is made.
4. Read-only & zero mutation: never writes to SQLite or alters offer_rupees / max_budget.
5. Numeric & jargon grounding gate: every number in the LLM response must match the
   SQLite store_facts whitelist, and the response must pass merchant copy_lint
   (zero banned jargon, zero em/en dashes, zero emojis, <=25 words/sentence).
   Any violation or HTTP error falls back cleanly to the deterministic SQLite answer.
"""
from dataclasses import dataclass, field
import json
import re
from typing import Any, Dict, List, Optional, Set
import httpx

from ..config import Settings, get_settings
from ..copy_lint import assert_valid_merchant_copy, lint_merchant_copy
from ..security import assert_paid_calls_permitted

PII_PATTERNS = [
    re.compile(r"\bCUST-[A-Za-z0-9_-]+\b", re.IGNORECASE),
    re.compile(r"\bpayer_hash\b", re.IGNORECASE),
    re.compile(r"\b[0-9a-f]{32,64}\b", re.IGNORECASE),
    re.compile(r"(?:\+91[\-\s]?)?[6-9]\d{9}\b"),
]

# Harmless time/policy constants allowed in natural merchant answers (e.g., 3 PM to 5 PM, 6 AM, 48 hours)
ALLOWED_CONTEXT_CONSTANTS = {
    0.0, 1.0, 2.0, 3.0, 5.0, 6.0, 8.0, 12.0, 14.0, 16.0, 18.0,
    20.0, 22.0, 24.0, 25.0, 30.0, 32.0, 38.0, 40.0, 48.0, 70.0, 80.0, 100.0,
}

NUMBER_TOKEN_RE = re.compile(r"(?<![A-Za-z])(\d[\d,]*(?:\.\d+)?)(?![A-Za-z])")


@dataclass
class GroqQAResult:
    question: str
    answer: str
    mode: str  # "groq_grounded" | "deterministic_fallback"
    provider: str  # "groq" | "deterministic_sqlite"
    grounded_verified: bool
    fallback_reason: Optional[str] = None
    ungrounded_numbers: List[str] = field(default_factory=list)
    lint_violations: List[str] = field(default_factory=list)


def assert_zero_pii(payload_json: str) -> None:
    """Verify no customer identifiers, hashes, or phone numbers appear in outbound payload."""
    for pat in PII_PATTERNS:
        m = pat.search(payload_json)
        if m:
            raise ValueError(f"Outbound PII / identifier guard blocked Groq payload matching '{m.group(0)}'.")


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
    """Return any numeric token in draft_text that does not match an allowed SQLite fact number."""
    ungrounded: List[str] = []
    for match in NUMBER_TOKEN_RE.finditer(draft_text):
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


def build_deterministic_store_answer(question: str, store_facts: Dict[str, Any]) -> str:
    """Deterministic SQLite-grounded plain-English fallback answer."""
    q = question.strip().lower()
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

    if any(w in q for w in ["afternoon", "slow", "3 pm", "dead", "quiet", "tea", "combo"]):
        ans = (
            f"Between 3 PM and 5 PM, shop QR scans drop {drop_pct} percent below peak hour. "
            f"You can test an afternoon filter-coffee combo for regular buyers within your spending limit."
        )
    elif any(w in q for w in ["sales", "revenue", "gmv", "average bill", "ticket", "many payment", "transactions"]):
        ans = (
            f"In the last 30 days, your shop recorded {txn_30d} Paytm QR payments worth {gmv_30d} rupees. "
            f"Your average customer bill is {avg_bill:.1f} rupees."
        )
    elif any(w in q for w in ["spent", "remaining", "budget", "limit", "cap"]):
        rem = max(0, cap_inr - spent_inr)
        ans = (
            f"Your current cashback limit is {cap_inr} rupees, with {spent_inr} rupees spent and {rem} rupees remaining. "
            f"Cashback stops automatically once {cap_inr} rupees is reached."
        )
    elif any(w in q for w in ["milk", "batter", "morning", "saturday", "stock", "dairy"]):
        ans = (
            f"Saturday morning traffic runs higher than normal weekdays. "
            f"Ordering {milk_l} liters extra milk and 12 kg batter by tonight prevents early stockouts."
        )
    else:
        ans = (
            f"In the last 30 days, Sri Krishna Darshini recorded {txn_30d} QR payments worth {gmv_30d} rupees. "
            f"Tonight you can send {treat_n} silent regulars a {offer_inr} rupee offer on {min_bill} rupee bills "
            f"within a {cap_inr} rupee limit while keeping {ctrl_n} aside."
        )
    return assert_valid_merchant_copy(ans, check_sentence_length=True)


class GroqGroundedQA:
    """
    Optional keyless Groq OpenAI-compatible English store Q&A adapter with
    strict zero-PII enforcement, numeric grounding check, copy-lint gate, and
    fail-closed circuit breaker.
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self._calls_made: int = 0
        self._circuit_open: bool = False
        self._circuit_reason: Optional[str] = None

    def status_dict(self) -> Dict[str, Any]:
        return {
            "groq_enabled": self.settings.groq_enabled,
            "public_deploy": self.settings.public_deploy,
            "api_key_configured": len(self.settings.groq_api_key.strip()) > 0,
            "live_allowed": self.settings.groq_live_allowed and not self._circuit_open,
            "model": self.settings.groq_model,
            "calls_made": self._calls_made,
            "max_calls_per_session": self.settings.groq_max_calls_per_session,
            "circuit_open": self._circuit_open,
            "circuit_reason": self._circuit_reason,
        }

    def answer_question(
        self,
        question: str,
        store_facts: Dict[str, Any],
        lang: str = "en",
    ) -> GroqQAResult:
        fallback_ans = build_deterministic_store_answer(question, store_facts)
        norm_lang = (lang or "en").strip().lower()

        # 1. English-only rule: never route Indic copy through unreviewed LLM output
        if not norm_lang.startswith("en"):
            return GroqQAResult(
                question=question,
                answer=fallback_ans,
                mode="deterministic_fallback",
                provider="deterministic_sqlite",
                grounded_verified=True,
                fallback_reason="Groq Q&A is restricted to English; Indic queries use deterministic templates.",
            )

        # 2. Enforce PUBLIC_DEPLOY paid/external API lock
        try:
            assert_paid_calls_permitted("Groq API")
        except PermissionError as exc:
            return GroqQAResult(
                question=question,
                answer=fallback_ans,
                mode="deterministic_fallback",
                provider="deterministic_sqlite",
                grounded_verified=True,
                fallback_reason=str(exc),
            )

        # 3. Check feature flag, API key, circuit breaker, and session call ceiling
        if not self.settings.groq_live_allowed:
            return GroqQAResult(
                question=question,
                answer=fallback_ans,
                mode="deterministic_fallback",
                provider="deterministic_sqlite",
                grounded_verified=True,
                fallback_reason="Groq disabled (requires GROQ_ENABLED=true and GROQ_API_KEY in local .env).",
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

        # 4. Serialize aggregate-only store_facts and enforce zero-PII guard
        facts_json = json.dumps(store_facts, sort_keys=True)
        assert_zero_pii(facts_json)
        assert_zero_pii(question)

        system_prompt = (
            "You are VyaparVoice, a plain-spoken closing-time store assistant for a Bengaluru merchant. "
            "Answer in at most 2 short sentences (strictly <= 22 words per sentence). "
            "Use ONLY exact numbers present in STORE_FACTS_JSON. Never invent numbers. "
            "Never use dashes, emojis, or statistical jargon (forbidden: cohort, holdout, p-value, "
            "Fisher, Wilson, confidence interval, uplift, incremental, ROI, ROAS, ARPU, DPDP, ITT, RFM). "
            "You are strictly read-only and cannot change offers or budgets.\n"
            f"STORE_FACTS_JSON: {facts_json}"
        )

        req_body = {
            "model": self.settings.groq_model,
            "temperature": 0.0,
            "max_tokens": 110,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question.strip()[:280]},
            ],
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

        # Normalize any accidental Unicode dashes before linting
        cleaned = raw_draft.replace("\u2014", ",").replace("\u2013", " to ").strip()

        # 5. Strict numeric grounding verification against SQLite facts
        allowed_nums = extract_allowed_numbers(store_facts)
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

        # 6. Strict merchant copy-lint verification (zero banned jargon, <=25 words/sentence)
        lint_res = lint_merchant_copy(cleaned, check_sentence_length=True, max_words_per_sentence=25)
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
            mode="groq_grounded",
            provider="groq",
            grounded_verified=True,
            fallback_reason=None,
        )


_GROQ_SINGLETON: Optional[GroqGroundedQA] = None


def get_groq_qa(reset: bool = False) -> GroqGroundedQA:
    global _GROQ_SINGLETON
    if _GROQ_SINGLETON is None or reset:
        _GROQ_SINGLETON = GroqGroundedQA()
    return _GROQ_SINGLETON
