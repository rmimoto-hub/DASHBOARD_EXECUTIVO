"""Hash de senha (bcrypt) e emissao/validacao de tokens JWT."""
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()

# bcrypt trunca a entrada em 72 bytes; validamos antes para nao aceitar
# silenciosamente uma senha maior do que o que sera realmente verificado.
LIMITE_BYTES_SENHA = 72


def hash_senha(senha: str) -> str:
    senha_bytes = senha.encode("utf-8")
    if len(senha_bytes) > LIMITE_BYTES_SENHA:
        raise ValueError(
            f"Senha excede o limite de {LIMITE_BYTES_SENHA} bytes suportado "
            "pelo bcrypt"
        )
    return bcrypt.hashpw(senha_bytes, bcrypt.gensalt()).decode("utf-8")


def verificar_senha(senha_plana: str, senha_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            senha_plana.encode("utf-8"), senha_hash.encode("utf-8")
        )
    except ValueError:
        # Hash malformado no banco — trata como falha de autenticacao.
        return False


def criar_access_token(subject: str, perfil: str) -> str:
    expira = datetime.now(UTC) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "perfil": perfil,
        "exp": expira,
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decodificar_token(token: str) -> dict[str, Any] | None:
    """Devolve o payload, ou None se o token for invalido/expirado."""
    try:
        return jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
    except JWTError:
        return None
