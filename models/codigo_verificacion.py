from datetime import datetime
from extensions import db


class CodigoVerificacion(db.Model):
    """
    Reemplaza el dict _codigos_correo en RAM de verification_service.py.
    Persiste los códigos en la DB para que sobrevivan reinicios de Gunicorn
    y deploys en Render.
    """
    __tablename__ = "codigos_verificacion"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    codigo = db.Column(db.String(6), nullable=False)
    expira = db.Column(db.DateTime, nullable=False)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    def esta_vigente(self) -> bool:
        return datetime.utcnow() <= self.expira

    def __repr__(self):
        return f"<CodigoVerificacion usuario={self.usuario_id} expira={self.expira}>"
