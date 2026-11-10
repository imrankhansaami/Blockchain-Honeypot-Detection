"""Database engine and session management."""

from __future__ import annotations

import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models import Base, Chain as ChainRow

logger = get_logger(__name__)

_settings = get_settings()

# Ensure the SQLite directory exists when a file URL is used.
if _settings.database_url.startswith("sqlite"):
    db_path = _settings.database_url.split("///")[-1]
    directory = os.path.dirname(os.path.abspath(db_path))
    os.makedirs(directory, exist_ok=True)

_connect_args = {"check_same_thread": False} if _settings.database_url.startswith("sqlite") else {}

engine = create_engine(
    _settings.database_url,
    echo=_settings.db_echo,
    future=True,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def init_db() -> None:
    """Create tables and seed the chain registry."""
    Base.metadata.create_all(bind=engine)
    _seed_chains()


def _seed_chains() -> None:
    from app.core.chains import list_chains

    with SessionLocal() as session:
        existing = {c.chain_id for c in session.query(ChainRow).all()}
        for chain in list_chains():
            if chain.chain_id in existing:
                continue
            session.add(
                ChainRow(
                    chain_id=chain.chain_id,
                    name=chain.name,
                    native_symbol=chain.native_symbol,
                    explorer_url=chain.explorer_url,
                )
            )
        session.commit()


def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
