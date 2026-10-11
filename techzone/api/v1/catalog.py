"""API pública del catálogo (la consume el frontend Astro)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from techzone.core.database import get_db
from techzone.schemas.catalog import BuildOut, ProductOut
from techzone.services import catalog

router = APIRouter(prefix="/catalog", tags=["catálogo"])


@router.get("/products", response_model=list[ProductOut], summary="Productos activos")
def products(db: Session = Depends(get_db)):
    return [ProductOut.of(p) for p in catalog.active_products(db)]


@router.get("/builds", response_model=list[BuildOut], summary="Builds activas")
def builds(db: Session = Depends(get_db)):
    return [BuildOut.of(b) for b in catalog.active_builds(db)]


@router.get("/builds/{build_id}", response_model=BuildOut, summary="Detalle de una build")
def build_detail(build_id: int, db: Session = Depends(get_db)):
    build = catalog.visible_build(db, build_id)
    if build is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Build no encontrada.")
    return BuildOut.of(build)
