from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.connectors.base import AssetInfo
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models import FirmwareAsset, Project, Release, Repository, User
from app.schemas.public import (
    AssetOut,
    ProjectOut,
    PublicLoginRequest,
    PublicLoginResponse,
    PublicUserOut,
    ReleaseDetail,
    ReleaseSummary,
)
from app.services.sync_service import build_connector
from app.services.download_service import record_download


router = APIRouter()
DbDep = Annotated[Session, Depends(get_db)]
UserDep = Annotated[User, Depends(get_current_user)]


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


def public_user_out(user: User) -> PublicUserOut:
    return PublicUserOut(id=user.id, username=user.username, display_name=user.display_name, role=user.role)


def accessible_repository_ids(db: Session, user: User) -> list[int] | None:
    if user.role == "admin":
        return None
    rows = db.execute(select(Repository.id).join(Repository.users).where(User.id == user.id)).all()
    return [row[0] for row in rows]


@router.post("/login", response_model=PublicLoginResponse)
def login(payload: PublicLoginRequest, db: DbDep) -> PublicLoginResponse:
    user = db.scalar(select(User).where(User.username == payload.username).options(selectinload(User.repositories)))
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return PublicLoginResponse(access_token=create_access_token(user.username), user=public_user_out(user))


@router.get("/me", response_model=PublicUserOut)
def me(user: UserDep) -> PublicUserOut:
    return public_user_out(user)


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(
    user: UserDep,
    db: DbDep,
    q: str | None = Query(default=None),
    project: str | None = Query(default=None),
    device_model: str | None = Query(default=None),
    version: str | None = Query(default=None),
) -> list[ProjectOut]:
    stmt = select(Project).where(Project.releases.any()).options(selectinload(Project.releases).selectinload(Release.repository))
    joined_release = False
    repo_ids = accessible_repository_ids(db, user)
    if repo_ids is not None:
        if not repo_ids:
            return []
        stmt = stmt.join(Release).where(Release.repository_id.in_(repo_ids))
        joined_release = True
    filters = []
    search = q or project
    if search:
        filters.append(Project.name.ilike(f"%{search}%"))
    if device_model:
        filters.append(Project.device_model.ilike(f"%{device_model}%"))
    if version:
        if not joined_release:
            stmt = stmt.join(Release)
            joined_release = True
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
def project_releases(project_id: int, user: UserDep, db: DbDep, q: str | None = Query(default=None)) -> list[ReleaseSummary]:
    repo_ids = accessible_repository_ids(db, user)
    stmt = (
        select(Release)
        .where(Release.project_id == project_id)
        .options(selectinload(Release.repository))
        .order_by(desc(Release.released_at), desc(Release.updated_at))
    )
    if repo_ids is not None:
        if not repo_ids:
            return []
        stmt = stmt.where(Release.repository_id.in_(repo_ids))
    if q:
        stmt = stmt.where(or_(Release.version.ilike(f"%{q}%"), Release.title.ilike(f"%{q}%")))
    releases = db.scalars(stmt).all()
    return [release_summary(release) for release in releases]


@router.get("/releases/{release_id}", response_model=ReleaseDetail)
def release_detail(release_id: int, user: UserDep, db: DbDep) -> ReleaseDetail:
    repo_ids = accessible_repository_ids(db, user)
    stmt = select(Release).where(Release.id == release_id).options(selectinload(Release.assets), selectinload(Release.repository))
    if repo_ids is not None:
        if not repo_ids:
            raise HTTPException(status_code=404, detail="Release not found")
        stmt = stmt.where(Release.repository_id.in_(repo_ids))
    release = db.scalar(stmt)
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    summary = release_summary(release)
    return ReleaseDetail(**summary.model_dump(), assets=[AssetOut.model_validate(asset) for asset in release.assets])


@router.get("/assets/{asset_id}/download")
async def download_asset(asset_id: int, request: Request, user: UserDep, db: DbDep) -> Response:
    repo_ids = accessible_repository_ids(db, user)
    asset = db.scalar(
        select(FirmwareAsset)
        .where(FirmwareAsset.id == asset_id)
        .options(selectinload(FirmwareAsset.release).selectinload(Release.repository))
    )
    if not asset or (repo_ids is not None and asset.release and asset.release.repository_id not in repo_ids):
        raise HTTPException(status_code=404, detail="Asset not found")
    record_download(db, asset, request)
    if asset.source == "cnb" and (asset.local_path or asset.download_url.startswith("cnb-archive://")):
        release = asset.release
        repository = release.repository if release else None
        if not release or not repository:
            raise HTTPException(status_code=500, detail="CNB asset metadata is incomplete")
        connector = build_connector(repository)
        metadata = {"cnb_tag": release.version}
        if asset.local_path:
            metadata["cnb_path"] = asset.local_path
        if asset.download_url.startswith("cnb-archive://"):
            metadata["cnb_archive_format"] = "zip" if asset.download_url.endswith("/zip") else "tar.gz"
        content = await connector.download_asset(
            AssetInfo(
                name=asset.name,
                file_name=asset.file_name,
                file_size=asset.file_size,
                content_type=asset.content_type,
                download_url=asset.download_url,
                metadata=metadata,
            )
        )
        headers = {
            "Content-Disposition": f'attachment; filename="{asset.file_name or asset.name}"',
        }
        media_type = asset.content_type or "application/octet-stream"
        return Response(content=content, media_type=media_type, headers=headers)
    if asset.local_path:
        raise HTTPException(status_code=501, detail="Local file serving is reserved for the next version")
    return RedirectResponse(asset.download_url, status_code=302)
