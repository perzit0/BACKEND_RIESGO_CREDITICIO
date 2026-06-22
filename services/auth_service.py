import jwt
import os
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db
from models.usuario import Usuario


def hashear_password(password_plano: str) -> str:
    return generate_password_hash(password_plano)


def verificar_password(password_plano: str, hash_guardado: str) -> bool:
    return check_password_hash(hash_guardado, password_plano)


def crear_usuario(nombre, dni, email, telefono, password_plano, rol="user") -> Usuario:
    if Usuario.query.filter_by(email=email).first():
        raise ValueError("El correo ya está registrado")
    if Usuario.query.filter_by(dni=dni).first():
        raise ValueError("El DNI ya está registrado")

    usuario = Usuario(
        nombre=nombre,
        dni=dni,
        email=email,
        telefono=telefono,
        password_hash=hashear_password(password_plano),
        rol=rol,
    )
    db.session.add(usuario)
    db.session.commit()
    return usuario


def autenticar(email: str, password_plano: str):
    usuario = Usuario.query.filter_by(email=email).first()
    if usuario is None:
        return None
    if not verificar_password(password_plano, usuario.password_hash):
        return None
    if usuario.bloqueado:
        return None
    return usuario


def generar_token(usuario: Usuario) -> str:
    secret = os.environ.get("JWT_SECRET_KEY", "cambia-esto-en-produccion")
    payload = {
        "usuario_id": usuario.id,
        "email": usuario.email,
        "rol": usuario.rol,
        "exp": datetime.utcnow() + timedelta(hours=24),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decodificar_token(token: str) -> dict:
    secret = os.environ.get("JWT_SECRET_KEY", "cambia-esto-en-produccion")
    return jwt.decode(token, secret, algorithms=["HS256"])


def generar_token_recuperacion(email: str) -> str | None:
    usuario = Usuario.query.filter_by(email=email).first()
    if not usuario:
        return None
    import secrets
    codigo = str(secrets.randbelow(900000) + 100000)
    usuario.token_recuperacion = codigo
    usuario.token_recuperacion_expira = datetime.utcnow() + timedelta(minutes=10)
    db.session.commit()
    return codigo


def verificar_token_recuperacion(email: str, codigo: str) -> bool:
    usuario = Usuario.query.filter_by(email=email).first()
    if not usuario:
        return False
    if usuario.token_recuperacion != codigo:
        return False
    if usuario.token_recuperacion_expira is None:
        return False
    if datetime.utcnow() > usuario.token_recuperacion_expira:
        return False
    return True


def cambiar_password(email: str, nueva_password: str) -> None:
    usuario = Usuario.query.filter_by(email=email).first()
    if usuario:
        usuario.password_hash = hashear_password(nueva_password)
        usuario.token_recuperacion = None
        usuario.token_recuperacion_expira = None
        db.session.commit()