import logging
from pathlib import Path
from typing import Dict

import soundfile as sf
import torch
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from qwen_omni_utils import process_mm_info
from transformers import Qwen2_5OmniModel, Qwen2_5OmniProcessor

from .config import Settings
from .utils.audio import AudioProcessor
from .utils.audio_handler import AudioHandler
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

model_path = "/root/autodl-tmp/model/Qwen2_5-Omni-7B"


class QwenModel:
    def __init__(self):
        self.model = Qwen2_5OmniModel.from_pretrained(
            model_path,
            torch_dtype=torch.bfloat16,
            device_map="auto",
            attn_implementation="flash_attention_2",
            enable_audio_output=True,
        )
        self.processor = Qwen2_5OmniProcessor.from_pretrained(model_path)
        self.conversations: Dict[str, list] = {}
        self.audio_handler = AudioHandler()

    async def process_audio(self, client_id: str, audio_data: bytes, voice_type: str = "Chelsie"):
        temp_path = None
        try:
            # 保存音频文件
            temp_path, audio_array = self.audio_handler.save_audio(audio_data, client_id)

            # 初始化对话
            if client_id not in self.conversations:
                self.conversations[client_id] = [{
                    "role": "system",
                    "content": "You are Qwen..."
                }]

            # 添加用户输入
            self.conversations[client_id].append({
                "role": "user",
                "content": [{"type": "audio", "audio": temp_path}]
            })

            # 处理和生成响应
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
            ).to(self.model.device, self.model.dtype)

            # 生成响应
            text_ids, audio = self.model.generate(
                **inputs,
                use_audio_in_video=True,
                spk=voice_type
            )

            response_text = self.processor.batch_decode(
                text_ids,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False
            )[0]

            # 保存响应
            audio_bytes = self.audio_handler.save_response(
                audio.reshape(-1).detach().cpu().numpy()
            )

            # 更新对话历史
            self.conversations[client_id].append({
                "role": "assistant",
                "content": response_text
            })

            return {
                "text": response_text,
                "audio": audio_bytes
            }

        except Exception as e:
            logger.error(f"Error in process_audio: {str(e)}")
            raise

        finally:
            # 清理临时文件
            if temp_path:
                Path(temp_path).unlink(missing_ok=True)
            # 定期清���过期文件
            self.audio_handler.cleanup_temp_files()


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
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
