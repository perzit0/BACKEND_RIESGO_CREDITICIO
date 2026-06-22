import os
import joblib
import warnings
from datetime import datetime

warnings.filterwarnings("ignore")

_modelo_fraude = None


def _cargar_modelo():
    global _modelo_fraude
    if _modelo_fraude is None:
        from flask import current_app
        ruta = os.path.join(current_app.config["ML_MODELS_PATH"], "modelo_fraude.pkl")
        _modelo_fraude = joblib.load(ruta)
    return _modelo_fraude


def evaluar_fraude(
    edad: int,
    antiguedad_laboral_meses: int,
    dni: str,
    ip_registro: str,
    telefono: str,
) -> bool:
    """
    Evalúa si un registro de usuario nuevo es sospechoso de fraude.
    Devuelve True si es sospechoso, False si es normal.

    Columnas que usa el modelo (en este orden exacto):
    edad, antiguedad_laboral_meses, dni_valido,
    ip_registros_simultaneos, telefono_repetido, hora_registro

    NOTA: edad y antiguedad_laboral_meses son opcionales en el registro.
    Si no vienen del formulario, auth_routes.py usa valores neutrales (30, 12)
    que no sesgan el modelo hacia ningún extremo.
    """
    modelo = _cargar_modelo()

    dni_valido = 1 if (dni and len(dni) == 8 and dni.isdigit() and len(set(dni)) > 1) else 0
    ip_registros_simultaneos = _contar_registros_ip(ip_registro)
    telefono_repetido = _telefono_ya_existe(telefono)
    hora_registro = datetime.utcnow().hour

    import pandas as pd
    df_entrada = pd.DataFrame([{
        "edad": edad,
        "antiguedad_laboral_meses": antiguedad_laboral_meses,
        "dni_valido": dni_valido,
        "ip_registros_simultaneos": ip_registros_simultaneos,
        "telefono_repetido": telefono_repetido,
        "hora_registro": hora_registro,
    }])

    prediccion = modelo.predict(df_entrada)[0]
    return bool(prediccion == 1)


def _contar_registros_ip(ip: str) -> int:
    """
    Cuenta cuántos usuarios se registraron desde la misma IP
    en los últimos 10 minutos.
    """
    if not ip:
        return 1
    try:
        from models.usuario import Usuario
        from datetime import timedelta
        hace_10_min = datetime.utcnow() - timedelta(minutes=10)
        count = Usuario.query.filter(
            Usuario.ip_registro == ip,
            Usuario.fecha_registro >= hace_10_min,
        ).count()
        return max(count, 1)
    except Exception:
        return 1


def _telefono_ya_existe(telefono: str) -> int:
    """
    Verifica si el teléfono ya está registrado en otra cuenta.
    Nota: teléfono no es unique en la DB por decisión de diseño,
    pero sí se usa como señal de fraude si se repite.
    """
    if not telefono:
        return 0
    try:
        from models.usuario import Usuario
        existe = Usuario.query.filter_by(telefono=telefono).first()
        return 1 if existe else 0
    except Exception:
        return 0
