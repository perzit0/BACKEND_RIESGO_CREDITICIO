from flask import Blueprint, request, jsonify
from extensions import db
from models.usuario import Usuario
from services.auth_service import (
    crear_usuario, autenticar, generar_token,
    generar_token_recuperacion, verificar_token_recuperacion, cambiar_password,
)
from services.verification_service import (
    generar_y_enviar_codigo_correo,
    generar_y_enviar_codigo_sms,
    verificar_codigo_correo,
    verificar_codigo_sms,
    generar_y_enviar_codigo_recuperacion,
)
from services.fraud_service import evaluar_fraude

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/registro", methods=["POST"])
def registro():
    data = request.get_json()

    campos_requeridos = ["nombre", "dni", "email", "telefono", "password"]
    faltantes = [c for c in campos_requeridos if not data.get(c)]
    if faltantes:
        return jsonify({"error": f"Faltan campos: {', '.join(faltantes)}"}), 400

    # Validar formato DNI antes de crear usuario
    dni = data["dni"].strip()
    if len(dni) != 8 or not dni.isdigit():
        return jsonify({"error": "El DNI debe tener exactamente 8 dígitos numéricos"}), 400

    try:
        usuario = crear_usuario(
            nombre=data["nombre"],
            dni=dni,
            email=data["email"],
            telefono=data["telefono"],
            password_plano=data["password"],
            rol="user",
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 409

    ip_registro = request.headers.get("X-Forwarded-For", request.remote_addr)
    # X-Forwarded-For puede traer múltiples IPs separadas por coma; tomar la primera
    if ip_registro and "," in ip_registro:
        ip_registro = ip_registro.split(",")[0].strip()
    usuario.ip_registro = ip_registro
    db.session.commit()

    # Evaluar fraude (no bloquea el registro si falla)
    try:
        es_sospechoso = evaluar_fraude(
            # CORRECCIÓN: edad y antiguedad usan valores del formulario si vienen,
            # o valores neutrales que no sesguen el modelo
            edad=data.get("edad", 30),
            antiguedad_laboral_meses=data.get("antiguedad_laboral_meses", 12),
            dni=dni,
            ip_registro=ip_registro,
            telefono=data["telefono"],
        )
        if es_sospechoso:
            usuario.marcado_fraude = True
            db.session.commit()
    except Exception as e:
        print(f"[FRAUDE] Error al evaluar fraude: {e}")

    # CORRECCIÓN CRÍTICA: si el envío de correo falla, hacer rollback del usuario
    # para que no quede huérfano en la DB y el usuario pueda reintentar el registro
    try:
        generar_y_enviar_codigo_correo(usuario.id, usuario.email)
    except Exception as e:
        print(f"[REGISTRO] Error al enviar correo a {usuario.email}: {e}")
        db.session.delete(usuario)
        db.session.commit()
        return jsonify({
            "error": "No se pudo enviar el correo de verificación. Intenta nuevamente en unos minutos."
        }), 503

    return jsonify({
        "mensaje": "Usuario registrado. Verifica tu correo para continuar.",
        "usuario_id": usuario.id,
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Correo y contrasena son obligatorios"}), 400

    usuario = autenticar(email, password)
    if usuario is None:
        return jsonify({"error": "Correo o contrasena incorrectos"}), 401

    token = generar_token(usuario)

    return jsonify({
        "token": token,
        "rol": usuario.rol,
        "usuario": {
            "id": usuario.id,
            "nombre": usuario.nombre,
            "email": usuario.email,
            "correo_verificado": usuario.correo_verificado,
            "telefono_verificado": usuario.telefono_verificado,
        }
    }), 200


@auth_bp.route("/verificar-correo", methods=["POST"])
def verificar_correo():
    data = request.get_json()
    usuario_id = data.get("usuario_id")
    codigo = data.get("codigo")

    if not usuario_id or not codigo:
        return jsonify({"error": "usuario_id y codigo son obligatorios"}), 400

    if not verificar_codigo_correo(usuario_id, codigo):
        return jsonify({"error": "Codigo invalido o expirado"}), 400

    # CORRECCIÓN: db.session.get() reemplaza el deprecado Usuario.query.get()
    usuario = db.session.get(Usuario, usuario_id)
    if usuario is None:
        return jsonify({"error": "Usuario no encontrado"}), 404

    usuario.correo_verificado = True
    db.session.commit()

    generar_y_enviar_codigo_sms(usuario.id, usuario.telefono)

    return jsonify({"mensaje": "Correo verificado. Se envio un codigo SMS."}), 200


@auth_bp.route("/verificar-sms", methods=["POST"])
def verificar_sms():
    data = request.get_json()
    usuario_id = data.get("usuario_id")
    codigo = data.get("codigo")

    if not usuario_id or not codigo:
        return jsonify({"error": "usuario_id y codigo son obligatorios"}), 400

    usuario = db.session.get(Usuario, usuario_id)
    if usuario is None:
        return jsonify({"error": "Usuario no encontrado"}), 404

    if not verificar_codigo_sms(usuario.telefono, codigo):
        return jsonify({"error": "Codigo invalido o expirado"}), 400

    usuario.telefono_verificado = True
    db.session.commit()

    return jsonify({"mensaje": "Telefono verificado. Registro completo."}), 200


@auth_bp.route("/olvide-password", methods=["POST"])
def olvide_password():
    data = request.get_json()
    email = data.get("email")

    if not email:
        return jsonify({"error": "El correo es obligatorio"}), 400

    codigo = generar_token_recuperacion(email)

    # Siempre respondemos igual, no revelamos si el correo existe
    if codigo:
        try:
            generar_y_enviar_codigo_recuperacion(email, codigo)
        except Exception as e:
            print(f"[CORREO] Error enviando recuperacion: {e}")

    return jsonify({
        "mensaje": "Si ese correo esta registrado, recibiras un codigo para restablecer tu contrasena."
    }), 200


@auth_bp.route("/verificar-codigo-recuperacion", methods=["POST"])
def verificar_codigo_recuperacion():
    data = request.get_json()
    email = data.get("email")
    codigo = data.get("codigo")

    if not email or not codigo:
        return jsonify({"error": "Correo y codigo son obligatorios"}), 400

    if not verificar_token_recuperacion(email, codigo):
        return jsonify({"error": "Codigo invalido o expirado"}), 400

    return jsonify({"mensaje": "Codigo valido. Puedes cambiar tu contrasena."}), 200


@auth_bp.route("/nueva-password", methods=["POST"])
def nueva_password():
    data = request.get_json()
    email = data.get("email")
    codigo = data.get("codigo")
    nueva = data.get("nueva_password")

    if not email or not codigo or not nueva:
        return jsonify({"error": "Faltan campos obligatorios"}), 400

    if len(nueva) < 8:
        return jsonify({"error": "La contrasena debe tener al menos 8 caracteres"}), 400

    if not verificar_token_recuperacion(email, codigo):
        return jsonify({"error": "Codigo invalido o expirado"}), 400

    cambiar_password(email, nueva)

    return jsonify({"mensaje": "Contrasena actualizada correctamente."}), 200


@auth_bp.route("/reenviar-codigo-correo", methods=["POST"])
def reenviar_codigo_correo():
    data = request.get_json()
    usuario_id = data.get("usuario_id")
    if not usuario_id:
        return jsonify({"error": "usuario_id es obligatorio"}), 400

    usuario = db.session.get(Usuario, usuario_id)
    if not usuario:
        return jsonify({"error": "Usuario no encontrado"}), 404

    generar_y_enviar_codigo_correo(usuario.id, usuario.email)
    return jsonify({"mensaje": "Codigo reenviado"}), 200


@auth_bp.route("/reenviar-codigo-sms", methods=["POST"])
def reenviar_codigo_sms():
    data = request.get_json()
    usuario_id = data.get("usuario_id")
    if not usuario_id:
        return jsonify({"error": "usuario_id es obligatorio"}), 400

    usuario = db.session.get(Usuario, usuario_id)
    if not usuario:
        return jsonify({"error": "Usuario no encontrado"}), 404

    generar_y_enviar_codigo_sms(usuario.id, usuario.telefono)
    return jsonify({"mensaje": "SMS reenviado"}), 200
