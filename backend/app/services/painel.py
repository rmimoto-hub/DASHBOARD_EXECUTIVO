"""Monta as visoes do relatorio do comite a partir do banco.

Segue a ordem do ritual da reuniao:
  linha_do_painel()  — quanto realizamos e quanto e da meta
  abertura_regional() — onde esta a quebra
  serie_semanal()     — como chegamos aqui
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cadastro import Ciclo, Indicador, Regional
from app.models.fatos import Medicao, Meta
from app.services.kpi import (
    Projecao,
    Semaforo,
    ValorMedido,
    acumular,
    atingimento,
    consolidar,
    desvio_do_ritmo,
    esperado_na_semana,
    projetar_fechamento,
    semaforo,
)


@dataclass
class LinhaRegional:
    """Um indicador visto por uma regional."""

    regional_codigo: str
    regional_nome: str
    valor: Decimal | None
    meta: Decimal | None
    atingimento_pct: Decimal | None
    semaforo: Semaforo
    desvio_pp: Decimal | None


@dataclass
class PontoSerie:
    semana: int
    valor: Decimal | None
    valor_acumulado: Decimal | None


@dataclass
class LinhaPainel:
    """Um indicador no painel geral, com sua abertura por regional."""

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
    semaforo: Semaforo

    projecao: Projecao
    regionais: list[LinhaRegional]
    serie: list[PontoSerie]


def _medicoes_do_ciclo(
    db: Session, ciclo: Ciclo, ate_semana: int
) -> dict[int, dict[int, dict[int, Medicao]]]:
    """Medicoes indexadas por indicador -> semana -> regional.

    Uma consulta para todo o painel, em vez de uma por indicador.
    """
    stmt = select(Medicao).where(
        Medicao.ciclo_id == ciclo.id, Medicao.semana <= ate_semana
    )
    indice: dict[int, dict[int, dict[int, Medicao]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    for m in db.scalars(stmt):
        indice[m.indicador_id][m.semana][m.regional_id] = m
    return indice


def _metas_do_ciclo(db: Session, ciclo: Ciclo) -> dict[tuple[int, int | None], Decimal]:
    """Metas indexadas por (indicador, regional). regional None = consolidada."""
    stmt = select(Meta).where(Meta.ciclo_id == ciclo.id)
    return {(m.indicador_id, m.regional_id): m.valor for m in db.scalars(stmt)}


def _medido(m: Medicao) -> ValorMedido:
    return ValorMedido(m.valor_numerador, m.valor_denominador)


def montar_painel(
    db: Session,
    ciclo: Ciclo,
    semana: int | None = None,
    area: str | None = None,
) -> list[LinhaPainel]:
    """O painel geral: uma linha por indicador, com abertura regional."""
    semana = semana or ciclo.semana_corrente

    stmt = select(Indicador).where(
        Indicador.ativo.is_(True), Indicador.exibe_no_painel.is_(True)
    )
    if area:
        stmt = stmt.where(Indicador.area == area)
    indicadores = list(db.scalars(stmt.order_by(Indicador.area, Indicador.ordem)))
    if not indicadores:
        return []

    regionais = {
        r.id: r
        for r in db.scalars(
            select(Regional).where(Regional.ativo.is_(True)).order_by(Regional.ordem)
        )
    }
    medicoes = _medicoes_do_ciclo(db, ciclo, semana)
    metas = _metas_do_ciclo(db, ciclo)

    painel: list[LinhaPainel] = []
    for ind in indicadores:
        por_semana = medicoes.get(ind.id, {})
        semanas_ordenadas = sorted(por_semana)

        # Consolidado da empresa em cada semana, e o acumulado do mes.
        consolidado_semanal = [
            consolidar([_medido(m) for m in por_semana[s].values()])
            for s in semanas_ordenadas
        ]
        consolidado_semanal = [c for c in consolidado_semanal if c is not None]
        total = acumular(consolidado_semanal, ind.tipo_acumulacao)

        meta_consolidada = metas.get((ind.id, None))
        esperado = esperado_na_semana(ind.tipo_acumulacao, semana, ciclo.semanas_total)
        ating = atingimento(
            total.valor if total else None, meta_consolidada, ind.melhor_direcao
        )

        painel.append(
            LinhaPainel(
                codigo=ind.codigo,
                nome=ind.nome,
                area=ind.area.value,
                unidade=ind.unidade.value,
                tipo_acumulacao=ind.tipo_acumulacao.value,
                melhor_direcao=ind.melhor_direcao.value,
                rotulo_numerador=ind.rotulo_numerador,
                rotulo_denominador=ind.rotulo_denominador,
                valor=total.valor if total else None,
                numerador=total.numerador if total else None,
                denominador=total.denominador if total else None,
                meta=meta_consolidada,
                atingimento_pct=ating,
                esperado_pct=esperado,
                desvio_pp=desvio_do_ritmo(ating, esperado),
                semaforo=semaforo(ating, esperado),
                projecao=projetar_fechamento(
                    ind.tipo_acumulacao,
                    total.valor if total else None,
                    meta_consolidada,
                    ind.melhor_direcao,
                    semana,
                    ciclo.semanas_total,
                ),
                regionais=_abertura_regional(
                    ind, por_semana, semanas_ordenadas, regionais,
                    metas, esperado, semana, ciclo,
                ),
                serie=_serie_semanal(ind, por_semana, semanas_ordenadas),
            )
        )

    return painel


def _abertura_regional(
    ind: Indicador,
    por_semana: dict[int, dict[int, Medicao]],
    semanas: list[int],
    regionais: dict[int, Regional],
    metas: dict[tuple[int, int | None], Decimal],
    esperado: Decimal,
    semana_atual: int,
    ciclo: Ciclo,
) -> list[LinhaRegional]:
    """O indicador aberto por regional — "onde esta a quebra".

    Sem meta cadastrada para a regional, cai-se num rateio da meta
    consolidada. Se ratear ou nao depende de o valor ser ADITIVO ou uma
    RAZAO — e nao do tipo de acumulacao:

      sem denominador  valor aditivo (faturamento, clientes ativos,
                       leads). A meta se rateia: somar as regionais tem
                       de reproduzir o consolidado.
      com denominador  razao (margem %, OTIF, inadimplencia). A meta NAO
                       se rateia: 98% de OTIF e exigido de cada regional.

    Comparar um estoque contra a meta consolidada produziria absurdos —
    RS com 64 clientes ativos contra a meta de 448 da empresa daria 14%.

    Aviso: o rateio pelo peso do realizado faz todas as regionais
    exibirem o mesmo atingimento, o que apaga a quebra. E melhor que
    nada para nao deixar a regional sem semaforo, mas o comite deve
    cadastrar meta por regional — e isso que revela quem esta fora.
    """
    meta_consolidada = metas.get((ind.id, None))

    # Realizado de cada regional no mes.
    realizado: dict[int, ValorMedido | None] = {}
    for rid in regionais:
        serie = [
            _medido(por_semana[s][rid]) for s in semanas if rid in por_semana[s]
        ]
        realizado[rid] = acumular(serie, ind.tipo_acumulacao) if serie else None

    # O indicador e uma razao quando as medicoes trazem denominador.
    eh_razao = any(
        v.denominador is not None for v in realizado.values() if v is not None
    )

    # Peso da regional, para ratear a meta consolidada quando preciso.
    base = sum(
        (v.numerador for v in realizado.values() if v is not None), Decimal(0)
    )

    linhas: list[LinhaRegional] = []
    for rid, reg in sorted(regionais.items(), key=lambda kv: kv[1].ordem):
        medido = realizado[rid]
        meta_reg = metas.get((ind.id, rid))

        if meta_reg is None and meta_consolidada is not None and medido is not None:
            if eh_razao:
                # Uma razao nao se rateia: exigida por inteiro de todos.
                meta_reg = meta_consolidada
            elif base > 0:
                # Valor aditivo: rateia pelo peso da regional.
                meta_reg = meta_consolidada * (medido.numerador / base)

        ating = atingimento(
            medido.valor if medido else None, meta_reg, ind.melhor_direcao
        )
        linhas.append(
            LinhaRegional(
                regional_codigo=reg.codigo,
                regional_nome=reg.nome,
                valor=medido.valor if medido else None,
                meta=meta_reg,
                atingimento_pct=ating,
                semaforo=semaforo(ating, esperado),
                desvio_pp=desvio_do_ritmo(ating, esperado),
            )
        )
    return linhas


def _serie_semanal(
    ind: Indicador,
    por_semana: dict[int, dict[int, Medicao]],
    semanas: list[int],
) -> list[PontoSerie]:
    """Evolucao semana a semana, com o acumulado corrente."""
    pontos: list[PontoSerie] = []
    consolidados: list[ValorMedido] = []

    for s in semanas:
        c = consolidar([_medido(m) for m in por_semana[s].values()])
        if c is None:
            pontos.append(PontoSerie(semana=s, valor=None, valor_acumulado=None))
            continue
        consolidados.append(c)
        acumulado = acumular(consolidados, ind.tipo_acumulacao)
        pontos.append(
            PontoSerie(
                semana=s,
                valor=c.valor,
                valor_acumulado=acumulado.valor if acumulado else None,
            )
        )
    return pontos


# =====================================================================
# Visoes derivadas: pauta e matriz
# =====================================================================

# Um KPI cai na pauta quando esta pelo menos este tanto atras do ritmo.
# Acima disso e desempenho normal e nao merece tempo de reuniao.
LIMITE_PAUTA_PP = Decimal("-1")


@dataclass
class ItemPautaCalc:
    posicao: int
    linha: LinhaPainel
    regional_critica: LinhaRegional | None


def montar_pauta(painel: list[LinhaPainel]) -> list[ItemPautaCalc]:
    """Ordena os KPIs pelo pior desvio do ritmo.

    O painel geral agrupa por area, que e bom para consultar e ruim para
    conduzir a reuniao. A pauta responde "por onde comecar": o mais
    atrasado primeiro, e ja aponta qual regional puxa o indicador.
    """
    candidatos = [
        linha
        for linha in painel
        if linha.desvio_pp is not None and linha.desvio_pp <= LIMITE_PAUTA_PP
    ]
    candidatos.sort(key=lambda linha: linha.desvio_pp or Decimal(0))

    itens: list[ItemPautaCalc] = []
    for pos, linha in enumerate(candidatos, start=1):
        com_desvio = [
            r for r in linha.regionais if r.desvio_pp is not None
        ]
        pior = min(com_desvio, key=lambda r: r.desvio_pp) if com_desvio else None
        itens.append(ItemPautaCalc(posicao=pos, linha=linha, regional_critica=pior))
    return itens


@dataclass
class ResumoRegionalCalc:
    regional_codigo: str
    regional_nome: str
    verdes: int
    ambares: int
    vermelhos: int
    sem_dado: int
    desvio_medio_pp: Decimal | None
    status: str
    kpis_criticos: list[str]


# Classificacao da regional pelo DESVIO MEDIO do ritmo, em pontos
# percentuais. Politica do comite, exposta aqui em vez de escondida no
# meio do calculo.
#
# Contar vermelhos nao serve: quando um problema e estrutural da empresa
# — estoque e inadimplencia fora da meta em toda parte — a regional mais
# forte acumula tantos vermelhos quanto a mais fraca e todas viram
# "criticas", apagando a diferenca. O desvio medio compara desempenho,
# nao quantidade de problemas herdados.
DESVIO_ATENCAO_PP = Decimal("-10")
DESVIO_CRITICO_PP = Decimal("-25")


def resumir_regionais(painel: list[LinhaPainel]) -> list[ResumoRegionalCalc]:
    """Sintese por regional — a conclusao do "onde esta a quebra".

    O deck escreve esse diagnostico a mao. Aqui ele e derivado: conta os
    semaforos de cada regional em todos os KPIs e nomeia os criticos.
    Assim a leitura nao depende de quem montou o slide.
    """
    if not painel:
        return []

    por_regional: dict[str, dict] = {}
    for linha in painel:
        for r in linha.regionais:
            acc = por_regional.setdefault(
                r.regional_codigo,
                {"nome": r.regional_nome, "sem": [], "desvios": [], "criticos": []},
            )
            acc["sem"].append(r.semaforo)
            if r.desvio_pp is not None:
                acc["desvios"].append(r.desvio_pp)
            if r.semaforo is Semaforo.VERMELHO:
                acc["criticos"].append(linha.codigo)

    resumos: list[ResumoRegionalCalc] = []
    for codigo, acc in por_regional.items():
        vermelhos = acc["sem"].count(Semaforo.VERMELHO)
        desvios = acc["desvios"]
        media = (
            sum(desvios, Decimal(0)) / Decimal(len(desvios)) if desvios else None
        )

        if media is None:
            status = "NO_RITMO"
        elif media < DESVIO_CRITICO_PP:
            status = "CRITICO"
        elif media < DESVIO_ATENCAO_PP:
            status = "ATENCAO"
        else:
            status = "NO_RITMO"
        resumos.append(
            ResumoRegionalCalc(
                regional_codigo=codigo,
                regional_nome=acc["nome"],
                verdes=acc["sem"].count(Semaforo.VERDE),
                ambares=acc["sem"].count(Semaforo.AMBAR),
                vermelhos=vermelhos,
                sem_dado=acc["sem"].count(Semaforo.SEM_DADO),
                desvio_medio_pp=media,
                status=status,
                kpis_criticos=acc["criticos"],
            )
        )

    # Pior primeiro: e a ordem em que a reuniao deve tratar as regionais.
    resumos.sort(key=lambda r: r.desvio_medio_pp or Decimal(0))
    return resumos
