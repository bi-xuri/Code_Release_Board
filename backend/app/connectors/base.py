from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol


@dataclass
class AssetInfo:
    name: str
    download_url: str
    file_name: str | None = None
    file_size: int | None = None
    content_type: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReleaseInfo:
    version: str
    tag_name: str | None
    title: str | None
    description: str | None
    source_url: str | None
    released_at: datetime | None
    is_prerelease: bool = False
    assets: list[AssetInfo] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


class BaseConnector(Protocol):
    async def list_releases(self) -> list[ReleaseInfo]:
        ...

    async def get_release_detail(self, version: str) -> ReleaseInfo | None:
        ...

    async def list_assets(self, release: ReleaseInfo) -> list[AssetInfo]:
        ...

    async def download_asset(self, asset: AssetInfo) -> bytes:
        ...
