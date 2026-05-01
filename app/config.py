from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env")

    app_env: str = "development"
    faq_file_path: str = "data/faq.xlsx"
    similarity_threshold: float = 0.55
    log_level: str = "INFO"

    admin_username: str = "admin"
    admin_password: str = "changeme"

    api_base_url: str = "http://127.0.0.1:8000"


settings = Settings()
