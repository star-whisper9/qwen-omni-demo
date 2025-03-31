import asyncio
import io
import json
import logging
import numpy as np
import soundfile as sf
import torch
import uvicorn
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from qwen_omni_utils import process_mm_info
from transformers import Qwen2_5OmniModel, Qwen2_5OmniProcessor
from typing import Dict

from .config import Settings
from .utils.audio import AudioProcessor
from .utils.websocket import ConnectionManager

app = FastAPI()
settings = Settings()

# CORS设置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化WebSocket连接管理器
connection_manager = ConnectionManager()


class QwenModel:
    def __init__(self):
        self.model = Qwen2_5OmniModel.from_pretrained(
            "Qwen/Qwen2.5-Omni-7B",
            torch_dtype=torch.bfloat16,
            device_map="auto",
            attn_implementation="flash_attention_2",
            enable_audio_output=True,
        )
        self.processor = Qwen2_5OmniProcessor.from_pretrained("Qwen/Qwen2.5-Omni-7B")
        self.conversations: Dict[str, list] = {}

    async def process_audio(self, client_id: str, audio_data: bytes, voice_type: str = "Chelsie"):
        try:
            # 将音频数据转换为numpy数组
            audio_array = np.frombuffer(audio_data, dtype=np.float32)

            # 构建对话内容
            if client_id not in self.conversations:
                self.conversations[client_id] = [
                    {
                        "role": "system",
                        "content": "You are Qwen, a virtual human developed by the Qwen Team, Alibaba Group, capable of perceiving auditory and visual inputs, as well as generating text and speech.",
                    }
                ]

            # 保存音频到临时文件
            temp_audio_path = f"temp_{client_id}_{datetime.now().timestamp()}.wav"
            sf.write(temp_audio_path, audio_array, samplerate=24000)

            # 添加用户输入到对话
            self.conversations[client_id].append({
                "role": "user",
                "content": [
                    {"type": "audio", "audio": temp_audio_path}
                ]
            })

            # 准备模型输入
            text = self.processor.apply_chat_template(
                self.conversations[client_id],
                add_generation_prompt=True,
                tokenize=False
            )
            audios, images, videos = process_mm_info(
                self.conversations[client_id],
                use_audio_in_video=True
            )

            inputs = self.processor(
                text=text,
                audios=audios,
                images=images,
                videos=videos,
                return_tensors="pt",
                padding=True,
                use_audio_in_video=True
            )
            inputs = inputs.to(self.model.device).to(self.model.dtype)

            # 生成响应
            text_ids, audio = self.model.generate(
                **inputs,
                use_audio_in_video=True,
                spk=voice_type
            )

            # 解码文本
            response_text = self.processor.batch_decode(
                text_ids,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False
            )[0]

            # 将音频转换为bytes
            audio_bytes = io.BytesIO()
            sf.write(
                audio_bytes,
                audio.reshape(-1).detach().cpu().numpy(),
                samplerate=24000,
                format='WAV'
            )

            # 添加助手回复到对话历史
            self.conversations[client_id].append({
                "role": "assistant",
                "content": response_text
            })

            # 清理临时文件
            Path(temp_audio_path).unlink()

            return {
                "text": response_text,
                "audio": audio_bytes.getvalue()
            }

        except Exception as e:
            logger.error(f"Error processing audio: {str(e)}")
            raise


qwen_model = QwenModel()
audio_processor = AudioProcessor()


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await connection_manager.connect(websocket, client_id)
    try:
        while True:
            # 接收音频数据
            data = await websocket.receive_bytes()

            # 处理音频数据
            processed_audio = await audio_processor.process_chunk(data)
            if processed_audio:
                # 获取语音类型设置
                voice_type = connection_manager.get_voice_type(client_id)

                # 使用模型处理音频
                response = await qwen_model.process_audio(
                    client_id,
                    processed_audio,
                    voice_type
                )

                # 发送响应
                await websocket.send_json({
                    "type": "ai_speak_start"
                })

                # 发送文本转写
                await websocket.send_json({
                    "type": "transcript",
                    "text": response["text"],
                    "isUser": False
                })

                # 发送音频数据
                await websocket.send_bytes(response["audio"])

                await websocket.send_json({
                    "type": "ai_speak_end"
                })

    except WebSocketDisconnect:
        connection_manager.disconnect(client_id)


@app.websocket("/ws/{client_id}/config")
async def config_endpoint(websocket: WebSocket, client_id: str):
    await connection_manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_json()
            if data["type"] == "config":
                connection_manager.set_voice_type(client_id, data["voiceType"])
                await websocket.send_json({"status": "ok"})
    except WebSocketDisconnect:
        connection_manager.disconnect(client_id)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
