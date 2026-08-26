"""Detalhe nominal: clientes, ocorrencias, titulos, compromissos, notas.

E o que transforma diagnostico em acao — cliente, causa, responsavel, prazo.
"""
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
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, Id, IdPequeno
from app.models.cadastro import Indicador, Regional


class StatusCompromisso(str, enum.Enum):
    ABERTO = "ABERTO"
    EM_ANDAMENTO = "EM_ANDAMENTO"
    CONCLUIDO = "CONCLUIDO"
    CANCELADO = "CANCELADO"
    ATRASADO = "ATRASADO"


class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(Id, primary_key=True)
    codigo_externo: Mapped[str | None] = mapped_column(
        String(60), unique=True, nullable=True
    )
    nome: Mapped[str] = mapped_column(String(180), nullable=False)
    regional_id: Mapped[int | None] = mapped_column(IdPequeno, ForeignKey("regionais.id", ondelete="SET NULL"), nullable=True
    )
    consultor: Mapped[str | None] = mapped_column(String(120), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    regional: Mapped[Regional | None] = relationship()


class OcorrenciaEntrega(Base):
    """Pedidos com problema da semana, por cliente, causa e plano."""

    __tablename__ = "ocorrencias_entrega"

    id: Mapped[int] = mapped_column(Id, primary_key=True)
    ciclo_id: Mapped[int] = mapped_column(Id, ForeignKey("ciclos.id", ondelete="CASCADE"), nullable=False
    )
    semana: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    cliente_id: Mapped[int | None] = mapped_column(Id, ForeignKey("clientes.id", ondelete="SET NULL"), nullable=True
    )
    cliente_rotulo: Mapped[str] = mapped_column(String(180), nullable=False)
    regional_id: Mapped[int | None] = mapped_column(IdPequeno, ForeignKey("regionais.id", ondelete="SET NULL"), nullable=True
    )
    causa: Mapped[str] = mapped_column(String(60), nullable=False)
    motivo: Mapped[str] = mapped_column(String(300), nullable=False)
    pedidos_afetados: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=1
    )
    plano_acao: Mapped[str | None] = mapped_column(String(300), nullable=True)
    responsavel: Mapped[str | None] = mapped_column(String(120), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    regional: Mapped[Regional | None] = relationship()


class TituloInadimplente(Base):
    """Carteira em aberto, cliente a cliente. Sustenta a leitura 80/20."""

    __tablename__ = "titulos_inadimplentes"

    id: Mapped[int] = mapped_column(Id, primary_key=True)
    ciclo_id: Mapped[int] = mapped_column(Id, ForeignKey("ciclos.id", ondelete="CASCADE"), nullable=False
    )
    semana: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    cliente_id: Mapped[int | None] = mapped_column(Id, ForeignKey("clientes.id", ondelete="SET NULL"), nullable=True
    )
    cliente_rotulo: Mapped[str] = mapped_column(String(180), nullable=False)
    regional_id: Mapped[int | None] = mapped_column(IdPequeno, ForeignKey("regionais.id", ondelete="SET NULL"), nullable=True
    )
    consultor: Mapped[str | None] = mapped_column(String(120), nullable=True)
    valor_aberto: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    dias_atraso: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    em_negociacao: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    observacao: Mapped[str | None] = mapped_column(String(300), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    regional: Mapped[Regional | None] = relationship()


class Compromisso(Base):
    """O que o comite decidiu, com responsavel e prazo.

    indicador_id liga a acao ao KPI que ela deve mover, para a reuniao
    seguinte cobrar o resultado.
    """

    __tablename__ = "compromissos"

    id: Mapped[int] = mapped_column(Id, primary_key=True)
    ciclo_id: Mapped[int] = mapped_column(Id, ForeignKey("ciclos.id", ondelete="CASCADE"), nullable=False
    )
    semana_origem: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    frente: Mapped[str] = mapped_column(String(120), nullable=False)
    acao: Mapped[str] = mapped_column(String(400), nullable=False)
    responsavel: Mapped[str] = mapped_column(String(120), nullable=False)
    prazo: Mapped[date] = mapped_column(Date, nullable=False)
    indicador_id: Mapped[int | None] = mapped_column(Id, ForeignKey("indicadores.id", ondelete="SET NULL"), nullable=True
    )
    regional_id: Mapped[int | None] = mapped_column(IdPequeno, ForeignKey("regionais.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[StatusCompromisso] = mapped_column(
        Enum(StatusCompromisso), nullable=False, default=StatusCompromisso.ABERTO
    )
    resultado: Mapped[str | None] = mapped_column(String(400), nullable=True)
    criado_por: Mapped[int | None] = mapped_column(Id, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    criado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    indicador: Mapped[Indicador | None] = relationship()
    regional: Mapped[Regional | None] = relationship()


class NotaAnalitica(Base):
    """A leitura que o comite registra sobre um KPI numa semana.

    E o texto de rodape de cada slide, que hoje se perde entre reunioes.
    """

    __tablename__ = "notas_analiticas"

    id: Mapped[int] = mapped_column(Id, primary_key=True)
    ciclo_id: Mapped[int] = mapped_column(Id, ForeignKey("ciclos.id", ondelete="CASCADE"), nullable=False
    )
    semana: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    indicador_id: Mapped[int | None] = mapped_column(Id, ForeignKey("indicadores.id", ondelete="CASCADE"), nullable=True
    )
    regional_id: Mapped[int | None] = mapped_column(IdPequeno, ForeignKey("regionais.id", ondelete="SET NULL"), nullable=True
    )
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    autor_id: Mapped[int | None] = mapped_column(Id, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    criado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    regional: Mapped[Regional | None] = relationship()
