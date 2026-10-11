"""Versión 1 de la API JSON."""

from fastapi import APIRouter

from techzone.api.v1 import catalog, community, pages

router = APIRouter(prefix="/api/v1")
router.include_router(pages.router)
router.include_router(catalog.router)
router.include_router(community.router)
