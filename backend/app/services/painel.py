"""Regra de negocio do painel: consolida indicadores e suas medicoes."""
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.indicador import Indicador, Medicao, MelhorDirecao
from app.schemas.indicador import ResumoIndicador


def _variacao_pct(atual: Decimal, anterior: Decimal) -> float | None:
    """Variacao percentual entre duas medicoes. None se a base for zero."""
    if anterior == 0:
        return None
    return float((atual - anterior) / abs(anterior) * 100)


def _atingimento_pct(
    valor: Decimal, meta: Decimal | None, melhor_direcao: MelhorDirecao
) -> float | None:
    """Atingimento da meta, sempre na leitura "acima de 100% e bom".

    Para indicadores em que menor e melhor (inadimplencia, turnover), a razao
    e invertida: ficar abaixo da meta e o resultado desejado. Sem isso, uma
    inadimplencia de 4,3% contra meta de 3% apareceria como 142% de
    atingimento — numero alto sugerindo bom desempenho, quando e o oposto.
    """
    if meta is None or meta == 0 or valor == 0:
        return None
    if melhor_direcao is MelhorDirecao.MAIOR:
        return float(valor / meta * 100)
    return float(meta / valor * 100)


def montar_resumo(db: Session, area: str | None = None) -> list[ResumoIndicador]:
    """Uma linha por indicador ativo, com a medicao mais recente e a anterior."""
    stmt = select(Indicador).where(Indicador.ativo.is_(True))
    if area:
        stmt = stmt.where(Indicador.area == area)
    indicadores = list(db.scalars(stmt.order_by(Indicador.area, Indicador.nome)))

    if not indicadores:
        return []

    # Busca as duas ultimas medicoes de cada indicador em uma consulta por
    # indicador — suficiente para a escala de um painel executivo (dezenas
    # de indicadores), e mais legivel que uma window function.
    resumo: list[ResumoIndicador] = []
    for ind in indicadores:
        ultimas = list(
            db.scalars(
                select(Medicao)
                .where(Medicao.indicador_id == ind.id)
                .order_by(Medicao.competencia.desc())
                .limit(2)
            )
        )

        atual = ultimas[0] if ultimas else None
        anterior = ultimas[1] if len(ultimas) > 1 else None

        resumo.append(
            ResumoIndicador(
                codigo=ind.codigo,
                nome=ind.nome,
                area=ind.area,
                unidade=ind.unidade,
                melhor_direcao=ind.melhor_direcao,
                competencia=atual.competencia if atual else None,
                valor=atual.valor if atual else None,
                meta=atual.meta if atual else None,
                valor_anterior=anterior.valor if anterior else None,
                variacao_pct=(
                    _variacao_pct(atual.valor, anterior.valor)
                    if atual and anterior
                    else None
                ),
                atingimento_pct=(
                    _atingimento_pct(atual.valor, atual.meta, ind.melhor_direcao)
                    if atual
                    else None
                ),
            )
        )

    return resumo
