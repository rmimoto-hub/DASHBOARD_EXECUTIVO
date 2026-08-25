"""Configuracao central, lida do ambiente (.env)."""
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# RFC 7518 secao 3.2: a chave HMAC deve ter ao menos o tamanho da saida do
# hash — 32 bytes para SHA-256. Abaixo disso o PyJWT so emite aviso; aqui a
# aplicacao se recusa a subir, para nao rodar com chave fraca em producao.
MIN_BYTES_SECRET_KEY = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    CORS_ORIGINS: str = "http://localhost:3000"
    ENVIRONMENT: str = "development"

    ALGORITHM: str = "HS256"

    # Senha dos usuarios criados por "make seed-fake". Fora do repositorio
    # de proposito — o valor real fica apenas em backend/.env.
    SEED_SENHA_PADRAO: str = ""

    @field_validator("SECRET_KEY")
    @classmethod
    def _chave_forte(cls, valor: str) -> str:
        if len(valor.encode()) < MIN_BYTES_SECRET_KEY:
            raise ValueError(
                f"SECRET_KEY tem {len(valor.encode())} bytes; o minimo e "
                f"{MIN_BYTES_SECRET_KEY} (RFC 7518). Gere uma nova com: "
                'python -c "import secrets; print(secrets.token_urlsafe(64))"'
            )
        return valor

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
