from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.discovery import (
    DiscoveryCollectionCreateRequest,
    DiscoveryCollectionItemCreateRequest,
    DiscoveryCollectionListResponse,
    DiscoveryCollectionResponse,
    DiscoveryCollectionUpdateRequest,
    DiscoveryDailyDigestResponse,
    DiscoveryPaperDetailResponse,
    DiscoveryPaperListResponse,
    DiscoveryPaperTaskCreateRequest,
    DiscoveryPaperTaskResponse,
)
from backend.app.services.arxiv_collection_service import ArxivCollectionService
from backend.app.services.arxiv_discovery_service import ArxivDiscoveryService
from backend.app.services.auth_service import get_current_user, get_optional_user


router = APIRouter(prefix="/discovery", tags=["discovery"])


def get_discovery_service(db: Session = Depends(get_db)) -> ArxivDiscoveryService:
    return ArxivDiscoveryService(db)


def get_collection_service(db: Session = Depends(get_db)) -> ArxivCollectionService:
    return ArxivCollectionService(db)


@router.get("/papers", response_model=DiscoveryPaperListResponse)
def list_papers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    category: str | None = None,
    keyword: str | None = None,
    worth_read: bool | None = None,
    translated: bool | None = None,
    collection_id: int | None = None,
    source_run_date: date | None = None,
    service: ArxivDiscoveryService = Depends(get_discovery_service),
    current_user: User = Depends(get_current_user),
) -> DiscoveryPaperListResponse:
    return service.list_papers(
        page=page,
        page_size=page_size,
        category=category,
        keyword=keyword,
        worth_read=worth_read,
        translated=translated,
        collection_id=collection_id,
        source_run_date=source_run_date,
        current_user=current_user,
    )


@router.get("/public/papers", response_model=DiscoveryPaperListResponse)
def list_public_papers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    category: str | None = None,
    keyword: str | None = None,
    worth_read: bool | None = None,
    translated: bool | None = None,
    source_run_date: date | None = None,
    service: ArxivDiscoveryService = Depends(get_discovery_service),
) -> DiscoveryPaperListResponse:
    return service.list_papers(
        page=page,
        page_size=page_size,
        category=category,
        keyword=keyword,
        worth_read=worth_read,
        translated=translated,
        collection_id=None,
        source_run_date=source_run_date,
        current_user=None,
    )


@router.get("/papers/{paper_id}", response_model=DiscoveryPaperDetailResponse)
def get_paper_detail(
    paper_id: int,
    service: ArxivDiscoveryService = Depends(get_discovery_service),
    current_user: User = Depends(get_current_user),
) -> DiscoveryPaperDetailResponse:
    return service.get_paper_detail(paper_id, current_user=current_user)


@router.get("/public/papers/{paper_id}", response_model=DiscoveryPaperDetailResponse)
def get_public_paper_detail(
    paper_id: int,
    service: ArxivDiscoveryService = Depends(get_discovery_service),
    current_user: User | None = Depends(get_optional_user),
) -> DiscoveryPaperDetailResponse:
    return service.get_paper_detail(paper_id, current_user=current_user)


@router.post("/papers/{paper_id}/tasks", response_model=DiscoveryPaperTaskResponse, status_code=status.HTTP_201_CREATED)
def create_task_from_paper(
    paper_id: int,
    payload: DiscoveryPaperTaskCreateRequest,
    service: ArxivDiscoveryService = Depends(get_discovery_service),
    current_user: User = Depends(get_current_user),
) -> DiscoveryPaperTaskResponse:
    return service.create_task_from_paper(paper_id, payload, current_user=current_user)


@router.get("/daily-digest", response_model=DiscoveryDailyDigestResponse)
def get_daily_digest(
    service: ArxivDiscoveryService = Depends(get_discovery_service),
    current_user: User = Depends(get_current_user),
) -> DiscoveryDailyDigestResponse:
    return service.get_daily_digest(current_user=current_user)


@router.get("/collections", response_model=DiscoveryCollectionListResponse)
def list_collections(
    service: ArxivDiscoveryService = Depends(get_discovery_service),
    current_user: User = Depends(get_current_user),
) -> DiscoveryCollectionListResponse:
    return service.list_collections(current_user=current_user)


@router.post("/collections", response_model=DiscoveryCollectionResponse, status_code=status.HTTP_201_CREATED)
def create_collection(
    payload: DiscoveryCollectionCreateRequest,
    service: ArxivCollectionService = Depends(get_collection_service),
    discovery_service: ArxivDiscoveryService = Depends(get_discovery_service),
    current_user: User = Depends(get_current_user),
) -> DiscoveryCollectionResponse:
    collection = service.create_collection(payload, current_user=current_user)
    return discovery_service._build_collection_response(collection, current_user=current_user)


@router.patch("/collections/{collection_id}", response_model=DiscoveryCollectionResponse)
def update_collection(
    collection_id: int,
    payload: DiscoveryCollectionUpdateRequest,
    service: ArxivCollectionService = Depends(get_collection_service),
    discovery_service: ArxivDiscoveryService = Depends(get_discovery_service),
    current_user: User = Depends(get_current_user),
) -> DiscoveryCollectionResponse:
    collection = service.update_collection(collection_id, payload, current_user=current_user)
    return discovery_service._build_collection_response(collection, current_user=current_user)


@router.post("/collections/{collection_id}/items", response_model=DiscoveryCollectionResponse)
def add_collection_item(
    collection_id: int,
    payload: DiscoveryCollectionItemCreateRequest,
    service: ArxivCollectionService = Depends(get_collection_service),
    discovery_service: ArxivDiscoveryService = Depends(get_discovery_service),
    current_user: User = Depends(get_current_user),
) -> DiscoveryCollectionResponse:
    service.add_item(collection_id, payload, current_user=current_user)
    collection = service._require_collection(collection_id, current_user=current_user)
    return discovery_service._build_collection_response(collection, current_user=current_user)


@router.delete("/collections/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection(
    collection_id: int,
    service: ArxivCollectionService = Depends(get_collection_service),
    current_user: User = Depends(get_current_user),
) -> Response:
    service.delete_collection(collection_id, current_user=current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/collections/{collection_id}/items/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection_item(
    collection_id: int,
    paper_id: int,
    service: ArxivCollectionService = Depends(get_collection_service),
    current_user: User = Depends(get_current_user),
) -> Response:
    service.remove_item(collection_id, paper_id, current_user=current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
