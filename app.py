"""Punto de entrada ASGI de TechZone.

La aplicación vive en el paquete `techzone/`; este módulo solo la expone para
que `uvicorn app:app` y @vercel/python (ver vercel.json) la encuentren.

    uvicorn app:app --reload
"""

from techzone.app import app

__all__ = ["app"]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
