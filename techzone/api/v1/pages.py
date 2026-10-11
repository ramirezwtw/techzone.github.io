"""API de contenido: payload del home y páginas legales."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from techzone.core.database import get_db
from techzone.schemas.catalog import BuildOut, ProductOut
from techzone.schemas.community import PostOut
from techzone.schemas.pages import HomeOut, HomeStatsOut, LegalPageOut
from techzone.services import catalog, community, pages, stats

router = APIRouter(tags=["contenido"])


@router.get("/home", response_model=HomeOut, summary="Todo lo que necesita el home")
def home(db: Session = Depends(get_db)):
    return HomeOut(
        products=[ProductOut.of(p) for p in catalog.active_products(db)],
        builds=[BuildOut.of(b) for b in catalog.active_builds(db)],
        recent_posts=[PostOut.of(p) for p in community.recent_posts(db)],
        stats=HomeStatsOut(**stats.community(db)),
    )


@router.get("/legal/{slug}", response_model=LegalPageOut, summary="Página legal")
def legal(slug: str):
    page = pages.legal(slug)
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Página no encontrada.")
    return LegalPageOut(slug=slug, title=page["title"], body=page["body"])
