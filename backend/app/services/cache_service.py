from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.models.cache import CacheEntryStatus, TranslationCacheEntry


CACHE_OPTIONS_INCLUDE_KEYS = frozenset({"terminology", "custom_prompt", "glossary"})


def _normalize_arxiv_id(arxiv_id: str) -> str:
    return arxiv_id.strip().lower().replace("_", ".")


def _options_hash(options: dict) -> str:
    filtered = {k: v for k, v in sorted(options.items()) if k in CACHE_OPTIONS_INCLUDE_KEYS}
    return hashlib.sha256(json.dumps(filtered, sort_keys=True).encode()).hexdigest()[:16]


def build_cache_key(
    engine: str,
    source_fingerprint: str,
    source_language: str,
    target_language: str,
    model_name: str,
    options: dict,
    cache_version: int,
) -> str:
    payload = {
        "engine": engine,
        "source_fingerprint": source_fingerprint,
        "source_language": source_language,
        "target_language": target_language,
        "model_name": model_name,
        "options_hash": _options_hash(options),
        "cache_version": cache_version,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


class CacheService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()

    def lookup(self, cache_key: str) -> TranslationCacheEntry | None:
        if not self.settings.cache_enabled:
            return None
        entry = self.db.query(TranslationCacheEntry).filter_by(cache_key=cache_key).first()
        if entry and entry.status == CacheEntryStatus.READY:
            return entry
        return None

    def lookup_building(self, cache_key: str) -> TranslationCacheEntry | None:
        return self.db.query(TranslationCacheEntry).filter_by(
            cache_key=cache_key, status=CacheEntryStatus.BUILDING
        ).first()

    def create_building(
        self,
        *,
        cache_key: str,
        engine: str,
        source_fingerprint_type: str,
        normalized_arxiv_id: str | None,
        source_file_hash: str | None,
        source_language: str,
        target_language: str,
        model_name: str,
        options: dict,
        canonical_task_id: str,
    ) -> TranslationCacheEntry:
        entry = TranslationCacheEntry(
            cache_key=cache_key,
            engine=engine,
            source_fingerprint_type=source_fingerprint_type,
            normalized_arxiv_id=normalized_arxiv_id,
            source_file_hash=source_file_hash,
            source_language=source_language,
            target_language=target_language,
            model_name=model_name,
            options_hash=_options_hash(options),
            cache_version=self.settings.cache_version,
            status=CacheEntryStatus.BUILDING,
            canonical_task_id=canonical_task_id,
        )
        self.db.add(entry)
        return entry

    def mark_ready(self, entry: TranslationCacheEntry, artifact_manifest: dict) -> None:
        entry.status = CacheEntryStatus.READY
        entry.artifact_manifest_json = artifact_manifest

    def mark_failed(self, entry: TranslationCacheEntry) -> None:
        if entry.status == CacheEntryStatus.BUILDING:
            entry.status = CacheEntryStatus.FAILED

    def record_hit(self, entry: TranslationCacheEntry) -> None:
        entry.hit_count += 1
        entry.last_hit_at = datetime.now(timezone.utc)

    def invalidate(self, entry: TranslationCacheEntry) -> None:
        entry.status = CacheEntryStatus.INVALIDATED

    def get_cache_key_for_arxiv(
        self, engine: str, arxiv_id: str, source_language: str, target_language: str,
        model_name: str, options: dict
    ) -> tuple[str, str, str]:
        """Returns (cache_key, normalized_arxiv_id, source_fingerprint)."""
        normalized = _normalize_arxiv_id(arxiv_id)
        fingerprint = f"arxiv:{normalized}"
        key = build_cache_key(
            engine=engine,
            source_fingerprint=fingerprint,
            source_language=source_language,
            target_language=target_language,
            model_name=model_name,
            options=options,
            cache_version=self.settings.cache_version,
        )
        return key, normalized, fingerprint

    def get_cache_key_for_file(
        self, engine: str, file_hash: str, source_language: str, target_language: str,
        model_name: str, options: dict
    ) -> tuple[str, str]:
        """Returns (cache_key, source_fingerprint)."""
        fingerprint = f"file:{file_hash}"
        key = build_cache_key(
            engine=engine,
            source_fingerprint=fingerprint,
            source_language=source_language,
            target_language=target_language,
            model_name=model_name,
            options=options,
            cache_version=self.settings.cache_version,
        )
        return key, fingerprint
