from __future__ import annotations

import logging

from pythonjsonlogger.json import JsonFormatter


def configure_logging() -> None:
    root_logger = logging.getLogger()

    if getattr(root_logger, "_latex_trans_logging_configured", False):
        return

    handler = logging.StreamHandler()
    handler.setFormatter(
        JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
            rename_fields={"asctime": "timestamp", "levelname": "level", "name": "logger"},
        )
    )

    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
    root_logger._latex_trans_logging_configured = True  # type: ignore[attr-defined]
