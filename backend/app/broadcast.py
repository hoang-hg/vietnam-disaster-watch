import asyncio
import json
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional
from fastapi import Request

# Simple in-memory broadcaster for Server-Sent Events (SSE)
from collections import deque
_subscribers: list[asyncio.Queue] = []
_buffer_file = None
_buffer_size = 200

# In-memory fast buffer for sub-second catchup
_memory_buffer = deque(maxlen=_buffer_size)
_append_count = 0

def _init_buffer_file():
    global _buffer_file
    if _buffer_file is None:
        from pathlib import Path
        logs_dir = Path(__file__).resolve().parents[1] / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        _buffer_file = logs_dir / "sse_buffer.jsonl"
        # Load existing file into memory on startup
        if _buffer_file.exists():
            try:
                with open(_buffer_file, "r", encoding="utf-8") as f:
                    for line in deque(f, maxlen=_buffer_size):
                        if line.strip(): _memory_buffer.append(line.strip())
            except Exception: pass

def _make_message(data: dict) -> str:
    return json.dumps(data, default=str, ensure_ascii=False)

def _save_buffer_to_disk():
    """Sync memory buffer to disk (Run in thread)."""
    try:
        _init_buffer_file()
        snapshot = list(_memory_buffer)
        with open(_buffer_file, "w", encoding="utf-8") as f:
            for line in snapshot:
                f.write(line + "\n")
    except Exception: pass

async def _append_to_buffer_background(msg: str) -> None:
    global _append_count
    _memory_buffer.append(msg)
    _append_count += 1
    
    # Persistent sync every 10 messages or on high-impact events
    if _append_count >= 10:
        _append_count = 0
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _save_buffer_to_disk)

def subscribe() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    # enqueue existing buffer messages from memory (Instant)
    for msg in list(_memory_buffer):
        try:
            q.put_nowait(msg)
        except Exception:
            pass
    _subscribers.append(q)
    return q

def unsubscribe(q: asyncio.Queue) -> None:
    try:
        _subscribers.remove(q)
    except ValueError:
        pass

async def publish_event(data: dict) -> None:
    msg = _make_message(data)
    await _append_to_buffer_background(msg)
    for q in list(_subscribers):
        try:
            await q.put(msg)
        except Exception:
            continue

# Reference to the main event loop for cross-thread scheduling
_main_loop: asyncio.AbstractEventLoop | None = None

def set_main_loop(loop: asyncio.AbstractEventLoop):
    global _main_loop
    _main_loop = loop
    # Initial load of buffer on main loop setup
    _init_buffer_file()

def publish_event_sync(data: dict) -> None:
    """Thread-safe and sync-safe way to publish events."""
    msg = _make_message(data)
    
    # Dispatch memory update and disk sync to main loop
    if _main_loop and not _main_loop.is_closed():
        def _dispatch():
            _memory_buffer.append(msg)
            for q in list(_subscribers):
                try: q.put_nowait(msg)
                except Exception: pass
            
            # Save to disk asynchronously
            asyncio.create_task(_append_to_buffer_background(msg))
            
        _main_loop.call_soon_threadsafe(_dispatch)
        return

    # Fallback logic (only works if on same loop)
    try:
        loop = asyncio.get_running_loop()
        _memory_buffer.append(msg)
        for q in list(_subscribers):
            try: q.put_nowait(msg)
            except Exception: pass
    except RuntimeError:
        pass

async def event_generator(q: asyncio.Queue, request: Optional[Request] = None) -> AsyncGenerator[str, None]:
    """Centralized generator for SSE events with heartbeats and disconnect handling."""
    try:
        # 1. Connection confirmation
        yield f"data: {{\"type\": \"connected\", \"timestamp\": \"{datetime.now(timezone.utc).isoformat()}\"}}\n\n"
        
        while True:
            # Check for client disconnect if request object provided
            if request and await request.is_disconnected():
                break
                
            try:
                # [OPTIMIZATION] Wait with timeout to send heartbeats (Prevents Heroku/Nginx timeouts)
                msg = await asyncio.wait_for(q.get(), timeout=25.0)
                yield f"data: {msg}\n\n"
            except asyncio.TimeoutError:
                # SSE Heartbeat comment (ignored by most clients, keeps TCP alive)
                yield ": heartbeat\n\n"
            except asyncio.CancelledError:
                break
    finally:
        unsubscribe(q)
