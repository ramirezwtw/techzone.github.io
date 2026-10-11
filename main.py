from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from database import get_db
from models import Build, Comment, Post, Product, User
from templating import render

router = APIRouter(default_response_class=HTMLResponse)

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


def _count(db: Session, model) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


@router.get("/", name="main.index")
def index(request: Request, db: Session = Depends(get_db)):
    products = db.scalars(
        select(Product).where(Product.active.is_(True)).order_by(Product.id.asc())
    ).all()
    builds = db.scalars(
        select(Build).where(Build.active.is_(True)).order_by(Build.id.asc())
    ).all()
    recent_posts = db.scalars(
        select(Post)
        .options(
            selectinload(Post.user),
            selectinload(Post.comments),
            selectinload(Post.likes),
        )
        .order_by(Post.created_at.desc())
        .limit(3)
    ).all()
    community_stats = dict(
        users=_count(db, User),
        posts=_count(db, Post),
        comments=_count(db, Comment),
    )
    return render(
        request,
        "index.html",
        {
            "products": products,
            "builds": builds,
            "recent_posts": recent_posts,
            "community_stats": community_stats,
        },
    )


@router.get("/legal/{slug}", name="main.legal")
def legal(request: Request, slug: str):
    page = LEGAL_PAGES.get(slug)
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Página no encontrada.")
    return render(request, "legal.html", {"page": page})
