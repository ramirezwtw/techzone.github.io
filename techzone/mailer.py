"""Envío de correos transaccionales (verificación de cuenta, recuperación de contraseña).

Si no hay un servidor SMTP configurado por variables de entorno (MAIL_SERVER, etc.),
el correo se imprime en la consola en lugar de enviarse — así el flujo funciona en
el entorno local de pruebas sin depender de un servicio externo.
"""

import os
import smtplib
from email.message import EmailMessage

MAIL_SERVER = os.environ.get("MAIL_SERVER")
MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() != "false"
MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "TechZone <no-reply@techzone.app>")


def send_email(to, subject, body):
    if not MAIL_SERVER:
        print("\n" + "=" * 60)
        print("[TechZone] Envío de correo simulado (no hay MAIL_SERVER configurado)")
        print(f"Para: {to}")
        print(f"Asunto: {subject}")
        print("-" * 60)
        print(body)
        print("=" * 60 + "\n")
        return

    message = EmailMessage()
    message["From"] = MAIL_DEFAULT_SENDER
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(MAIL_SERVER, MAIL_PORT) as server:
        if MAIL_USE_TLS:
            server.starttls()
        if MAIL_USERNAME and MAIL_PASSWORD:
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
        server.send_message(message)


def send_verification_email(user, url):
    send_email(
        to=user.email,
        subject="Verifica tu cuenta de TechZone",
        body=(
            f"Hola {user.name},\n\n"
            "Gracias por registrarte en TechZone. Confirma tu correo electrónico "
            f"visitando el siguiente enlace:\n\n{url}\n\n"
            "Este enlace vence en 24 horas. Si tú no creaste esta cuenta, ignora este mensaje.\n\n"
            "— El equipo de TechZone"
        ),
    )


def send_password_reset_email(user, url):
    send_email(
        to=user.email,
        subject="Recupera tu contraseña de TechZone",
        body=(
            f"Hola {user.name},\n\n"
            "Recibimos una solicitud para restablecer la contraseña de tu cuenta. "
            f"Si fuiste tú, visita el siguiente enlace para elegir una nueva contraseña:\n\n{url}\n\n"
            "Este enlace vence en 1 hora. Si tú no solicitaste este cambio, puedes ignorar este mensaje.\n\n"
            "— El equipo de TechZone"
        ),
    )
