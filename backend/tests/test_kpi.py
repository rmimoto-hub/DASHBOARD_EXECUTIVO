"""Motor de KPI: ritmo esperado, consolidacao, atingimento e semaforo."""
from decimal import Decimal as D

import pytest

from app.models.cadastro import MelhorDirecao, TipoAcumulacao
from app.services.kpi import (
    TOLERANCIA_AMBAR_PP,
    Semaforo,
    ValorMedido,
    acumular,
    atingimento,
    consolidar,
    desvio_do_ritmo,
    esperado_na_semana,
    semaforo,
)

ACUMULA = TipoAcumulacao.ACUMULA
TAXA = TipoAcumulacao.TAXA
MAIOR = MelhorDirecao.MAIOR
MENOR = MelhorDirecao.MENOR


# --- ritmo esperado na semana -----------------------------------------


@pytest.mark.parametrize(
    ("semana", "total", "esperado"),
    [(1, 4, 25), (2, 4, 50), (3, 4, 75), (4, 4, 100), (3, 5, 60), (1, 1, 100)],
)
def test_acumula_cresce_proporcional_a_semana(semana, total, esperado):
    assert esperado_na_semana(ACUMULA, semana, total) == D(esperado)


@pytest.mark.parametrize(("semana", "total"), [(1, 4), (2, 4), (3, 4), (4, 4)])
def test_taxa_exige_cem_por_cento_em_qualquer_semana(semana, total):
    assert esperado_na_semana(TAXA, semana, total) == D(100)


def test_semana_fora_do_ciclo_e_erro():
    with pytest.raises(ValueError, match="fora do ciclo"):
        esperado_na_semana(ACUMULA, 5, 4)
    with pytest.raises(ValueError, match="fora do ciclo"):
        esperado_na_semana(ACUMULA, 0, 4)


def test_ciclo_sem_semanas_e_erro():
    with pytest.raises(ValueError, match="positivo"):
        esperado_na_semana(ACUMULA, 1, 0)


# --- consolidacao entre regionais -------------------------------------


def test_consolidar_valores_soma():
    r = consolidar([ValorMedido(D("0.89")), ValorMedido(D("0.78")), ValorMedido(D("0.77"))])
    assert r.valor == D("2.44")


def test_consolidar_taxa_pondera_pelo_denominador():
    """Regressao: o OTIF do comite.

    SP 95,7% / RJ 91,1% / RS 81,9% consolidam em 92,3% ponderado pelo
    volume. A media simples daria 89,5% — 2,8 p.p. de erro.
    """
    otif = consolidar([
        ValorMedido(D("706"), D("738")),  # SP
        ValorMedido(D("316"), D("347")),  # RJ
        ValorMedido(D("163"), D("199")),  # RS
    ])
    assert round(float(otif.valor) * 100, 1) == 92.3

    media_simples = (95.7 + 91.1 + 81.9) / 3
    assert round(media_simples, 1) == 89.6  # o resultado errado
    assert abs(float(otif.valor) * 100 - media_simples) > 2.5


def test_consolidar_serie_vazia_e_none():
    assert consolidar([]) is None


def test_consolidar_mistura_taxa_e_valor_e_erro():
    """Somar um valor absoluto com uma taxa nao significa nada."""
    with pytest.raises(ValueError, match="todo taxa ou todo valor"):
        consolidar([ValorMedido(D("10")), ValorMedido(D("5"), D("20"))])


# --- acumulacao ao longo do mes ---------------------------------------


def test_acumula_soma_as_semanas():
    semanas = [ValorMedido(D("0.89")), ValorMedido(D("0.78")), ValorMedido(D("0.77"))]
    assert acumular(semanas, ACUMULA).valor == D("2.44")


def test_taxa_toma_a_semana_mais_recente():
    """Somar percentuais de semanas nao significa nada."""
    semanas = [ValorMedido(D("74"), D("1000")), ValorMedido(D("68"), D("1000"))]
    r = acumular(semanas, TAXA)
    assert r.numerador == D("68")


def test_acumular_serie_vazia_e_none():
    assert acumular([], ACUMULA) is None


# --- atingimento ------------------------------------------------------


def test_atingimento_quando_maior_e_melhor():
    assert float(atingimento(D("2.44"), D("3.70"), MAIOR)) == pytest.approx(65.9, abs=0.1)


def test_atingimento_quando_menor_e_melhor_e_invertido():
    """Inadimplencia de 6,8% contra meta de 4,0% da 59%, nao 170%."""
    assert float(atingimento(D("6.8"), D("4.0"), MENOR)) == pytest.approx(58.8, abs=0.1)


def test_atingimento_sem_meta_ou_sem_realizado():
    assert atingimento(None, D("10"), MAIOR) is None
    assert atingimento(D("10"), None, MAIOR) is None
    assert atingimento(D("10"), D("0"), MAIOR) is None


def test_indicador_menor_e_melhor_zerado_nao_divide_por_zero():
    """Zerar inadimplencia e o melhor caso possivel, nao um erro."""
    assert atingimento(D("0"), D("4"), MENOR) == D("200")


@pytest.mark.parametrize("direcao", [MAIOR, MENOR])
def test_acima_de_cem_significa_sempre_bom(direcao):
    meta = D("100")
    bom = D("120") if direcao is MAIOR else D("80")
    ruim = D("80") if direcao is MAIOR else D("120")
    assert atingimento(bom, meta, direcao) > 100
    assert atingimento(ruim, meta, direcao) < 100


# --- semaforo ---------------------------------------------------------


def test_no_ritmo_e_verde():
    assert semaforo(D("75"), D("75")) is Semaforo.VERDE
    assert semaforo(D("80"), D("75")) is Semaforo.VERDE


def test_ate_a_tolerancia_abaixo_e_ambar():
    assert semaforo(D("66"), D("75")) is Semaforo.AMBAR   # -9 pp
    assert semaforo(D("65"), D("75")) is Semaforo.AMBAR   # -10 pp, no limite


def test_alem_da_tolerancia_e_vermelho():
    assert semaforo(D("64.9"), D("75")) is Semaforo.VERMELHO


def test_sem_atingimento_e_sem_dado():
    assert semaforo(None, D("75")) is Semaforo.SEM_DADO


def test_tolerancia_e_parametrizavel():
    """E politica do comite, nao lei da natureza."""
    assert semaforo(D("60"), D("75"), tolerancia_pp=D("20")) is Semaforo.AMBAR
    assert semaforo(D("70"), D("75"), tolerancia_pp=D("2")) is Semaforo.VERMELHO


def test_tolerancia_padrao_e_dez_pontos():
    assert TOLERANCIA_AMBAR_PP == D("10")


# --- desvio do ritmo --------------------------------------------------


def test_desvio_negativo_indica_atraso():
    assert desvio_do_ritmo(D("66"), D("75")) == D("-9")


def test_desvio_ordena_a_pauta_do_pior_para_o_melhor():
    kpis = {"faturamento": D("66"), "recuperacao": D("46"), "positivacao": D("76")}
    esperados = {"faturamento": D("75"), "recuperacao": D("75"), "positivacao": D("75")}
    ordem = sorted(kpis, key=lambda k: desvio_do_ritmo(kpis[k], esperados[k]))
    assert ordem == ["recuperacao", "faturamento", "positivacao"]


def test_desvio_sem_dado_e_none():
    assert desvio_do_ritmo(None, D("75")) is None


# --- regressao contra o deck do comite --------------------------------

PAINEL_SEMANA_3 = [
    ("FATURAMENTO",   D("2.44"), D("3.70"), ACUMULA, MAIOR, 66,  Semaforo.AMBAR),
    ("MARGEM",        D("34.2"), D("34.0"), TAXA,    MAIOR, 101, Semaforo.VERDE),
    ("BASE_ATIVA",    D("394"),  D("448"),  TAXA,    MAIOR, 88,  Semaforo.VERMELHO),
    ("POSITIVACAO",   D("230"),  D("303"),  ACUMULA, MAIOR, 76,  Semaforo.VERDE),
    ("CONVERSAO",     D("23"),   D("27"),   ACUMULA, MAIOR, 85,  Semaforo.VERDE),
    ("OTIF",          D("92.3"), D("98.0"), TAXA,    MAIOR, 94,  Semaforo.AMBAR),
    ("TEMPO_ENTREGA", D("2.3"),  D("1.9"),  TAXA,    MENOR, 83,  Semaforo.VERMELHO),
    ("COBERTURA",     D("68"),   D("45"),   TAXA,    MENOR, 66,  Semaforo.VERMELHO),
    ("OBSOLESCENCIA", D("32"),   D("15"),   TAXA,    MENOR, 47,  Semaforo.VERMELHO),
    ("INADIMPLENCIA", D("6.8"),  D("4.0"),  TAXA,    MENOR, 59,  Semaforo.VERMELHO),
    ("RECUPERACAO",   D("506"),  D("1100"), ACUMULA, MAIOR, 46,  Semaforo.VERMELHO),
    ("LEADS_QUALIF",  D("107"),  D("132"),  ACUMULA, MAIOR, 81,  Semaforo.VERDE),
    ("CUSTO_LEAD",    D("293"),  D("240"),  TAXA,    MENOR, 82,  Semaforo.VERMELHO),
]


@pytest.mark.parametrize(
    ("codigo", "realizado", "meta", "tipo", "direcao", "ating_deck", "sem_deck"),
    PAINEL_SEMANA_3,
    ids=[k[0] for k in PAINEL_SEMANA_3],
)
def test_reproduz_o_painel_do_comite(
    codigo, realizado, meta, tipo, direcao, ating_deck, sem_deck
):
    """Cada KPI do painel geral, semana 3 de 4, contra o deck original."""
    a = atingimento(realizado, meta, direcao)
    e = esperado_na_semana(tipo, 3, 4)
    assert round(float(a)) == ating_deck
    assert semaforo(a, e) is sem_deck
