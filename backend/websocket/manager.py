# app/websocket/manager.py
import json
from datetime import datetime
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.connections = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.connections[session_id] = websocket

    async def send(self, session_id: str, message: str):
        """Legacy send method for backward compatibility"""
        if session_id in self.connections:
            await self.connections[session_id].send_text(message)
    
    async def send_progress(self, session_id: str, step: str, status: str, progress: int = 0, details: str = ""):
        """Send structured progress update"""
        if session_id in self.connections:
            message = {
                "type": "progress",
                "timestamp": datetime.now().isoformat(),
                "step": step,
                "status": status,  # "pending", "running", "completed", "failed"
                "progress": progress,  # 0-100
                "details": details
            }
            try:
                await self.connections[session_id].send_text(json.dumps(message))
            except Exception as e:
                print(f"⚠️ Failed to send progress to {session_id}: {e}")
    
    async def send_log(self, session_id: str, level: str, message: str):
        """Send log message"""
        if session_id in self.connections:
            log_msg = {
                "type": "log",
                "timestamp": datetime.now().isoformat(),
                "level": level,  # "info", "warning", "error"
                "message": message
            }
            try:
                await self.connections[session_id].send_text(json.dumps(log_msg))
            except Exception as e:
                print(f"⚠️ Failed to send log to {session_id}: {e}")
    
    async def send_completion(self, session_id: str, success: bool, data: dict = None):
        """Send workflow completion message"""
        if session_id in self.connections:
            completion_msg = {
                "type": "completion",
                "timestamp": datetime.now().isoformat(),
                "success": success,
                "data": data or {}
            }
            try:
                await self.connections[session_id].send_text(json.dumps(completion_msg))
            except Exception as e:
                print(f"⚠️ Failed to send completion to {session_id}: {e}")
    
    def disconnect(self, session_id: str):
        """Disconnect a WebSocket connection"""
        if session_id in self.connections:
            del self.connections[session_id]

manager = ConnectionManager()
