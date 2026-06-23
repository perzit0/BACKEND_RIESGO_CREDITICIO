import os
import warnings
from datetime import datetime

warnings.filterwarnings("ignore")

_modelo_fraude = None


def _cargar_modelo():
    global _modelo_fraude
    if _modelo_fraude is None:
        try:
            import joblib
            from flask import current_app
            ruta = os.path.join(current_app.config["ML_MODELS_PATH"], "modelo_fraude.pkl")
            _modelo_fraude = joblib.load(ruta)
        except Exception as e:
            print(f"[FRAUDE] No se pudo cargar el modelo: {e}")
            return None
    return _modelo_fraude


def evaluar_fraude(edad, antiguedad_laboral_meses, dni, ip_registro, telefono) -> bool:
    modelo = _cargar_modelo()

    # Si el modelo no carga, usar reglas heurísticas simples
    if modelo is None:
        return _evaluar_heuristico(dni, ip_registro, telefono)

    try:
        import pandas as pd
        dni_valido = 1 if (dni and len(dni) == 8 and dni.isdigit() and len(set(dni)) > 1) else 0
        ip_registros_simultaneos = _contar_registros_ip(ip_registro)
        telefono_repetido = _telefono_ya_existe(telefono)
        hora_registro = datetime.utcnow().hour

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
    except Exception as e:
        print(f"[FRAUDE] Error en predicción: {e}")
        return _evaluar_heuristico(dni, ip_registro, telefono)


def _evaluar_heuristico(dni: str, ip_registro: str, telefono: str) -> bool:
    """Reglas simples si el modelo no está disponible."""
    # DNI inválido
    if not (dni and len(dni) == 8 and dni.isdigit() and len(set(dni)) > 1):
        return True
    # Teléfono repetido en más de 2 cuentas
    if _telefono_ya_existe(telefono) and _contar_cuentas_telefono(telefono) > 2:
        return True
    return False


def _contar_registros_ip(ip: str) -> int:
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
    if not telefono:
        return 0
    try:
        from models.usuario import Usuario
        existe = Usuario.query.filter_by(telefono=telefono).first()
        return 1 if existe else 0
    except Exception:
        return 0


def _contar_cuentas_telefono(telefono: str) -> int:
    if not telefono:
        return 0
    try:
        from models.usuario import Usuario
        return Usuario.query.filter_by(telefono=telefono).count()
    except Exception:
        return 0