import logging
import os
import uuid
from typing import Optional

import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from audio_processor import audio_processor
from config import settings
from model_service import model_service
from session_manager import session_manager

from fastapi import Body
import base64
import io

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(title="Qwen Voice Chat API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Should be more restrictive in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConfigRequest(BaseModel):
    clientId: str
    voiceType: str


class PauseRequest(BaseModel):
    clientId: str
    isPaused: bool


class EndRequest(BaseModel):
    clientId: str


@app.on_event("startup")
async def startup_event():
    # Preload model
    await model_service.initialize()
    logging.info("Service started, model is loading...")


@app.post("/api/config")
async def configure_session(config: ConfigRequest):
    """Configure a new voice chat session"""
    if config.voiceType not in settings.AVAILABLE_VOICES:
        config.voiceType = settings.DEFAULT_VOICE

    session_manager.create_or_update_session(config.clientId, {
        'voiceType': config.voiceType,
        'isPaused': False,
        'isProcessing': False
    })

    return {"status": "success", "clientId": config.clientId}


@app.post("/api/chat")
async def process_audio(request_data: dict = Body(...)):
    """处理上传的音频并返回AI响应"""
    client_id = request_data.get("clientId")
    voice_type = request_data.get("voiceType")
    base64_audio = request_data.get("audio")
    audio_type = request_data.get("audioType", "webm")  # 获取音频格式类型

    try:
        # 解码 base64 音频
        audio_bytes = base64.b64decode(base64_audio)

        # 转换音频为 float32 数组
        if audio_type == "webm":
            audio_data = audio_processor.webm_to_float32(audio_bytes)
        else:
            raise ValueError(f"不支持的音频格式: {audio_type}")

        # 处理音频
        response = await model_service.process_audio(audio_data, voice_type)

        # 转换响应音频为 WAV
        audio_output = audio_processor.float32_to_wav(
            response["audio"],
            response["sample_rate"]
        )

        # 转换为 base64
        base64_output = base64.b64encode(audio_output).decode()

        return {
            "status": "success",
            "aiTranscript": response["text"],
            "audioResponse": base64_output
        }

    except Exception as e:
        logging.error(f"处理音频时出错: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.post("/api/pause")
async def pause_session(pause_request: PauseRequest):
    """Pause or resume a session"""
    if not session_manager.session_exists(pause_request.clientId):
        raise HTTPException(status_code=404, detail="Session not found")

    session_manager.set_pause_state(pause_request.clientId, pause_request.isPaused)
    return {"status": "success", "isPaused": pause_request.isPaused}


@app.post("/api/end")
async def end_session(end_request: EndRequest):
    """End a session and clean up resources"""
    session_manager.delete_session(end_request.clientId)
    return {"status": "success", "message": "Session ended"}


@app.get("/")
async def get_status():
    return {"status": "running", "model": settings.MODEL_PATH}


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )