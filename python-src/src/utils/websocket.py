import asyncio
import logging
from fastapi import WebSocket
from typing import Dict

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.voice_types: Dict[str, str] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.voice_types[client_id] = "Chelsie"  # 默认值
        logger.info(f"Client {client_id} connected")

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.voice_types:
            del self.voice_types[client_id]
        logger.info(f"Client {client_id} disconnected")

    def get_voice_type(self, client_id: str) -> str:
        return self.voice_types.get(client_id, "Chelsie")

    def set_voice_type(self, client_id: str, voice_type: str):
        self.voice_types[client_id] = voice_type
