"""
Unified Provider Router for PaytmAI VyaparVoice (Tasks B, C, D).

Strict provider priority order across TTS, STT, and Chat / Plain-Language LLM:
  1. Primary: Sarvam (`bulbul:v3` TTS, `saaras:v4` STT, `sarvam-105b-conversations` Chat)
     when `SARVAM_API_KEY` is set, within `SARVAM_MAX_CALLS` / 30% credit cap, and
     permitted by `PUBLIC_DEPLOY` / `DEMO_PIN`.
  2. Secondary: Groq (`canopylabs/orpheus-v1-english` TTS for EN, `whisper-large-v3-turbo` STT,
     `openai/gpt-oss-20b` Chat) when `GROQ_API_KEY` is set and permitted.
  3. Tertiary: Browser Web Speech (`speechSynthesis` / `SpeechRecognition`) and
     static deterministic SQLite templates across English, Hindi, and Kannada.

Any error, timeout, or quota failure from Sarvam falls back automatically and silently,
recording only a small non-blocking notice for the Technical & Audit View.
"""
import base64
import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple
import httpx

from ..config import Settings, get_settings
from ..security import assert_paid_calls_permitted, get_current_request_session, is_session_demo_unlocked
from .base import STTResult, TTSResult
from .persistent_cache import PersistentProviderCache
from .sarvam import (
    SarvamProvider,
    SarvamProviderError,
    get_fallback_notice,
    get_sarvam_call_counts,
    set_fallback_notice,
)
from .webspeech import WebSpeechFallbackProvider


def _iso_lang(lang_code: str) -> str:
    low = (lang_code or "en-IN").lower()
    if low.startswith("hi"):
        return "hi"
    if low.startswith("kn"):
        return "kn"
    return "en"


class ProviderRouter:
    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.persistent_cache = PersistentProviderCache(
            self.settings.provider_cache_db_path,
            prewarmed_dir=self.settings.prewarmed_assets_dir,
        )
        self.sarvam = SarvamProvider(settings=self.settings, persistent_cache=self.persistent_cache)
        self.webspeech = WebSpeechFallbackProvider()

    def active_provider_badge(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        sid = session_id if session_id is not None else get_current_request_session()
        unlocked = is_session_demo_unlocked(sid)
        s_status = self.sarvam.status_dict(session_id=sid)
        s_calls = s_status["calls"]
        within_calls = (
            s_calls["global_calls"] < s_calls["global_max_calls"]
            and s_calls["session_calls"] < s_calls["session_max_calls"]
        )

        if self.settings.public_deploy and not unlocked:
            label = "Cached + Fallback (Demo PIN Locked)"
            tier = "fallback_locked"
        elif s_status["live_allowed"] and within_calls and self.settings.stt_tts_provider in ("auto", "sarvam"):
            label = "Sarvam (Primary)"
            tier = "sarvam"
        elif self.settings.is_groq_live_allowed(demo_unlocked=unlocked):
            label = "Groq (Secondary)"
            tier = "groq"
        else:
            label = "Web Speech + Static Templates (Tertiary)"
            tier = "tertiary"

        return {
            "provider_in_use": label,
            "tier": tier,
            "public_deploy": self.settings.public_deploy,
            "demo_unlocked": unlocked,
            "demo_pin_configured": len(self.settings.demo_pin) > 0,
            "sarvam": s_status,
            "groq_configured": len(self.settings.groq_api_key.strip()) > 0,
            "groq_live_allowed": self.settings.is_groq_live_allowed(demo_unlocked=unlocked),
            "groq_models": {
                "chat": self.settings.groq_model,
                "stt": self.settings.groq_stt_model,
                "tts": self.settings.groq_tts_model,
            },
            "cache": self.persistent_cache.stats(),
            "last_fallback_notice": get_fallback_notice(),
        }

    def synthesize_tts(
        self,
        text: str,
        lang_code: str = "en-IN",
        strict: bool = False,
        session_id: Optional[str] = None,
    ) -> TTSResult:
        sid = session_id if session_id is not None else get_current_request_session()
        unlocked = is_session_demo_unlocked(sid)

        # 1. Serve cached Sarvam or Groq audio immediately with 0 API calls (even when PUBLIC_DEPLOY=true & locked!)
        s_cached = self.sarvam.get_cached_tts(text, lang_code=lang_code)
        if s_cached is not None:
            return s_cached

        g_cached = self.persistent_cache.get_tts("groq", lang_code, self.settings.groq_tts_voice, text)
        if g_cached is not None:
            b64_audio, mime = g_cached
            return TTSResult(
                text=text,
                lang_code=lang_code,
                provider="groq_cached",
                mode="cached_audio",
                audio_base64=b64_audio,
                mime_type=mime,
                cached=True,
                credits_used=0.0,
            )

        # 2. Primary: Sarvam Bulbul v3 TTS across en-IN, hi-IN, kn-IN
        if self.settings.stt_tts_provider in ("auto", "sarvam"):
            s_res = self.sarvam.synthesize(text, lang_code=lang_code, strict=strict, session_id=sid)
            if s_res.provider in ("sarvam_live", "sarvam_cached"):
                return s_res

        # 3. Secondary: Groq TTS (supported for English; Indic languages fall through to Web Speech)
        try:
            assert_paid_calls_permitted("Groq TTS", demo_unlocked=unlocked)
            groq_permitted = self.settings.is_groq_live_allowed(demo_unlocked=unlocked)
        except PermissionError:
            groq_permitted = False

        if groq_permitted and _iso_lang(lang_code) == "en" and self.settings.stt_tts_provider in ("auto", "groq"):
            url = f"{self.settings.groq_base_url}/audio/speech"
            headers = {
                "Authorization": f"Bearer {self.settings.groq_api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.settings.groq_tts_model,
                "voice": self.settings.groq_tts_voice,
                "input": text[:1500],
                "response_format": "wav",
            }
            try:
                with httpx.Client(timeout=self.settings.groq_timeout_seconds) as client:
                    resp = client.post(url, headers=headers, json=payload)
                if resp.status_code == 200 and resp.content:
                    b64 = base64.b64encode(resp.content).decode("ascii")
                    self.persistent_cache.put_tts(
                        "groq", lang_code, self.settings.groq_tts_voice, text, b64, "audio/wav"
                    )
                    return TTSResult(
                        text=text,
                        lang_code=lang_code,
                        provider="groq_live",
                        mode="orpheus_tts",
                        audio_base64=b64,
                        mime_type="audio/wav",
                        cached=False,
                        credits_used=0.0,
                    )
            except Exception:
                pass

        # 4. Tertiary: Browser Web Speech API
        reason = get_fallback_notice() or "Using browser Web Speech fallback."
        return self.webspeech.synthesize(text, lang_code=lang_code, reason=reason)

    def transcribe_stt(
        self,
        audio_base64: str,
        lang_code: str = "en-IN",
        duration_seconds: float = 5.0,
        mime_type: str = "audio/wav",
        strict: bool = False,
        session_id: Optional[str] = None,
    ) -> STTResult:
        sid = session_id if session_id is not None else get_current_request_session()
        unlocked = is_session_demo_unlocked(sid)

        # Enforce 10-second spoken recording cap before any provider call
        max_secs = float(self.settings.sarvam_max_recording_seconds)
        if float(duration_seconds) > max_secs + 0.25:
            reason = f"Spoken input exceeds {int(max_secs)}-second recording limit ({duration_seconds:.1f}s)."
            set_fallback_notice(reason)
            if strict:
                raise SarvamProviderError(reason)
            return self.webspeech.transcribe_Simulated("", lang_code=lang_code, reason=reason)

        # 1. Primary: Sarvam Saaras v4 STT across en-IN, hi-IN, kn-IN
        if self.settings.stt_tts_provider in ("auto", "sarvam"):
            s_res = self.sarvam.transcribe(
                audio_base64,
                lang_code=lang_code,
                duration_seconds=duration_seconds,
                strict=strict,
                session_id=sid,
                mime_type=mime_type,
            )
            if s_res.provider == "sarvam_live":
                return s_res

        # 2. Secondary: Groq Whisper Large V3 Turbo STT across en, hi, kn
        try:
            assert_paid_calls_permitted("Groq STT", demo_unlocked=unlocked)
            groq_permitted = self.settings.is_groq_live_allowed(demo_unlocked=unlocked)
        except PermissionError:
            groq_permitted = False

        if groq_permitted and self.settings.stt_tts_provider in ("auto", "groq"):
            try:
                audio_bytes = base64.b64decode(audio_base64)
                ext = "webm" if "webm" in mime_type.lower() else ("ogg" if "ogg" in mime_type.lower() else "wav")
                url = f"{self.settings.groq_base_url}/audio/transcriptions"
                headers = {"Authorization": f"Bearer {self.settings.groq_api_key}"}
                data = {
                    "model": self.settings.groq_stt_model,
                    "language": _iso_lang(lang_code),
                    "response_format": "json",
                }
                files = {"file": (f"utterance.{ext}", audio_bytes, mime_type or "audio/wav")}
                with httpx.Client(timeout=self.settings.groq_timeout_seconds) as client:
                    resp = client.post(url, headers=headers, data=data, files=files)
                if resp.status_code == 200:
                    transcript = str(resp.json().get("text", "")).strip()
                    return STTResult(
                        transcript=transcript,
                        lang_code=lang_code,
                        provider="groq_live",
                        mode="whisper_stt",
                        credits_used=0.0,
                    )
            except Exception as exc:
                set_fallback_notice(f"Groq STT fallback error ({type(exc).__name__}); using browser Web Speech.")

        # 3. Tertiary: Browser Web Speech API
        reason = get_fallback_notice() or "Using browser Web Speech STT fallback."
        return self.webspeech.transcribe_Simulated("", lang_code=lang_code, reason=reason)

    def plain_explain_chat(
        self,
        facts: Dict[str, Any],
        lang: str,
        allowed_numbers: Set[str],
        required_numbers: Set[str],
        validate_fn,
        session_id: Optional[str] = None,
    ) -> Optional[Tuple[Dict[str, str], str]]:
        """
        Plain-language 3-sentence campaign explanation via Sarvam Primary -> Groq Secondary.
        Returns (validated_dict, provider_name) or None so caller falls back to deterministic template.
        """
        sid = session_id if session_id is not None else get_current_request_session()
        unlocked = is_session_demo_unlocked(sid)
        lg = "hi" if str(lang).startswith("hi") else ("kn" if str(lang).startswith("kn") else "en")
        lang_code = "hi-IN" if lg == "hi" else ("kn-IN" if lg == "kn" else "en-IN")
        lang_name = "Hindi" if lg == "hi" else ("Kannada" if lg == "kn" else "simple Indian English")

        facts_json = json.dumps(facts, sort_keys=True, separators=(",", ":"))
        cache_key = f"explain_simply|{lg}|{facts_json}"
        sys_prompt = (
            f"Write 3 short everyday sentences in {lang_name} as JSON keys "
            '{"cap_performance": "...", "customer_comparison": "...", "spend_vs_return": "..."}. '
            "NEVER use jargon ('uplift', 'control group', 'break-even', 'treatment', 'holdout', 'incremental', 'ROI' forbidden). "
            "NEVER invent, round, or change any number; copy numbers verbatim from FACTS."
        )
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": f"FACTS:{facts_json}"},
        ]

        def _parse_and_check(raw: str) -> Optional[Dict[str, str]]:
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if not m:
                return None
            try:
                parsed = json.loads(m.group(0))
            except Exception:
                return None
            if not all(isinstance(parsed.get(k), str) and parsed.get(k).strip() for k in ("cap_performance", "customer_comparison", "spend_vs_return")):
                return None
            cand = {
                "cap_performance": parsed["cap_performance"].strip(),
                "customer_comparison": parsed["customer_comparison"].strip(),
                "spend_vs_return": parsed["spend_vs_return"].strip(),
            }
            return cand if validate_fn(cand, allowed_numbers, required_numbers) else None

        # Check persistent cache first
        for prov_name, model_name in (("sarvam", self.settings.sarvam_chat_model), ("groq", self.settings.groq_model)):
            c_hit = self.persistent_cache.get_llm(prov_name, lang_code, model_name, cache_key)
            if c_hit:
                checked = _parse_and_check(c_hit)
                if checked is not None:
                    return checked, f"{prov_name}_cached"

        try:
            assert_paid_calls_permitted("Explain Simply LLM", demo_unlocked=unlocked)
        except PermissionError:
            return None

        # 1. Primary: Sarvam Chat (`sarvam-105b-conversations`)
        if self.settings.is_sarvam_live_allowed(demo_unlocked=unlocked) and self.settings.llm_provider in ("auto", "sarvam"):
            try:
                s_raw, s_cached = self.sarvam.chat_complete(
                    messages=messages,
                    lang_code=lang_code,
                    cache_key_text=cache_key,
                    max_tokens=240,
                    session_id=sid,
                )
                checked = _parse_and_check(s_raw)
                if checked is not None:
                    return checked, ("sarvam_cached" if s_cached else "sarvam")
                set_fallback_notice("Sarvam Explain-Simply draft failed numeric/jargon gate; fell back automatically.")
            except SarvamProviderError:
                pass

        # 2. Secondary: Groq Chat
        if self.settings.is_groq_live_allowed(demo_unlocked=unlocked) and self.settings.llm_provider in ("auto", "groq"):
            try:
                with httpx.Client(timeout=self.settings.groq_timeout_seconds) as client:
                    resp = client.post(
                        f"{self.settings.groq_base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.settings.groq_api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": self.settings.groq_model,
                            "temperature": 0.0,
                            "max_tokens": 240,
                            "messages": messages,
                        },
                    )
                if resp.status_code == 200:
                    raw = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                    checked = _parse_and_check(raw)
                    if checked is not None:
                        self.persistent_cache.put_llm("groq", lang_code, self.settings.groq_model, cache_key, raw)
                        return checked, "groq"
            except Exception:
                pass

        return None
