"""Rotas de autenticacao."""
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import usuario_atual
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import criar_access_token, verificar_senha
from app.models.auditoria import LogAuditoria
from app.models.usuario import Usuario
from app.schemas.usuario import LoginRequest, TokenResponse, UsuarioOut

router = APIRouter(prefix="/auth", tags=["autenticacao"])
settings = get_settings()


@router.post("/login", response_model=TokenResponse)
def login(
    dados: LoginRequest, request: Request, db: Session = Depends(get_db)
) -> TokenResponse:
    usuario = db.query(Usuario).filter(Usuario.email == dados.email).first()

    # Mensagem generica de proposito: nao revela se o e-mail existe.
    if usuario is None or not verificar_senha(dados.senha, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
        )

    if not usuario.ativo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inativo"
        )

    usuario.ultimo_acesso = datetime.now(UTC).replace(tzinfo=None)
    db.add(
        LogAuditoria(
            usuario_id=usuario.id,
            acao="LOGIN",
            entidade="usuarios",
            entidade_id=usuario.id,
            ip=request.client.host if request.client else None,
        )
    )
    db.commit()

    return TokenResponse(
        access_token=criar_access_token(usuario.email, usuario.perfil.value),
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )


@router.get("/eu", response_model=UsuarioOut)
def eu(usuario: Usuario = Depends(usuario_atual)) -> Usuario:
    """Dados do usuario logado — usado pelo frontend para validar a sessao."""
    return usuario
