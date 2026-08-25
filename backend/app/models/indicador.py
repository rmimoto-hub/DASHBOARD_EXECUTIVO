"""Modelos de indicador e medicao."""
import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MelhorDirecao(str, enum.Enum):
    MAIOR = "MAIOR"
    MENOR = "MENOR"


class Indicador(Base):
    __tablename__ = "indicadores"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    nome: Mapped[str] = mapped_column(String(160), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    unidade: Mapped[str] = mapped_column(String(20), nullable=False, default="NUM")
    area: Mapped[str] = mapped_column(String(60), nullable=False, default="GERAL")
    melhor_direcao: Mapped[MelhorDirecao] = mapped_column(
        Enum(MelhorDirecao, native_enum=True),
        nullable=False,
        default=MelhorDirecao.MAIOR,
    )
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    medicoes: Mapped[list["Medicao"]] = relationship(
        back_populates="indicador", cascade="all, delete-orphan"
    )


class Medicao(Base):
    __tablename__ = "medicoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    indicador_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("indicadores.id", ondelete="CASCADE"), nullable=False
    )
    competencia: Mapped[date] = mapped_column(Date, nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    meta: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    observacao: Mapped[str | None] = mapped_column(String(500), nullable=True)
    registrado_por: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    criado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    indicador: Mapped[Indicador] = relationship(back_populates="medicoes")
