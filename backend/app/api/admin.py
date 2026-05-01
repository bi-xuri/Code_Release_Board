from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_admin
from app.core.security import create_access_token, encrypt_token, hash_password, verify_password
from app.db.session import get_db
from app.models import DownloadLog, Project, Release, Repository, SyncLog, User
from app.schemas.admin import (
    DownloadLogOut,
    LoginRequest,
    LoginResponse,
    RepositoryCreate,
    RepositoryOut,
    RepositoryUpdate,
    SyncLogOut,
    UserCreate,
    UserOut,
    UserRepositoryAccessOut,
    UserUpdate,
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
        device_model=repository.device_model,
        hardware_version=repository.hardware_version,
        release_tag_prefix=repository.release_tag_prefix,
        enabled=repository.enabled,
        show_source_archives=repository.show_source_archives,
        sync_interval_minutes=repository.sync_interval_minutes,
        access_token_set=bool(repository.access_token_encrypted),
        created_at=repository.created_at,
        updated_at=repository.updated_at,
    )


def user_out(user: User) -> UserOut:
    repositories = [UserRepositoryAccessOut(id=repository.id, name=repository.name, provider=repository.provider) for repository in user.repositories]
    return UserOut(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        repository_ids=[repository.id for repository in user.repositories],
        repositories=repositories,
        created_at=user.created_at,
    )


def _load_repositories(db: Session, repository_ids: list[int]) -> list[Repository]:
    if not repository_ids:
        return []
    repositories = db.scalars(select(Repository).where(Repository.id.in_(repository_ids))).all()
    found_ids = {repository.id for repository in repositories}
    missing_ids = sorted(set(repository_ids) - found_ids)
    if missing_ids:
        raise HTTPException(status_code=400, detail=f"Repository not found: {', '.join(map(str, missing_ids))}")
    return repositories


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: DbDep) -> LoginResponse:
    user = db.scalar(select(User).where(User.username == payload.username))
    if not user or not user.is_active or user.role != "admin" or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    return LoginResponse(access_token=create_access_token(user.username))


@router.get("/repositories", response_model=list[RepositoryOut])
def list_repositories(_: AdminDep, db: DbDep) -> list[RepositoryOut]:
    repositories = db.scalars(select(Repository).order_by(desc(Repository.created_at))).all()
    return [repo_out(repository) for repository in repositories]


@router.get("/users", response_model=list[UserOut])
def list_users(_: AdminDep, db: DbDep) -> list[UserOut]:
    users = db.scalars(
        select(User).where(User.role != "admin").options(selectinload(User.repositories)).order_by(desc(User.created_at))
    ).all()
    return [user_out(user) for user in users]


@router.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, _: AdminDep, db: DbDep) -> UserOut:
    user = db.scalar(select(User).where(User.id == user_id, User.role != "admin").options(selectinload(User.repositories)))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user_out(user)


@router.post("/users", response_model=UserOut)
def create_user(payload: UserCreate, _: AdminDep, db: DbDep) -> UserOut:
    existing = db.scalar(select(User).where(User.username == payload.username))
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    user = User(
        username=payload.username,
        display_name=payload.display_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role="viewer",
        is_active=payload.is_active,
        repositories=_load_repositories(db, payload.repository_ids),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    user = db.scalar(select(User).where(User.id == user.id).options(selectinload(User.repositories)))
    return user_out(user)


@router.put("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, current_user: AdminDep, db: DbDep) -> UserOut:
    user = db.scalar(select(User).where(User.id == user_id, User.role != "admin").options(selectinload(User.repositories)))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    duplicate = db.scalar(select(User).where(User.username == payload.username, User.id != user_id))
    if duplicate:
        raise HTTPException(status_code=400, detail="Username already exists")

    user.username = payload.username
    user.display_name = payload.display_name
    user.email = payload.email
    user.role = "viewer"
    user.is_active = payload.is_active
    user.repositories = _load_repositories(db, payload.repository_ids)
    if payload.password:
        user.password_hash = hash_password(payload.password)
    db.commit()
    db.refresh(user)
    user = db.scalar(select(User).where(User.id == user.id).options(selectinload(User.repositories)))
    return user_out(user)


@router.delete("/users/{user_id}")
def delete_user(user_id: int, current_user: AdminDep, db: DbDep) -> dict[str, str]:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    db.delete(user)
    db.commit()
    return {"status": "deleted"}


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
        device_model=payload.device_model,
        hardware_version=payload.hardware_version,
        release_tag_prefix=payload.release_tag_prefix,
        access_token_encrypted=encrypt_token(payload.access_token),
        enabled=payload.enabled,
        show_source_archives=payload.show_source_archives,
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
    repository.device_model = payload.device_model
    repository.hardware_version = payload.hardware_version
    repository.release_tag_prefix = payload.release_tag_prefix
    repository.enabled = payload.enabled
    repository.show_source_archives = payload.show_source_archives
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
    project_id = db.scalar(select(Release.project_id).where(Release.repository_id == repository.id).limit(1))
    db.delete(repository)
    db.flush()
    if project_id is not None:
        has_releases = db.scalar(select(Release.id).where(Release.project_id == project_id).limit(1))
        if not has_releases:
            project = db.get(Project, project_id)
            if project:
                db.delete(project)
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
