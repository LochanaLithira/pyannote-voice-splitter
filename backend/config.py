from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    pyannote_api_key: str
    tmp_dir: str = "./tmp"
    max_file_size_mb: int = 200

    class Config:
        env_file = ".env"

settings = Settings()
os.makedirs(settings.tmp_dir, exist_ok=True)