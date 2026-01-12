import asyncio
from fastapi import WebSocket
from typing import Set
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Optimization: Use a Set for faster O(1) removals and existence checks
        self.active_connections: Set[WebSocket] = set()
        self._main_loop = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.debug(f"WS Connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.debug(f"WS Disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        if not self.active_connections:
            return

        # Optimization: Create tasks for parallel sending instead of sequential await
        # This significantly reduces latency when broadcasting to many clients
        # Use a snapshot of connections to avoid modification during iteration issues
        connections = list(self.active_connections)
        
        # Create a list of coroutines
        tasks = [self._safe_send(ws, message) for ws in connections]
        
        # Run all sends concurrently
        if tasks:
            await asyncio.gather(*tasks)

    async def _safe_send(self, websocket: WebSocket, message: dict):
        """Helper to safely send a message and handle disconnects automatically."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            # Most likely the client disconnected abnormally
            # logger.warning(f"WS Send Error: {e}")
            self.disconnect(websocket)

    def set_main_loop(self, loop):
        self._main_loop = loop

    def broadcast_sync(self, message: dict):
        """Thread-safe way to broadcast websocket messages from sync code (e.g. background threads)."""
        if self._main_loop and not self._main_loop.is_closed():
             self._main_loop.call_soon_threadsafe(
                 lambda: asyncio.create_task(self.broadcast(message))
             )
        else:
            # Fallback for when running within an event loop context (e.g. testing)
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.broadcast(message))
            except RuntimeError:
                logger.warning("Could not find event loop to broadcast message")
                pass

manager = ConnectionManager()
