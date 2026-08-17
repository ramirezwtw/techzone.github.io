from flask import Blueprint, abort, render_template

from models import Build, Comment, Post, Product, User

main_bp = Blueprint("main", __name__)

LEGAL_PAGES = {
    "privacidad": {
        "title": "Política de Privacidad",
        "body": [
            "TechZone recopila únicamente los datos necesarios para crear tu cuenta y gestionar tus "
            "solicitudes de asesoría: nombre, correo electrónico y la información que nos compartes "
            "en el formulario de armado de PC.",
            "Tu contraseña se almacena siempre cifrada (hash) y nunca en texto plano. No compartimos "
            "tus datos con terceros.",
            "Puedes solicitar la eliminación de tu cuenta y de tus solicitudes en cualquier momento "
            "contactándonos a hola@techzone.app.",
        ],
    },
    "terminos": {
        "title": "Términos y Condiciones",
        "body": [
            "Al registrarte en TechZone aceptas usar la plataforma de forma responsable y aportar "
            "información veraz en tus solicitudes de asesoría.",
            "Las recomendaciones de hardware son orientativas y elaboradas por nuestro equipo en base "
            "a la información que nos entregas; los precios de los componentes pueden variar respecto "
            "al mercado real.",
            "TechZone se reserva el derecho de desactivar cuentas que hagan un uso indebido de la "
            "plataforma.",
        ],
    },
    "cookies": {
        "title": "Política de Cookies",
        "body": [
            "TechZone utiliza únicamente una cookie de sesión, necesaria para mantenerte identificado "
            "mientras usas la plataforma (iniciar sesión, ver tu perfil, gestionar tus solicitudes).",
            "No utilizamos cookies de seguimiento ni de publicidad de terceros.",
            "Al cerrar sesión o cerrar el navegador, la cookie de sesión deja de ser válida.",
        ],
    },
}


@main_bp.route("/")
def index():
    products = Product.query.filter_by(active=True).order_by(Product.id.asc()).all()
    builds = Build.query.filter_by(active=True).order_by(Build.id.asc()).all()
    recent_posts = Post.query.order_by(Post.created_at.desc()).limit(3).all()
    community_stats = dict(
        users=User.query.count(),
        posts=Post.query.count(),
        comments=Comment.query.count(),
    )
    return render_template(
        "index.html",
        products=products,
        builds=builds,
        recent_posts=recent_posts,
        community_stats=community_stats,
    )


@main_bp.route("/legal/<slug>")
def legal(slug):
    page = LEGAL_PAGES.get(slug)
    if page is None:
        abort(404)
    return render_template("legal.html", page=page)
