from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    reviva_env: str = "test"
    database_url: str = "postgresql+psycopg://reviva:reviva@postgres:5432/reviva"
    redis_url: str = "redis://redis:6379/0"
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.2:1b"
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""
    merchant_id: str = "merch_local_1"
    merchant_kill_switch: bool = False
    diagnosis_url: str = "http://diagnosis-service:8000"
    policy_url: str = "http://policy-service:8000"
    executor_url: str = "http://executor-service:8000"
    ingest_url: str = "http://ingest-service:8000"


settings = Settings()
