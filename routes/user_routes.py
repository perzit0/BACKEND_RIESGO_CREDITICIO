from flask import Blueprint, request, jsonify, Response
from extensions import db
from models.usuario import Usuario
from models.evaluacion import Evaluacion
from services.risk_service import evaluar_riesgo
from services.pdf_service import generar_pdf_evaluacion
from services.middleware import requiere_token
from services.auth_service import (
    verificar_token_recuperacion, cambiar_password,
)
from services.verification_service import (
    generar_y_enviar_correo_cambio_perfil,
    generar_y_enviar_codigo_sms,
    verificar_codigo_sms,
)
import secrets

user_bp = Blueprint("user", __name__)


# ── EVALUACIÓN ──

@user_bp.route("/evaluar-riesgo", methods=["POST"])
@requiere_token
def evaluar():
    usuario_id = request.usuario_actual["usuario_id"]
    data = request.get_json()

    campos_requeridos = [
        "ingreso_mensual", "monto_en_bancos", "num_cuentas_bancarias", "edad",
    ]
    faltantes = [c for c in campos_requeridos if data.get(c) is None]
    if faltantes:
        return jsonify({"error": f"Faltan campos: {', '.join(faltantes)}"}), 400

    resultado = evaluar_riesgo(data)

    nueva_evaluacion = Evaluacion(
        usuario_id=usuario_id,
        ingreso_mensual=data["ingreso_mensual"],
        num_creditos_previos=data.get("num_creditos_previos", 0),
        dias_mora_historico=data.get("dias_mora_historico", 0),
        ratio_deuda_ingreso=data.get("ratio_deuda_ingreso", 0),
        num_lineas_credito_abiertas=data.get("num_lineas_credito_abiertas", 0),
        num_dependientes_economicos=data.get("num_dependientes_economicos", 0),
        monto_en_bancos=data["monto_en_bancos"],
        num_cuentas_bancarias=data["num_cuentas_bancarias"],
        edad=data["edad"],
        antiguedad_laboral_meses=data.get("antiguedad_laboral_meses", 0),
        tipo_empleo=data.get("tipo_empleo"),
        nivel_educativo=data.get("nivel_educativo"),
        estado_civil=data.get("estado_civil"),
        tipo_vivienda=data.get("tipo_vivienda"),
        num_dependientes_hogar=data.get("num_dependientes_hogar", 0),
        score_final=resultado["score_final"],
        categoria_riesgo=resultado["categoria_riesgo"],
        factores_influyentes=resultado["factores_influyentes"],
        recomendaciones=resultado["recomendaciones"],
    )
    db.session.add(nueva_evaluacion)
    db.session.commit()

    return jsonify({
        "evaluacion_id": nueva_evaluacion.id,
        "score_final": resultado["score_final"],
        "categoria_riesgo": resultado["categoria_riesgo"],
        "factores_influyentes": resultado["factores_influyentes"],
        "recomendaciones": resultado["recomendaciones"],
    }), 201


@user_bp.route("/mi-historial", methods=["GET"])
@requiere_token
def mi_historial():
    usuario_id = request.usuario_actual["usuario_id"]

    evaluaciones = (
        Evaluacion.query
        .filter_by(usuario_id=usuario_id)
        .order_by(Evaluacion.fecha_evaluacion.desc())
        .all()
    )

    resultado = [
        {
            "id": e.id,
            "fecha": e.fecha_evaluacion.isoformat(),
            "score_final": e.score_final,
            "categoria_riesgo": e.categoria_riesgo,
            "recomendaciones": e.recomendaciones,
        }
        for e in evaluaciones
    ]
    return jsonify(resultado), 200


@user_bp.route("/evaluacion/<int:evaluacion_id>/pdf", methods=["GET"])
@requiere_token
def descargar_pdf(evaluacion_id):
    usuario_id = request.usuario_actual["usuario_id"]

    evaluacion = Evaluacion.query.filter_by(
        id=evaluacion_id, usuario_id=usuario_id
    ).first()
    if evaluacion is None:
        return jsonify({"error": "Evaluacion no encontrada"}), 404

    # CORRECCIÓN: db.session.get reemplaza Usuario.query.get (deprecado en SQLAlchemy 2.x)
    usuario = db.session.get(Usuario, usuario_id)
    pdf_bytes = generar_pdf_evaluacion(usuario, evaluacion)

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=reporte_riesgo_{evaluacion_id}.pdf",
            # Header necesario para que el navegador permita la descarga desde web
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


# ── ESTADÍSTICAS COMUNIDAD ──

@user_bp.route("/comunidad", methods=["GET"])
@requiere_token
def comunidad():
    from sqlalchemy import func

    # Subconsulta: última evaluación de cada usuario
    subq = (
        db.session.query(
            Evaluacion.usuario_id,
            func.max(Evaluacion.fecha_evaluacion).label("ultima_fecha")
        )
        .group_by(Evaluacion.usuario_id)
        .subquery()
    )

    ultimas = (
        db.session.query(Evaluacion)
        .join(subq, (Evaluacion.usuario_id == subq.c.usuario_id) &
              (Evaluacion.fecha_evaluacion == subq.c.ultima_fecha))
        .all()
    )

    total = len(ultimas)
    if total == 0:
        return jsonify({
            "total_personas": 0,
            "distribucion": {"bajo": 0, "medio": 0, "alto": 0},
            "porcentajes": {"bajo": 0, "medio": 0, "alto": 0},
        }), 200

    distribucion = {"bajo": 0, "medio": 0, "alto": 0}
    for e in ultimas:
        if e.categoria_riesgo in distribucion:
            distribucion[e.categoria_riesgo] += 1

    porcentajes = {
        k: round((v / total) * 100, 1)
        for k, v in distribucion.items()
    }

    return jsonify({
        "total_personas": total,
        "distribucion": distribucion,
        "porcentajes": porcentajes,
    }), 200


# ── PERFIL ──

@user_bp.route("/mi-perfil", methods=["GET"])
@requiere_token
def mi_perfil():
    usuario_id = request.usuario_actual["usuario_id"]
    usuario = db.session.get(Usuario, usuario_id)

    return jsonify({
        "id": usuario.id,
        "nombre": usuario.nombre,
        "email": usuario.email,
        "telefono": usuario.telefono,
        "dni": usuario.dni,
        "fecha_registro": usuario.fecha_registro.isoformat(),
    }), 200


@user_bp.route("/actualizar-nombre", methods=["POST"])
@requiere_token
def actualizar_nombre():
    usuario_id = request.usuario_actual["usuario_id"]
    data = request.get_json()
    nuevo_nombre = data.get("nombre", "").strip()

    if not nuevo_nombre:
        return jsonify({"error": "El nombre no puede estar vacio"}), 400

    usuario = db.session.get(Usuario, usuario_id)
    usuario.nombre = nuevo_nombre
    db.session.commit()

    return jsonify({"mensaje": "Nombre actualizado correctamente"}), 200


@user_bp.route("/solicitar-cambio-password", methods=["POST"])
@requiere_token
def solicitar_cambio_password():
    usuario_id = request.usuario_actual["usuario_id"]
    usuario = db.session.get(Usuario, usuario_id)

    from datetime import datetime, timedelta
    codigo = str(secrets.randbelow(900000) + 100000)
    usuario.token_recuperacion = codigo
    usuario.token_recuperacion_expira = datetime.utcnow() + timedelta(minutes=10)
    db.session.commit()

    generar_y_enviar_correo_cambio_perfil(usuario.email, codigo, "contrasena")

    return jsonify({
        "mensaje": "Te enviamos un codigo a tu correo para confirmar el cambio de contrasena."
    }), 200


@user_bp.route("/confirmar-cambio-password", methods=["POST"])
@requiere_token
def confirmar_cambio_password():
    usuario_id = request.usuario_actual["usuario_id"]
    data = request.get_json()
    codigo = data.get("codigo")
    nueva = data.get("nueva_password")
    confirmar = data.get("confirmar_password")

    if not codigo or not nueva or not confirmar:
        return jsonify({"error": "Faltan campos obligatorios"}), 400

    if nueva != confirmar:
        return jsonify({"error": "Las contrasenas no coinciden"}), 400

    if len(nueva) < 8:
        return jsonify({"error": "La contrasena debe tener al menos 8 caracteres"}), 400

    usuario = db.session.get(Usuario, usuario_id)

    if not verificar_token_recuperacion(usuario.email, codigo):
        return jsonify({"error": "Codigo invalido o expirado"}), 400

    cambiar_password(usuario.email, nueva)

    return jsonify({"mensaje": "Contrasena actualizada correctamente"}), 200


@user_bp.route("/solicitar-cambio-telefono", methods=["POST"])
@requiere_token
def solicitar_cambio_telefono():
    usuario_id = request.usuario_actual["usuario_id"]
    data = request.get_json()
    nuevo_telefono = data.get("nuevo_telefono", "").strip()

    if not nuevo_telefono:
        return jsonify({"error": "El nuevo telefono es obligatorio"}), 400

    usuario = db.session.get(Usuario, usuario_id)

    from datetime import datetime, timedelta
    codigo = str(secrets.randbelow(900000) + 100000)
    usuario.token_recuperacion = codigo
    usuario.token_recuperacion_expira = datetime.utcnow() + timedelta(minutes=10)
    usuario.telefono_nuevo_pendiente = nuevo_telefono
    db.session.commit()

    generar_y_enviar_correo_cambio_perfil(usuario.email, codigo, "telefono")

    return jsonify({
        "mensaje": "Te enviamos un codigo a tu correo para confirmar el cambio de telefono."
    }), 200


@user_bp.route("/confirmar-cambio-telefono", methods=["POST"])
@requiere_token
def confirmar_cambio_telefono():
    usuario_id = request.usuario_actual["usuario_id"]
    data = request.get_json()
    codigo_correo = data.get("codigo_correo")

    if not codigo_correo:
        return jsonify({"error": "El codigo de correo es obligatorio"}), 400

    usuario = db.session.get(Usuario, usuario_id)

    if not verificar_token_recuperacion(usuario.email, codigo_correo):
        return jsonify({"error": "Codigo de correo invalido o expirado"}), 400

    if not usuario.telefono_nuevo_pendiente:
        return jsonify({"error": "No hay cambio de telefono pendiente"}), 400

    generar_y_enviar_codigo_sms(usuario_id, usuario.telefono_nuevo_pendiente)

    usuario.token_recuperacion = None
    usuario.token_recuperacion_expira = None
    db.session.commit()

    return jsonify({
        "mensaje": "Correo confirmado. Te enviamos un SMS al nuevo numero para verificarlo."
    }), 200


@user_bp.route("/verificar-nuevo-telefono", methods=["POST"])
@requiere_token
def verificar_nuevo_telefono():
    usuario_id = request.usuario_actual["usuario_id"]
    data = request.get_json()
    codigo_sms = data.get("codigo_sms")

    if not codigo_sms:
        return jsonify({"error": "El codigo SMS es obligatorio"}), 400

    usuario = db.session.get(Usuario, usuario_id)

    if not usuario.telefono_nuevo_pendiente:
        return jsonify({"error": "No hay cambio de telefono pendiente"}), 400

    if not verificar_codigo_sms(usuario.telefono_nuevo_pendiente, codigo_sms):
        return jsonify({"error": "Codigo SMS invalido o expirado"}), 400

    usuario.telefono = usuario.telefono_nuevo_pendiente
    usuario.telefono_nuevo_pendiente = None
    db.session.commit()

    return jsonify({"mensaje": "Numero de telefono actualizado correctamente"}), 200
