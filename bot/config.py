from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class LLMSettings(BaseModel):
    base_url: str = "http://llama-server:8080/v1"
    model: str = "lfm2.5-8b-a1b"
    timeout: int = 10
    max_tokens: int = 512
    temperature: float = 0.1


class RoutingSettings(BaseModel):
    local_first: bool = True
    local_timeout: int = 10
    local_only: List[str] = Field(default_factory=lambda: [
        "intent_parsing", "simple_qa", "greetings", "pin_verification"
    ])
    cloud_ok: List[str] = Field(default_factory=lambda: [
        "document_drafting", "complex_queries", "clarification"
    ])
    cloud_priority: List[Dict[str, str]] = Field(default_factory=lambda: [
        {"provider": "deepseek", "model": "v4-flash", "api_key_env": "DEEPSEEK_API_KEY"},
        {"provider": "openai", "model": "gpt-5-nano", "api_key_env": "OPENAI_API_KEY"},
    ])


class TelegramSettings(BaseModel):
    th_group_id: int = -1000000000000
    pin_attempts: int = 3
    pin_cooldown_seconds: int = 300


class SecuritySettings(BaseModel):
    whitelist_required: bool = True
    tiered_sensitivity: Dict[str, List[str]] = Field(default_factory=lambda: {
        "basic": ["laboral", "tiempos"],
        "sensitive": ["salario"],
    })


class DatabaseSettings(BaseModel):
    path: str = "/app/data/asistente_th.db"


class PDFSettings(BaseModel):
    qr_base_url: str = "https://oriente.local/verify"


class BudgetSettings(BaseModel):
    daily_usd: Dict[str, float] = Field(default_factory=lambda: {
        "deepseek": 0.10,
        "openai": 0.05,
    })
    alert_at_pct: int = 80


class Settings(BaseSettings):
    telegram_bot_token: str
    deepseek_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    llm_base_url: str = "http://llama-server:8080/v1"

    llm: LLMSettings = LLMSettings()
    routing: RoutingSettings = RoutingSettings()
    telegram: TelegramSettings = TelegramSettings()
    security: SecuritySettings = SecuritySettings()
    database: DatabaseSettings = DatabaseSettings()
    pdf: PDFSettings = PDFSettings()
    budget: BudgetSettings = BudgetSettings()

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @classmethod
    def from_yaml(cls, path: str = "config.yaml") -> "Settings":
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls(**data)


settings = Settings.from_yaml()


def get_settings() -> Settings:
    return settings