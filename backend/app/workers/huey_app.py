from __future__ import annotations

import logging

from backend.app.core.config import get_settings


logger = logging.getLogger(__name__)
settings = get_settings()

try:
    from huey import MemoryHuey, RedisHuey

    HUEY_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover - dependency may be intentionally absent in dev/test envs.
    MemoryHuey = None
    RedisHuey = None
    HUEY_AVAILABLE = False


def create_huey():
    if HUEY_AVAILABLE and settings.discovery_huey_enabled:
        return RedisHuey("latextrans-discovery", url=settings.redis_url)
    if HUEY_AVAILABLE:
        return MemoryHuey("latextrans-discovery")
    return None


huey = create_huey()
