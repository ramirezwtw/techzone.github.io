from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from database import get_db
from models import BuildRequest, Comment, Post, PostLike, User
from security import require_login, validate_csrf
from templating import flash, redirect, render

router = APIRouter(prefix="/comunidad", default_response_class=HTMLResponse)


def _count(db: Session, model) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


def _get_post_or_404(db: Session, post_id: int) -> Post:
    post = db.get(Post, post_id)
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Publicación no encontrada."
        )
    return post


@router.get("/", name="community.index")
def index(request: Request, db: Session = Depends(get_db)):
    posts = db.scalars(
        select(Post)
        .options(
            selectinload(Post.user),
            selectinload(Post.comments),
            selectinload(Post.likes),
        )
        .order_by(Post.created_at.desc())
    ).all()
    stats = dict(
        users=_count(db, User),
        posts=_count(db, Post),
        comments=_count(db, Comment),
        requests=_count(db, BuildRequest),
    )
    return render(request, "community/index.html", {"posts": posts, "stats": stats})


@router.get("/nueva", name="community.nueva")
def nueva_form(request: Request, user_id: int = Depends(require_login)):
    return render(request, "community/post_form.html", {"title": "", "content": ""})


@router.post("/nueva", name="community.nueva")
def nueva(
    request: Request,
    title: str = Form(""),
    content: str = Form(""),
    csrf_token: str = Form(""),
    user_id: int = Depends(require_login),
    db: Session = Depends(get_db),
):
    if not validate_csrf(request, csrf_token):
        flash(request, "Tu sesión expiró, intenta de nuevo.", "error")
        return redirect(request, "community.nueva")

    title = title.strip()
    content = content.strip()

    errors = []
    if len(title) < 5:
        errors.append("El título debe tener al menos 5 caracteres.")
    if len(content) < 20:
        errors.append("Cuéntanos un poco más (mínimo 20 caracteres).")

    if errors:
        for error in errors:
            flash(request, error, "error")
        return render(
            request,
            "community/post_form.html",
            {"title": title, "content": content},
            status_code=400,
        )

    post = Post(user_id=user_id, title=title, content=content)
    db.add(post)
    db.commit()
    flash(request, "Tu publicación ya está en la comunidad.", "success")
    return redirect(request, "community.detalle", post_id=post.id)


@router.get("/{post_id}", name="community.detalle")
def detalle(request: Request, post_id: int, db: Session = Depends(get_db)):
    post = _get_post_or_404(db, post_id)
    post.views += 1
    db.commit()

    comments = post.comments  # la relación ya viene ordenada por created_at

    liked = False
    user_id = request.session.get("user_id")
    if user_id:
        liked = (
            db.scalars(
                select(PostLike).where(
                    PostLike.post_id == post.id, PostLike.user_id == user_id
                )
            ).first()
            is not None
        )

    return render(
        request,
        "community/post_detail.html",
        {"post": post, "comments": comments, "liked": liked},
    )


@router.post("/{post_id}/comentar", name="community.comentar")
def comentar(
    request: Request,
    post_id: int,
    content: str = Form(""),
    csrf_token: str = Form(""),
    user_id: int = Depends(require_login),
    db: Session = Depends(get_db),
):
    post = _get_post_or_404(db, post_id)

    if not validate_csrf(request, csrf_token):
        flash(request, "Tu sesión expiró, intenta de nuevo.", "error")
        return redirect(request, "community.detalle", post_id=post_id)

    content = content.strip()
    if len(content) < 2:
        flash(request, "Escribe un comentario antes de enviarlo.", "error")
        return redirect(request, "community.detalle", post_id=post_id)

    db.add(Comment(post_id=post.id, user_id=user_id, content=content))
    db.commit()
    flash(request, "Comentario publicado.", "success")
    return redirect(request, "community.detalle", post_id=post_id)


@router.post("/{post_id}/like", name="community.like")
def like(
    request: Request,
    post_id: int,
    csrf_token: str = Form(""),
    user_id: int = Depends(require_login),
    db: Session = Depends(get_db),
):
    post = _get_post_or_404(db, post_id)

    if not validate_csrf(request, csrf_token):
        flash(request, "Tu sesión expiró, intenta de nuevo.", "error")
        return redirect(request, "community.detalle", post_id=post_id)

    existing = db.scalars(
        select(PostLike).where(PostLike.post_id == post.id, PostLike.user_id == user_id)
    ).first()
    if existing:
        db.delete(existing)
    else:
        db.add(PostLike(post_id=post.id, user_id=user_id))
    db.commit()
    return redirect(request, "community.detalle", post_id=post_id)
