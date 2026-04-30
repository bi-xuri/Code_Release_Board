from datetime import datetime
from urllib.parse import quote

import httpx

from app.connectors.base import AssetInfo, ReleaseInfo


class GitLabConnector:
    def __init__(
        self,
        project_id: str | None = None,
        owner: str | None = None,
        repo: str | None = None,
        token: str | None = None,
        api_base_url: str | None = None,
    ) -> None:
        project = project_id or f"{owner}/{repo}"
        self.project = quote(project or "", safe="")
        self.api_base_url = (api_base_url or "https://gitlab.com/api/v4").rstrip("/")
        self.headers: dict[str, str] = {}
        if token:
            self.headers["PRIVATE-TOKEN"] = token

    async def list_releases(self) -> list[ReleaseInfo]:
        url = f"{self.api_base_url}/projects/{self.project}/releases"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return [self._parse_release(item) for item in response.json()]

    async def get_release_detail(self, version: str) -> ReleaseInfo | None:
        url = f"{self.api_base_url}/projects/{self.project}/releases/{quote(version, safe='')}"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=self.headers)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return self._parse_release(response.json())

    async def list_assets(self, release: ReleaseInfo) -> list[AssetInfo]:
        return release.assets

    async def download_asset(self, asset: AssetInfo) -> bytes:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            response = await client.get(asset.download_url, headers=self.headers)
            response.raise_for_status()
            return response.content

    def _parse_release(self, item: dict) -> ReleaseInfo:
        links = item.get("assets", {}).get("links", [])
        assets = [
            AssetInfo(
                name=link.get("name") or link.get("link_type") or "asset",
                file_name=link.get("name"),
                download_url=link.get("direct_asset_url") or link.get("url"),
                metadata=link,
            )
            for link in links
            if link.get("direct_asset_url") or link.get("url")
        ]
        released_at = item.get("released_at") or item.get("created_at")
        milestones = item.get("milestones") or []
        is_prerelease = any("beta" in str(m.get("title", "")).lower() for m in milestones)
        return ReleaseInfo(
            version=item.get("tag_name") or item.get("name"),
            tag_name=item.get("tag_name"),
            title=item.get("name") or item.get("tag_name"),
            description=item.get("description"),
            source_url=item.get("_links", {}).get("self") or item.get("commit", {}).get("web_url"),
            released_at=datetime.fromisoformat(released_at.replace("Z", "+00:00")) if released_at else None,
            is_prerelease=is_prerelease,
            assets=assets,
            raw=item,
        )
