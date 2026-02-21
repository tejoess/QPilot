# app/websocket/manager.py
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.connections = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.connections[session_id] = websocket

    async def send(self, session_id: str, message: str):
        if session_id in self.connections:
            await self.connections[session_id].send_text(message)

manager = ConnectionManager()
