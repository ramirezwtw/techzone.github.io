from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from database import get_db
from models import Build
from templating import render

router = APIRouter(prefix="/builds", default_response_class=HTMLResponse)


@router.get("/{build_id}", name="builds.detail")
def detail(request: Request, build_id: int, db: Session = Depends(get_db)):
    build = db.get(Build, build_id)
    if build is None or not build.active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Build no encontrada.")
    return render(request, "builds/detail.html", {"b": build})
