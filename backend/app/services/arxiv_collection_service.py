from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.models.discovery import ArxivCollection, ArxivCollectionItem, ArxivTranslateDecision
from backend.app.models.user import User
from backend.app.repositories.arxiv_repository import ArxivRepository
from backend.app.schemas.discovery import (
    DiscoveryCollectionCreateRequest,
    DiscoveryCollectionItemCreateRequest,
    DiscoveryCollectionUpdateRequest,
)


class ArxivCollectionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = ArxivRepository(db)

    def list_collections(self, *, current_user: User) -> list[ArxivCollection]:
        return self.repository.list_collections(current_user=current_user)

    def create_collection(
        self,
        payload: DiscoveryCollectionCreateRequest,
        *,
        current_user: User,
    ) -> ArxivCollection:
        collection = ArxivCollection(
            user_id=current_user.id,
            name=payload.name.strip(),
            description=self._clean_nullable_text(payload.description),
            categories_json=self._normalize_categories(payload.categories_json),
            prefer_keywords=self._clean_nullable_text(payload.prefer_keywords),
            avoid_keywords=self._clean_nullable_text(payload.avoid_keywords),
            translation_mode=payload.translation_mode,
            auto_translate_enabled=payload.auto_translate_enabled,
        )
        self.repository.add_collection(collection)
        self.repository.commit()
        return self._require_collection(collection.id, current_user=current_user)

    def update_collection(
        self,
        collection_id: int,
        payload: DiscoveryCollectionUpdateRequest,
        *,
        current_user: User,
    ) -> ArxivCollection:
        collection = self._require_collection(collection_id, current_user=current_user)
        if payload.name is not None:
            collection.name = payload.name.strip()
        if payload.description is not None:
            collection.description = self._clean_nullable_text(payload.description)
        if payload.categories_json is not None:
            collection.categories_json = self._normalize_categories(payload.categories_json)
        if payload.prefer_keywords is not None:
            collection.prefer_keywords = self._clean_nullable_text(payload.prefer_keywords)
        if payload.avoid_keywords is not None:
            collection.avoid_keywords = self._clean_nullable_text(payload.avoid_keywords)
        if payload.translation_mode is not None:
            collection.translation_mode = payload.translation_mode
        if payload.auto_translate_enabled is not None:
            collection.auto_translate_enabled = payload.auto_translate_enabled
        self.repository.commit()
        return self._require_collection(collection_id, current_user=current_user)

    def add_item(
        self,
        collection_id: int,
        payload: DiscoveryCollectionItemCreateRequest,
        *,
        current_user: User,
    ) -> ArxivCollectionItem:
        collection = self._require_collection(collection_id, current_user=current_user)
        paper = self.repository.get_paper_by_id(payload.paper_id)
        if paper is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found.")

        item = self.repository.get_collection_item(collection_id=collection.id, paper_id=paper.id)
        if item is None:
            item = ArxivCollectionItem(
                collection_id=collection.id,
                paper_id=paper.id,
                added_by_user_id=current_user.id,
                note=self._clean_nullable_text(payload.note),
                translate_decision=payload.translate_decision,
            )
            self.repository.add_collection_item(item)
        else:
            item.note = self._clean_nullable_text(payload.note)
            item.translate_decision = payload.translate_decision

        self.repository.commit()
        refreshed = self.repository.get_collection(collection.id, current_user=current_user)
        if refreshed is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Collection refresh failed.")
        refreshed_item = self.repository.get_collection_item(collection_id=collection.id, paper_id=paper.id)
        if refreshed_item is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Collection item refresh failed.")
        return refreshed_item

    def remove_item(self, collection_id: int, paper_id: int, *, current_user: User) -> None:
        collection = self._require_collection(collection_id, current_user=current_user)
        item = self.repository.get_collection_item(collection_id=collection.id, paper_id=paper_id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection item not found.")
        self.repository.delete_collection_item(item)
        self.repository.commit()

    def delete_collection(self, collection_id: int, *, current_user: User) -> None:
        collection = self._require_collection(collection_id, current_user=current_user)
        self.repository.delete_collection(collection)
        self.repository.commit()

    def update_item_translate_decision(
        self,
        *,
        collection_id: int,
        paper_id: int,
        translate_decision: ArxivTranslateDecision,
        current_user: User,
    ) -> ArxivCollectionItem | None:
        self._require_collection(collection_id, current_user=current_user)
        item = self.repository.get_collection_item(collection_id=collection_id, paper_id=paper_id)
        if item is None:
            return None
        item.translate_decision = translate_decision
        self.repository.commit()
        return item

    def _require_collection(self, collection_id: int, *, current_user: User) -> ArxivCollection:
        collection = self.repository.get_collection(collection_id, current_user=current_user)
        if collection is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found.")
        return collection

    def _normalize_categories(self, values: list[str]) -> list[str]:
        categories: list[str] = []
        seen: set[str] = set()
        for value in values:
            normalized = value.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            categories.append(normalized)
        return categories

    def _clean_nullable_text(self, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None
