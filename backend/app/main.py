"""Ponto de entrada da API do dir-dashboard."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, indicadores
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="dir-dashboard — API",
    description="Painel de gestao executiva. KAMI CO.",
    version="1.0.0",
    # Em producao a documentacao fica fechada.
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router)
app.include_router(indicadores.router)


@app.get("/health", tags=["infra"])
def health() -> dict[str, str]:
    return {"status": "ok", "ambiente": settings.ENVIRONMENT}
