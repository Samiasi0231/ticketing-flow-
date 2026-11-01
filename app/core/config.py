from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    reservation_minutes: int = 10
    # PRD says new events are "active"; flip to true to make admin approval required
    events_require_approval: bool = False


settings = Settings()
