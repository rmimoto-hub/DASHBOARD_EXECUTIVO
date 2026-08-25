"""Rotas de indicadores, medicoes e o resumo do painel."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import exige_admin, exige_escrita, usuario_atual
from app.core.database import get_db
from app.models.indicador import Indicador, Medicao
from app.models.usuario import Usuario
from app.schemas.indicador import (
    IndicadorCreate,
    IndicadorOut,
    MedicaoCreate,
    MedicaoOut,
    ResumoIndicador,
)
from app.services.painel import montar_resumo

router = APIRouter(prefix="/indicadores", tags=["indicadores"])


@router.get("", response_model=list[IndicadorOut])
def listar(
    area: str | None = Query(default=None),
    apenas_ativos: bool = Query(default=True),
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_atual),
) -> list[Indicador]:
    stmt = select(Indicador)
    if area:
        stmt = stmt.where(Indicador.area == area)
    if apenas_ativos:
        stmt = stmt.where(Indicador.ativo.is_(True))
    return list(db.scalars(stmt.order_by(Indicador.area, Indicador.nome)))


@router.post("", response_model=IndicadorOut, status_code=status.HTTP_201_CREATED)
def criar(
    dados: IndicadorCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(exige_admin),
) -> Indicador:
    existente = db.scalar(
        select(Indicador).where(Indicador.codigo == dados.codigo)
    )
    if existente is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ja existe indicador com o codigo {dados.codigo}",
        )

    indicador = Indicador(**dados.model_dump())
    db.add(indicador)
    db.commit()
    db.refresh(indicador)
    return indicador


@router.get("/resumo", response_model=list[ResumoIndicador])
def resumo(
    area: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_atual),
) -> list[ResumoIndicador]:
    """Visao do painel: ultimo valor, meta, variacao e atingimento."""
    return montar_resumo(db, area=area)


@router.post(
    "/medicoes", response_model=MedicaoOut, status_code=status.HTTP_201_CREATED
)
def registrar_medicao(
    dados: MedicaoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(exige_escrita),
) -> Medicao:
    indicador = db.get(Indicador, dados.indicador_id)
    if indicador is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Indicador nao encontrado"
        )

    # Competencia e sempre o primeiro dia do mes.
    competencia = dados.competencia.replace(day=1)

    existente = db.scalar(
        select(Medicao).where(
            Medicao.indicador_id == dados.indicador_id,
            Medicao.competencia == competencia,
        )
    )
    if existente is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ja existe medicao deste indicador nesta competencia",
        )

    medicao = Medicao(
        **{**dados.model_dump(), "competencia": competencia},
        registrado_por=usuario.id,
    )
    db.add(medicao)
    db.commit()
    db.refresh(medicao)
    return medicao


@router.get("/{indicador_id}/medicoes", response_model=list[MedicaoOut])
def listar_medicoes(
    indicador_id: int,
    limite: int = Query(default=24, ge=1, le=120),
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_atual),
) -> list[Medicao]:
    if db.get(Indicador, indicador_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Indicador nao encontrado"
        )

    stmt = (
        select(Medicao)
        .where(Medicao.indicador_id == indicador_id)
        .order_by(Medicao.competencia.desc())
        .limit(limite)
    )
    return list(db.scalars(stmt))
