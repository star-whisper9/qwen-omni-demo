from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # 基础配置
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS配置
    CORS_ORIGINS: List[str] = ["*"]

    # 模型配置
    MODEL_NAME: str = "Qwen/Qwen2.5-Omni-7B"
    ENABLE_FLASH_ATTENTION: bool = True

    # 音频配置
    SAMPLE_RATE: int = 24000
    CHUNK_SIZE: int = 4096
    VAD_THRESHOLD: float = 0.5

    # WebSocket配置
    WS_HEARTBEAT_INTERVAL: int = 30  # seconds

    class Config:
        env_file = ".env"
