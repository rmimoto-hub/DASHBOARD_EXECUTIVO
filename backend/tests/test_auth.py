"""Testes de autenticacao e de controle por perfil."""


def test_login_com_credenciais_validas(cliente, usuarios):
    r = cliente.post(
        "/auth/login",
        json={"email": "admin@teste.br", "senha": "SenhaDeTeste@2026"},
    )
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["token_type"] == "bearer"
    assert corpo["access_token"]
    assert corpo["expires_in_minutes"] > 0


def test_login_com_senha_errada(cliente, usuarios):
    r = cliente.post(
        "/auth/login", json={"email": "admin@teste.br", "senha": "errada"}
    )
    assert r.status_code == 401


def test_login_de_email_inexistente_nao_revela_a_diferenca(cliente, usuarios):
    """A mensagem deve ser identica a de senha errada — nao enumerar contas."""
    inexistente = cliente.post(
        "/auth/login", json={"email": "ninguem@teste.br", "senha": "x"}
    )
    senha_errada = cliente.post(
        "/auth/login", json={"email": "admin@teste.br", "senha": "x"}
    )
    assert inexistente.status_code == senha_errada.status_code == 401
    assert inexistente.json()["detail"] == senha_errada.json()["detail"]


def test_usuario_inativo_nao_entra(cliente, usuarios):
    r = cliente.post(
        "/auth/login",
        json={"email": "inativo@teste.br", "senha": "SenhaDeTeste@2026"},
    )
    assert r.status_code == 403


def test_login_registra_ultimo_acesso(cliente, usuarios, db_session):
    assert usuarios["admin"].ultimo_acesso is None
    cliente.post(
        "/auth/login",
        json={"email": "admin@teste.br", "senha": "SenhaDeTeste@2026"},
    )
    db_session.refresh(usuarios["admin"])
    assert usuarios["admin"].ultimo_acesso is not None


def test_eu_devolve_o_usuario_logado(cliente, auth):
    r = cliente.get("/auth/eu", headers=auth("leitor"))
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["email"] == "leitor@teste.br"
    assert corpo["perfil"] == "READ_ONLY"
    # A resposta nao deve carregar o hash da senha.
    assert "senha_hash" not in corpo


def test_sem_token_nao_acessa(cliente, usuarios):
    assert cliente.get("/auth/eu").status_code == 401


def test_token_malformado_nao_acessa(cliente, usuarios):
    r = cliente.get("/auth/eu", headers={"Authorization": "Bearer abc.def.ghi"})
    assert r.status_code == 401


def test_token_assinado_com_outra_chave_nao_acessa(cliente, usuarios):
    """Token valido na forma, mas com assinatura de outra chave."""
    import jwt

    falso = jwt.encode(
        {"sub": "admin@teste.br", "perfil": "ADMIN"},
        "chave-do-atacante-que-nao-e-a-nossa",
        algorithm="HS256",
    )
    r = cliente.get("/auth/eu", headers={"Authorization": f"Bearer {falso}"})
    assert r.status_code == 401


def test_token_de_usuario_desativado_depois_do_login(
    cliente, usuarios, auth, db_session
):
    """Desativar o usuario invalida o token que ele ja tinha."""
    cabecalho = auth("user")
    assert cliente.get("/auth/eu", headers=cabecalho).status_code == 200

    usuarios["user"].ativo = False
    db_session.commit()

    assert cliente.get("/auth/eu", headers=cabecalho).status_code == 401
