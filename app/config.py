import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_YAML_PATH = REPO_ROOT / "config" / "default.yaml"
SARVAM_YAML_PATH = REPO_ROOT / "config" / "sarvam.yaml"
DOTENV_PATH = REPO_ROOT / ".env"


def _parse_bool(val: Optional[str], default: bool = False) -> bool:
    if val is None or val.strip() == "":
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def _env_str(key: str, default: str) -> str:
    raw = os.environ.get(key)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip()


def _env_int(key: str, default: int) -> int:
    raw = os.environ.get(key)
    if raw is None or raw.strip() == "":
        return int(default)
    return int(raw.strip())


def _env_float(key: str, default: float) -> float:
    raw = os.environ.get(key)
    if raw is None or raw.strip() == "":
        return float(default)
    return float(raw.strip())


def _load_dotenv_non_destructive(dotenv_path: Path) -> None:
    """Load local .env key-values into os.environ only if not already set."""
    if not dotenv_path.exists():
        return
    for raw_line in dotenv_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_version: str
    live_demo_url: str
    public_deploy: bool
    admin_token: str

    # Session isolation & resource bounds
    isolate_visitors: bool
    session_cookie_name: str
    session_header_name: str
    session_ttl_seconds: int
    max_active_sessions: int
    max_session_db_bytes: int
    max_total_sessions_bytes: int
    session_storage_dir: Path

    # Economics & guardrails
    default_gross_margin_pct: float
    paytm_promo_fee_pct: float
    steady_state_campaigns_per_month: float
    steady_state_redeemed_gmv_monthly_inr: float
    max_discount_floor_pct: float
    cooldown_days: int

    # Statistical power & cap-binding alert
    default_allocation_ratio: float
    alpha_two_sided: float
    target_power: float
    cap_overrun_warn_threshold: float
    assumed_redemption_rates: Dict[str, float] = field(default_factory=dict)

    # Keyless Sarvam AI & provider switches (auto-detected when API keys are present)
    stt_tts_provider: str = "auto"
    llm_provider: str = "auto"
    sarvam_enabled: bool = False
    sarvam_live_calls_enabled: bool = False
    sarvam_api_key: str = ""
    sarvam_base_url: str = "https://api.sarvam.ai"
    sarvam_timeout_seconds: float = 8.0
    sarvam_tts_endpoint: str = "/text-to-speech"
    sarvam_tts_model: str = "bulbul:v3"
    sarvam_tts_cost_per_10k_inr: float = 30.0
    sarvam_speakers: Dict[str, str] = field(default_factory=dict)
    sarvam_stt_endpoint: str = "/speech-to-text"
    sarvam_stt_model: str = "saaras:v4"
    sarvam_stt_cost_per_hour_inr: float = 30.0
    sarvam_chat_endpoint: str = "/v1/chat/completions"
    sarvam_chat_model: str = "sarvam-105b-conversations"
    sarvam_chat_cost_credits: float = 0.15
    sarvam_translate_endpoint: str = "/translate"
    sarvam_translate_cost_per_10k_inr: float = 20.0
    sarvam_tts_cap_pct: float = 15.0
    sarvam_stt_cap_pct: float = 15.0
    sarvam_total_cap_pct: float = 30.0
    sarvam_initial_balance: float = 500.0
    sarvam_max_calls: int = 60
    sarvam_session_max_calls: int = 35
    sarvam_max_recording_seconds: float = 10.0
    sarvam_ledger_path: Path = REPO_ROOT / "data" / "sarvam_credit_ledger.json"
    sarvam_cache_dir: Path = REPO_ROOT / "data" / "audio_cache"
    provider_cache_db_path: Path = REPO_ROOT / "data" / "provider_cache.db"
    prewarmed_assets_dir: Path = REPO_ROOT / "assets" / "prewarmed"

    # Public Render demo unlock & rate limiting
    demo_pin: str = ""
    demo_live_flag: bool = False
    rate_limit_per_minute: int = 30

    # Secondary Groq provider (Chat + STT + English TTS fallback)
    groq_enabled: bool = False
    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"

    # Stage 2 Cap Editor bounds
    min_cap_inr: int = 50
    max_cap_inr: int = 2500
    cap_presets_inr: tuple = (150, 250, 300, 400, 500)

    # Secondary Groq model parameters
    groq_model: str = "openai/gpt-oss-20b"
    groq_stt_model: str = "whisper-large-v3-turbo"
    groq_tts_model: str = "canopylabs/orpheus-v1-english"
    groq_tts_voice: str = "troy"
    groq_timeout_seconds: float = 6.0
    groq_max_calls_per_session: int = 20

    def is_sarvam_live_allowed(self, demo_unlocked: bool = False) -> bool:
        if self.public_deploy and not (demo_unlocked or self.demo_live_flag):
            return False
        return bool(
            self.sarvam_enabled
            and self.sarvam_live_calls_enabled
            and len(self.sarvam_api_key.strip()) > 0
        )

    def is_groq_live_allowed(self, demo_unlocked: bool = False) -> bool:
        if self.public_deploy and not (demo_unlocked or self.demo_live_flag):
            return False
        return bool(self.groq_enabled and len(self.groq_api_key.strip()) > 0)

    @property
    def sarvam_live_allowed(self) -> bool:
        """Live Sarvam calls require local mode or active server/PIN unlock when PUBLIC_DEPLOY=true."""
        return self.is_sarvam_live_allowed(demo_unlocked=False)

    @property
    def groq_live_allowed(self) -> bool:
        """Live Groq calls require local mode or active server/PIN unlock when PUBLIC_DEPLOY=true."""
        return self.is_groq_live_allowed(demo_unlocked=False)


_CACHED_SETTINGS: Optional[Settings] = None


def load_settings(force_reload: bool = False) -> Settings:
    global _CACHED_SETTINGS
    if _CACHED_SETTINGS is not None and not force_reload:
        return _CACHED_SETTINGS

    _load_dotenv_non_destructive(DOTENV_PATH)
    d_cfg = _load_yaml(DEFAULT_YAML_PATH)
    s_cfg = _load_yaml(SARVAM_YAML_PATH)

    app_sec = d_cfg.get("app", {})
    sess_sec = d_cfg.get("sessions", {})
    econ_sec = d_cfg.get("economics", {})
    exp_sec = d_cfg.get("experiment", {})
    groq_sec = d_cfg.get("groq", {})

    tts_sec = s_cfg.get("tts", {})
    stt_sec = s_cfg.get("stt", {})
    chat_sec = s_cfg.get("chat", {})
    tr_sec = s_cfg.get("translate", {})
    cap_sec = s_cfg.get("credit_caps", {})

    # Render automatically sets RENDER=true; default public_deploy=True on Render unless overridden
    render_detected = _parse_bool(os.environ.get("RENDER"), False)
    default_pub = bool(app_sec.get("public_deploy_default", False)) or render_detected
    public_deploy = _parse_bool(os.environ.get("PUBLIC_DEPLOY"), default_pub)

    isolate_default = bool(sess_sec.get("isolate_visitors", True))
    isolate_visitors = _parse_bool(os.environ.get("ISOLATE_VISITORS"), isolate_default)

    ledger_rel = cap_sec.get("ledger_path", "data/sarvam_credit_ledger.json")
    cache_rel = cap_sec.get("cache_dir", "data/audio_cache")
    cache_db_rel = cap_sec.get("cache_db_path", "data/provider_cache.db")
    sess_rel = sess_sec.get("storage_dir", "app/sessions_db")

    ledger_path = Path(_env_str("SARVAM_LEDGER_PATH", str(REPO_ROOT / ledger_rel)))
    cache_dir = Path(_env_str("SARVAM_CACHE_DIR", str(REPO_ROOT / cache_rel)))
    sess_dir = Path(_env_str("SESSION_STORAGE_DIR", str(REPO_ROOT / sess_rel)))
    default_cache_db = (
        str(sess_dir / "_provider_cache.db")
        if ("SESSION_STORAGE_DIR" in os.environ and "PROVIDER_CACHE_DB_PATH" not in os.environ)
        else str(REPO_ROOT / cache_db_rel)
    )
    cache_db_path = Path(_env_str("PROVIDER_CACHE_DB_PATH", default_cache_db))
    prewarmed_dir_path = Path(
        _env_str("PREWARMED_ASSETS_DIR", str(REPO_ROOT / "assets" / "prewarmed"))
    )

    sarvam_key_val = os.environ.get("SARVAM_API_KEY", "").strip()
    groq_key_val = os.environ.get("GROQ_API_KEY", "").strip()
    stt_tts_prov = _env_str("STT_TTS_PROVIDER", "auto").lower()
    llm_prov = _env_str("LLM_PROVIDER", "auto").lower()

    sarvam_switch_on = stt_tts_prov in ("auto", "sarvam") and bool(sarvam_key_val)
    raw_sarvam_en = os.environ.get("SARVAM_ENABLED")
    raw_sarvam_live = os.environ.get("SARVAM_LIVE_CALLS_ENABLED")
    sarvam_en_val = _parse_bool(raw_sarvam_en, sarvam_switch_on) and stt_tts_prov not in ("webspeech", "browser", "disabled", "off")
    sarvam_live_val = _parse_bool(raw_sarvam_live, sarvam_switch_on) and stt_tts_prov not in ("webspeech", "browser", "disabled", "off")

    groq_switch_on = (llm_prov in ("auto", "groq") or stt_tts_prov in ("auto", "groq")) and bool(groq_key_val)
    raw_groq_en = os.environ.get("GROQ_ENABLED")
    groq_en_val = _parse_bool(raw_groq_en, groq_switch_on or bool(groq_sec.get("enabled", False))) and llm_prov not in ("static", "disabled", "off")

    _CACHED_SETTINGS = Settings(
        app_name=str(app_sec.get("name", "PaytmAI VyaparVoice")),
        app_version=str(app_sec.get("version", "1.1.0")),
        live_demo_url=str(app_sec.get("live_demo_url", "https://paytmai-vyaparvoice.onrender.com")),
        public_deploy=public_deploy,
        admin_token=os.environ.get("ADMIN_TOKEN", "").strip(),
        isolate_visitors=isolate_visitors,
        session_cookie_name=str(sess_sec.get("cookie_name", "vyaparvoice_sid")),
        session_header_name=str(sess_sec.get("header_name", "X-Demo-Session")),
        session_ttl_seconds=_env_int("SESSION_TTL_SECONDS", int(sess_sec.get("ttl_seconds", 1800))),
        max_active_sessions=_env_int("MAX_ACTIVE_SESSIONS", int(sess_sec.get("max_active_sessions", 64))),
        max_session_db_bytes=_env_int("MAX_SESSION_DB_BYTES", int(sess_sec.get("max_session_db_bytes", 2097152))),
        max_total_sessions_bytes=_env_int(
            "MAX_TOTAL_SESSIONS_BYTES", int(sess_sec.get("max_total_sessions_bytes", 33554432))
        ),
        session_storage_dir=sess_dir,
        default_gross_margin_pct=float(econ_sec.get("default_gross_margin_pct", 30.0)),
        paytm_promo_fee_pct=float(econ_sec.get("paytm_promo_fee_pct", 5.0)),
        steady_state_campaigns_per_month=float(econ_sec.get("steady_state_campaigns_per_month", 0.782)),
        steady_state_redeemed_gmv_monthly_inr=float(econ_sec.get("steady_state_redeemed_gmv_monthly_inr", 2040.0)),
        max_discount_floor_pct=float(econ_sec.get("max_discount_floor_pct", 22.0)),
        cooldown_days=int(econ_sec.get("cooldown_days", 14)),
        min_cap_inr=int(econ_sec.get("min_cap_inr", 50)),
        max_cap_inr=int(econ_sec.get("max_cap_inr", 2500)),
        cap_presets_inr=tuple(int(x) for x in econ_sec.get("cap_presets_inr", [150, 250, 300, 400, 500])),
        default_allocation_ratio=float(exp_sec.get("default_allocation_ratio", 4.0)),
        alpha_two_sided=float(exp_sec.get("alpha_two_sided", 0.05)),
        target_power=float(exp_sec.get("target_power", 0.80)),
        cap_overrun_warn_threshold=float(exp_sec.get("cap_overrun_warn_threshold", 0.10)),
        assumed_redemption_rates=dict(
            exp_sec.get("assumed_redemption_rates", {"CMP-WINBACK-01": 0.375, "CMP-DEADHOUR-02": 0.407, "default": 0.35})
        ),
        stt_tts_provider=stt_tts_prov,
        llm_provider=llm_prov,
        sarvam_enabled=sarvam_en_val,
        sarvam_live_calls_enabled=sarvam_live_val,
        sarvam_api_key=sarvam_key_val,
        sarvam_base_url=_env_str("SARVAM_BASE_URL", str(s_cfg.get("base_url", "https://api.sarvam.ai"))).rstrip("/"),
        sarvam_timeout_seconds=_env_float("SARVAM_TIMEOUT_SECONDS", float(s_cfg.get("timeout_seconds", 8.0))),
        sarvam_tts_endpoint=str(tts_sec.get("endpoint", "/text-to-speech")),
        sarvam_tts_model=_env_str("SARVAM_TTS_MODEL", str(tts_sec.get("model", "bulbul:v3"))),
        sarvam_tts_cost_per_10k_inr=float(tts_sec.get("cost_per_10k_chars_inr", 30.0)),
        sarvam_speakers=dict(tts_sec.get("speakers", {"en-IN": "priya", "kn-IN": "priya", "hi-IN": "shubh"})),
        sarvam_stt_endpoint=str(stt_sec.get("endpoint", "/speech-to-text")),
        sarvam_stt_model=_env_str("SARVAM_STT_MODEL", str(stt_sec.get("model", "saaras:v4"))),
        sarvam_stt_cost_per_hour_inr=float(stt_sec.get("cost_per_hour_inr", 30.0)),
        sarvam_chat_endpoint=str(chat_sec.get("endpoint", "/v1/chat/completions")),
        sarvam_chat_model=_env_str("SARVAM_CHAT_MODEL", str(chat_sec.get("model", "sarvam-105b-conversations"))),
        sarvam_chat_cost_credits=_env_float("SARVAM_CHAT_COST_CREDITS", float(chat_sec.get("cost_per_call_credits", 0.15))),
        sarvam_translate_endpoint=str(tr_sec.get("endpoint", "/translate")),
        sarvam_translate_cost_per_10k_inr=float(tr_sec.get("cost_per_10k_chars_inr", 20.0)),
        sarvam_tts_cap_pct=float(cap_sec.get("tts_max_share_pct", 15.0)),
        sarvam_stt_cap_pct=float(cap_sec.get("stt_max_share_pct", 15.0)),
        sarvam_total_cap_pct=float(cap_sec.get("total_max_share_pct", 30.0)),
        sarvam_initial_balance=_env_float(
            "SARVAM_INITIAL_BALANCE", float(cap_sec.get("default_initial_balance", 500.0))
        ),
        sarvam_max_calls=_env_int("SARVAM_MAX_CALLS", int(cap_sec.get("max_calls_global", 60))),
        sarvam_session_max_calls=_env_int(
            "SARVAM_SESSION_MAX_CALLS", int(cap_sec.get("max_calls_per_session", 35))
        ),
        sarvam_max_recording_seconds=_env_float(
            "SARVAM_MAX_RECORDING_SECONDS", float(cap_sec.get("max_recording_seconds", 10.0))
        ),
        sarvam_ledger_path=ledger_path,
        sarvam_cache_dir=cache_dir,
        provider_cache_db_path=cache_db_path,
        prewarmed_assets_dir=prewarmed_dir_path,
        demo_pin=os.environ.get("DEMO_PIN", "").strip(),
        demo_live_flag=_parse_bool(os.environ.get("DEMO_LIVE_UNLOCKED"), False),
        rate_limit_per_minute=_env_int("RATE_LIMIT_PER_MINUTE", 30),
        groq_enabled=groq_en_val,
        groq_api_key=groq_key_val,
        groq_base_url=_env_str(
            "GROQ_BASE_URL", str(groq_sec.get("base_url", "https://api.groq.com/openai/v1"))
        ).rstrip("/"),
        groq_model=_env_str("GROQ_MODEL", str(groq_sec.get("model", "openai/gpt-oss-20b"))),
        groq_stt_model=_env_str("GROQ_STT_MODEL", str(groq_sec.get("stt_model", "whisper-large-v3-turbo"))),
        groq_tts_model=_env_str("GROQ_TTS_MODEL", str(groq_sec.get("tts_model", "canopylabs/orpheus-v1-english"))),
        groq_tts_voice=_env_str("GROQ_TTS_VOICE", str(groq_sec.get("tts_voice", "troy"))),
        groq_timeout_seconds=_env_float("GROQ_TIMEOUT_SECONDS", float(groq_sec.get("timeout_seconds", 6.0))),
        groq_max_calls_per_session=_env_int(
            "GROQ_MAX_CALLS_PER_SESSION", int(groq_sec.get("max_calls_per_session", 20))
        ),
    )
    return _CACHED_SETTINGS


def get_settings() -> Settings:
    return load_settings(force_reload=False)
