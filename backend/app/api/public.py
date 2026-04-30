from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models import FirmwareAsset, Project, Release, Repository
from app.schemas.public import AssetOut, ProjectOut, ReleaseDetail, ReleaseSummary
from app.services.download_service import record_download


router = APIRouter()
DbDep = Annotated[Session, Depends(get_db)]


def release_summary(release: Release) -> ReleaseSummary:
    return ReleaseSummary(
        id=release.id,
        repository_id=release.repository_id,
        project_id=release.project_id,
        version=release.version,
        tag_name=release.tag_name,
        title=release.title,
        description=release.description,
        release_type=release.release_type,
        source_url=release.source_url,
        released_at=release.released_at,
        is_latest=release.is_latest,
        is_prerelease=release.is_prerelease,
        updated_at=release.updated_at,
        repository_name=release.repository.name if release.repository else None,
    )


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(
    db: DbDep,
    q: str | None = Query(default=None),
    project: str | None = Query(default=None),
    device_model: str | None = Query(default=None),
    version: str | None = Query(default=None),
) -> list[ProjectOut]:
    stmt = select(Project).options(selectinload(Project.releases).selectinload(Release.repository))
    filters = []
    search = q or project
    if search:
        filters.append(Project.name.ilike(f"%{search}%"))
    if device_model:
        filters.append(Project.device_model.ilike(f"%{device_model}%"))
    if version:
        stmt = stmt.join(Release)
        filters.append(Release.version.ilike(f"%{version}%"))
    if filters:
        stmt = stmt.where(or_(*filters))
    projects = db.scalars(stmt.order_by(Project.name)).unique().all()
    result = []
    for item in projects:
        latest = next((release for release in item.releases if release.is_latest), None)
        if not latest and item.releases:
            latest = sorted(item.releases, key=lambda release: release.released_at or release.updated_at, reverse=True)[0]
        result.append(
            ProjectOut(
                id=item.id,
                name=item.name,
                description=item.description,
                device_model=item.device_model,
                hardware_version=item.hardware_version,
                created_at=item.created_at,
                latest_release=release_summary(latest) if latest else None,
            )
        )
    return result


@router.get("/projects/{project_id}/releases", response_model=list[ReleaseSummary])
def project_releases(project_id: int, db: DbDep, q: str | None = Query(default=None)) -> list[ReleaseSummary]:
    stmt = (
        select(Release)
        .where(Release.project_id == project_id)
        .options(selectinload(Release.repository))
        .order_by(desc(Release.released_at), desc(Release.updated_at))
    )
    if q:
        stmt = stmt.where(or_(Release.version.ilike(f"%{q}%"), Release.title.ilike(f"%{q}%")))
    releases = db.scalars(stmt).all()
    return [release_summary(release) for release in releases]


@router.get("/releases/{release_id}", response_model=ReleaseDetail)
def release_detail(release_id: int, db: DbDep) -> ReleaseDetail:
    release = db.scalar(
        select(Release)
        .where(Release.id == release_id)
        .options(selectinload(Release.assets), selectinload(Release.repository))
    )
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    summary = release_summary(release)
    return ReleaseDetail(**summary.model_dump(), assets=[AssetOut.model_validate(asset) for asset in release.assets])


@router.get("/assets/{asset_id}/download")
def download_asset(asset_id: int, request: Request, db: DbDep) -> RedirectResponse:
    asset = db.scalar(select(FirmwareAsset).where(FirmwareAsset.id == asset_id))
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    record_download(db, asset, request)
    if asset.local_path:
        raise HTTPException(status_code=501, detail="Local file serving is reserved for the next version")
    return RedirectResponse(asset.download_url, status_code=302)
