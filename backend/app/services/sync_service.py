from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.cnb import CNBConnector
from app.connectors.github import GitHubConnector
from app.connectors.gitlab import GitLabConnector
from app.connectors.manual import ManualConnector
from app.core.security import decrypt_token
from app.models import FirmwareAsset, Project, Release, Repository, SyncLog


def build_connector(repository: Repository):
    token = decrypt_token(repository.access_token_encrypted)
    provider = repository.provider.lower()
    if provider == "github":
        return GitHubConnector(
            owner=repository.owner or "",
            repo=repository.repo_name or "",
            token=token,
            api_base_url=repository.api_base_url,
            include_source_archives=repository.show_source_archives,
        )
    if provider == "gitlab":
        return GitLabConnector(
            project_id=repository.project_id,
            owner=repository.owner,
            repo=repository.repo_name,
            token=token,
            api_base_url=repository.api_base_url,
        )
    if provider == "cnb":
        return CNBConnector(
            repo_url=repository.repo_url,
            owner=repository.owner,
            repo=repository.repo_name,
            token=token,
            include_source_archives=repository.show_source_archives,
        )
    return ManualConnector()


async def sync_repository(db: Session, repository_id: int) -> SyncLog:
    repository = db.get(Repository, repository_id)
    if not repository:
        raise ValueError("Repository not found")

    log = SyncLog(repository_id=repository.id, status="running", started_at=datetime.now(timezone.utc))
    db.add(log)
    db.commit()
    db.refresh(log)

    try:
        connector = build_connector(repository)
        releases = await connector.list_releases()
        project = _get_or_create_project(db, repository)

        for index, item in enumerate(releases):
            existing = db.scalar(
                select(Release).where(
                    Release.repository_id == repository.id,
                    Release.version == item.version,
                )
            )
            release_type = "beta" if item.is_prerelease else "stable"
            if not existing:
                existing = Release(
                    repository_id=repository.id,
                    project_id=project.id,
                    version=item.version,
                    created_at=datetime.now(timezone.utc),
                )
                db.add(existing)
            existing.project_id = project.id
            existing.tag_name = item.tag_name
            existing.title = item.title
            existing.description = item.description
            existing.release_type = release_type
            existing.source_url = item.source_url
            existing.released_at = item.released_at
            existing.is_latest = index == 0
            existing.is_prerelease = item.is_prerelease
            existing.updated_at = datetime.now(timezone.utc)
            db.flush()

            seen_asset_urls = set()
            for asset in item.assets:
                seen_asset_urls.add(asset.download_url)
                existing_asset = db.scalar(
                    select(FirmwareAsset).where(
                        FirmwareAsset.release_id == existing.id,
                        FirmwareAsset.download_url == asset.download_url,
                    )
                )
                if not existing_asset:
                    existing_asset = FirmwareAsset(
                        release_id=existing.id,
                        download_url=asset.download_url,
                    )
                    db.add(existing_asset)
                existing_asset.name = asset.name
                existing_asset.file_name = asset.file_name
                existing_asset.file_size = asset.file_size
                existing_asset.content_type = asset.content_type
                existing_asset.source = repository.provider
                existing_asset.local_path = asset.metadata.get("cnb_path")

            stale_assets = db.scalars(select(FirmwareAsset).where(FirmwareAsset.release_id == existing.id)).all()
            for stale_asset in stale_assets:
                if stale_asset.download_url not in seen_asset_urls:
                    db.delete(stale_asset)

        log.status = "success"
        log.message = f"Synced {len(releases)} release(s)."
    except Exception as exc:
        log.status = "failed"
        log.message = str(exc)
    finally:
        log.finished_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(log)
    return log


def _get_or_create_project(db: Session, repository: Repository) -> Project:
    project = db.scalar(select(Project).where(Project.name == repository.name))
    if project:
        return project
    project = Project(name=repository.name, description=repository.repo_url)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project
