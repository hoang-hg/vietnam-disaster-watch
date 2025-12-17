import asyncio
import json
from typing import AsyncGenerator

# Simple in-memory broadcaster for Server-Sent Events (SSE)
_subscribers: list[asyncio.Queue] = []
_buffer_file = None
_buffer_size = 200

def _init_buffer_file():
    global _buffer_file
    if _buffer_file is None:
        from pathlib import Path
        logs_dir = Path(__file__).resolve().parents[1] / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        _buffer_file = logs_dir / "sse_buffer.jsonl"

def _make_message(data: dict) -> str:
    return json.dumps(data, default=str, ensure_ascii=False)

def _append_to_buffer(msg: str) -> None:
    try:
        _init_buffer_file()
        with open(_buffer_file, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
        # trim buffer if too large
        with open(_buffer_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) > _buffer_size:
            with open(_buffer_file, "w", encoding="utf-8") as f:
                f.writelines(lines[-_buffer_size:])
    except Exception:
        pass

def _load_buffer() -> list[str]:
    try:
        _init_buffer_file()
        with open(_buffer_file, "r", encoding="utf-8") as f:
            return [l.strip() for l in f.readlines() if l.strip()]
    except Exception:
        return []

def subscribe() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    # enqueue existing buffer messages so new subscribers catch up
    for msg in _load_buffer():
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
    _append_to_buffer(msg)
    for q in list(_subscribers):
        try:
            await q.put(msg)
        except Exception:
            continue

async def event_generator(q: asyncio.Queue) -> AsyncGenerator[str, None]:
    try:
        while True:
            msg = await q.get()
            yield msg
    finally:
        return
