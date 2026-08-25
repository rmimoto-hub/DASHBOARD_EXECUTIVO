"""Hash de senha e tokens JWT."""
import base64
import json
from datetime import UTC, datetime, timedelta

import pytest
import jwt

from app.core.config import get_settings
from app.core.security import (
    LIMITE_BYTES_SENHA,
    criar_access_token,
    decodificar_token,
    hash_senha,
    verificar_senha,
)

settings = get_settings()


def test_hash_confere_com_a_senha_correta():
    h = hash_senha("MinhaSenha@2026")
    assert verificar_senha("MinhaSenha@2026", h)


def test_hash_recusa_senha_errada():
    h = hash_senha("MinhaSenha@2026")
    assert not verificar_senha("OutraSenha@2026", h)


def test_hash_nao_guarda_a_senha_em_claro():
    h = hash_senha("MinhaSenha@2026")
    assert "MinhaSenha@2026" not in h
    assert h.startswith("$2b$")


def test_dois_hashes_da_mesma_senha_sao_diferentes():
    """Sal aleatorio: hashes iguais delatariam senhas iguais entre usuarios."""
    assert hash_senha("igual") != hash_senha("igual")


def test_hash_malformado_nao_explode():
    """Hash corrompido no banco e falha de autenticacao, nao erro 500."""
    assert not verificar_senha("qualquer", "isto-nao-e-um-hash-bcrypt")


def test_senha_acima_do_limite_do_bcrypt_e_recusada():
    """O bcrypt trunca em 72 bytes; aceitar em silencio validaria so o inicio."""
    with pytest.raises(ValueError, match="72 bytes"):
        hash_senha("a" * (LIMITE_BYTES_SENHA + 1))


def test_limite_e_medido_em_bytes_nao_em_caracteres():
    """Acentos ocupam 2 bytes em UTF-8 — 40 'ç' passam de 72 bytes."""
    with pytest.raises(ValueError):
        hash_senha("ç" * 40)


def test_senha_no_limite_exato_e_aceita():
    h = hash_senha("a" * LIMITE_BYTES_SENHA)
    assert verificar_senha("a" * LIMITE_BYTES_SENHA, h)


def test_token_carrega_assunto_e_perfil():
    t = criar_access_token("alguem@teste.br", "ADMIN")
    payload = decodificar_token(t)
    assert payload["sub"] == "alguem@teste.br"
    assert payload["perfil"] == "ADMIN"


def test_token_com_lixo_devolve_none():
    assert decodificar_token("abc.def.ghi") is None
    assert decodificar_token("") is None


def test_token_assinado_com_outra_chave_devolve_none():
    outra_chave = "chave-do-atacante-com-mais-de-32-bytes-de-tamanho"
    falso = jwt.encode({"sub": "x"}, outra_chave, algorithm="HS256")
    assert decodificar_token(falso) is None


def test_token_expirado_devolve_none():
    expirado = jwt.encode(
        {
            "sub": "alguem@teste.br",
            "exp": datetime.now(UTC) - timedelta(minutes=1),
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    assert decodificar_token(expirado) is None


def test_token_com_algoritmo_none_e_recusado():
    """Ataque classico: alg=none passaria se o decode nao fixasse o algoritmo.

    Montado a mao porque a propria biblioteca se recusa a assinar com
    "none" — um atacante nao tem essa limitacao.
    """
    def b64(dados: dict) -> str:
        bruto = json.dumps(dados, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(bruto).rstrip(b"=").decode()

    sem_assinatura = (
        f"{b64({'alg': 'none', 'typ': 'JWT'})}."
        f"{b64({'sub': 'admin@teste.br', 'perfil': 'ADMIN'})}."
    )
    assert decodificar_token(sem_assinatura) is None


def test_chave_curta_impede_a_aplicacao_de_subir():
    """SECRET_KEY fraca falha no boot, nao silenciosamente em producao."""
    import pytest as _pytest
    from pydantic import ValidationError

    from app.core.config import Settings

    with _pytest.raises(ValidationError, match="RFC 7518"):
        Settings(
            DATABASE_URL="sqlite://",
            SECRET_KEY="curta",  # security-check: ok — valor de teste, 5 bytes
        )


def test_chave_no_minimo_exato_e_aceita():
    from app.core.config import MIN_BYTES_SECRET_KEY, Settings

    s = Settings(
        DATABASE_URL="sqlite://",
        SECRET_KEY="a" * MIN_BYTES_SECRET_KEY,  # security-check: ok
    )
    assert len(s.SECRET_KEY) == MIN_BYTES_SECRET_KEY
