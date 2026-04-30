import asyncio
from urllib.parse import urlsplit, urlunsplit

from app.connectors.base import AssetInfo, ReleaseInfo


class CNBConnector:
    def __init__(
        self,
        repo_url: str | None = None,
        owner: str | None = None,
        repo: str | None = None,
        token: str | None = None,
    ) -> None:
        self.repo_url = self._build_repo_url(repo_url, owner, repo)
        self.token = token

    async def list_releases(self) -> list[ReleaseInfo]:
        tag_names = await self._list_tags()
        releases = [self._tag_to_release(tag_name) for tag_name in tag_names]
        releases.sort(key=self._sort_key, reverse=True)
        for index, release in enumerate(releases):
            release.is_prerelease = self._is_prerelease(release.version)
            release.raw["provider"] = "cnb"
            release.raw["tag_name"] = release.tag_name
            release.raw["repo_url"] = self._public_repo_url()
            release.source_url = self._public_repo_url()
            release.released_at = None
            if index == 0:
                release.raw["is_latest"] = True
        return releases

    async def get_release_detail(self, version: str) -> ReleaseInfo | None:
        releases = await self.list_releases()
        return next((release for release in releases if release.version == version), None)

    async def list_assets(self, release: ReleaseInfo) -> list[AssetInfo]:
        return release.assets

    async def download_asset(self, asset: AssetInfo) -> bytes:
        raise NotImplementedError("CNB tag sync does not provide release asset downloads yet.")

    async def _list_tags(self) -> list[str]:
        command = ["git", "ls-remote", "--tags", "--refs", self._auth_repo_url()]
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            message = stderr.decode("utf-8", errors="replace").strip() or "Failed to list CNB tags."
            raise RuntimeError(message)
        tag_names: list[str] = []
        for line in stdout.decode("utf-8", errors="replace").splitlines():
            parts = line.strip().split("\t", 1)
            if len(parts) != 2 or not parts[1].startswith("refs/tags/"):
                continue
            tag_name = parts[1].removeprefix("refs/tags/").strip()
            if tag_name:
                tag_names.append(tag_name)
        return tag_names

    def _build_repo_url(self, repo_url: str | None, owner: str | None, repo: str | None) -> str:
        if repo_url:
            return repo_url.rstrip("/")
        if owner and repo:
            return f"https://cnb.cool/{owner}/{repo}.git"
        raise ValueError("CNB repository requires repo_url or owner/repo.")

    def _auth_repo_url(self) -> str:
        if not self.token:
            return self.repo_url
        parsed = urlsplit(self.repo_url)
        netloc = f"cnb:{self.token}@{parsed.netloc}"
        return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))

    def _public_repo_url(self) -> str:
        parsed = urlsplit(self.repo_url)
        path = parsed.path[:-4] if parsed.path.endswith(".git") else parsed.path
        return urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, parsed.fragment)).rstrip("/")

    def _tag_to_release(self, tag_name: str) -> ReleaseInfo:
        return ReleaseInfo(
            version=tag_name,
            tag_name=tag_name,
            title=tag_name,
            description=f"Imported from CNB tag {tag_name}",
            source_url=None,
            released_at=None,
            assets=[],
            raw={},
        )

    def _sort_key(self, release: ReleaseInfo) -> tuple[int, tuple[tuple[int, int | str], ...]]:
        version = release.version.strip()
        normalized = version[1:] if version.lower().startswith("v") else version
        segments: list[tuple[int, int | str]] = []
        for part in normalized.replace("-", ".").split("."):
            if not part:
                continue
            if part.isdigit():
                segments.append((1, int(part)))
            else:
                segments.append((0, part.lower()))
        return (1 if segments else 0, tuple(segments or [(0, version.lower())]))

    def _is_prerelease(self, version: str) -> bool:
        lowered = version.lower()
        return any(marker in lowered for marker in ("alpha", "beta", "rc", "preview"))
