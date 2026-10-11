"""Contadores que alimentan el home, la comunidad y el dashboard del admin."""

from sqlalchemy.orm import Session

from techzone.repositories import build_requests as requests_repo
from techzone.repositories import posts as posts_repo
from techzone.repositories import products as products_repo
from techzone.repositories import users as users_repo


def community(db: Session) -> dict:
    """Las tres cifras que muestra el home."""
    return {
        "users": users_repo.count(db),
        "posts": posts_repo.count(db),
        "comments": posts_repo.count_comments(db),
    }


def community_page(db: Session) -> dict:
    """Las del foro, que además cuenta las solicitudes de asesoría."""
    return dict(community(db), requests=requests_repo.count(db))


def admin_dashboard(db: Session) -> dict:
    return {
        "total_users": users_repo.count(db),
        "admins": users_repo.count_admins(db),
        "total_products": products_repo.count(db),
        "active_products": products_repo.count_active(db),
        "out_of_stock": products_repo.count_out_of_stock(db),
        "pending_requests": requests_repo.count_pending(db),
    }
