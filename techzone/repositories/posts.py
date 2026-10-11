"""Acceso a datos del foro: publicaciones, comentarios y likes."""

from typing import Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from techzone.models import Comment, Post, PostLike

# Las tarjetas del foro muestran autor, número de comentarios y de likes:
# se cargan de una vez para no disparar una consulta por publicación.
_CARD_LOADS = (
    selectinload(Post.user),
    selectinload(Post.comments),
    selectinload(Post.likes),
)


def get(db: Session, post_id: int) -> Optional[Post]:
    return db.get(Post, post_id)


def list_all(db: Session) -> Sequence[Post]:
    return db.scalars(
        select(Post).options(*_CARD_LOADS).order_by(Post.created_at.desc())
    ).all()


def list_recent(db: Session, limit: int = 3) -> Sequence[Post]:
    return db.scalars(
        select(Post).options(*_CARD_LOADS).order_by(Post.created_at.desc()).limit(limit)
    ).all()


def count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Post)) or 0


def count_comments(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Comment)) or 0


def create(db: Session, user_id: int, title: str, content: str) -> Post:
    post = Post(user_id=user_id, title=title, content=content)
    db.add(post)
    db.commit()
    return post


def increment_views(db: Session, post: Post) -> None:
    post.views += 1
    db.commit()


def add_comment(db: Session, post_id: int, user_id: int, content: str) -> Comment:
    comment = Comment(post_id=post_id, user_id=user_id, content=content)
    db.add(comment)
    db.commit()
    return comment


def find_like(db: Session, post_id: int, user_id: int) -> Optional[PostLike]:
    return db.scalars(
        select(PostLike).where(PostLike.post_id == post_id, PostLike.user_id == user_id)
    ).first()


def add_like(db: Session, post_id: int, user_id: int) -> None:
    db.add(PostLike(post_id=post_id, user_id=user_id))
    db.commit()


def remove_like(db: Session, like: PostLike) -> None:
    db.delete(like)
    db.commit()
