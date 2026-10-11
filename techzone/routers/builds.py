"""Detalle público de una build recomendada."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from techzone.core.database import get_db
from techzone.core.templating import render
from techzone.services import catalog

router = APIRouter(prefix="/builds", default_response_class=HTMLResponse)


@router.get("/{build_id}", name="builds.detail")
def detail(request: Request, build_id: int, db: Session = Depends(get_db)):
    build = catalog.visible_build(db, build_id)
    if build is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Build no encontrada.")
    return render(request, "builds/detail.html", {"b": build})
