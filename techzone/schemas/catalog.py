"""DTOs de salida del catálogo (lo que ve el frontend, no lo que hay en la BD).

Los precios viajan como número: JSON no tiene tipo decimal, así que el
formato de moneda lo pone el frontend.
"""

from pydantic import BaseModel, ConfigDict

from techzone.models import Build, Product


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    brand: str
    description: str
    image_url: str
    price: float
    stock: int

    @classmethod
    def of(cls, product: Product) -> "ProductOut":
        return cls.model_validate(product)


class BuildOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tier: str
    name: str
    tier_emoji: str
    budget_label: str
    cpu: str
    gpu: str
    ram: str
    storage: str
    performance_note: str
    performance_pct: int
    image_url: str
    featured: bool

    @classmethod
    def of(cls, build: Build) -> "BuildOut":
        return cls.model_validate(build)
