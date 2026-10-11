"""Contenido estático de las páginas legales.

Es texto, no lógica: vive en la capa de servicios para que lo pueda consumir
tanto la plantilla Jinja como la API JSON.
"""

from typing import Optional

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


def legal(slug: str) -> Optional[dict]:
    return LEGAL_PAGES.get(slug)


def legal_slugs() -> list[str]:
    return list(LEGAL_PAGES)
