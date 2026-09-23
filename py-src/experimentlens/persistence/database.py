from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from .models import Base


class Database:
    """SQLAlchemy database boundary shared by API and workers."""

    def __init__(self, url: str | None = None) -> None:
        database_url = url or os.environ.get("EXPERIMENTLENS_DATABASE_URL")
        if not database_url:
            root = Path(os.environ.get("EXPERIMENTLENS_WORKSPACE", ".experimentlens/workspace"))
            root.mkdir(parents=True, exist_ok=True)
            database_url = f"sqlite:///{root.parent / 'control-plane.db'}"
        self.url = database_url
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        self.engine: Engine = create_engine(
            database_url, pool_pre_ping=True, connect_args=connect_args
        )
        if database_url.startswith("sqlite"):
            event.listen(self.engine, "connect", _configure_sqlite)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)

    def create_schema(self) -> None:
        Base.metadata.create_all(self.engine)
        with self.session() as session, session.begin():
            from .models import OrganizationRecord

            if session.get(OrganizationRecord, "org_local") is None:
                session.add(OrganizationRecord(id="org_local", name="Local organization"))

    def session(self) -> Session:
        return self.sessions()

    def ready(self) -> bool:
        try:
            with self.session() as session:
                session.execute(text("SELECT 1 FROM agent_runs LIMIT 1"))
            return True
        except Exception:
            return False


def _configure_sqlite(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()
