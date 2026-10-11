"""Reglas de negocio del foro de la comunidad."""

from typing import Optional, Sequence

from sqlalchemy.orm import Session

from techzone.models import Comment, Post
from techzone.repositories import posts as posts_repo

MIN_TITLE = 5
MIN_CONTENT = 20
MIN_COMMENT = 2
HOME_POSTS = 3


def list_posts(db: Session) -> Sequence[Post]:
    return posts_repo.list_all(db)


def recent_posts(db: Session, limit: int = HOME_POSTS) -> Sequence[Post]:
    return posts_repo.list_recent(db, limit)


def get_post(db: Session, post_id: int) -> Optional[Post]:
    return posts_repo.get(db, post_id)


def register_view(db: Session, post: Post) -> None:
    posts_repo.increment_views(db, post)


def create_post(
    db: Session, user_id: int, title: str, content: str
) -> tuple[Optional[Post], list[str]]:
    title = (title or "").strip()
    content = (content or "").strip()

    errors = []
    if len(title) < MIN_TITLE:
        errors.append(f"El título debe tener al menos {MIN_TITLE} caracteres.")
    if len(content) < MIN_CONTENT:
        errors.append(f"Cuéntanos un poco más (mínimo {MIN_CONTENT} caracteres).")

    if errors:
        return None, errors

    return posts_repo.create(db, user_id, title, content), []


def add_comment(
    db: Session, post: Post, user_id: int, content: str
) -> tuple[Optional[Comment], list[str]]:
    content = (content or "").strip()
    if len(content) < MIN_COMMENT:
        return None, ["Escribe un comentario antes de enviarlo."]

    return posts_repo.add_comment(db, post.id, user_id, content), []


def has_liked(db: Session, post: Post, user_id: Optional[int]) -> bool:
    if not user_id:
        return False
    return posts_repo.find_like(db, post.id, user_id) is not None


def toggle_like(db: Session, post: Post, user_id: int) -> bool:
    """Da o quita el like y devuelve si quedó marcado."""
    existing = posts_repo.find_like(db, post.id, user_id)
    if existing:
        posts_repo.remove_like(db, existing)
        return False

    posts_repo.add_like(db, post.id, user_id)
    return True
