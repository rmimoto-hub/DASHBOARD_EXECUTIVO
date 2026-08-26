"""Rotas do relatorio do comite executivo.

Somente leitura nesta versao. A ordem dos endpoints acompanha o ritual
da reuniao: pauta -> painel -> matriz -> detalhe -> compromissos.
"""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import usuario_atual
from app.core.database import get_db
from app.models.cadastro import Area, Ciclo, Indicador, Regional, StatusCiclo
from app.models.fatos import Detalhamento
from app.models.nominal import (
    Compromisso,
    NotaAnalitica,
    OcorrenciaEntrega,
    TituloInadimplente,
)
from app.models.usuario import Usuario
from app.schemas.painel import (
    CelulaMatriz,
    CompromissoOut,
    DetalhamentoOut,
    ItemPauta,
    LinhaMatriz,
    LinhaPainelOut,
    LinhaRegionalOut,
    MatrizOut,
    NotaOut,
    OcorrenciaEntregaOut,
    PainelOut,
    PautaOut,
    PontoSerieOut,
    ProjecaoOut,
    RegionalOut,
    ResumoRegional,
    TituloInadimplenteOut,
)
from app.services.kpi import TipoAcumulacao, esperado_na_semana
from app.services.painel import montar_painel, montar_pauta, resumir_regionais

router = APIRouter(prefix="/comite", tags=["comite executivo"])


# ---------------------------------------------------------------------
# Resolucao do ciclo e da semana
# ---------------------------------------------------------------------


def _resolver_ciclo(db: Session, ciclo_id: int | None) -> Ciclo:
    if ciclo_id is not None:
        ciclo = db.get(Ciclo, ciclo_id)
        if ciclo is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Ciclo nao encontrado"
            )
        return ciclo

    # Sem ciclo informado: o aberto mais recente, ou o ultimo de todos.
    ciclo = db.scalar(
        select(Ciclo)
        .where(Ciclo.status == StatusCiclo.ABERTO)
        .order_by(Ciclo.ano.desc(), Ciclo.mes.desc())
        .limit(1)
    ) or db.scalar(
        select(Ciclo).order_by(Ciclo.ano.desc(), Ciclo.mes.desc()).limit(1)
    )
    if ciclo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhum ciclo cadastrado",
        )
    return ciclo


def _resolver_semana(ciclo: Ciclo, semana: int | None) -> int:
    if semana is None:
        return ciclo.semana_corrente
    if not 1 <= semana <= ciclo.semanas_total:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Semana {semana} fora do ciclo, que tem "
                f"{ciclo.semanas_total} semanas"
            ),
        )
    return semana


# ---------------------------------------------------------------------
# Ciclos
# ---------------------------------------------------------------------


@router.get("/ciclos", response_model=list[dict])
def listar_ciclos(
    db: Session = Depends(get_db), _: Usuario = Depends(usuario_atual)
) -> list[dict]:
    ciclos = db.scalars(
        select(Ciclo).order_by(Ciclo.ano.desc(), Ciclo.mes.desc())
    )
    return [
        {
            "id": c.id,
            "ano": c.ano,
            "mes": c.mes,
            "rotulo": c.rotulo,
            "semanas_total": c.semanas_total,
            "semana_corrente": c.semana_corrente,
            "data_fechamento": c.data_fechamento.isoformat(),
            "status": c.status.value,
        }
        for c in ciclos
    ]


# ---------------------------------------------------------------------
# 1. Pauta — por onde comecar a reuniao
# ---------------------------------------------------------------------


@router.get("/pauta", response_model=PautaOut)
def pauta(
    ciclo_id: int | None = Query(default=None),
    semana: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_atual),
) -> PautaOut:
    """Os KPIs fora do ritmo, do pior desvio para o menor."""
    ciclo = _resolver_ciclo(db, ciclo_id)
    sem = _resolver_semana(ciclo, semana)
    painel = montar_painel(db, ciclo, sem)

    itens = [
        ItemPauta(
            posicao=item.posicao,
            codigo=item.linha.codigo,
            nome=item.linha.nome,
            area=item.linha.area,
            semaforo=item.linha.semaforo.value,
            atingimento_pct=item.linha.atingimento_pct,
            esperado_pct=item.linha.esperado_pct,
            desvio_pp=item.linha.desvio_pp,
            regional_critica=(
                item.regional_critica.regional_codigo
                if item.regional_critica
                else None
            ),
            desvio_regional_pp=(
                item.regional_critica.desvio_pp if item.regional_critica else None
            ),
            projecao_pct=item.linha.projecao.atingimento_projetado_pct,
        )
        for item in montar_pauta(painel)
    ]
    return PautaOut(ciclo=ciclo, semana=sem, itens=itens)


# ---------------------------------------------------------------------
# 2. Painel geral
# ---------------------------------------------------------------------


def _linha_out(linha) -> LinhaPainelOut:
    return LinhaPainelOut(
        codigo=linha.codigo,
        nome=linha.nome,
        area=linha.area,
        unidade=linha.unidade,
        tipo_acumulacao=linha.tipo_acumulacao,
        melhor_direcao=linha.melhor_direcao,
        rotulo_numerador=linha.rotulo_numerador,
        rotulo_denominador=linha.rotulo_denominador,
        valor=linha.valor,
        numerador=linha.numerador,
        denominador=linha.denominador,
        meta=linha.meta,
        atingimento_pct=linha.atingimento_pct,
        esperado_pct=linha.esperado_pct,
        desvio_pp=linha.desvio_pp,
        semaforo=linha.semaforo.value,
        projecao=ProjecaoOut(
            valor_projetado=linha.projecao.valor_projetado,
            atingimento_projetado_pct=linha.projecao.atingimento_projetado_pct,
            gap=linha.projecao.gap,
            necessario_por_semana=linha.projecao.necessario_por_semana,
            esforco_vs_ritmo=linha.projecao.esforco_vs_ritmo,
            semanas_restantes=linha.projecao.semanas_restantes,
            alcancavel=linha.projecao.alcancavel,
        ),
        regionais=[
            LinhaRegionalOut(
                regional_codigo=r.regional_codigo,
                regional_nome=r.regional_nome,
                valor=r.valor,
                meta=r.meta,
                atingimento_pct=r.atingimento_pct,
                semaforo=r.semaforo.value,
                desvio_pp=r.desvio_pp,
            )
            for r in linha.regionais
        ],
        serie=[
            PontoSerieOut(
                semana=p.semana,
                valor=p.valor,
                valor_acumulado=p.valor_acumulado,
            )
            for p in linha.serie
        ],
    )


@router.get("/painel", response_model=PainelOut)
def painel_geral(
    ciclo_id: int | None = Query(default=None),
    semana: int | None = Query(default=None),
    area: Area | None = Query(default=None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_atual),
) -> PainelOut:
    """Todos os KPIs com realizado, meta, atingimento, ritmo e projecao."""
    ciclo = _resolver_ciclo(db, ciclo_id)
    sem = _resolver_semana(ciclo, semana)
    linhas = montar_painel(db, ciclo, sem, area.value if area else None)

    return PainelOut(
        ciclo=ciclo,
        semana=sem,
        esperado_acumula_pct=esperado_na_semana(
            TipoAcumulacao.ACUMULA, sem, ciclo.semanas_total
        ),
        linhas=[_linha_out(linha) for linha in linhas],
    )


@router.get("/painel/{codigo}", response_model=LinhaPainelOut)
def detalhe_indicador(
    codigo: str,
    ciclo_id: int | None = Query(default=None),
    semana: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_atual),
) -> LinhaPainelOut:
    """Um KPI aberto: serie semanal, regionais e projecao."""
    ciclo = _resolver_ciclo(db, ciclo_id)
    sem = _resolver_semana(ciclo, semana)
    for linha in montar_painel(db, ciclo, sem):
        if linha.codigo == codigo:
            return _linha_out(linha)
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Indicador {codigo} nao encontrado no painel deste ciclo",
    )


# ---------------------------------------------------------------------
# 3. Matriz — onde esta a quebra, de relance
# ---------------------------------------------------------------------


@router.get("/matriz", response_model=MatrizOut)
def matriz(
    ciclo_id: int | None = Query(default=None),
    semana: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_atual),
) -> MatrizOut:
    """Todos os KPIs contra todas as regionais, em uma grade."""
    ciclo = _resolver_ciclo(db, ciclo_id)
    sem = _resolver_semana(ciclo, semana)
    painel = montar_painel(db, ciclo, sem)

    regionais = list(
        db.scalars(
            select(Regional).where(Regional.ativo.is_(True)).order_by(Regional.ordem)
        )
    )

    return MatrizOut(
        ciclo=ciclo,
        semana=sem,
        regionais=[RegionalOut.model_validate(r) for r in regionais],
        linhas=[
            LinhaMatriz(
                codigo=linha.codigo,
                nome=linha.nome,
                area=linha.area,
                consolidado_semaforo=linha.semaforo.value,
                consolidado_desvio_pp=linha.desvio_pp,
                celulas=[
                    CelulaMatriz(
                        regional_codigo=r.regional_codigo,
                        atingimento_pct=r.atingimento_pct,
                        desvio_pp=r.desvio_pp,
                        semaforo=r.semaforo.value,
                    )
                    for r in linha.regionais
                ],
            )
            for linha in painel
        ],
        resumo_regional=[
            ResumoRegional(
                regional_codigo=r.regional_codigo,
                regional_nome=r.regional_nome,
                verdes=r.verdes,
                ambares=r.ambares,
                vermelhos=r.vermelhos,
                sem_dado=r.sem_dado,
                desvio_medio_pp=r.desvio_medio_pp,
                status=r.status,
                kpis_criticos=r.kpis_criticos,
            )
            for r in resumir_regionais(painel)
        ],
    )


# ---------------------------------------------------------------------
# 4. Detalhe nominal — o que transforma diagnostico em acao
# ---------------------------------------------------------------------


@router.get("/detalhamentos/{codigo}", response_model=list[DetalhamentoOut])
def detalhamentos(
    codigo: str,
    dimensao: str | None = Query(default=None),
    ciclo_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_atual),
) -> list[DetalhamentoOut]:
    """Quebra de um KPI por categoria: motivos de perda, faixas de cobertura."""
    ciclo = _resolver_ciclo(db, ciclo_id)
    indicador = db.scalar(select(Indicador).where(Indicador.codigo == codigo))
    if indicador is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Indicador {codigo} nao encontrado",
        )

    stmt = select(Detalhamento).where(
        Detalhamento.indicador_id == indicador.id,
        Detalhamento.ciclo_id == ciclo.id,
    )
    if dimensao:
        stmt = stmt.where(Detalhamento.dimensao == dimensao)

    return [
        DetalhamentoOut(
            dimensao=d.dimensao,
            categoria=d.categoria,
            valor=d.valor,
            regional_codigo=d.regional.codigo if d.regional else None,
            ordem=d.ordem,
        )
        for d in db.scalars(stmt.order_by(Detalhamento.ordem, Detalhamento.valor.desc()))
    ]


@router.get("/ocorrencias-entrega", response_model=list[OcorrenciaEntregaOut])
def ocorrencias_entrega(
    ciclo_id: int | None = Query(default=None),
    semana: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_atual),
) -> list[OcorrenciaEntregaOut]:
    """Pedidos com problema da semana, por cliente, causa e plano."""
    ciclo = _resolver_ciclo(db, ciclo_id)
    sem = _resolver_semana(ciclo, semana)

    stmt = (
        select(OcorrenciaEntrega)
        .where(
            OcorrenciaEntrega.ciclo_id == ciclo.id,
            OcorrenciaEntrega.semana == sem,
        )
        .order_by(OcorrenciaEntrega.pedidos_afetados.desc())
    )
    return [
        OcorrenciaEntregaOut(
            cliente_rotulo=o.cliente_rotulo,
            regional_codigo=o.regional.codigo if o.regional else None,
            causa=o.causa,
            motivo=o.motivo,
            pedidos_afetados=o.pedidos_afetados,
            plano_acao=o.plano_acao,
            responsavel=o.responsavel,
        )
        for o in db.scalars(stmt)
    ]


@router.get("/inadimplentes", response_model=list[TituloInadimplenteOut])
def inadimplentes(
    ciclo_id: int | None = Query(default=None),
    semana: int | None = Query(default=None),
    limite: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_atual),
) -> list[TituloInadimplenteOut]:
    """Carteira em aberto por cliente, com concentracao acumulada.

    O % acumulado sustenta a leitura 80/20 do comite — quantos clientes
    respondem pela maior parte do valor.
    """
    ciclo = _resolver_ciclo(db, ciclo_id)
    sem = _resolver_semana(ciclo, semana)

    titulos = list(
        db.scalars(
            select(TituloInadimplente)
            .where(
                TituloInadimplente.ciclo_id == ciclo.id,
                TituloInadimplente.semana == sem,
            )
            .order_by(TituloInadimplente.valor_aberto.desc())
        )
    )
    if not titulos:
        return []

    # O total considera a carteira inteira, nao apenas os `limite`
    # primeiros — senao o percentual acumulado fecharia sempre em 100%.
    total = sum((t.valor_aberto for t in titulos), Decimal(0))

    saida: list[TituloInadimplenteOut] = []
    acumulado = Decimal(0)
    for pos, t in enumerate(titulos[:limite], start=1):
        acumulado += t.valor_aberto
        saida.append(
            TituloInadimplenteOut(
                posicao=pos,
                cliente_rotulo=t.cliente_rotulo,
                regional_codigo=t.regional.codigo if t.regional else None,
                consultor=t.consultor,
                valor_aberto=t.valor_aberto,
                dias_atraso=t.dias_atraso,
                em_negociacao=t.em_negociacao,
                pct_do_total=(
                    t.valor_aberto / total * 100 if total else Decimal(0)
                ),
                pct_acumulado=acumulado / total * 100 if total else Decimal(0),
            )
        )
    return saida


# ---------------------------------------------------------------------
# 5. Compromissos e notas — o que fecha o ciclo da reuniao
# ---------------------------------------------------------------------


@router.get("/compromissos", response_model=list[CompromissoOut])
def compromissos(
    ciclo_id: int | None = Query(default=None),
    apenas_abertos: bool = Query(default=False),
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_atual),
) -> list[CompromissoOut]:
    """O que o comite assumiu, com responsavel, prazo e o KPI ligado."""
    ciclo = _resolver_ciclo(db, ciclo_id)

    stmt = select(Compromisso).where(Compromisso.ciclo_id == ciclo.id)
    if apenas_abertos:
        stmt = stmt.where(
            Compromisso.status.in_(["ABERTO", "EM_ANDAMENTO", "ATRASADO"])
        )

    return [
        CompromissoOut(
            id=c.id,
            frente=c.frente,
            acao=c.acao,
            responsavel=c.responsavel,
            prazo=c.prazo,
            status=c.status.value,
            semana_origem=c.semana_origem,
            indicador_codigo=c.indicador.codigo if c.indicador else None,
            regional_codigo=c.regional.codigo if c.regional else None,
            resultado=c.resultado,
        )
        for c in db.scalars(stmt.order_by(Compromisso.prazo))
    ]


@router.get("/notas", response_model=list[NotaOut])
def notas(
    ciclo_id: int | None = Query(default=None),
    semana: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_atual),
) -> list[NotaOut]:
    """A leitura registrada pelo comite sobre cada KPI na semana."""
    ciclo = _resolver_ciclo(db, ciclo_id)
    sem = _resolver_semana(ciclo, semana)

    stmt = (
        select(NotaAnalitica)
        .where(NotaAnalitica.ciclo_id == ciclo.id, NotaAnalitica.semana == sem)
        .order_by(NotaAnalitica.indicador_id)
    )
    saida: list[NotaOut] = []
    for n in db.scalars(stmt):
        indicador = db.get(Indicador, n.indicador_id) if n.indicador_id else None
        saida.append(
            NotaOut(
                semana=n.semana,
                indicador_codigo=indicador.codigo if indicador else None,
                regional_codigo=n.regional.codigo if n.regional else None,
                texto=n.texto,
            )
        )
    return saida
