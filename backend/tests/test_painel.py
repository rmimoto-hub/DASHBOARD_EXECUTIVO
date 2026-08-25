"""Calculos do resumo do painel: variacao e atingimento de meta."""
from datetime import date
from decimal import Decimal

import pytest

from app.models.indicador import Indicador, Medicao, MelhorDirecao
from app.services.painel import _atingimento_pct, _variacao_pct, montar_resumo

# --- variacao ---------------------------------------------------------


def test_variacao_positiva():
    assert _variacao_pct(Decimal("110"), Decimal("100")) == pytest.approx(10)


def test_variacao_negativa():
    assert _variacao_pct(Decimal("90"), Decimal("100")) == pytest.approx(-10)


def test_variacao_sem_mudanca():
    assert _variacao_pct(Decimal("100"), Decimal("100")) == 0


def test_variacao_com_base_zero_e_indefinida():
    """Dividir por zero nao produz "infinito por cento" na tela."""
    assert _variacao_pct(Decimal("50"), Decimal("0")) is None


def test_variacao_a_partir_de_base_negativa_usa_modulo():
    """Prejuizo de -100 para -50 e melhora de 50%, nao de -50%."""
    assert _variacao_pct(Decimal("-50"), Decimal("-100")) == pytest.approx(50)


# --- atingimento ------------------------------------------------------


def test_atingimento_quando_maior_e_melhor():
    r = _atingimento_pct(Decimal("110"), Decimal("100"), MelhorDirecao.MAIOR)
    assert r == pytest.approx(110)


def test_atingimento_quando_menor_e_melhor_e_invertido():
    """Regressao: inadimplencia de 4 contra meta 3 nao pode dar 133%.

    Pela razao direta daria 133% — numero alto que se le como bom
    desempenho, quando a meta foi estourada. Invertido, da 75%.
    """
    r = _atingimento_pct(Decimal("4"), Decimal("3"), MelhorDirecao.MENOR)
    assert r == pytest.approx(75)


def test_atingimento_menor_e_melhor_dentro_da_meta_passa_de_100():
    r = _atingimento_pct(Decimal("3"), Decimal("4"), MelhorDirecao.MENOR)
    assert r == pytest.approx(133.33, abs=0.01)


@pytest.mark.parametrize("direcao", [MelhorDirecao.MAIOR, MelhorDirecao.MENOR])
def test_acima_de_cem_por_cento_significa_sempre_bom(direcao):
    """A leitura ">100% e bom" vale para as duas direcoes."""
    if direcao is MelhorDirecao.MAIOR:
        bom, ruim = Decimal("120"), Decimal("80")
    else:
        bom, ruim = Decimal("80"), Decimal("120")
    meta = Decimal("100")
    assert _atingimento_pct(bom, meta, direcao) > 100
    assert _atingimento_pct(ruim, meta, direcao) < 100


def test_atingimento_sem_meta_e_indefinido():
    assert _atingimento_pct(Decimal("10"), None, MelhorDirecao.MAIOR) is None


def test_atingimento_com_meta_zero_e_indefinido():
    assert (
        _atingimento_pct(Decimal("10"), Decimal("0"), MelhorDirecao.MAIOR) is None
    )


def test_atingimento_com_valor_zero_e_indefinido():
    """Valor zero seria divisao por zero no caso MENOR."""
    assert (
        _atingimento_pct(Decimal("0"), Decimal("5"), MelhorDirecao.MENOR) is None
    )


# --- montar_resumo ----------------------------------------------------


def test_resumo_usa_a_medicao_mais_recente(db_session, indicador_maior):
    (linha,) = montar_resumo(db_session)
    assert linha.competencia == date(2026, 7, 1)
    assert linha.valor == Decimal("1100.0000")
    assert linha.valor_anterior == Decimal("1000.0000")
    assert linha.variacao_pct == pytest.approx(10)


def test_resumo_de_indicador_sem_medicao(db_session):
    db_session.add(Indicador(codigo="VAZIO", nome="Sem dados"))
    db_session.commit()

    (linha,) = montar_resumo(db_session)
    assert linha.competencia is None
    assert linha.valor is None
    assert linha.variacao_pct is None
    assert linha.atingimento_pct is None


def test_resumo_com_uma_unica_medicao_nao_tem_variacao(db_session):
    ind = Indicador(codigo="UNICA", nome="Uma medicao")
    db_session.add(ind)
    db_session.flush()
    db_session.add(
        Medicao(indicador_id=ind.id, competencia=date(2026, 7, 1), valor=10)
    )
    db_session.commit()

    (linha,) = montar_resumo(db_session)
    assert linha.valor == Decimal("10.0000")
    assert linha.valor_anterior is None
    assert linha.variacao_pct is None


def test_resumo_ignora_indicador_inativo(db_session, indicador_maior):
    db_session.add(Indicador(codigo="OFF", nome="Desativado", ativo=False))
    db_session.commit()

    codigos = {linha.codigo for linha in montar_resumo(db_session)}
    assert codigos == {"FAT"}


def test_resumo_filtra_por_area(db_session, indicador_maior, indicador_menor):
    todas = montar_resumo(db_session)
    assert len(todas) == 2

    financeiro = montar_resumo(db_session, area="FINANCEIRO")
    assert [linha.codigo for linha in financeiro] == ["INAD"]


def test_resumo_sem_indicador_devolve_lista_vazia(db_session):
    assert montar_resumo(db_session) == []
