from datetime import datetime

import httpx

from app.connectors.base import AssetInfo, ReleaseInfo


class GitHubConnector:
    def __init__(
        self,
        owner: str,
        repo: str,
        token: str | None = None,
        api_base_url: str | None = None,
        include_source_archives: bool = False,
    ) -> None:
        self.owner = owner
        self.repo = repo
        self.include_source_archives = include_source_archives
        self.api_base_url = (api_base_url or "https://api.github.com").rstrip("/")
        self.headers = {"Accept": "application/vnd.github+json"}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"

    async def list_releases(self) -> list[ReleaseInfo]:
        url = f"{self.api_base_url}/repos/{self.owner}/{self.repo}/releases"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            return [self._parse_release(item) for item in response.json()]

    async def get_release_detail(self, version: str) -> ReleaseInfo | None:
        url = f"{self.api_base_url}/repos/{self.owner}/{self.repo}/releases/tags/{version}"
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
        assets = [
            AssetInfo(
                name=asset.get("name") or asset.get("label") or "asset",
                file_name=asset.get("name"),
                file_size=asset.get("size"),
                content_type=asset.get("content_type"),
                download_url=asset.get("browser_download_url"),
                metadata=asset,
            )
            for asset in item.get("assets", [])
            if asset.get("browser_download_url")
        ]
        if self.include_source_archives:
            assets.extend(self._parse_source_archives(item))
        released_at = item.get("published_at") or item.get("created_at")
        return ReleaseInfo(
            version=item.get("tag_name") or item.get("name") or str(item.get("id")),
            tag_name=item.get("tag_name"),
            title=item.get("name") or item.get("tag_name"),
            description=item.get("body"),
            source_url=item.get("html_url"),
            released_at=datetime.fromisoformat(released_at.replace("Z", "+00:00")) if released_at else None,
            is_prerelease=bool(item.get("prerelease")),
            assets=assets,
            raw=item,
        )

    def _parse_source_archives(self, item: dict) -> list[AssetInfo]:
        tag_name = item.get("tag_name") or item.get("name") or str(item.get("id"))
        archives = []
        if item.get("zipball_url"):
            archives.append(
                AssetInfo(
                    name="Source code (zip)",
                    file_name=f"{tag_name}.zip",
                    content_type="application/zip",
                    download_url=item["zipball_url"],
                    metadata={"source_archive": True},
                )
            )
        if item.get("tarball_url"):
            archives.append(
                AssetInfo(
                    name="Source code (tar.gz)",
                    file_name=f"{tag_name}.tar.gz",
                    content_type="application/gzip",
                    download_url=item["tarball_url"],
                    metadata={"source_archive": True},
                )
            )
        return archives
