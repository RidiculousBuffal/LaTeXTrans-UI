from pydantic import BaseModel, field_validator

from backend.app.schemas.discovery import DiscoveryRunResponse


class QuotaAdjustRequest(BaseModel):
    delta: int
    reason: str = "manual adjustment"


class QuotaAdjustResponse(BaseModel):
    user_id: str
    new_balance: int
    delta: int


class UserAdminItem(BaseModel):
    id: str
    username: str
    role: str
    is_active: bool
    quota_balance: int

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    items: list[UserAdminItem]
    total: int


class AdminCreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "user"
    initial_quota: int = 0

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ("user", "admin"):
            raise ValueError("role must be 'user' or 'admin'")
        return v


class AdminChangePasswordRequest(BaseModel):
    new_password: str


class SharingState(BaseModel):
    task_id: str
    visibility: str
    shared_users: list[dict]


class SharingUpdateRequest(BaseModel):
    visibility: str | None = None
    grant_usernames: list[str] = []


class CacheEntryItem(BaseModel):
    id: str
    cache_key: str
    engine: str
    status: str
    hit_count: int
    canonical_task_id: str | None
    created_at: str

    model_config = {"from_attributes": True}


class CacheListResponse(BaseModel):
    items: list[CacheEntryItem]
    total: int


class AdminDiscoverySyncRequest(BaseModel):
    source_run_date: str | None = None
    force_refresh: bool = False
    run_inline: bool = False


class AdminDiscoveryRunListResponse(BaseModel):
    items: list[DiscoveryRunResponse]
    total: int
    page: int
    page_size: int
