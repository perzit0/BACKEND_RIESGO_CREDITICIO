import random
import os
from datetime import datetime, timedelta
from flask import current_app
from twilio.rest import Client

_codigos_correo = {}
DURACION_CODIGO_MINUTOS = 10


def _generar_codigo() -> str:
    return str(random.randint(100000, 999999))


def _enviar_correo_sendgrid(destinatario: str, asunto: str, codigo: str, mensaje: str):
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail

    cuerpo_html = f"""
<html>
<body style="font-family: Arial, sans-serif; background-color: #F0EFFF; padding: 32px;">
  <div style="max-width: 480px; margin: 0 auto; background: white; border-radius: 16px; padding: 32px;">
    <div style="margin-bottom:24px;">
      <span style="background:#6B4EFF; border-radius:10px; padding:8px 14px; color:white; font-weight:700; font-size:14px;">UNFV</span>
      <span style="font-size:15px; font-weight:600; color:#1A1A2E; margin-left:10px;">Riesgo Crediticio</span>
    </div>
    <p style="color:#4A5568; font-size:14px; margin-bottom:8px;">{mensaje}</p>
    <div style="background:#F0EFFF; border-radius:12px; padding:24px; text-align:center; margin:20px 0;">
      <span style="font-size:40px; font-weight:700; color:#6B4EFF; letter-spacing:14px;">{codigo}</span>
    </div>
    <p style="color:#8892B0; font-size:12px;">Este codigo expira en {DURACION_CODIGO_MINUTOS} minutos.</p>
    <p style="color:#8892B0; font-size:12px;">Si no solicitaste este cambio, ignora este mensaje.</p>
    <div style="margin-top:24px; padding-top:16px; border-top:1px solid #E2E8F0;">
      <p style="color:#A0AEC0; font-size:11px;">Universidad Nacional Federico Villarreal</p>
    </div>
  </div>
</body>
</html>
"""

    api_key = os.environ.get("SENDGRID_API_KEY", "")
    remitente = current_app.config["SMTP_EMAIL"]

    message = Mail(
        from_email=remitente,
        to_emails=destinatario,
        subject=asunto,
        html_content=cuerpo_html
    )

    sg = SendGridAPIClient(api_key)
    response = sg.send(message)
    print(f"[SENDGRID] Correo enviado a {destinatario} — status: {response.status_code}")


def generar_y_enviar_codigo_correo(usuario_id: int, email: str) -> str:
    codigo = _generar_codigo()
    _codigos_correo[usuario_id] = {
        "codigo": codigo,
        "expira": datetime.utcnow() + timedelta(minutes=DURACION_CODIGO_MINUTOS),
    }
    try:
        _enviar_correo_sendgrid(
            destinatario=email,
            asunto="Codigo de verificacion — UNFV Riesgo Crediticio",
            codigo=codigo,
            mensaje="Tu codigo de verificacion es:",
        )
    except Exception as e:
        print(f"[SENDGRID] Error al enviar correo a {email}: {e}")
        print(f"[SIMULADO] Codigo para {email}: {codigo}")
    return codigo


def generar_y_enviar_codigo_recuperacion(email: str, codigo: str) -> None:
    try:
        _enviar_correo_sendgrid(
            destinatario=email,
            asunto="Recuperacion de contrasena — UNFV Riesgo Crediticio",
            codigo=codigo,
            mensaje="Usa este codigo para restablecer tu contrasena:",
        )
    except Exception as e:
        print(f"[SENDGRID] Error al enviar recuperacion a {email}: {e}")
        print(f"[SIMULADO] Codigo recuperacion para {email}: {codigo}")


def generar_y_enviar_correo_cambio_perfil(email: str, codigo: str, tipo: str) -> None:
    if tipo == "contrasena":
        asunto = "Cambio de contrasena — UNFV Riesgo Crediticio"
        mensaje = "Has solicitado cambiar tu contrasena. Usa este codigo para confirmar:"
    else:
        asunto = "Cambio de telefono — UNFV Riesgo Crediticio"
        mensaje = "Has solicitado cambiar tu numero de telefono. Usa este codigo para confirmar:"

    try:
        _enviar_correo_sendgrid(
            destinatario=email,
            asunto=asunto,
            codigo=codigo,
            mensaje=mensaje,
        )
    except Exception as e:
        print(f"[SENDGRID] Error: {e}")
        print(f"[SIMULADO] Codigo {tipo} para {email}: {codigo}")


def verificar_codigo_correo(usuario_id: int, codigo_ingresado: str) -> bool:
    registro = _codigos_correo.get(usuario_id)
    if registro is None:
        return False
    if datetime.utcnow() > registro["expira"]:
        return False
    if registro["codigo"] != codigo_ingresado:
        return False
    del _codigos_correo[usuario_id]
    return True


# ── SMS via Twilio ──

def _cliente_twilio() -> Client:
    return Client(
        current_app.config["TWILIO_ACCOUNT_SID"],
        current_app.config["TWILIO_AUTH_TOKEN"],
    )


def _normalizar_telefono_pe(telefono: str) -> str:
    telefono = telefono.strip()
    if telefono.startswith("+"):
        return telefono
    return f"+51{telefono}"


def generar_y_enviar_codigo_sms(usuario_id: int, telefono: str) -> None:
    cliente = _cliente_twilio()
    telefono_normalizado = _normalizar_telefono_pe(telefono)
    cliente.verify.v2.services(
        current_app.config["TWILIO_VERIFY_SERVICE_SID"]
    ).verifications.create(to=telefono_normalizado, channel="sms")


def verificar_codigo_sms(telefono: str, codigo_ingresado: str) -> bool:
    cliente = _cliente_twilio()
    telefono_normalizado = _normalizar_telefono_pe(telefono)
    try:
        resultado = cliente.verify.v2.services(
            current_app.config["TWILIO_VERIFY_SERVICE_SID"]
        ).verification_checks.create(to=telefono_normalizado, code=codigo_ingresado)
    except Exception:
        return False
    return resultado.status == "approved"