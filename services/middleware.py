from functools import wraps
from flask import request, jsonify
from services.auth_service import decodificar_token


def requiere_token(f):
    @wraps(f)
    def decorador(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Token no proporcionado"}), 401

        token = auth_header.split(" ")[1]
        payload = decodificar_token(token)
        if payload is None:
            return jsonify({"error": "Token invalido o expirado"}), 401

        request.usuario_actual = payload
        return f(*args, **kwargs)
    return decorador


def requiere_rol(rol_requerido):
    def decorador_externo(f):
        @wraps(f)
        @requiere_token
        def decorador_interno(*args, **kwargs):
            if request.usuario_actual.get("rol") != rol_requerido:
                return jsonify({"error": "No tienes permiso para acceder a este recurso"}), 403
            return f(*args, **kwargs)
        return decorador_interno
    return decorador_externo