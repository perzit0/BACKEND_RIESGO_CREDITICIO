import bcrypt
import jwt
import secrets
from datetime import datetime, timedelta
from flask import current_app
from extensions import db
from models.usuario import Usuario


def hashear_password(password_plano: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_plano.encode("utf-8"), salt).decode("utf-8")


def verificar_password(password_plano: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password_plano.encode("utf-8"), password_hash.encode("utf-8"))


def generar_token(usuario: Usuario) -> str:
    payload = {
        "usuario_id": usuario.id,
        "email": usuario.email,
        "rol": usuario.rol,
        "exp": datetime.utcnow() + timedelta(hours=current_app.config["JWT_EXP_HORAS"]),
    }
    return jwt.encode(payload, current_app.config["JWT_SECRET_KEY"], algorithm="HS256")


def decodificar_token(token: str):
    try:
        return jwt.decode(token, current_app.config["JWT_SECRET_KEY"], algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def crear_usuario(nombre, dni, email, telefono, password_plano, rol="user"):
    if Usuario.query.filter_by(email=email).first():
        raise ValueError("Ese correo ya esta registrado")

    if Usuario.query.filter_by(dni=dni).first():
        raise ValueError("Ese DNI ya esta registrado")

    nuevo_usuario = Usuario(
        nombre=nombre,
        dni=dni,
        email=email,
        telefono=telefono,
        password_hash=hashear_password(password_plano),
        rol=rol,
        correo_verificado=False,
        telefono_verificado=False,
    )
    db.session.add(nuevo_usuario)
    db.session.commit()
    return nuevo_usuario


def autenticar(email, password_plano):
    usuario = Usuario.query.filter_by(email=email).first()
    if not usuario:
        return None
    if not verificar_password(password_plano, usuario.password_hash):
        return None
    return usuario


def generar_token_recuperacion(email: str) -> str | None:
    """
    Genera un token de recuperacion de contrasena para el usuario
    con ese correo. Si el correo no existe devuelve None de todas
    formas (no revelamos si el correo esta registrado o no).
    """
    usuario = Usuario.query.filter_by(email=email).first()
    if not usuario:
        return None

    codigo = str(secrets.randbelow(900000) + 100000)
    usuario.token_recuperacion = codigo
    usuario.token_recuperacion_expira = datetime.utcnow() + timedelta(minutes=10)
    db.session.commit()
    return codigo


def verificar_token_recuperacion(email: str, codigo: str) -> bool:
    usuario = Usuario.query.filter_by(email=email).first()
    if not usuario:
        return False
    if not usuario.token_recuperacion:
        return False
    if datetime.utcnow() > usuario.token_recuperacion_expira:
        return False
    if usuario.token_recuperacion != codigo:
        return False
    return True


def cambiar_password(email: str, nueva_password: str) -> bool:
    usuario = Usuario.query.filter_by(email=email).first()
    if not usuario:
        return False
    usuario.password_hash = hashear_password(nueva_password)
    usuario.token_recuperacion = None
    usuario.token_recuperacion_expira = None
    db.session.commit()
    return True