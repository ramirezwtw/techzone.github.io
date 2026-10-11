"""API pública del foro: lectura de publicaciones y estadísticas."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from techzone.core.database import get_db
from techzone.schemas.community import CommunityStatsOut, PostDetailOut, PostOut
from techzone.services import community, stats

router = APIRouter(prefix="/community", tags=["comunidad"])


@router.get("/posts", response_model=list[PostOut], summary="Publicaciones del foro")
def posts(db: Session = Depends(get_db)):
    return [PostOut.of(p) for p in community.list_posts(db)]


@router.get("/posts/{post_id}", response_model=PostDetailOut, summary="Publicación con comentarios")
def post_detail(request: Request, post_id: int, db: Session = Depends(get_db)):
    post = community.get_post(db, post_id)
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Publicación no encontrada."
        )
    liked = community.has_liked(db, post, request.session.get("user_id"))
    return PostDetailOut.of(post, liked=liked)


@router.get("/stats", response_model=CommunityStatsOut, summary="Cifras de la comunidad")
def community_stats(db: Session = Depends(get_db)):
    return CommunityStatsOut(**stats.community_page(db))
