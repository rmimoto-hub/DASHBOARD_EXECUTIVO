"""Fixtures dos testes.

Roda contra SQLite em memoria: os testes nao dependem de um MySQL de pe e
nao tocam o banco de desenvolvimento.
"""
import os
from datetime import date

# Definido antes de importar a app: Settings le o ambiente na importacao.
os.environ.setdefault("DATABASE_URL", "sqlite://")
# Chave ficticia, so para os testes assinarem e validarem tokens entre si.
os.environ.setdefault(
    "SECRET_KEY",
    "chave-de-teste-longa-o-suficiente-para-hs256",  # security-check: ok
)
os.environ.setdefault("ENVIRONMENT", "development")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.database import Base, get_db  # noqa: E402
from app.core.security import hash_senha  # noqa: E402
from app.main import app  # noqa: E402
from app.models.indicador import Indicador, Medicao, MelhorDirecao  # noqa: E402
from app.models.usuario import Perfil, Usuario  # noqa: E402

# Senha das fixtures. Existe apenas em SQLite em memoria, destruido ao
# fim de cada teste — nao da acesso a nenhum ambiente real.
SENHA = "SenhaDeTeste@2026"  # security-check: ok


@pytest.fixture
def db_session():
    # StaticPool + check_same_thread=False: uma unica conexao compartilhada,
    # senao cada sessao veria um banco em memoria diferente.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    sessao = Session()
    try:
        yield sessao
    finally:
        sessao.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def cliente(db_session):
    """TestClient com o banco de teste injetado."""

    def _get_db():
        yield db_session

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def usuarios(db_session):
    """Um usuario de cada perfil, mais um inativo."""
    senha_hash = hash_senha(SENHA)
    registros = {
        "admin": Usuario(
            nome="Admin", email="admin@teste.br",
            senha_hash=senha_hash, perfil=Perfil.ADMIN,
        ),
        "user": Usuario(
            nome="User", email="user@teste.br",
            senha_hash=senha_hash, perfil=Perfil.USER,
        ),
        "leitor": Usuario(
            nome="Leitor", email="leitor@teste.br",
            senha_hash=senha_hash, perfil=Perfil.READ_ONLY,
        ),
        "inativo": Usuario(
            nome="Inativo", email="inativo@teste.br",
            senha_hash=senha_hash, perfil=Perfil.USER, ativo=False,
        ),
    }
    db_session.add_all(registros.values())
    db_session.commit()
    for u in registros.values():
        db_session.refresh(u)
    return registros


@pytest.fixture
def token(cliente, usuarios):
    """Fabrica de token: token('admin') -> str."""

    def _token(papel: str) -> str:
        resposta = cliente.post(
            "/auth/login",
            json={"email": usuarios[papel].email, "senha": SENHA},
        )
        assert resposta.status_code == 200, resposta.text
        return resposta.json()["access_token"]

    return _token


@pytest.fixture
def auth(token):
    """Cabecalho de autorizacao: auth('admin') -> dict."""

    def _auth(papel: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token(papel)}"}

    return _auth


@pytest.fixture
def indicador_maior(db_session):
    """Indicador em que maior e melhor, com duas medicoes."""
    ind = Indicador(
        codigo="FAT", nome="Faturamento", unidade="BRL",
        area="COMERCIAL", melhor_direcao=MelhorDirecao.MAIOR,
    )
    db_session.add(ind)
    db_session.flush()
    db_session.add_all([
        Medicao(indicador_id=ind.id, competencia=date(2026, 6, 1),
                valor=1000, meta=1200),
        Medicao(indicador_id=ind.id, competencia=date(2026, 7, 1),
                valor=1100, meta=1200),
    ])
    db_session.commit()
    db_session.refresh(ind)
    return ind


@pytest.fixture
def indicador_menor(db_session):
    """Indicador em que menor e melhor, estourando a meta."""
    ind = Indicador(
        codigo="INAD", nome="Inadimplencia", unidade="PCT",
        area="FINANCEIRO", melhor_direcao=MelhorDirecao.MENOR,
    )
    db_session.add(ind)
    db_session.flush()
    db_session.add_all([
        Medicao(indicador_id=ind.id, competencia=date(2026, 6, 1),
                valor=5, meta=3),
        Medicao(indicador_id=ind.id, competencia=date(2026, 7, 1),
                valor=4, meta=3),
    ])
    db_session.commit()
    db_session.refresh(ind)
    return ind
