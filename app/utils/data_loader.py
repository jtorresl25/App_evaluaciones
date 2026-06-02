import pandas as pd
import streamlit as st

SHEET_GENERAL = "BASE_GENERAL_DOCENTE"
SHEET_PDF = "BASE_DETALLE_PDF"

REQUIRED_COLS_GENERAL = [
    "id_registro", "periodo", "anio", "semestre", "modelo_evaluacion",
    "escala_original", "nivel_analisis", "codigo_curso", "nombre_curso",
    "puntaje_profesor", "benchmark_universidad", "benchmark_facultad",
    "benchmark_departamento", "delta_vs_universidad", "delta_vs_facultad",
    "delta_vs_departamento", "estado_registro", "calidad_dato", "fuente",
]

REQUIRED_COLS_PDF = [
    "id_detalle", "periodo", "codigo_curso", "nombre_curso", "nivel_analisis",
    "aspecto", "puntaje", "confianza", "requiere_revision", "estado_revision",
]


def load_excel(uploaded_file) -> dict:
    """
    Reads BASE_GENERAL_DOCENTE and (optionally) BASE_DETALLE_PDF from an uploaded Excel file.
    Returns a dict with keys 'df_general' and 'df_pdf' (None if sheet missing).
    Raises RuntimeError with a user-friendly message on critical failures.
    """
    try:
        xl = pd.ExcelFile(uploaded_file)
    except Exception as exc:
        raise RuntimeError(f"No se pudo leer el archivo Excel: {exc}") from exc

    # ── BASE_GENERAL_DOCENTE ──────────────────────────────────────────────────
    if SHEET_GENERAL not in xl.sheet_names:
        available = ", ".join(xl.sheet_names)
        raise RuntimeError(
            f"No se encontró la hoja **{SHEET_GENERAL}** en el archivo. "
            f"Hojas disponibles: {available}"
        )

    df_general = xl.parse(SHEET_GENERAL)
    df_general.columns = [str(c).strip().lower().replace(" ", "_") for c in df_general.columns]

    missing = [c for c in REQUIRED_COLS_GENERAL if c not in df_general.columns]
    if missing:
        st.warning(
            f"Faltan las siguientes columnas en {SHEET_GENERAL}: "
            f"{', '.join(missing)}. Algunos indicadores pueden no calcularse."
        )

    # ── BASE_DETALLE_PDF ──────────────────────────────────────────────────────
    df_pdf = None
    if SHEET_PDF in xl.sheet_names:
        df_pdf = xl.parse(SHEET_PDF)
        df_pdf.columns = [str(c).strip().lower().replace(" ", "_") for c in df_pdf.columns]
        missing_pdf = [c for c in REQUIRED_COLS_PDF if c not in df_pdf.columns]
        if missing_pdf:
            st.info(
                f"Hoja {SHEET_PDF} cargada con columnas faltantes: "
                f"{', '.join(missing_pdf)}. Se mostrará con la información disponible."
            )

    return {"df_general": df_general, "df_pdf": df_pdf}
