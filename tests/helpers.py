"""Utilidades para las pruebas: CSRF, login y creación de datos."""

import re

from conftest import USER_EMAIL, USER_NAME, USER_PASSWORD
from techzone.database import SessionLocal
from techzone.models import BuildRequest, Post, User

CSRF_RE = re.compile(r'name="csrf_token" value="([^"]+)"')
FLASH_RE = re.compile(r'flash-msg flash-\w+">([^<]*)<')
STAT_RE = re.compile(r'admin-stat-value">([^<]*)<')


def csrf_token(html: str) -> str:
    match = CSRF_RE.search(html)
    assert match, "la página no trae un campo csrf_token"
    return match.group(1)


def flashes(html: str) -> list:
    return FLASH_RE.findall(html)


def stats(html: str) -> list:
    """Valores de las tarjetas del dashboard, en el orden de la plantilla."""
    return STAT_RE.findall(html)


def post_form(client, path, data=None, token_from=None, follow_redirects=False):
    """POST con un csrf_token recién obtenido (de `token_from` o de `path`)."""
    page = client.get(token_from or path)
    payload = dict(data or {})
    payload["csrf_token"] = csrf_token(page.text)
    return client.post(path, data=payload, follow_redirects=follow_redirects)


def login(client, email, password, next_url=None):
    page = client.get("/login")
    path = "/login" if next_url is None else f"/login?next={next_url}"
    return client.post(
        path,
        data={"email": email, "password": password, "csrf_token": csrf_token(page.text)},
        follow_redirects=False,
    )


def create_user(
    email=USER_EMAIL,
    password=USER_PASSWORD,
    name=USER_NAME,
    role="user",
    active=True,
    email_verified=False,
) -> int:
    with SessionLocal() as session:
        user = User(
            name=name, email=email, role=role, active=active, email_verified=email_verified
        )
        user.set_password(password)
        session.add(user)
        session.commit()
        return user.id


def create_post(user_id, title="¿Vale la pena una RTX 4070?", content="Dudo entre 4070 y 7800 XT.") -> int:
    with SessionLocal() as session:
        post = Post(user_id=user_id, title=title, content=content)
        session.add(post)
        session.commit()
        return post.id


def create_build_request(user_id, **kwargs) -> int:
    data = dict(
        purpose="Gaming",
        budget="$3.000.000 - $5.000.000",
        description="Quiero un PC para jugar y programar sin problemas.",
        status="Pendiente",
    )
    data.update(kwargs)
    with SessionLocal() as session:
        build_request = BuildRequest(user_id=user_id, **data)
        session.add(build_request)
        session.commit()
        return build_request.id


ARMAR_PC_FORM = {
    "purpose": ["Gaming", "Programación"],
    "games": ["GTA VI", "Valorant"],
    "games_other": "Elden Ring",
    "programs": ["Blender"],
    "peripherals": ["Monitor", "Teclado"],
    "budget_range": "$3.000.000 - $5.000.000",
    "has_components": "si",
    "current_cpu": "Ryzen 3 3200G",
    "pref_cpu_brand": "AMD",
    "pref_color": "Otro",
    "pref_color_other": "Blanco",
    "description": "Quiero un PC para jugar y programar sin problemas.",
}

PRODUCT_FORM = {
    "name": "Cooler AIO 360",
    "brand": "Cooling",
    "description": "Refrigeración líquida de 360 mm.",
    "image_url": "",
    "price": "199.90",
    "stock": "5",
    "active": "on",
}

BUILD_FORM = {
    "tier": "Inicial",
    "name": "Gamer Inicial",
    "tier_emoji": "🎮",
    "budget_label": "$500 – $800 USD",
    "cpu": "Ryzen 5 5600",
    "gpu": "RTX 3060",
    "ram": "16 GB DDR4",
    "storage": "500 GB NVMe",
    "performance_note": "1080p / 60-100 fps",
    "performance_pct": "45",
    "image_url": "",
    "active": "on",
}
