from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.core.security import create_access_token, encrypt_token, verify_password
from app.db.session import get_db
from app.models import DownloadLog, Repository, SyncLog, User
from app.schemas.admin import (
    DownloadLogOut,
    LoginRequest,
    LoginResponse,
    RepositoryCreate,
    RepositoryOut,
    RepositoryUpdate,
    SyncLogOut,
)
from app.services.sync_service import sync_repository


router = APIRouter()
AdminDep = Annotated[User, Depends(get_current_admin)]
DbDep = Annotated[Session, Depends(get_db)]


def repo_out(repository: Repository) -> RepositoryOut:
    return RepositoryOut(
        id=repository.id,
        name=repository.name,
        provider=repository.provider,
        repo_url=repository.repo_url,
        api_base_url=repository.api_base_url,
        owner=repository.owner,
        repo_name=repository.repo_name,
        project_id=repository.project_id,
        enabled=repository.enabled,
        sync_interval_minutes=repository.sync_interval_minutes,
        access_token_set=bool(repository.access_token_encrypted),
        created_at=repository.created_at,
        updated_at=repository.updated_at,
    )


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: DbDep) -> LoginResponse:
    user = db.scalar(select(User).where(User.username == payload.username))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    return LoginResponse(access_token=create_access_token(user.username))


@router.get("/repositories", response_model=list[RepositoryOut])
def list_repositories(_: AdminDep, db: DbDep) -> list[RepositoryOut]:
    repositories = db.scalars(select(Repository).order_by(desc(Repository.created_at))).all()
    return [repo_out(repository) for repository in repositories]


@router.post("/repositories", response_model=RepositoryOut)
def create_repository(payload: RepositoryCreate, _: AdminDep, db: DbDep) -> RepositoryOut:
    repository = Repository(
        name=payload.name,
        provider=payload.provider.lower(),
        repo_url=payload.repo_url,
        api_base_url=payload.api_base_url,
        owner=payload.owner,
        repo_name=payload.repo_name,
        project_id=payload.project_id,
        access_token_encrypted=encrypt_token(payload.access_token),
        enabled=payload.enabled,
        sync_interval_minutes=payload.sync_interval_minutes,
    )
    db.add(repository)
    db.commit()
    db.refresh(repository)
    return repo_out(repository)


@router.put("/repositories/{repository_id}", response_model=RepositoryOut)
def update_repository(repository_id: int, payload: RepositoryUpdate, _: AdminDep, db: DbDep) -> RepositoryOut:
    repository = db.get(Repository, repository_id)
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    repository.name = payload.name
    repository.provider = payload.provider.lower()
    repository.repo_url = payload.repo_url
    repository.api_base_url = payload.api_base_url
    repository.owner = payload.owner
    repository.repo_name = payload.repo_name
    repository.project_id = payload.project_id
    repository.enabled = payload.enabled
    repository.sync_interval_minutes = payload.sync_interval_minutes
    if payload.access_token:
        repository.access_token_encrypted = encrypt_token(payload.access_token)
    db.commit()
    db.refresh(repository)
    return repo_out(repository)


@router.delete("/repositories/{repository_id}")
def delete_repository(repository_id: int, _: AdminDep, db: DbDep) -> dict[str, str]:
    repository = db.get(Repository, repository_id)
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found")
    db.delete(repository)
    db.commit()
    return {"status": "deleted"}


@router.post("/repositories/{repository_id}/sync", response_model=SyncLogOut)
async def sync_repo(repository_id: int, _: AdminDep, db: DbDep) -> SyncLogOut:
    try:
        log = await sync_repository(db, repository_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Repository not found") from None
    return SyncLogOut(
        id=log.id,
        repository_id=log.repository_id,
        repository_name=log.repository.name if log.repository else None,
        status=log.status,
        message=log.message,
        started_at=log.started_at,
        finished_at=log.finished_at,
    )


@router.get("/sync-logs", response_model=list[SyncLogOut])
def sync_logs(_: AdminDep, db: DbDep) -> list[SyncLogOut]:
    logs = db.scalars(select(SyncLog).order_by(desc(SyncLog.started_at)).limit(200)).all()
    return [
        SyncLogOut(
            id=log.id,
            repository_id=log.repository_id,
            repository_name=log.repository.name if log.repository else None,
            status=log.status,
            message=log.message,
            started_at=log.started_at,
            finished_at=log.finished_at,
        )
        for log in logs
    ]


@router.get("/download-logs", response_model=list[DownloadLogOut])
def download_logs(_: AdminDep, db: DbDep) -> list[DownloadLogOut]:
    logs = db.scalars(select(DownloadLog).order_by(desc(DownloadLog.downloaded_at)).limit(200)).all()
    return [
        DownloadLogOut(
            id=log.id,
            release_id=log.release_id,
            asset_id=log.asset_id,
            asset_name=log.asset.name if log.asset else None,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            downloaded_at=log.downloaded_at,
        )
        for log in logs
    ]
