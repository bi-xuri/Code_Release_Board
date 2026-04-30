from fastapi import Request
from sqlalchemy.orm import Session

from app.models import DownloadLog, FirmwareAsset


def record_download(db: Session, asset: FirmwareAsset, request: Request) -> None:
    forwarded_for = request.headers.get("x-forwarded-for")
    ip_address = forwarded_for.split(",")[0].strip() if forwarded_for else (request.client.host if request.client else None)
    db.add(
        DownloadLog(
            release_id=asset.release_id,
            asset_id=asset.id,
            ip_address=ip_address,
            user_agent=request.headers.get("user-agent"),
        )
    )
    db.commit()
