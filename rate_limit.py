import asyncio
import time

_last_request_ts: float = 0.0
_lock = asyncio.Lock()


async def acquire(min_interval_seconds: float) -> tuple[bool, int]:
    global _last_request_ts
    async with _lock:
        now = time.monotonic()
        elapsed = now - _last_request_ts
        if elapsed < min_interval_seconds:
            return False, int(min_interval_seconds - elapsed) + 1
        _last_request_ts = now
        return True, 0
