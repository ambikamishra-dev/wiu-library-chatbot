from pydantic_settings import BaseSettings


class Settings(BaseSettings)


app_env: str = "development"
faq_file_path: str = "data/faq.xlsx"

similarity_threshold: float = 0.55
log_level: str = "INFO"


class Config:
    env_file = ".env"


settings = Settings()
