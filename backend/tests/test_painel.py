"""Montagem do painel a partir do banco: consolidacao, regionais, pauta."""
from decimal import Decimal as D

import pytest

from app.models.cadastro import Indicador, MelhorDirecao, TipoAcumulacao
from app.services.kpi import Semaforo
from app.services.painel import (
    montar_painel,
    montar_pauta,
    resumir_regionais,
)


# --- consolidacao vinda do banco --------------------------------------


def test_acumula_soma_semanas_e_regionais(
    db_session, ciclo, regionais, indicador_acumula, lancar, definir_meta
):
    """Faturamento do deck: 3 semanas x 3 regionais somam 2,44 mi."""
    valores = {
        "SP": [D("0.33"), D("0.30"), D("0.29")],
        "RJ": [D("0.34"), D("0.28"), D("0.28")],
        "RS": [D("0.22"), D("0.20"), D("0.20")],
    }
    for cod, semanas in valores.items():
        for i, v in enumerate(semanas, start=1):
            lancar(indicador_acumula, ciclo, i, regionais[cod], v)
    definir_meta(indicador_acumula, ciclo, D("3.70"))

    (linha,) = montar_painel(db_session, ciclo, semana=3)
    esperado = sum(sum(v) for v in valores.values())
    assert linha.valor == esperado
    assert linha.meta == D("3.70")
    # 2,44 / 3,70 = 66%
    assert round(float(linha.atingimento_pct)) == 66
    assert linha.esperado_pct == D("75")
    assert linha.semaforo is Semaforo.AMBAR


def test_taxa_consolida_ponderada_nao_pela_media(
    db_session, ciclo, regionais, indicador_taxa, lancar, definir_meta
):
    """OTIF do deck: ponderado da 92,3%, media simples daria 89,6%."""
    # (no prazo, entregues) acumulados do mes, lancados na semana 3
    lancar(indicador_taxa, ciclo, 3, regionais["SP"], D("706"), D("738"))
    lancar(indicador_taxa, ciclo, 3, regionais["RJ"], D("316"), D("347"))
    lancar(indicador_taxa, ciclo, 3, regionais["RS"], D("163"), D("199"))
    definir_meta(indicador_taxa, ciclo, D("0.98"))

    (linha,) = montar_painel(db_session, ciclo, semana=3)
    assert round(float(linha.valor) * 100, 1) == 92.3
    assert linha.numerador == D("1185")
    assert linha.denominador == D("1284")
    # Taxa exige 100% em qualquer semana.
    assert linha.esperado_pct == D("100")


def test_taxa_toma_a_semana_mais_recente_nao_a_soma(
    db_session, ciclo, regionais, indicador_taxa, lancar, definir_meta
):
    lancar(indicador_taxa, ciclo, 1, regionais["SP"], D("90"), D("100"))
    lancar(indicador_taxa, ciclo, 2, regionais["SP"], D("80"), D("100"))
    lancar(indicador_taxa, ciclo, 3, regionais["SP"], D("95"), D("100"))
    definir_meta(indicador_taxa, ciclo, D("0.98"))

    (linha,) = montar_painel(db_session, ciclo, semana=3)
    assert linha.valor == D("0.95")  # a S3, nao 265/300


def test_semana_anterior_ignora_lancamentos_futuros(
    db_session, ciclo, regionais, indicador_acumula, lancar, definir_meta
):
    """Consultar a semana 2 deve mostrar o mundo como era na semana 2."""
    for s, v in [(1, D("1.0")), (2, D("1.0")), (3, D("1.0"))]:
        lancar(indicador_acumula, ciclo, s, regionais["SP"], v)
    definir_meta(indicador_acumula, ciclo, D("4.0"))

    linha_s2 = montar_painel(db_session, ciclo, semana=2)[0]
    linha_s3 = montar_painel(db_session, ciclo, semana=3)[0]
    assert linha_s2.valor == D("2.0")
    assert linha_s3.valor == D("3.0")
    assert linha_s2.esperado_pct == D("50")
    assert linha_s3.esperado_pct == D("75")


# --- abertura por regional --------------------------------------------


def test_regional_sem_meta_recebe_rateio_proporcional(
    db_session, ciclo, regionais, indicador_acumula, lancar, definir_meta
):
    """Sem meta propria, a regional e comparada com sua fatia do total.

    Sem isso ela apareceria sem semaforo, escondendo a quebra.
    """
    lancar(indicador_acumula, ciclo, 3, regionais["SP"], D("60"))
    lancar(indicador_acumula, ciclo, 3, regionais["RJ"], D("30"))
    lancar(indicador_acumula, ciclo, 3, regionais["RS"], D("10"))
    definir_meta(indicador_acumula, ciclo, D("200"))

    (linha,) = montar_painel(db_session, ciclo, semana=3)
    por_codigo = {r.regional_codigo: r for r in linha.regionais}

    # SP fez 60 de 100 realizados = 60% do peso -> meta rateada 120
    assert por_codigo["SP"].meta == D("120")
    assert por_codigo["RJ"].meta == D("60")
    assert por_codigo["RS"].meta == D("20")
    # Todas com o mesmo atingimento, porque o rateio segue o realizado.
    assert all(
        round(float(r.atingimento_pct)) == 50 for r in linha.regionais
    )


def test_taxa_nao_rateia_meta_entre_regionais(
    db_session, ciclo, regionais, indicador_taxa, lancar, definir_meta
):
    """Uma taxa e exigida por inteiro de cada regional."""
    lancar(indicador_taxa, ciclo, 3, regionais["SP"], D("95"), D("100"))
    lancar(indicador_taxa, ciclo, 3, regionais["RS"], D("80"), D("100"))
    definir_meta(indicador_taxa, ciclo, D("0.98"))

    (linha,) = montar_painel(db_session, ciclo, semana=3)
    for r in linha.regionais:
        if r.meta is not None:
            assert r.meta == D("0.98")


def test_meta_propria_da_regional_prevalece_sobre_o_rateio(
    db_session, ciclo, regionais, indicador_acumula, lancar, definir_meta
):
    lancar(indicador_acumula, ciclo, 3, regionais["SP"], D("50"))
    lancar(indicador_acumula, ciclo, 3, regionais["RS"], D("50"))
    definir_meta(indicador_acumula, ciclo, D("200"))
    definir_meta(indicador_acumula, ciclo, D("40"), regional=regionais["RS"])

    (linha,) = montar_painel(db_session, ciclo, semana=3)
    por_codigo = {r.regional_codigo: r for r in linha.regionais}
    assert por_codigo["RS"].meta == D("40")
    assert round(float(por_codigo["RS"].atingimento_pct)) == 125
    # SP segue no rateio: 50% do realizado -> 100 de meta
    assert por_codigo["SP"].meta == D("100")


def test_regional_sem_lancamento_fica_sem_dado(
    db_session, ciclo, regionais, indicador_acumula, lancar, definir_meta
):
    lancar(indicador_acumula, ciclo, 3, regionais["SP"], D("100"))
    definir_meta(indicador_acumula, ciclo, D("200"))

    (linha,) = montar_painel(db_session, ciclo, semana=3)
    por_codigo = {r.regional_codigo: r for r in linha.regionais}
    assert por_codigo["RS"].valor is None
    assert por_codigo["RS"].semaforo is Semaforo.SEM_DADO


# --- serie semanal ----------------------------------------------------


def test_serie_traz_valor_da_semana_e_acumulado(
    db_session, ciclo, regionais, indicador_acumula, lancar, definir_meta
):
    for s, v in [(1, D("0.89")), (2, D("0.78")), (3, D("0.77"))]:
        lancar(indicador_acumula, ciclo, s, regionais["SP"], v)
    definir_meta(indicador_acumula, ciclo, D("3.70"))

    (linha,) = montar_painel(db_session, ciclo, semana=3)
    assert [p.semana for p in linha.serie] == [1, 2, 3]
    assert [p.valor for p in linha.serie] == [D("0.89"), D("0.78"), D("0.77")]
    assert [p.valor_acumulado for p in linha.serie] == [
        D("0.89"), D("1.67"), D("2.44"),
    ]


# --- projecao ---------------------------------------------------------


def test_projecao_extrapola_o_ritmo(
    db_session, ciclo, regionais, indicador_acumula, lancar, definir_meta
):
    """2,44 mi em 3 semanas projeta 3,25 mi no fechamento (88% da meta)."""
    for s, v in [(1, D("0.89")), (2, D("0.78")), (3, D("0.77"))]:
        lancar(indicador_acumula, ciclo, s, regionais["SP"], v)
    definir_meta(indicador_acumula, ciclo, D("3.70"))

    (linha,) = montar_painel(db_session, ciclo, semana=3)
    p = linha.projecao
    assert round(float(p.gap), 2) == 1.26
    assert round(float(p.atingimento_projetado_pct)) == 88
    assert p.semanas_restantes == 1
    assert round(float(p.esforco_vs_ritmo), 2) == 1.55


# --- pauta ------------------------------------------------------------


def _criar_indicador(db, codigo, tipo, direcao, ordem):
    ind = Indicador(
        codigo=codigo, nome=codigo.title(), area="COMERCIAL", unidade="NUM",
        tipo_acumulacao=tipo, melhor_direcao=direcao, ordem=ordem,
    )
    db.add(ind)
    db.commit()
    db.refresh(ind)
    return ind


def test_pauta_ordena_do_pior_desvio_para_o_melhor(
    db_session, ciclo, regionais, lancar, definir_meta
):
    bom = _criar_indicador(db_session, "BOM", TipoAcumulacao.ACUMULA, MelhorDirecao.MAIOR, 1)
    medio = _criar_indicador(db_session, "MEDIO", TipoAcumulacao.ACUMULA, MelhorDirecao.MAIOR, 2)
    ruim = _criar_indicador(db_session, "RUIM", TipoAcumulacao.ACUMULA, MelhorDirecao.MAIOR, 3)

    for ind, realizado in [(bom, D("80")), (medio, D("65")), (ruim, D("40"))]:
        lancar(ind, ciclo, 3, regionais["SP"], realizado)
        definir_meta(ind, ciclo, D("100"))

    painel = montar_painel(db_session, ciclo, semana=3)
    pauta = montar_pauta(painel)

    # BOM esta a 80% contra 75% esperado: no ritmo, fora da pauta.
    assert [i.linha.codigo for i in pauta] == ["RUIM", "MEDIO"]
    assert [i.posicao for i in pauta] == [1, 2]


def test_pauta_aponta_a_regional_mais_atrasada(
    db_session, ciclo, regionais, indicador_acumula, lancar, definir_meta
):
    lancar(indicador_acumula, ciclo, 3, regionais["SP"], D("60"))
    lancar(indicador_acumula, ciclo, 3, regionais["RS"], D("10"))
    definir_meta(indicador_acumula, ciclo, D("100"))
    definir_meta(indicador_acumula, ciclo, D("50"), regional=regionais["SP"])
    definir_meta(indicador_acumula, ciclo, D("50"), regional=regionais["RS"])

    painel = montar_painel(db_session, ciclo, semana=3)
    (item,) = montar_pauta(painel)
    assert item.regional_critica.regional_codigo == "RS"


def test_pauta_vazia_quando_tudo_no_ritmo(
    db_session, ciclo, regionais, indicador_acumula, lancar, definir_meta
):
    lancar(indicador_acumula, ciclo, 3, regionais["SP"], D("90"))
    definir_meta(indicador_acumula, ciclo, D("100"))
    painel = montar_painel(db_session, ciclo, semana=3)
    assert montar_pauta(painel) == []


# --- sintese por regional ---------------------------------------------


def test_resumo_regional_classifica_pelo_desvio_medio(
    db_session, ciclo, regionais, lancar, definir_meta
):
    """RS muito atras do ritmo sai CRITICO; SP no ritmo sai NO_RITMO.

    Regressao: a versao anterior contava vermelhos, e por isso
    classificava SP como critica quando havia problemas estruturais da
    empresa — todas as regionais acumulavam vermelhos herdados.
    """
    for i in range(3):
        ind = _criar_indicador(
            db_session, f"KPI{i}", TipoAcumulacao.ACUMULA, MelhorDirecao.MAIOR, i
        )
        lancar(ind, ciclo, 3, regionais["SP"], D("80"))
        lancar(ind, ciclo, 3, regionais["RS"], D("20"))
        definir_meta(ind, ciclo, D("200"))
        definir_meta(ind, ciclo, D("100"), regional=regionais["SP"])
        definir_meta(ind, ciclo, D("100"), regional=regionais["RS"])

    painel = montar_painel(db_session, ciclo, semana=3)
    resumos = {r.regional_codigo: r for r in resumir_regionais(painel)}

    assert resumos["RS"].status == "CRITICO"
    assert resumos["RS"].vermelhos == 3
    assert len(resumos["RS"].kpis_criticos) == 3
    assert resumos["SP"].status == "NO_RITMO"


def test_resumo_ordena_a_pior_regional_primeiro(
    db_session, ciclo, regionais, indicador_acumula, lancar, definir_meta
):
    lancar(indicador_acumula, ciclo, 3, regionais["SP"], D("90"))
    lancar(indicador_acumula, ciclo, 3, regionais["RJ"], D("70"))
    lancar(indicador_acumula, ciclo, 3, regionais["RS"], D("30"))
    definir_meta(indicador_acumula, ciclo, D("300"))
    for cod in ("SP", "RJ", "RS"):
        definir_meta(indicador_acumula, ciclo, D("100"), regional=regionais[cod])

    painel = montar_painel(db_session, ciclo, semana=3)
    ordem = [r.regional_codigo for r in resumir_regionais(painel)]
    assert ordem == ["RS", "RJ", "SP"]


def test_painel_vazio_nao_quebra_as_visoes_derivadas(db_session, ciclo):
    painel = montar_painel(db_session, ciclo, semana=1)
    assert painel == []
    assert montar_pauta(painel) == []
    assert resumir_regionais(painel) == []


# --- regra de rateio: aditivo vs razao --------------------------------


def test_estoque_sem_denominador_rateia_a_meta(
    db_session, ciclo, regionais, lancar, definir_meta
):
    """Regressao: base ativa comparada contra a meta consolidada dava 14%.

    Clientes ativos e um valor aditivo, ainda que o indicador seja TAXA
    para efeito de ritmo esperado. A meta consolidada precisa ser
    rateada, senao RS com 64 clientes e cobrada dos 448 da empresa.
    """
    ind = Indicador(
        codigo="BASE_ATIVA", nome="Base ativa", area="COMERCIAL",
        unidade="CLIENTES", tipo_acumulacao=TipoAcumulacao.TAXA,
        melhor_direcao=MelhorDirecao.MAIOR, ordem=1,
    )
    db_session.add(ind)
    db_session.commit()

    lancar(ind, ciclo, 3, regionais["SP"], D("220"))
    lancar(ind, ciclo, 3, regionais["RJ"], D("110"))
    lancar(ind, ciclo, 3, regionais["RS"], D("64"))
    definir_meta(ind, ciclo, D("448"))

    (linha,) = montar_painel(db_session, ciclo, semana=3)
    por_codigo = {r.regional_codigo: r for r in linha.regionais}

    # Cada regional cobrada da sua fatia, nao dos 448 da empresa.
    assert all(r.meta < D("448") for r in linha.regionais)
    assert sum(r.meta for r in linha.regionais) == D("448")
    # Sem meta propria o rateio segue o realizado, logo o atingimento
    # e o mesmo — o consolidado de 394 sobre 448.
    assert round(float(por_codigo["RS"].atingimento_pct)) == 88
    assert por_codigo["RS"].atingimento_pct > D("80")


def test_razao_com_denominador_nao_rateia_a_meta(
    db_session, ciclo, regionais, indicador_taxa, lancar, definir_meta
):
    """OTIF de 98% e exigido de cada regional, nao rateado entre elas."""
    lancar(indicador_taxa, ciclo, 3, regionais["SP"], D("706"), D("738"))
    lancar(indicador_taxa, ciclo, 3, regionais["RS"], D("163"), D("199"))
    definir_meta(indicador_taxa, ciclo, D("0.98"))

    (linha,) = montar_painel(db_session, ciclo, semana=3)
    com_meta = [r for r in linha.regionais if r.meta is not None]
    assert com_meta
    assert all(r.meta == D("0.98") for r in com_meta)


def test_problema_estrutural_nao_torna_toda_regional_critica(
    db_session, ciclo, regionais, lancar, definir_meta
):
    """Regressao: contar vermelhos classificava SP como critica.

    Cenario: 4 KPIs em que a empresa toda esta fora da meta (estoque,
    inadimplencia) mais 2 em que SP vai bem. Contando vermelhos, SP teria
    4 e seria "critica" igual a RS. Pelo desvio medio, SP fica no ritmo.
    """
    # KPIs estruturalmente ruins: todas as regionais longe da meta.
    for i in range(4):
        ind = _criar_indicador(
            db_session, f"ESTRUT{i}", TipoAcumulacao.TAXA, MelhorDirecao.MAIOR, i
        )
        for cod, valor in (("SP", D("70")), ("RJ", D("60")), ("RS", D("40"))):
            lancar(ind, ciclo, 3, regionais[cod], valor, D("100"))
        definir_meta(ind, ciclo, D("0.95"))

    # KPIs em que SP vai muito bem e RS muito mal.
    for i in range(2):
        ind = _criar_indicador(
            db_session, f"BOM{i}", TipoAcumulacao.ACUMULA, MelhorDirecao.MAIOR, 10 + i
        )
        lancar(ind, ciclo, 3, regionais["SP"], D("110"))
        lancar(ind, ciclo, 3, regionais["RJ"], D("80"))
        lancar(ind, ciclo, 3, regionais["RS"], D("30"))
        definir_meta(ind, ciclo, D("300"))
        for cod in ("SP", "RJ", "RS"):
            definir_meta(ind, ciclo, D("100"), regional=regionais[cod])

    resumos = {r.regional_codigo: r for r in resumir_regionais(
        montar_painel(db_session, ciclo, semana=3)
    )}

    # Todas herdam vermelhos dos KPIs estruturais...
    assert resumos["SP"].vermelhos >= 4
    # ...mas a classificacao separa desempenho de problema herdado.
    assert resumos["RS"].status == "CRITICO"
    assert resumos["SP"].status != "CRITICO"
    assert resumos["SP"].desvio_medio_pp > resumos["RS"].desvio_medio_pp
