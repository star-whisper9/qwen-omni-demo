import logging

import torch
from qwen_omni_utils import process_mm_info
from transformers import Qwen2_5OmniModel, Qwen2_5OmniProcessor

from audio_processor import *
from config import settings


class ModelService:
    def __init__(self):
        self.model = None
        self.processor = None
        self.initialized = False

    async def initialize(self):
        if self.initialized:
            return

        logging.info(f"正在加载模型: {settings.MODEL_PATH}")

        # 设置模型加载参数
        model_kwargs = {
            "torch_dtype": getattr(torch, settings.TORCH_DTYPE),
            "device_map": settings.DEVICE_MAP,
            "enable_audio_output": True
        }

        # 添加FlashAttention支持
        if settings.USE_FLASH_ATTENTION:
            model_kwargs["attn_implementation"] = "flash_attention_2"

        # 加载模型和处理器
        self.model = Qwen2_5OmniModel.from_pretrained(settings.MODEL_PATH, **model_kwargs)
        self.processor = Qwen2_5OmniProcessor.from_pretrained(settings.MODEL_PATH)

        logging.info("模型加载完成")
        self.initialized = True

    async def process_audio(self, audio_data, voice_type, first_utterance=False):
        """处理音频数据并返回模型响应"""
        if not self.initialized:
            await self.initialize()

        try:
            import tempfile
            import os

            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_filename = temp_file.name
                audio_bytes = audio_processor.float32_to_wav(audio_data, 24000)
                temp_file.write(audio_bytes)

            try:
                file_url = f"file://{temp_filename}"
                logging.info(file_url)

                conversation = [
                    {
                        "role": "system",
                        "content": settings.SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "audio", "audio": file_url}
                        ]
                    }
                ]

                text = self.processor.apply_chat_template(conversation, add_generation_prompt=True, tokenize=False)
                audios, images, videos = process_mm_info(conversation, use_audio_in_video=False)
                inputs = self.processor(
                    text=text,
                    audios=audios,
                    images=images,
                    videos=videos,
                    return_tensors="pt",
                    padding=True,
                    use_audio_in_video=False
                )
                inputs = inputs.to(self.model.device).to(self.model.dtype)

                text_ids, audio = self.model.generate(
                    **inputs,
                    use_audio_in_video=False,
                    spk=voice_type,
                    max_new_tokens=256,
                    return_audio=True
                )

                # 解码文本输出
                full_text = self.processor.batch_decode(
                    text_ids,
                    skip_special_tokens=True,
                    clean_up_tokenization_spaces=False
                )[0]

                # 提取助手回复部分
                try:
                    # 尝试根据角色标识分割
                    if "assistant" in full_text.lower():
                        response_text = full_text.split("assistant")[-1].strip()
                    else:
                        # 如果找不到明确的分隔符，提取最后的回复部分
                        parts = full_text.split("\n")
                        response_text = parts[-1].strip()

                    # 清理可能的残余标记
                    response_text = response_text.lstrip(": ").strip()
                except Exception as e:
                    logging.warning(f"提取回复文本时出错: {str(e)}")
                    response_text = full_text  # 降级处理：使用完整文本

                # 处理音频输出
                audio_output = audio.reshape(-1).detach().cpu().numpy()

                return {
                    "text": response_text,
                    "audio": audio_output,
                    "sample_rate": 24000
                }

            finally:
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)

        except Exception as e:
            logging.error(f"模型处理错误: {str(e)}")
            raise


model_service = ModelService()
