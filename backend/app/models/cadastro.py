"""Cadastro: regionais, indicadores, ciclos e fontes de dados."""
import enum
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, Id, IdPequeno


class Area(str, enum.Enum):
    COMERCIAL = "COMERCIAL"
    OPERACOES = "OPERACOES"
    ESTOQUE = "ESTOQUE"
    FINANCEIRO = "FINANCEIRO"
    MARKETING = "MARKETING"


class Unidade(str, enum.Enum):
    BRL = "BRL"
    BRL_MIL = "BRL_MIL"
    BRL_MI = "BRL_MI"
    PCT = "PCT"
    NUM = "NUM"
    DIAS = "DIAS"
    CLIENTES = "CLIENTES"
    PEDIDOS = "PEDIDOS"
    LEADS = "LEADS"


class TipoAcumulacao(str, enum.Enum):
    """Define o atingimento esperado na semana — a base do semaforo.

    ACUMULA: soma ao longo do mes. Esperado na semana N de T = N/T.
    TAXA:    razao valida a qualquer momento. Esperado = 100% sempre.
    """

    ACUMULA = "ACUMULA"
    TAXA = "TAXA"


class MelhorDirecao(str, enum.Enum):
    MAIOR = "MAIOR"
    MENOR = "MENOR"


class StatusCiclo(str, enum.Enum):
    ABERTO = "ABERTO"
    FECHADO = "FECHADO"


class TipoFonte(str, enum.Enum):
    MANUAL = "MANUAL"
    SUPABASE = "SUPABASE"
    API_REST = "API_REST"
    PLANILHA = "PLANILHA"
    BANCO_EXTERNO = "BANCO_EXTERNO"


class Regional(Base):
    __tablename__ = "regionais"

    id: Mapped[int] = mapped_column(IdPequeno, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    nome: Mapped[str] = mapped_column(String(80), nullable=False)
    ordem: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Indicador(Base):
    __tablename__ = "indicadores"

    id: Mapped[int] = mapped_column(Id, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    nome: Mapped[str] = mapped_column(String(160), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    area: Mapped[Area] = mapped_column(Enum(Area), nullable=False)
    unidade: Mapped[Unidade] = mapped_column(
        Enum(Unidade), nullable=False, default=Unidade.NUM
    )
    tipo_acumulacao: Mapped[TipoAcumulacao] = mapped_column(
        Enum(TipoAcumulacao), nullable=False
    )
    melhor_direcao: Mapped[MelhorDirecao] = mapped_column(
        Enum(MelhorDirecao), nullable=False, default=MelhorDirecao.MAIOR
    )
    rotulo_numerador: Mapped[str | None] = mapped_column(String(80), nullable=True)
    rotulo_denominador: Mapped[str | None] = mapped_column(String(80), nullable=True)
    indicador_pai_id: Mapped[int | None] = mapped_column(Id, ForeignKey("indicadores.id", ondelete="SET NULL"), nullable=True
    )
    exibe_no_painel: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    ordem: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    filhos: Mapped[list["Indicador"]] = relationship(
        back_populates="pai", cascade="all"
    )
    pai: Mapped["Indicador | None"] = relationship(
        back_populates="filhos", remote_side=[id]
    )


class Ciclo(Base):
    """O mes de apuracao, dividido em semanas."""

    __tablename__ = "ciclos"

    id: Mapped[int] = mapped_column(Id, primary_key=True)
    ano: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    mes: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    semanas_total: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=4
    )
    semana_corrente: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=1
    )
    data_fechamento: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[StatusCiclo] = mapped_column(
        Enum(StatusCiclo), nullable=False, default=StatusCiclo.ABERTO
    )
    criado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    @property
    def rotulo(self) -> str:
        return f"{self.mes:02d}/{self.ano}"


class FonteDados(Base):
    """De onde vem cada numero. Hoje tudo MANUAL; a tabela existe para
    plugar Supabase, ERP, CRM e planilhas sem mexer na camada de KPI.

    Segredo de conexao NAO fica em `config` — vive no ambiente.
    """

    __tablename__ = "fontes_dados"

    id: Mapped[int] = mapped_column(Id, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    nome: Mapped[str] = mapped_column(String(160), nullable=False)
    tipo: Mapped[TipoFonte] = mapped_column(Enum(TipoFonte), nullable=False)
    config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ultima_sincronia: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    criado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
