import asyncio
import os
import shutil
import tempfile
from datetime import datetime
from urllib.parse import quote, urlsplit, urlunsplit

import httpx

from app.connectors.base import AssetInfo, ReleaseInfo


class CNBConnector:
    ASSET_EXTENSIONS = {".bin", ".hex", ".uf2", ".elf", ".zip", ".rar", ".7z"}

    def __init__(
        self,
        repo_url: str | None = None,
        owner: str | None = None,
        repo: str | None = None,
        token: str | None = None,
        include_source_archives: bool = False,
    ) -> None:
        self.repo_url = self._build_repo_url(repo_url, owner, repo)
        self.token = token
        self.include_source_archives = include_source_archives
        self.api_base_url = "https://api.cnb.cool"
        self.repo_path = self._build_repo_path(owner, repo)
        self.headers = {"Accept": "application/json"}
        if token:
            self.headers["Authorization"] = f"token {token}"
            self.headers["PRIVATE-TOKEN"] = token
            self.headers["X-Access-Token"] = token

    async def list_releases(self) -> list[ReleaseInfo]:
        releases = await self._list_release_objects()
        if not releases:
            releases = await self._list_tag_releases()

        releases.sort(key=self._release_sort_key, reverse=True)
        for index, release in enumerate(releases):
            release = await self._enrich_release_from_git(release)
            release.is_prerelease = release.is_prerelease or self._is_prerelease(release.version)
            release.raw["provider"] = "cnb"
            release.raw["tag_name"] = release.tag_name
            release.raw["repo_url"] = self._public_repo_url()
            if not release.source_url:
                release.source_url = self._public_repo_url()
            if index == 0:
                release.raw["is_latest"] = True
        return releases

    async def get_release_detail(self, version: str) -> ReleaseInfo | None:
        releases = await self.list_releases()
        return next((release for release in releases if release.version == version), None)

    async def list_assets(self, release: ReleaseInfo) -> list[AssetInfo]:
        return release.assets

    async def download_asset(self, asset: AssetInfo) -> bytes:
        if asset.metadata.get("cnb_tag") and asset.metadata.get("cnb_archive_format"):
            return await self._download_git_archive(asset.metadata["cnb_tag"], asset.metadata["cnb_archive_format"])
        if asset.metadata.get("cnb_tag") and asset.metadata.get("cnb_path"):
            return await self._download_git_file(asset.metadata["cnb_tag"], asset.metadata["cnb_path"])
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            response = await client.get(asset.download_url, headers=self.headers)
            response.raise_for_status()
            return response.content

    async def _list_release_objects(self) -> list[ReleaseInfo]:
        for url in self._release_api_candidates():
            payload = await self._get_json(url)
            if isinstance(payload, list):
                return [self._parse_release(item) for item in payload if isinstance(item, dict)]
            if isinstance(payload, dict):
                for key in ("releases", "items", "data"):
                    value = payload.get(key)
                    if isinstance(value, list):
                        return [self._parse_release(item) for item in value if isinstance(item, dict)]
        return []

    async def _list_tag_releases(self) -> list[ReleaseInfo]:
        tags = await self._list_tags_via_api()
        if tags:
            return [self._parse_tag(item) for item in tags]

        tag_names = await self._list_tags()
        return [self._tag_to_release(tag_name) for tag_name in tag_names]

    async def _list_tags_via_api(self) -> list[dict]:
        for url in self._tag_api_candidates():
            payload = await self._get_json(url)
            if isinstance(payload, list):
                return [item for item in payload if isinstance(item, dict)]
            if isinstance(payload, dict):
                for key in ("tags", "items", "data"):
                    value = payload.get(key)
                    if isinstance(value, list):
                        return [item for item in value if isinstance(item, dict)]
        return []

    async def _get_json(self, url: str) -> dict | list | None:
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                response = await client.get(url, headers=self.headers)
        except httpx.HTTPError:
            return None
        if response.status_code == 404:
            return None
        response.raise_for_status()
        try:
            return response.json()
        except ValueError:
            return None

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

    def _build_repo_path(self, owner: str | None, repo: str | None) -> str:
        if owner and repo:
            return f"{owner.strip('/')}/{repo.strip('/')}"
        parsed = urlsplit(self.repo_url)
        path = parsed.path[:-4] if parsed.path.endswith(".git") else parsed.path
        return path.strip("/")

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

    def _release_api_candidates(self) -> list[str]:
        encoded_repo_path = quote(self.repo_path, safe="")
        return [
            f"{self.api_base_url}/{self.repo_path}/-/releases",
            f"{self.api_base_url}/repos/{self.repo_path}/releases",
            f"{self.api_base_url}/repositories/{self.repo_path}/releases",
            f"{self.api_base_url}/projects/{encoded_repo_path}/releases",
        ]

    def _tag_api_candidates(self) -> list[str]:
        encoded_repo_path = quote(self.repo_path, safe="")
        return [
            f"{self.api_base_url}/repos/{self.repo_path}/tags",
            f"{self.api_base_url}/repositories/{self.repo_path}/tags",
            f"{self.api_base_url}/projects/{encoded_repo_path}/repository/tags",
        ]

    def _tag_to_release(self, tag_name: str) -> ReleaseInfo:
        return ReleaseInfo(
            version=tag_name,
            tag_name=tag_name,
            title=tag_name,
            description=f"Imported from CNB tag {tag_name}",
            source_url=self._public_repo_url(),
            released_at=None,
            assets=[],
            raw={},
        )

    def _parse_release(self, item: dict) -> ReleaseInfo:
        assets = [asset for asset in (self._parse_asset(asset) for asset in item.get("assets", [])) if asset]
        released_at = (
            self._parse_datetime(item.get("published_at"))
            or self._parse_datetime(item.get("released_at"))
            or self._parse_datetime(item.get("created_at"))
            or self._parse_datetime(item.get("updated_at"))
        )
        tag_name = item.get("tag_name") or item.get("tag") or item.get("name")
        version = tag_name or item.get("name") or str(item.get("id"))
        return ReleaseInfo(
            version=version,
            tag_name=tag_name,
            title=item.get("title") or item.get("name") or tag_name,
            description=item.get("body") or item.get("description") or item.get("message"),
            source_url=item.get("html_url") or item.get("url") or self._public_repo_url(),
            released_at=released_at,
            is_prerelease=bool(item.get("prerelease") or item.get("is_prerelease") or item.get("draft")),
            assets=assets,
            raw=item,
        )

    def _parse_tag(self, item: dict) -> ReleaseInfo:
        tag_name = (
            item.get("tag_name")
            or item.get("name")
            or item.get("tag")
            or item.get("ref")
            or str(item.get("id") or "")
        )
        commit = item.get("commit") if isinstance(item.get("commit"), dict) else {}
        released_at = (
            self._parse_datetime(item.get("commit_date"))
            or self._parse_datetime(item.get("created_at"))
            or self._parse_datetime(item.get("updated_at"))
            or self._parse_datetime(commit.get("committed_at"))
            or self._parse_datetime(commit.get("committed_date"))
            or self._parse_datetime(commit.get("created_at"))
        )
        message = (
            item.get("message")
            or item.get("description")
            or commit.get("message")
            or f"Imported from CNB tag {tag_name}"
        )
        return ReleaseInfo(
            version=tag_name,
            tag_name=tag_name,
            title=item.get("title") or tag_name,
            description=message,
            source_url=item.get("html_url") or item.get("url") or self._public_repo_url(),
            released_at=released_at,
            is_prerelease=self._is_prerelease(tag_name),
            assets=[],
            raw=item,
        )

    def _parse_asset(self, item: dict) -> AssetInfo | None:
        if not isinstance(item, dict):
            return None
        download_url = (
            item.get("browser_download_url")
            or item.get("brower_download_url")
            or item.get("download_url")
            or item.get("direct_asset_url")
            or item.get("url")
        )
        if not download_url:
            return None
        name = item.get("name") or item.get("label") or item.get("file_name") or "asset"
        return AssetInfo(
            name=name,
            file_name=item.get("file_name") or item.get("name"),
            file_size=item.get("size") or item.get("file_size"),
            content_type=item.get("content_type"),
            download_url=download_url,
            metadata=item,
        )

    def _release_sort_key(self, release: ReleaseInfo) -> tuple[int, datetime | None, tuple[int, tuple[tuple[int, int | str], ...]]]:
        return (
            1 if release.released_at else 0,
            release.released_at,
            self._version_sort_key(release),
        )

    def _version_sort_key(self, release: ReleaseInfo) -> tuple[int, tuple[tuple[int, int | str], ...]]:
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

    def _build_release_url(self, tag_name: str) -> str:
        return f"{self._public_repo_url()}/-/releases/{quote(tag_name, safe='')}"

    def _parse_datetime(self, value: str | None) -> datetime | None:
        if not value:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None

    def _is_prerelease(self, version: str) -> bool:
        lowered = version.lower()
        return any(marker in lowered for marker in ("alpha", "beta", "rc", "preview"))

    async def _enrich_release_from_git(self, release: ReleaseInfo) -> ReleaseInfo:
        tag_name = release.tag_name or release.version
        metadata = await self._load_git_release_metadata(tag_name)
        if not release.released_at:
            release.released_at = metadata.get("released_at")
        if self._is_placeholder_description(release.description) and metadata.get("description"):
            release.description = metadata["description"]
        if not release.title:
            release.title = tag_name
        archives = metadata.get("archives", []) if self.include_source_archives else []
        release.assets = self._merge_assets(release.assets, [], archives)
        release.raw.setdefault("git_fallback", True)
        return release

    def _is_placeholder_description(self, description: str | None) -> bool:
        if not description:
            return True
        lowered = description.lower()
        return lowered.startswith("imported from cnb tag ")

    async def _load_git_release_metadata(self, tag_name: str) -> dict:
        temp_dir = tempfile.mkdtemp(prefix="cnb-release-")
        try:
            await self._run_git(temp_dir, "init")
            await self._run_git(temp_dir, "remote", "add", "origin", self._auth_repo_url())
            await self._run_git(temp_dir, "fetch", "--depth", "1", "origin", f"refs/tags/{tag_name}:refs/tags/{tag_name}")
            tag_output = await self._run_git(
                temp_dir,
                "for-each-ref",
                f"refs/tags/{tag_name}",
                "--format=%(creatordate:iso8601)%n%(subject)%n%(body)",
            )
            commit_output = await self._run_git(temp_dir, "log", "-1", "--format=%cI%n%s%n%b", tag_name)
            assets_output = await self._run_git(temp_dir, "ls-tree", "-r", "-l", tag_name)
            return self._parse_git_metadata(tag_name, tag_output, commit_output, assets_output)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _parse_git_metadata(self, tag_name: str, tag_output: str, commit_output: str, assets_output: str) -> dict:
        tag_lines = [line.rstrip() for line in tag_output.splitlines()]
        commit_lines = [line.rstrip() for line in commit_output.splitlines()]

        tag_date = self._parse_datetime(tag_lines[0]) if tag_lines else None
        tag_subject = tag_lines[1] if len(tag_lines) > 1 else ""
        tag_body = "\n".join(tag_lines[2:]).strip() if len(tag_lines) > 2 else ""
        commit_date = self._parse_datetime(commit_lines[0]) if commit_lines else None
        commit_subject = commit_lines[1] if len(commit_lines) > 1 else ""
        commit_body = "\n".join(commit_lines[2:]).strip() if len(commit_lines) > 2 else ""

        description = "\n".join(part for part in [tag_subject, tag_body] if part).strip()
        if not description:
            description = "\n".join(part for part in [commit_subject, commit_body] if part).strip()

        return {
            "released_at": tag_date or commit_date,
            "description": description or None,
            "assets": self._parse_git_assets(tag_name, assets_output),
            "archives": self._build_archive_assets(tag_name),
        }

    def _parse_git_assets(self, tag_name: str, assets_output: str) -> list[AssetInfo]:
        assets: list[AssetInfo] = []
        for line in assets_output.splitlines():
            if "\t" not in line:
                continue
            meta, path = line.split("\t", 1)
            size_token = meta.rsplit(" ", 1)[-1].strip()
            file_name = os.path.basename(path)
            extension = os.path.splitext(file_name)[1].lower()
            if extension not in self.ASSET_EXTENSIONS:
                continue
            file_size = int(size_token) if size_token.isdigit() else None
            assets.append(
                AssetInfo(
                    name=file_name,
                    file_name=file_name,
                    file_size=file_size,
                    content_type=self._guess_content_type(extension),
                    download_url=f"cnb://{self.repo_path}/{quote(tag_name, safe='')}/{quote(path, safe='/')}",
                    metadata={"cnb_tag": tag_name, "cnb_path": path},
                )
            )
        return assets

    def _guess_content_type(self, extension: str) -> str | None:
        return {
            ".bin": "application/octet-stream",
            ".hex": "text/plain",
            ".uf2": "application/octet-stream",
            ".elf": "application/octet-stream",
            ".zip": "application/zip",
            ".rar": "application/vnd.rar",
            ".7z": "application/x-7z-compressed",
        }.get(extension)

    async def _download_git_file(self, tag_name: str, path: str) -> bytes:
        temp_dir = tempfile.mkdtemp(prefix="cnb-asset-")
        try:
            await self._run_git(temp_dir, "init")
            await self._run_git(temp_dir, "remote", "add", "origin", self._auth_repo_url())
            await self._run_git(temp_dir, "fetch", "--depth", "1", "origin", f"refs/tags/{tag_name}:refs/tags/{tag_name}")
            output = await self._run_git(temp_dir, "show", f"{tag_name}:{path}", decode=False)
            return output if isinstance(output, bytes) else output.encode("utf-8")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _build_archive_assets(self, tag_name: str) -> list[AssetInfo]:
        safe_tag = tag_name.replace("/", "_")
        return [
            AssetInfo(
                name="Source code (zip)",
                file_name=f"{self.repo_name_for_archive()}-{safe_tag}.zip",
                content_type="application/zip",
                download_url=f"cnb-archive://{self.repo_path}/{quote(tag_name, safe='')}/zip",
                metadata={"cnb_tag": tag_name, "cnb_archive_format": "zip"},
            ),
            AssetInfo(
                name="Source code (tar.gz)",
                file_name=f"{self.repo_name_for_archive()}-{safe_tag}.tar.gz",
                content_type="application/gzip",
                download_url=f"cnb-archive://{self.repo_path}/{quote(tag_name, safe='')}/tar.gz",
                metadata={"cnb_tag": tag_name, "cnb_archive_format": "tar.gz"},
            ),
        ]

    def repo_name_for_archive(self) -> str:
        return self.repo_path.rsplit("/", 1)[-1]

    def _merge_assets(self, primary: list[AssetInfo], scanned: list[AssetInfo], archives: list[AssetInfo]) -> list[AssetInfo]:
        merged: list[AssetInfo] = []
        seen: set[str] = set()
        for asset in [*primary, *archives, *scanned]:
            key = asset.download_url
            if key in seen:
                continue
            seen.add(key)
            merged.append(asset)
        return merged

    async def _download_git_archive(self, tag_name: str, archive_format: str) -> bytes:
        temp_dir = tempfile.mkdtemp(prefix="cnb-archive-")
        try:
            await self._run_git(temp_dir, "init")
            await self._run_git(temp_dir, "remote", "add", "origin", self._auth_repo_url())
            await self._run_git(temp_dir, "fetch", "--depth", "1", "origin", f"refs/tags/{tag_name}:refs/tags/{tag_name}")
            git_args = ["archive", f"--format={'zip' if archive_format == 'zip' else 'tar.gz'}", tag_name]
            output = await self._run_git(temp_dir, *git_args, decode=False)
            return output if isinstance(output, bytes) else output.encode("utf-8")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    async def _run_git(self, cwd: str, *args: str, decode: bool = True) -> str | bytes:
        process = await asyncio.create_subprocess_exec(
            "git",
            "-C",
            cwd,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            message = stderr.decode("utf-8", errors="replace").strip() or "CNB git metadata fetch failed."
            raise RuntimeError(message)
        if not decode:
            return stdout
        return stdout.decode("utf-8", errors="replace")
