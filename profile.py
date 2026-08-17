from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from extensions import db
from models import BuildRequest, User
from security import login_required, validate_csrf

profile_bp = Blueprint("profile", __name__, url_prefix="/perfil")

PURPOSE_OPTIONS = [
    "Gaming", "Trabajo", "Estudio", "Diseño gráfico", "Edición de video",
    "Programación", "Arquitectura", "Streaming", "Inteligencia artificial",
    "Uso general", "Otro",
]
GAME_OPTIONS = [
    "Fortnite", "GTA V", "GTA VI", "Valorant", "CS2", "Call of Duty",
    "Minecraft", "Apex Legends", "Warzone",
]
PROGRAM_OPTIONS = [
    "Adobe Photoshop", "Premiere Pro", "After Effects", "AutoCAD",
    "Blender", "Visual Studio Code", "Unreal Engine", "Unity",
]
PERIPHERAL_OPTIONS = ["Monitor", "Teclado", "Mouse", "Audífonos", "Micrófono", "Cámara web", "Parlantes", "Ninguno"]
BUDGET_RANGES = [
    "Menos de $1.500.000",
    "$1.500.000 - $3.000.000",
    "$3.000.000 - $5.000.000",
    "$5.000.000 - $8.000.000",
    "Más de $8.000.000",
]


def _csv(values):
    return ",".join(v.strip() for v in values if v and v.strip())


def _from_csv(value):
    return [v for v in (value or "").split(",") if v]


@profile_bp.route("/")
@login_required
def index():
    user = User.query.get_or_404(session["user_id"])
    requests_ = (
        BuildRequest.query.filter_by(user_id=user.id)
        .order_by(BuildRequest.created_at.desc())
        .all()
    )
    return render_template("profile/index.html", user=user, requests=requests_)


@profile_bp.route("/solicitudes/<int:request_id>")
@login_required
def solicitud_detalle(request_id):
    build_request = BuildRequest.query.get_or_404(request_id)
    if build_request.user_id != session["user_id"]:
        abort(403)
    return render_template("profile/solicitud_detalle.html", r=build_request)


@profile_bp.route("/armar-pc", methods=["GET", "POST"])
@login_required
def armar_pc():
    if request.method == "POST":
        if not validate_csrf(request.form.get("csrf_token")):
            flash("Tu sesión expiró, intenta de nuevo.", "error")
            return redirect(url_for("profile.armar_pc"))

        form = request.form
        purposes = form.getlist("purpose")
        purpose_other = form.get("purpose_other", "").strip()
        budget_range = form.get("budget_range", "").strip()
        budget_custom = form.get("budget_custom", "").strip()
        description = form.get("description", "").strip()
        has_components = form.get("has_components") == "si"

        errors = []
        if not purposes:
            errors.append("Selecciona para qué necesitas tu PC (al menos una opción).")
        if "Otro" in purposes and not purpose_other:
            errors.append("Especifica el uso en '¿Para qué necesitas tu PC?' → Otro.")

        budget = budget_custom if budget_range == "Otro (especificar)" else budget_range
        if not budget:
            errors.append("Indica tu presupuesto aproximado.")

        if len(description) < 20:
            errors.append("Cuéntanos con un poco más de detalle qué estás buscando (mínimo 20 caracteres).")

        pref_color = form.get("pref_color", "Me es indiferente")
        pref_color_other = form.get("pref_color_other", "").strip()
        if pref_color == "Otro" and not pref_color_other:
            errors.append("Especifica el color preferido.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template(
                "profile/armar_pc.html",
                purpose_options=PURPOSE_OPTIONS,
                game_options=GAME_OPTIONS,
                program_options=PROGRAM_OPTIONS,
                peripheral_options=PERIPHERAL_OPTIONS,
                budget_ranges=BUDGET_RANGES,
                form=form,
                selected_purposes=purposes,
                selected_games=form.getlist("games"),
                selected_programs=form.getlist("programs"),
                selected_peripherals=form.getlist("peripherals"),
            ), 400

        build_request = BuildRequest(
            user_id=session["user_id"],
            purpose=_csv(purposes),
            purpose_other=purpose_other,
            budget=budget,
            games=_csv(form.getlist("games") + ([form.get("games_other", "").strip()] if form.get("games_other", "").strip() else [])),
            programs=_csv(form.getlist("programs") + ([form.get("programs_other", "").strip()] if form.get("programs_other", "").strip() else [])),
            has_components=has_components,
            current_cpu=form.get("current_cpu", "").strip() if has_components else "",
            current_gpu=form.get("current_gpu", "").strip() if has_components else "",
            current_ram=form.get("current_ram", "").strip() if has_components else "",
            current_storage=form.get("current_storage", "").strip() if has_components else "",
            current_psu=form.get("current_psu", "").strip() if has_components else "",
            current_motherboard=form.get("current_motherboard", "").strip() if has_components else "",
            current_case=form.get("current_case", "").strip() if has_components else "",
            current_monitor=form.get("current_monitor", "").strip() if has_components else "",
            current_other=form.get("current_other", "").strip() if has_components else "",
            pref_cpu_brand=form.get("pref_cpu_brand", "Sin preferencia"),
            pref_gpu_brand=form.get("pref_gpu_brand", "Sin preferencia"),
            pref_aesthetics=form.get("pref_aesthetics", "Me es indiferente"),
            pref_color=pref_color,
            pref_color_other=pref_color_other if pref_color == "Otro" else "",
            pref_size=form.get("pref_size", "Me es indiferente"),
            peripherals=_csv(form.getlist("peripherals")),
            description=description,
            status="Pendiente",
        )
        db.session.add(build_request)
        db.session.commit()

        flash("Tu solicitud fue enviada. Nuestro equipo la revisará y te recomendará una configuración.", "success")
        return redirect(url_for("profile.index"))

    # Precarga opcional desde una build (?purpose=Gaming&budget=...&build=...)
    prefill_purpose = request.args.get("purpose", "").strip()
    prefill_budget = request.args.get("budget", "").strip()
    prefill_build = request.args.get("build", "").strip()

    prefill_form = {}
    selected_purposes = []
    if prefill_purpose:
        selected_purposes = [prefill_purpose]
    if prefill_budget:
        prefill_form["budget_range"] = "Otro (especificar)"
        prefill_form["budget_custom"] = prefill_budget
    if prefill_build:
        prefill_form["description"] = f"Me interesa la build recomendada '{prefill_build}'. "

    return render_template(
        "profile/armar_pc.html",
        purpose_options=PURPOSE_OPTIONS,
        game_options=GAME_OPTIONS,
        program_options=PROGRAM_OPTIONS,
        peripheral_options=PERIPHERAL_OPTIONS,
        budget_ranges=BUDGET_RANGES,
        form=prefill_form,
        selected_purposes=selected_purposes,
        selected_games=[],
        selected_programs=[],
        selected_peripherals=[],
    )
