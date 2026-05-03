from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    anthropic_api_key: str
    whisper_model: str = "large-v3-turbo"
    whisper_device: str = "cuda"
    whisper_compute_type: str = "float16"
    max_audio_duration_seconds: int = 300

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
