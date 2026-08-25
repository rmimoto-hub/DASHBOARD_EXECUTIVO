"""Cada perfil so alcanca o que lhe cabe."""
import pytest

CRIAR_INDICADOR = {"codigo": "NOVO", "nome": "Indicador novo"}


@pytest.mark.parametrize(
    ("papel", "esperado"),
    [("admin", 201), ("user", 403), ("leitor", 403)],
)
def test_criar_indicador_e_exclusivo_do_admin(cliente, auth, papel, esperado):
    r = cliente.post("/indicadores", json=CRIAR_INDICADOR, headers=auth(papel))
    assert r.status_code == esperado


@pytest.mark.parametrize(
    ("papel", "esperado"),
    [("admin", 201), ("user", 201), ("leitor", 403)],
)
def test_registrar_medicao_exige_perfil_de_escrita(
    cliente, auth, indicador_maior, papel, esperado
):
    r = cliente.post(
        "/indicadores/medicoes",
        json={
            "indicador_id": indicador_maior.id,
            # Competencia livre por perfil para nao colidir entre os casos.
            "competencia": f"2025-0{1 if papel == 'admin' else 2}-01",
            "valor": 500,
        },
        headers=auth(papel),
    )
    assert r.status_code == esperado


@pytest.mark.parametrize("papel", ["admin", "user", "leitor"])
def test_leitura_liberada_para_todos_os_perfis(cliente, auth, papel):
    assert cliente.get("/indicadores", headers=auth(papel)).status_code == 200
    assert (
        cliente.get("/indicadores/resumo", headers=auth(papel)).status_code == 200
    )


def test_codigo_de_indicador_e_unico(cliente, auth):
    primeiro = cliente.post(
        "/indicadores", json=CRIAR_INDICADOR, headers=auth("admin")
    )
    assert primeiro.status_code == 201
    repetido = cliente.post(
        "/indicadores", json=CRIAR_INDICADOR, headers=auth("admin")
    )
    assert repetido.status_code == 409


def test_medicao_duplicada_na_mesma_competencia_e_recusada(
    cliente, auth, indicador_maior
):
    corpo = {
        "indicador_id": indicador_maior.id,
        "competencia": "2025-05-01",
        "valor": 10,
    }
    assert cliente.post(
        "/indicadores/medicoes", json=corpo, headers=auth("admin")
    ).status_code == 201
    assert cliente.post(
        "/indicadores/medicoes", json=corpo, headers=auth("admin")
    ).status_code == 409


def test_competencia_e_normalizada_para_o_dia_primeiro(
    cliente, auth, indicador_maior
):
    r = cliente.post(
        "/indicadores/medicoes",
        json={
            "indicador_id": indicador_maior.id,
            "competencia": "2025-09-17",
            "valor": 10,
        },
        headers=auth("admin"),
    )
    assert r.status_code == 201
    assert r.json()["competencia"] == "2025-09-01"


def test_medicao_em_indicador_inexistente_da_404(cliente, auth):
    r = cliente.post(
        "/indicadores/medicoes",
        json={"indicador_id": 9999, "competencia": "2026-01-01", "valor": 1},
        headers=auth("admin"),
    )
    assert r.status_code == 404


def test_listar_medicoes_de_indicador_inexistente_da_404(cliente, auth):
    r = cliente.get("/indicadores/9999/medicoes", headers=auth("admin"))
    assert r.status_code == 404
