from __future__ import annotations

import time
from collections.abc import Mapping, MutableMapping
from typing import Any


class TaskTimeoutError(RuntimeError):
    pass


def format_timeout_label(timeout_seconds: int) -> str:
    if timeout_seconds % 60 == 0:
        minutes = timeout_seconds // 60
        unit = "minute" if minutes == 1 else "minutes"
        return f"{minutes} {unit}"
    unit = "second" if timeout_seconds == 1 else "seconds"
    return f"{timeout_seconds} {unit}"


def build_task_timeout_message(*, timeout_seconds: int, context: str = "Translation task") -> str:
    return f"{context} timeout: exceeded the maximum runtime of {format_timeout_label(timeout_seconds)}."


def get_task_runtime(config: Mapping[str, Any] | MutableMapping[str, Any] | None) -> MutableMapping[str, Any]:
    if config is None:
        return {}
    runtime = config.get("runtime")
    if isinstance(runtime, MutableMapping):
        return runtime
    if isinstance(config, MutableMapping):
        config["runtime"] = {}
        return config["runtime"]
    return {}


def get_task_timeout_seconds(
    config: Mapping[str, Any] | MutableMapping[str, Any] | None,
    *,
    default_timeout_seconds: int,
) -> int:
    runtime = get_task_runtime(config)
    raw_value = runtime.get("task_timeout_seconds")
    if raw_value in (None, ""):
        return int(default_timeout_seconds)
    return int(raw_value)


def initialize_task_deadline(
    config: MutableMapping[str, Any],
    *,
    default_timeout_seconds: int,
) -> tuple[int, float]:
    runtime = get_task_runtime(config)
    timeout_seconds = get_task_timeout_seconds(config, default_timeout_seconds=default_timeout_seconds)
    deadline_epoch = runtime.get("deadline_epoch")
    if deadline_epoch in (None, ""):
        deadline_epoch = time.time() + timeout_seconds
        runtime["deadline_epoch"] = deadline_epoch
    else:
        deadline_epoch = float(deadline_epoch)
    runtime["task_timeout_seconds"] = timeout_seconds
    return timeout_seconds, float(deadline_epoch)


def get_remaining_task_seconds(config: Mapping[str, Any] | None) -> float | None:
    runtime = get_task_runtime(config)
    deadline_epoch = runtime.get("deadline_epoch")
    if deadline_epoch in (None, ""):
        return None
    return float(deadline_epoch) - time.time()


def ensure_time_remaining(
    config: Mapping[str, Any] | None,
    *,
    default_timeout_seconds: int,
    context: str = "Translation task",
) -> float:
    timeout_seconds = get_task_timeout_seconds(config, default_timeout_seconds=default_timeout_seconds)
    remaining = get_remaining_task_seconds(config)
    if remaining is None:
        return float(timeout_seconds)
    if remaining <= 0:
        raise TaskTimeoutError(build_task_timeout_message(timeout_seconds=timeout_seconds, context=context))
    return max(1.0, remaining)
