from app.connectors.base import AssetInfo, ReleaseInfo


class ManualConnector:
    async def list_releases(self) -> list[ReleaseInfo]:
        return []

    async def get_release_detail(self, version: str) -> ReleaseInfo | None:
        return None

    async def list_assets(self, release: ReleaseInfo) -> list[AssetInfo]:
        return release.assets

    async def download_asset(self, asset: AssetInfo) -> bytes:
        raise NotImplementedError("Manual assets are served from local storage in a later version.")
