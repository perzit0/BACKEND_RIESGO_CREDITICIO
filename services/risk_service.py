import os
import joblib
import numpy as np
import warnings
from flask import current_app

warnings.filterwarnings("ignore")

_modelo_riesgo = None


def _cargar_modelo():
    global _modelo_riesgo
    if _modelo_riesgo is None:
        ruta = os.path.join(current_app.config["ML_MODELS_PATH"], "modelo_riesgo.pkl")
        _modelo_riesgo = joblib.load(ruta)
    return _modelo_riesgo


def evaluar_riesgo(datos_formulario: dict) -> dict:
    """
    Recibe el diccionario con los campos del formulario y devuelve
    el score, categoria, factores y recomendaciones.

    Columnas que usa el modelo (en este orden exacto):
    person_age, person_income, person_home_ownership,
    person_emp_length, cb_person_default_on_file,
    loan_percent_income, cb_person_cred_hist_length
    """
    modelo = _cargar_modelo()

    # Mapeo de campos del formulario a columnas del modelo
    person_age = datos_formulario.get("edad", 0)
    person_income = datos_formulario.get("ingreso_mensual", 0)
    person_home_ownership = _mapear_vivienda(datos_formulario.get("tipo_vivienda", "propia"))
    person_emp_length = datos_formulario.get("antiguedad_laboral_meses", 0) / 12
    cb_person_default_on_file = 1 if datos_formulario.get("dias_mora_historico", 0) > 0 else 0
    loan_percent_income = datos_formulario.get("ratio_deuda_ingreso", 0)
    cb_person_cred_hist_length = datos_formulario.get("num_lineas_credito_abiertas", 0)

    entrada = np.array([[
        person_age,
        person_income,
        person_home_ownership,
        person_emp_length,
        cb_person_default_on_file,
        loan_percent_income,
        cb_person_cred_hist_length,
    ]])

    import pandas as pd
    columnas = [
        "person_age", "person_income", "person_home_ownership",
        "person_emp_length", "cb_person_default_on_file",
        "loan_percent_income", "cb_person_cred_hist_length",
    ]
    df_entrada = pd.DataFrame(entrada, columns=columnas)

    score_final = round(float(modelo.predict_proba(df_entrada)[0][1]), 3)
    categoria_riesgo = _categorizar(score_final)
    factores_influyentes = _factores(datos_formulario, score_final)
    recomendaciones = _recomendaciones(categoria_riesgo, datos_formulario)

    return {
        "score_final": score_final,
        "categoria_riesgo": categoria_riesgo,
        "factores_influyentes": factores_influyentes,
        "recomendaciones": recomendaciones,
    }


def _mapear_vivienda(tipo: str) -> str:
    mapeo = {
        "propia": "OWN",
        "alquilada": "RENT",
        "familiar": "OTHER",
    }
    return mapeo.get(tipo, "OTHER")


def _categorizar(score: float) -> str:
    if score < 0.33:
        return "bajo"
    elif score < 0.66:
        return "medio"
    return "alto"


def _factores(datos: dict, score: float) -> list:
    factores = []

    mora = datos.get("dias_mora_historico", 0)
    if mora > 0:
        factores.append({"factor": "Historial de mora", "impacto": "negativo"})

    ratio = datos.get("ratio_deuda_ingreso", 0)
    if ratio > 0.3:
        factores.append({"factor": "Nivel de endeudamiento alto", "impacto": "negativo"})
    elif ratio < 0.1:
        factores.append({"factor": "Bajo nivel de endeudamiento", "impacto": "positivo"})

    antiguedad = datos.get("antiguedad_laboral_meses", 0)
    if antiguedad >= 24:
        factores.append({"factor": "Buena antiguedad laboral", "impacto": "positivo"})
    else:
        factores.append({"factor": "Poca antiguedad laboral", "impacto": "negativo"})

    ingreso = datos.get("ingreso_mensual", 0)
    if ingreso >= 3000:
        factores.append({"factor": "Ingreso mensual estable", "impacto": "positivo"})
    else:
        factores.append({"factor": "Ingreso mensual bajo", "impacto": "negativo"})

    return factores


def _recomendaciones(categoria: str, datos: dict) -> list:
    recs = []

    if categoria == "alto":
        recs.append("Reduce tu nivel de endeudamiento antes de solicitar un nuevo credito.")
        recs.append("Mantente al dia con tus pagos durante los proximos 6 meses.")
        recs.append("Considera aumentar tus ingresos o reducir gastos fijos.")
    elif categoria == "medio":
        recs.append("Tu perfil es aceptable, pero reducir tus deudas mejoraria tu score.")
        recs.append("Mantener un historial de pagos limpio mejorara tu perfil con el tiempo.")
    else:
        recs.append("Tu perfil de riesgo es bajo, sigue manteniendo tus habitos financieros.")
        recs.append("Diversificar tus productos financieros puede fortalecer aun mas tu perfil.")

    if datos.get("dias_mora_historico", 0) > 0:
        recs.append("Regulariza tus deudas pendientes lo antes posible.")

    return recs