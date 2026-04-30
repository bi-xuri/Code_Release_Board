import asyncio
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import desc, select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import Repository, SyncLog
from app.services.sync_service import sync_repository


scheduler = BackgroundScheduler(timezone="UTC")


def start_scheduler() -> None:
    if not settings.scheduler_enabled or scheduler.running:
        return
    scheduler.add_job(sync_enabled_repositories, "interval", minutes=5, id="sync-enabled-repositories", replace_existing=True)
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)


def sync_enabled_repositories() -> None:
    with SessionLocal() as db:
        repositories = db.scalars(select(Repository).where(Repository.enabled.is_(True))).all()
        for repository in repositories:
            last_log = db.scalar(
                select(SyncLog)
                .where(SyncLog.repository_id == repository.id)
                .order_by(desc(SyncLog.started_at))
                .limit(1)
            )
            interval = timedelta(minutes=repository.sync_interval_minutes)
            if last_log and last_log.started_at > datetime.now(timezone.utc) - interval:
                continue
            asyncio.run(sync_repository(db, repository.id))
