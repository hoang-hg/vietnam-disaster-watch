import asyncio
import json
from typing import AsyncGenerator

# Simple in-memory broadcaster for Server-Sent Events (SSE)
_subscribers: list[asyncio.Queue] = []

def _make_message(data: dict) -> str:
    return json.dumps(data, default=str, ensure_ascii=False)

def subscribe() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _subscribers.append(q)
    return q

def unsubscribe(q: asyncio.Queue) -> None:
    try:
        _subscribers.remove(q)
    except ValueError:
        pass

async def publish_event(data: dict) -> None:
    msg = _make_message(data)
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
        # cleanup handled by unsubscribe
        return
