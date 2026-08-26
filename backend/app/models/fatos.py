"""Fatos: metas, medicoes e detalhamentos."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, Id, IdPequeno
from app.models.cadastro import Indicador, Regional


class Meta(Base):
    """O alvo do mes. regional_id NULL = meta consolidada da empresa."""

    __tablename__ = "metas"

    id: Mapped[int] = mapped_column(Id, primary_key=True)
    indicador_id: Mapped[int] = mapped_column(Id, ForeignKey("indicadores.id", ondelete="CASCADE"), nullable=False
    )
    ciclo_id: Mapped[int] = mapped_column(Id, ForeignKey("ciclos.id", ondelete="CASCADE"), nullable=False
    )
    regional_id: Mapped[int | None] = mapped_column(IdPequeno, ForeignKey("regionais.id", ondelete="CASCADE"), nullable=True
    )
    valor: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    observacao: Mapped[str | None] = mapped_column(String(300), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    indicador: Mapped[Indicador] = relationship()
    regional: Mapped[Regional | None] = relationship()


class Medicao(Base):
    """O realizado, por indicador, ciclo, semana e regional.

    Sempre por regional: o consolidado e derivado, nunca digitado.

    valor_numerador   — o valor em si (ACUMULA) ou o numerador (TAXA)
    valor_denominador — apenas TAXA; permite consolidar por
                        soma(num)/soma(den), e nao pela media das regionais

    ACUMULA guarda o valor DA SEMANA, nao o acumulado — corrigir S2 nao
    obriga a recalcular S3 e S4. TAXA guarda a posicao daquela semana.
    """

    __tablename__ = "medicoes"

    id: Mapped[int] = mapped_column(Id, primary_key=True)
    indicador_id: Mapped[int] = mapped_column(Id, ForeignKey("indicadores.id", ondelete="CASCADE"), nullable=False
    )
    ciclo_id: Mapped[int] = mapped_column(Id, ForeignKey("ciclos.id", ondelete="CASCADE"), nullable=False
    )
    semana: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    regional_id: Mapped[int] = mapped_column(IdPequeno, ForeignKey("regionais.id", ondelete="CASCADE"), nullable=False
    )
    valor_numerador: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    valor_denominador: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 4), nullable=True
    )
    observacao: Mapped[str | None] = mapped_column(String(300), nullable=True)
    fonte_id: Mapped[int | None] = mapped_column(Id, ForeignKey("fontes_dados.id", ondelete="SET NULL"), nullable=True
    )
    registrado_por: Mapped[int | None] = mapped_column(Id, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    criado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    indicador: Mapped[Indicador] = relationship()
    regional: Mapped[Regional] = relationship()


class Detalhamento(Base):
    """Quebra de um indicador por categoria.

    Generico de proposito: uma pergunta nova no comite ("abra as perdas
    por faixa de desconto") entra como categoria, sem alterar o schema.
    """

    __tablename__ = "detalhamentos"

    id: Mapped[int] = mapped_column(Id, primary_key=True)
    indicador_id: Mapped[int] = mapped_column(Id, ForeignKey("indicadores.id", ondelete="CASCADE"), nullable=False
    )
    ciclo_id: Mapped[int] = mapped_column(Id, ForeignKey("ciclos.id", ondelete="CASCADE"), nullable=False
    )
    semana: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    regional_id: Mapped[int | None] = mapped_column(IdPequeno, ForeignKey("regionais.id", ondelete="CASCADE"), nullable=True
    )
    dimensao: Mapped[str] = mapped_column(String(60), nullable=False)
    categoria: Mapped[str] = mapped_column(String(160), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    ordem: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    regional: Mapped[Regional | None] = relationship()
