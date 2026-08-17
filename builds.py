from flask import Blueprint, abort, render_template

from models import Build

builds_bp = Blueprint("builds", __name__, url_prefix="/builds")


@builds_bp.route("/<int:build_id>")
def detail(build_id):
    build = Build.query.get_or_404(build_id)
    if not build.active:
        abort(404)
    return render_template("builds/detail.html", b=build)
