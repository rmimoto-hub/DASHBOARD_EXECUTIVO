"""Modelo de usuario."""
import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Perfil(str, enum.Enum):
    ADMIN = "ADMIN"
    USER = "USER"
    READ_ONLY = "READ_ONLY"


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(180), unique=True, nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    perfil: Mapped[Perfil] = mapped_column(
        Enum(Perfil, native_enum=True), nullable=False, default=Perfil.USER
    )
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ultimo_acesso: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
