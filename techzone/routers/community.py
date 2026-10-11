"""Foro de la comunidad. Capa HTTP: valida CSRF, delega y redirige."""

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from techzone.core.database import get_db
from techzone.core.security import require_login, validate_csrf
from techzone.core.templating import flash, redirect, render
from techzone.models import Post
from techzone.services import community, stats

router = APIRouter(prefix="/comunidad", default_response_class=HTMLResponse)


def _get_post_or_404(db: Session, post_id: int) -> Post:
    post = community.get_post(db, post_id)
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Publicación no encontrada."
        )
    return post


@router.get("/", name="community.index")
def index(request: Request, db: Session = Depends(get_db)):
    return render(
        request,
        "community/index.html",
        {"posts": community.list_posts(db), "stats": stats.community_page(db)},
    )


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

    post, errors = community.create_post(db, user_id, title, content)
    if errors:
        for error in errors:
            flash(request, error, "error")
        return render(
            request,
            "community/post_form.html",
            {"title": title.strip(), "content": content.strip()},
            status_code=400,
        )

    flash(request, "Tu publicación ya está en la comunidad.", "success")
    return redirect(request, "community.detalle", post_id=post.id)


@router.get("/{post_id}", name="community.detalle")
def detalle(request: Request, post_id: int, db: Session = Depends(get_db)):
    post = _get_post_or_404(db, post_id)
    community.register_view(db, post)

    return render(
        request,
        "community/post_detail.html",
        {
            "post": post,
            "comments": post.comments,  # la relación ya viene ordenada por fecha
            "liked": community.has_liked(db, post, request.session.get("user_id")),
        },
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

    _, errors = community.add_comment(db, post, user_id, content)
    if errors:
        for error in errors:
            flash(request, error, "error")
    else:
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

    community.toggle_like(db, post, user_id)
    return redirect(request, "community.detalle", post_id=post_id)
