from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    file_name: str | None
    file_size: int | None
    content_type: str | None
    download_url: str
    local_path: str | None
    sha256: str | None
    md5: str | None
    source: str
    created_at: datetime


class ReleaseSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    repository_id: int
    project_id: int
    version: str
    tag_name: str | None
    title: str | None
    description: str | None
    release_type: str
    source_url: str | None
    released_at: datetime | None
    is_latest: bool
    is_prerelease: bool
    updated_at: datetime
    repository_name: str | None = None


class ReleaseDetail(ReleaseSummary):
    assets: list[AssetOut] = []


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    device_model: str | None
    hardware_version: str | None
    created_at: datetime
    latest_release: ReleaseSummary | None = None
