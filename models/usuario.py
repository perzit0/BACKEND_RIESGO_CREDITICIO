from datetime import datetime
from extensions import db


class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    dni = db.Column(db.String(8), unique=True, nullable=False)

    email = db.Column(db.String(150), unique=True, nullable=False)
    telefono = db.Column(db.String(15), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    rol = db.Column(db.String(10), nullable=False, default="user")

    correo_verificado = db.Column(db.Boolean, default=False)
    telefono_verificado = db.Column(db.Boolean, default=False)

    marcado_fraude = db.Column(db.Boolean, default=False)
    revisado_por_admin = db.Column(db.Boolean, default=False)

    # NUEVO: cuenta bloqueada por el admin (fraude confirmado)
    bloqueado = db.Column(db.Boolean, default=False)

    ip_registro = db.Column(db.String(45))

    token_recuperacion = db.Column(db.String(100), nullable=True)
    token_recuperacion_expira = db.Column(db.DateTime, nullable=True)
    telefono_nuevo_pendiente = db.Column(db.String(15), nullable=True)

    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    evaluaciones = db.relationship("Evaluacion", backref="usuario", lazy=True)

    def __repr__(self):
        return f"<Usuario {self.email} rol={self.rol}>"
