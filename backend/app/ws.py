import json
from fastapi import WebSocket
from typing import List

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        try:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        except ValueError:
            pass

    async def broadcast(self, message: dict):
        # We need to handle potential disconnects during broadcast
        dead_connections = []
        # Iterate over a copy to allow modification during await calls if necessary
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)
        
        for dead in dead_connections:
            self.disconnect(dead)

    def broadcast_sync(self, message: dict):
        """Thread-safe way to broadcast websocket messages from sync code."""
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast(message))
        except RuntimeError:
            pass

manager = ConnectionManager()
