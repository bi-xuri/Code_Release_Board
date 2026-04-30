from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RepositoryBase(BaseModel):
    name: str
    provider: str
    repo_url: str | None = None
    api_base_url: str | None = None
    owner: str | None = None
    repo_name: str | None = None
    project_id: str | None = None
    enabled: bool = True
    sync_interval_minutes: int = 60


class RepositoryCreate(RepositoryBase):
    access_token: str | None = None


class RepositoryUpdate(RepositoryBase):
    access_token: str | None = None


class RepositoryOut(RepositoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    access_token_set: bool
    created_at: datetime
    updated_at: datetime


class SyncLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    repository_id: int
    repository_name: str | None = None
    status: str
    message: str | None
    started_at: datetime
    finished_at: datetime | None


class DownloadLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    release_id: int
    asset_id: int
    asset_name: str | None = None
    ip_address: str | None
    user_agent: str | None
    downloaded_at: datetime
