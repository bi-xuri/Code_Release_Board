from sqlalchemy import inspect, select, text

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine
from app.models import User


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_repository_columns()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == settings.admin_username))
        if not user:
            db.add(
                User(
                    username=settings.admin_username,
                    password_hash=hash_password(settings.admin_password),
                    role="admin",
                )
            )
            db.commit()


def _ensure_repository_columns() -> None:
    inspector = inspect(engine)
    default_false = "false" if engine.dialect.name == "postgresql" else "0"
    repository_columns = {column["name"] for column in inspector.get_columns("repositories")}
    with engine.begin() as connection:
        if "show_source_archives" not in repository_columns:
            connection.execute(
                text(f"ALTER TABLE repositories ADD COLUMN show_source_archives BOOLEAN NOT NULL DEFAULT {default_false}")
            )

        user_columns = {column["name"] for column in inspector.get_columns("users")}
        if "display_name" not in user_columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN display_name VARCHAR(100)"))
        if "email" not in user_columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN email VARCHAR(200)"))
        if "is_active" not in user_columns:
            connection.execute(text(f"ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT {default_false}"))
