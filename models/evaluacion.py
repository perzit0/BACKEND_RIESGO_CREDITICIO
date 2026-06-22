from datetime import datetime
from extensions import db


class Evaluacion(db.Model):
    __tablename__ = "evaluaciones"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)

    # ============================================================
    # INPUT — Datos financieros
    # ============================================================
    ingreso_mensual = db.Column(db.Float, nullable=False)
    num_creditos_previos = db.Column(db.Integer, default=0)
    dias_mora_historico = db.Column(db.Integer, default=0)
    ratio_deuda_ingreso = db.Column(db.Float, default=0)
    num_lineas_credito_abiertas = db.Column(db.Integer, default=0)
    num_dependientes_economicos = db.Column(db.Integer, default=0)
    monto_en_bancos = db.Column(db.Float, nullable=False)
    num_cuentas_bancarias = db.Column(db.Integer, nullable=False)

    # ============================================================
    # INPUT — Datos demograficos
    # ============================================================
    edad = db.Column(db.Integer, nullable=False)
    antiguedad_laboral_meses = db.Column(db.Integer, default=0)
    tipo_empleo = db.Column(db.String(20))
    nivel_educativo = db.Column(db.String(30))
    estado_civil = db.Column(db.String(20))
    tipo_vivienda = db.Column(db.String(20))
    num_dependientes_hogar = db.Column(db.Integer, default=0)

    # ============================================================
    # OUTPUT — Resultado del modelo de riesgo crediticio
    # ============================================================
    score_final = db.Column(db.Float)
    categoria_riesgo = db.Column(db.String(10))
    factores_influyentes = db.Column(db.JSON)
    recomendaciones = db.Column(db.JSON)

    fecha_evaluacion = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Evaluacion usuario={self.usuario_id} score={self.score_final}>"