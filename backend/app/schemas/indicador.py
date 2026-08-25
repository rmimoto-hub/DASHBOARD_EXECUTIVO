"""Schemas de indicador e medicao."""
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.indicador import MelhorDirecao


class IndicadorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nome: str
    descricao: str | None
    unidade: str
    area: str
    melhor_direcao: MelhorDirecao
    ativo: bool


class IndicadorCreate(BaseModel):
    codigo: str = Field(min_length=2, max_length=60)
    nome: str = Field(min_length=2, max_length=160)
    descricao: str | None = None
    unidade: str = "NUM"
    area: str = "GERAL"
    melhor_direcao: MelhorDirecao = MelhorDirecao.MAIOR


class MedicaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    indicador_id: int
    competencia: date
    valor: Decimal
    meta: Decimal | None
    observacao: str | None
    criado_em: datetime


class MedicaoCreate(BaseModel):
    indicador_id: int
    competencia: date
    valor: Decimal
    meta: Decimal | None = None
    observacao: str | None = Field(default=None, max_length=500)


class ResumoIndicador(BaseModel):
    """Linha do painel: indicador + ultima medicao + variacao."""

    codigo: str
    nome: str
    area: str
    unidade: str
    melhor_direcao: MelhorDirecao
    competencia: date | None
    valor: Decimal | None
    meta: Decimal | None
    valor_anterior: Decimal | None
    variacao_pct: float | None
    atingimento_pct: float | None
