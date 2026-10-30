import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

_LEDGER_LOCK = threading.RLock()


class CreditCapExceededError(RuntimeError):
    """Raised when a metered API call would exceed configured credit caps or circuit breaker."""


class SarvamCreditLedger:
    """
    Persistent fail-closed universal credit ledger for Sarvam AI.
    Enforces:
      - TTS spend <= tts_cap_pct (default 15%) of initial_balance
      - STT spend <= stt_cap_pct (default 15%) of initial_balance
      - Total spend <= total_cap_pct (default 30%) of initial_balance
      - Circuit breaker trips fail-closed on any billing/auth/rate-limit/server error.
    """

    def __init__(
        self,
        ledger_path: Path,
        tts_cap_pct: float = 15.0,
        stt_cap_pct: float = 15.0,
        total_cap_pct: float = 30.0,
    ) -> None:
        self.ledger_path = Path(ledger_path)
        self.tts_cap_pct = float(tts_cap_pct)
        self.stt_cap_pct = float(stt_cap_pct)
        self.total_cap_pct = float(total_cap_pct)

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _default_state(self) -> Dict[str, Any]:
        return {
            "initial_balance": 0.0,
            "tts_spent": 0.0,
            "stt_spent": 0.0,
            "translate_spent": 0.0,
            "halted": False,
            "halt_reason": None,
            "updated_at": self._now_iso(),
            "events": [],
        }

    def load(self) -> Dict[str, Any]:
        with _LEDGER_LOCK:
            if not self.ledger_path.exists():
                return self._default_state()
            try:
                raw = json.loads(self.ledger_path.read_text(encoding="utf-8"))
                state = self._default_state()
                state.update(raw)
                return state
            except Exception as exc:
                state = self._default_state()
                state["halted"] = True
                state["halt_reason"] = f"Corrupt ledger file: {exc}"
                return state

    def _save(self, state: Dict[str, Any]) -> None:
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        state["updated_at"] = self._now_iso()
        tmp = self.ledger_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
        tmp.replace(self.ledger_path)

    def set_balance(self, credits: float, reset_spend: bool = True) -> Dict[str, Any]:
        if credits < 0:
            raise ValueError("Credits balance cannot be negative.")
        with _LEDGER_LOCK:
            state = self._default_state() if reset_spend else self.load()
            state["initial_balance"] = round(float(credits), 4)
            state["halted"] = False
            state["halt_reason"] = None
            state["events"].append(
                {
                    "ts": self._now_iso(),
                    "event": "SET_BALANCE",
                    "credits": state["initial_balance"],
                }
            )
            self._save(state)
            return self.summary()

    def summary(self) -> Dict[str, Any]:
        state = self.load()
        bal = float(state["initial_balance"])
        tts_cap = round(bal * (self.tts_cap_pct / 100.0), 4)
        stt_cap = round(bal * (self.stt_cap_pct / 100.0), 4)
        tot_cap = round(bal * (self.total_cap_pct / 100.0), 4)
        tts_spent = round(float(state["tts_spent"]), 4)
        stt_spent = round(float(state["stt_spent"]), 4)
        tr_spent = round(float(state["translate_spent"]), 4)
        tot_spent = round(tts_spent + stt_spent + tr_spent, 4)
        return {
            "initial_balance": bal,
            "tts_cap": tts_cap,
            "stt_cap": stt_cap,
            "total_cap": tot_cap,
            "tts_spent": tts_spent,
            "stt_spent": stt_spent,
            "translate_spent": tr_spent,
            "total_spent": tot_spent,
            "remaining_within_cap": round(max(0.0, tot_cap - tot_spent), 4),
            "halted": bool(state["halted"]),
            "halt_reason": state["halt_reason"],
        }

    def check_allowance(self, capability: str, estimated_cost: float) -> None:
        if estimated_cost < 0:
            raise CreditCapExceededError("Estimated cost cannot be negative.")
        with _LEDGER_LOCK:
            s = self.summary()
            if s["halted"]:
                raise CreditCapExceededError(
                    f"Sarvam circuit breaker is halted: {s['halt_reason']}"
                )
            if s["initial_balance"] <= 0:
                raise CreditCapExceededError(
                    "Sarvam credit ledger balance is 0. Run make ledger-set-balance first."
                )
            new_total = s["total_spent"] + estimated_cost
            if new_total > s["total_cap"] + 1e-9:
                raise CreditCapExceededError(
                    f"Total cap ({self.total_cap_pct}% = {s['total_cap']} credits) exceeded: "
                    f"spent {s['total_spent']} + est {round(estimated_cost, 4)} > {s['total_cap']}."
                )
            if capability == "tts":
                if s["tts_spent"] + estimated_cost > s["tts_cap"] + 1e-9:
                    raise CreditCapExceededError(
                        f"TTS cap ({self.tts_cap_pct}% = {s['tts_cap']} credits) exceeded: "
                        f"spent {s['tts_spent']} + est {round(estimated_cost, 4)} > {s['tts_cap']}."
                    )
            elif capability == "stt":
                if s["stt_spent"] + estimated_cost > s["stt_cap"] + 1e-9:
                    raise CreditCapExceededError(
                        f"STT cap ({self.stt_cap_pct}% = {s['stt_cap']} credits) exceeded: "
                        f"spent {s['stt_spent']} + est {round(estimated_cost, 4)} > {s['stt_cap']}."
                    )
            elif capability != "translate":
                raise CreditCapExceededError(f"Unknown capability: {capability}")

    def record_spend(self, capability: str, cost: float, note: str = "") -> Dict[str, Any]:
        with _LEDGER_LOCK:
            self.check_allowance(capability, cost)
            state = self.load()
            key = f"{capability}_spent"
            state[key] = round(float(state.get(key, 0.0)) + float(cost), 6)
            state["events"].append(
                {
                    "ts": self._now_iso(),
                    "event": "SPEND",
                    "capability": capability,
                    "cost": round(float(cost), 6),
                    "note": note[:120],
                }
            )
            state["events"] = state["events"][-100:]
            self._save(state)
            return self.summary()

    def trip_circuit_breaker(self, reason: str, status_code: Optional[int] = None) -> Dict[str, Any]:
        with _LEDGER_LOCK:
            state = self.load()
            state["halted"] = True
            code_prefix = f"HTTP {status_code}: " if status_code is not None else ""
            state["halt_reason"] = f"{code_prefix}{reason}"
            state["events"].append(
                {
                    "ts": self._now_iso(),
                    "event": "CIRCUIT_HALT",
                    "reason": state["halt_reason"][:160],
                }
            )
            state["events"] = state["events"][-100:]
            self._save(state)
            return self.summary()
