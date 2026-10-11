"""DTOs del estado de sesión, para que el frontend pinte el menú y los avisos."""

from typing import Optional

from pydantic import BaseModel


class FlashOut(BaseModel):
    category: str
    message: str


class SessionOut(BaseModel):
    authenticated: bool
    name: Optional[str] = None
    role: Optional[str] = None
    is_admin: bool = False
    # Mensajes que dejó un redirect del backend (se entregan una sola vez).
    flashes: list[FlashOut] = []


class CsrfOut(BaseModel):
    csrf_token: str
