import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "6006"))
    MODEL_PATH: str = os.getenv("MODEL_PATH", "Qwen/Qwen2.5-Omni-7B")
    USE_FLASH_ATTENTION: bool = os.getenv("USE_FLASH_ATTENTION", "True").lower() == "true"
    DEVICE_MAP: str = os.getenv("DEVICE_MAP", "auto")
    TORCH_DTYPE: str = os.getenv("TORCH_DTYPE", "auto")

    # 支持的声音类型
    AVAILABLE_VOICES: list = ["Chelsie", "Ethan"]
    DEFAULT_VOICE: str = "Chelsie"

    # 系统提示词 - 必须包含以启用音频输出
    SYSTEM_PROMPT: str = "You are Qwen, a virtual human developed by the Qwen Team, Alibaba Group, capable of perceiving auditory and visual inputs, as well as generating text and speech."


settings = Settings()
