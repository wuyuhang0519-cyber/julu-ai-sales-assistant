from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./data/julu.db"
    app_env: str = "development"
    demo_mode: bool = True
    ai_provider: str = "openai"
    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = "gpt-4o-mini"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    ai_timeout_seconds: int = 30
    ai_max_retries: int = 2
    admin_username: str = ""
    admin_password: str = ""
    session_secret: str = ""
    cookie_secure: bool = False
    csrf_enabled: bool = True
    store_raw_ai_response: bool = False
    calendar_provider: str = "local"
    google_calendar_id: str = ""
    google_service_account_json: str = ""
    google_service_account_file: str = ""
    google_calendar_invite_attendees: bool = False
    resend_api_key: str = ""
    resend_from_email: str = ""
    email_test_allowlist: str = ""
    followup_scheduler_enabled: bool = True
    followup_poll_seconds: int = 15
    followup_demo_delay_seconds: int = 60
    followup_max_attempts: int = 3

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def selected_ai_key(self) -> str:
        return self.deepseek_api_key if self.ai_provider.lower() == "deepseek" else self.openai_api_key

    def validate_runtime(self) -> None:
        if self.is_production and (not self.admin_password or not self.session_secret or len(self.session_secret) < 32):
            raise RuntimeError("Production requires ADMIN_PASSWORD and SESSION_SECRET (32+ chars)")
        if self.is_production and not self.demo_mode and not self.selected_ai_key:
            raise RuntimeError(f"Production requires an API key for AI_PROVIDER={self.ai_provider}")
        if not self.admin_username:
            self.admin_username = "admin"
        if not self.admin_password and not self.is_production:
            self.admin_password = "change-me"
        if not self.session_secret and not self.is_production:
            self.session_secret = "development-only-session-secret-change-me"

settings = Settings()
