"""Contratos de saida do relatorio do comite."""
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class CicloOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ano: int
    mes: int
    semanas_total: int
    semana_corrente: int
    data_fechamento: date
    status: str


class RegionalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nome: str


class LinhaRegionalOut(BaseModel):
    regional_codigo: str
    regional_nome: str
    valor: Decimal | None
    meta: Decimal | None
    atingimento_pct: Decimal | None
    semaforo: str
    desvio_pp: Decimal | None


class PontoSerieOut(BaseModel):
    semana: int
    valor: Decimal | None
    valor_acumulado: Decimal | None


class ProjecaoOut(BaseModel):
    valor_projetado: Decimal | None
    atingimento_projetado_pct: Decimal | None
    gap: Decimal | None
    necessario_por_semana: Decimal | None
    esforco_vs_ritmo: Decimal | None
    semanas_restantes: int
    alcancavel: bool | None


class LinhaPainelOut(BaseModel):
    codigo: str
    nome: str
    area: str
    unidade: str
    tipo_acumulacao: str
    melhor_direcao: str
    rotulo_numerador: str | None
    rotulo_denominador: str | None

    valor: Decimal | None
    numerador: Decimal | None
    denominador: Decimal | None
    meta: Decimal | None
    atingimento_pct: Decimal | None
    esperado_pct: Decimal
    desvio_pp: Decimal | None
    semaforo: str

    projecao: ProjecaoOut
    regionais: list[LinhaRegionalOut]
    serie: list[PontoSerieOut]


class PainelOut(BaseModel):
    """Resposta do painel geral: o ciclo mais as linhas."""

    ciclo: CicloOut
    semana: int
    esperado_acumula_pct: Decimal
    linhas: list[LinhaPainelOut]


class ItemPauta(BaseModel):
    """Uma linha da pauta sugerida, ordenada pelo pior desvio."""

    posicao: int
    codigo: str
    nome: str
    area: str
    semaforo: str
    atingimento_pct: Decimal | None
    esperado_pct: Decimal
    desvio_pp: Decimal | None
    regional_critica: str | None
    desvio_regional_pp: Decimal | None
    projecao_pct: Decimal | None


class PautaOut(BaseModel):
    ciclo: CicloOut
    semana: int
    itens: list[ItemPauta]


class CelulaMatriz(BaseModel):
    regional_codigo: str
    atingimento_pct: Decimal | None
    desvio_pp: Decimal | None
    semaforo: str


class LinhaMatriz(BaseModel):
    codigo: str
    nome: str
    area: str
    consolidado_semaforo: str
    consolidado_desvio_pp: Decimal | None
    celulas: list[CelulaMatriz]


class ResumoRegional(BaseModel):
    """Sintese de uma regional — "onde esta a quebra"."""

    regional_codigo: str
    regional_nome: str
    verdes: int
    ambares: int
    vermelhos: int
    sem_dado: int
    desvio_medio_pp: Decimal | None
    status: str
    kpis_criticos: list[str]


class MatrizOut(BaseModel):
    ciclo: CicloOut
    semana: int
    regionais: list[RegionalOut]
    linhas: list[LinhaMatriz]
    resumo_regional: list[ResumoRegional]


class DetalhamentoOut(BaseModel):
    dimensao: str
    categoria: str
    valor: Decimal
    regional_codigo: str | None
    ordem: int


class OcorrenciaEntregaOut(BaseModel):
    cliente_rotulo: str
    regional_codigo: str | None
    causa: str
    motivo: str
    pedidos_afetados: int
    plano_acao: str | None
    responsavel: str | None


class TituloInadimplenteOut(BaseModel):
    posicao: int
    cliente_rotulo: str
    regional_codigo: str | None
    consultor: str | None
    valor_aberto: Decimal
    dias_atraso: int | None
    em_negociacao: bool
    pct_do_total: Decimal
    pct_acumulado: Decimal


class CompromissoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    frente: str
    acao: str
    responsavel: str
    prazo: date
    status: str
    semana_origem: int
    indicador_codigo: str | None
    regional_codigo: str | None
    resultado: str | None


class NotaOut(BaseModel):
    semana: int
    indicador_codigo: str | None
    regional_codigo: str | None
    texto: str
