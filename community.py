from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from extensions import db
from models import BuildRequest, Comment, Post, PostLike, User
from security import login_required, validate_csrf

community_bp = Blueprint("community", __name__, url_prefix="/comunidad")


@community_bp.route("/")
def index():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    stats = dict(
        users=User.query.count(),
        posts=Post.query.count(),
        comments=Comment.query.count(),
        requests=BuildRequest.query.count(),
    )
    return render_template("community/index.html", posts=posts, stats=stats)


@community_bp.route("/nueva", methods=["GET", "POST"])
@login_required
def nueva():
    if request.method == "POST":
        if not validate_csrf(request.form.get("csrf_token")):
            flash("Tu sesión expiró, intenta de nuevo.", "error")
            return redirect(url_for("community.nueva"))

        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()

        errors = []
        if len(title) < 5:
            errors.append("El título debe tener al menos 5 caracteres.")
        if len(content) < 20:
            errors.append("Cuéntanos un poco más (mínimo 20 caracteres).")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("community/post_form.html", title=title, content=content), 400

        post = Post(user_id=session["user_id"], title=title, content=content)
        db.session.add(post)
        db.session.commit()
        flash("Tu publicación ya está en la comunidad.", "success")
        return redirect(url_for("community.detalle", post_id=post.id))

    return render_template("community/post_form.html", title="", content="")


@community_bp.route("/<int:post_id>")
def detalle(post_id):
    post = Post.query.get_or_404(post_id)
    post.views += 1
    db.session.commit()
    comments = post.comments.order_by(Comment.created_at.asc()).all()
    liked = False
    if session.get("user_id"):
        liked = PostLike.query.filter_by(post_id=post.id, user_id=session["user_id"]).first() is not None
    return render_template("community/post_detail.html", post=post, comments=comments, liked=liked)


@community_bp.route("/<int:post_id>/comentar", methods=["POST"])
@login_required
def comentar(post_id):
    post = Post.query.get_or_404(post_id)
    if not validate_csrf(request.form.get("csrf_token")):
        flash("Tu sesión expiró, intenta de nuevo.", "error")
        return redirect(url_for("community.detalle", post_id=post_id))

    content = request.form.get("content", "").strip()
    if len(content) < 2:
        flash("Escribe un comentario antes de enviarlo.", "error")
        return redirect(url_for("community.detalle", post_id=post_id))

    db.session.add(Comment(post_id=post.id, user_id=session["user_id"], content=content))
    db.session.commit()
    flash("Comentario publicado.", "success")
    return redirect(url_for("community.detalle", post_id=post_id))


@community_bp.route("/<int:post_id>/like", methods=["POST"])
@login_required
def like(post_id):
    post = Post.query.get_or_404(post_id)
    if not validate_csrf(request.form.get("csrf_token")):
        flash("Tu sesión expiró, intenta de nuevo.", "error")
        return redirect(url_for("community.detalle", post_id=post_id))

    existing = PostLike.query.filter_by(post_id=post.id, user_id=session["user_id"]).first()
    if existing:
        db.session.delete(existing)
    else:
        db.session.add(PostLike(post_id=post.id, user_id=session["user_id"]))
    db.session.commit()
    return redirect(url_for("community.detalle", post_id=post_id))
