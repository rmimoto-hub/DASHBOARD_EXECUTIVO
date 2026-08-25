"""Schemas (contratos de API) de usuario e autenticacao."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.usuario import Perfil


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: EmailStr
    perfil: Perfil
    ativo: bool
    ultimo_acesso: datetime | None


class UsuarioCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    email: EmailStr
    senha: str = Field(min_length=8, max_length=128)
    perfil: Perfil = Perfil.USER
