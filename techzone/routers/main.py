"""Home y páginas legales. Capa HTTP: pide datos a los servicios y renderiza."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from techzone.core.database import get_db
from techzone.core.templating import render
from techzone.services import catalog, community, pages, stats

router = APIRouter(default_response_class=HTMLResponse)


@router.get("/", name="main.index")
def index(request: Request, db: Session = Depends(get_db)):
    return render(
        request,
        "index.html",
        {
            "products": catalog.active_products(db),
            "builds": catalog.active_builds(db),
            "recent_posts": community.recent_posts(db),
            "community_stats": stats.community(db),
        },
    )


@router.get("/legal/{slug}", name="main.legal")
def legal(request: Request, slug: str):
    page = pages.legal(slug)
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Página no encontrada.")
    return render(request, "legal.html", {"page": page})
