"""Engine e sessão do PostgreSQL.

O engine é criado sob demanda para que importar os modelos não exija um
`.env` nem tente abrir conexão antes da aplicação ser iniciada.
"""

from functools import lru_cache
from typing import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import load_settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    settings = load_settings()
    return create_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
    )


def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(
        bind=get_engine(),
        autoflush=False,
        expire_on_commit=False,
    )


def get_db() -> Iterator[Session]:
    """Dependency do FastAPI; sempre encerra a sessão ao fim da requisição."""

    with get_session_factory()() as session:
        yield session
