"""DTOs de las páginas de contenido."""

from pydantic import BaseModel

from techzone.schemas.catalog import BuildOut, ProductOut
from techzone.schemas.community import PostOut


class LegalPageOut(BaseModel):
    slug: str
    title: str
    body: list[str]


class HomeStatsOut(BaseModel):
    users: int
    posts: int
    comments: int


class HomeOut(BaseModel):
    """Todo lo que el home necesita, en una sola llamada."""

    products: list[ProductOut]
    builds: list[BuildOut]
    recent_posts: list[PostOut]
    stats: HomeStatsOut
