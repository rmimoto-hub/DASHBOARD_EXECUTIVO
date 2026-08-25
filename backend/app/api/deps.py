"""Dependencias compartilhadas: usuario autenticado e checagem de perfil."""
from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decodificar_token
from app.models.usuario import Perfil, Usuario

bearer = HTTPBearer(auto_error=False)

CREDENCIAIS_INVALIDAS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Credenciais invalidas ou expiradas",
    headers={"WWW-Authenticate": "Bearer"},
)


def usuario_atual(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    if cred is None:
        raise CREDENCIAIS_INVALIDAS

    payload = decodificar_token(cred.credentials)
    if payload is None:
        raise CREDENCIAIS_INVALIDAS

    email = payload.get("sub")
    if not email:
        raise CREDENCIAIS_INVALIDAS

    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if usuario is None or not usuario.ativo:
        raise CREDENCIAIS_INVALIDAS

    return usuario


def exige_perfil(*perfis: Perfil) -> Callable[[Usuario], Usuario]:
    """Fabrica de dependencia que restringe a rota aos perfis informados."""

    def _verificar(usuario: Usuario = Depends(usuario_atual)) -> Usuario:
        if usuario.perfil not in perfis:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seu perfil nao tem permissao para esta operacao",
            )
        return usuario

    return _verificar


# Atalhos de uso comum
exige_admin = exige_perfil(Perfil.ADMIN)
exige_escrita = exige_perfil(Perfil.ADMIN, Perfil.USER)
