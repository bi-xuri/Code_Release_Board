import httpx

from app.connectors.base import AssetInfo, ReleaseInfo


class GenericConnector:
    def __init__(self, api_base_url: str, token: str | None = None) -> None:
        self.api_base_url = api_base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}

    async def list_releases(self) -> list[ReleaseInfo]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(f"{self.api_base_url}/releases", headers=self.headers)
            response.raise_for_status()
            data = response.json()
        releases = data.get("releases", data if isinstance(data, list) else [])
        return [
            ReleaseInfo(
                version=item.get("version") or item.get("tag_name"),
                tag_name=item.get("tag_name"),
                title=item.get("title"),
                description=item.get("description"),
                source_url=item.get("source_url"),
                released_at=None,
                is_prerelease=bool(item.get("is_prerelease")),
                assets=[
                    AssetInfo(
                        name=asset.get("name") or asset.get("file_name") or "asset",
                        file_name=asset.get("file_name"),
                        file_size=asset.get("file_size"),
                        content_type=asset.get("content_type"),
                        download_url=asset.get("download_url"),
                        metadata=asset,
                    )
                    for asset in item.get("assets", [])
                    if asset.get("download_url")
                ],
                raw=item,
            )
            for item in releases
            if item.get("version") or item.get("tag_name")
        ]

    async def get_release_detail(self, version: str) -> ReleaseInfo | None:
        releases = await self.list_releases()
        return next((release for release in releases if release.version == version), None)

    async def list_assets(self, release: ReleaseInfo) -> list[AssetInfo]:
        return release.assets

    async def download_asset(self, asset: AssetInfo) -> bytes:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            response = await client.get(asset.download_url, headers=self.headers)
            response.raise_for_status()
            return response.content
