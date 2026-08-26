"""Conexao com o MySQL via SQLAlchemy."""
from collections.abc import Generator

from sqlalchemy import BigInteger, Integer, SmallInteger, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


# O SQLite so autoincrementa INTEGER PRIMARY KEY — uma chave BIGINT vira
# "NOT NULL constraint failed". A variante mantem BIGINT/SMALLINT no
# MySQL e usa INTEGER nos testes, que rodam em SQLite.
Id = BigInteger().with_variant(Integer, "sqlite")
IdPequeno = SmallInteger().with_variant(Integer, "sqlite")


def get_db() -> Generator[Session, None, None]:
    """Dependencia do FastAPI: abre e fecha a sessao por request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
