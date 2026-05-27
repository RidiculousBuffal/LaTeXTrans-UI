from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class UserInfo(BaseModel):
    id: str
    username: str
    role: str
    quota_balance: int
    is_active: bool

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    expires_in: int
    user: UserInfo


class MeResponse(BaseModel):
    id: str
    username: str
    role: str
    quota_balance: int
    is_active: bool


class AuthConfigResponse(BaseModel):
    registration_enabled: bool
