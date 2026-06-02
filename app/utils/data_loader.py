import pandas as pd
import streamlit as st

SHEET_GENERAL = "BASE_GENERAL_DOCENTE"
SHEET_PDF     = "BASE_DETALLE_PDF"

# ── Columnas obligatorias BASE_GENERAL_DOCENTE ────────────────────────────────
REQUIRED_COLS_GENERAL = [
    "id_registro", "periodo", "anio", "semestre", "modelo_evaluacion",
    "escala_original", "nivel_analisis", "codigo_curso", "nombre_curso",
    "puntaje_profesor", "benchmark_universidad", "benchmark_facultad",
    "benchmark_departamento", "delta_vs_universidad", "delta_vs_facultad",
    "delta_vs_departamento", "estado_registro", "calidad_dato", "fuente",
]

# ── Columnas críticas nuevo esquema BASE_DETALLE_PDF (v2) ────────────────────
# Si TODAS están presentes → nuevo esquema, sin warning.
REQUIRED_COLS_PDF_NEW_CRITICAL = [
    "periodo_label", "aspecto", "nivel_comparacion", "valor_central",
    "es_resumen_semestre_ponderado", "tiene_puntaje_calculado",
    "estado_calculo", "confianza_extraccion", "requiere_revision",
]
# Marcadores que identifican inequívocamente el nuevo esquema
_NEW_SCHEMA_MARKERS = frozenset({
    "valor_central", "nivel_comparacion", "es_resumen_semestre_ponderado",
    "id_pdf", "curso_codigo_base",
})
# Marcadores del esquema anterior
_OLD_SCHEMA_MARKERS = frozenset({"id_detalle", "puntaje", "estado_revision"})


def _detect_teacher_name(xl: pd.ExcelFile, df_general: pd.DataFrame) -> str | None:
    """
    Busca el nombre del docente en el archivo:
    1. Hoja CONFIG_APP → campo nombre_docente / docente / profesor
    2. Columna de BASE_GENERAL_DOCENTE → docente / profesor / nombre_docente
    Retorna None si no encuentra nada (el llamador usa el default).
    """
    # 1. CONFIG_APP
    if "CONFIG_APP" in xl.sheet_names:
        try:
            cfg = xl.parse("CONFIG_APP")
            cfg.columns = [str(c).strip().lower().replace(" ", "_") for c in cfg.columns]
            for col in ("nombre_docente", "docente", "profesor", "nombre"):
                if col in cfg.columns:
                    val = cfg[col].dropna()
                    if not val.empty:
                        s = str(val.iloc[0]).strip()
                        if s:
                            return s
        except Exception:
            pass

    # 2. BASE_GENERAL_DOCENTE
    if df_general is not None:
        for col in ("docente", "profesor", "nombre_docente", "nombre_profesor", "nombre"):
            if col in df_general.columns:
                val = df_general[col].dropna()
                if not val.empty:
                    s = str(val.iloc[0]).strip()
                    if s:
                        return s

    return None


def load_excel(uploaded_file) -> dict:
    """
    Lee BASE_GENERAL_DOCENTE y (opcionalmente) BASE_DETALLE_PDF.
    Retorna:
      {
        "df_general":   DataFrame,
        "df_pdf":       DataFrame | None,
        "pdf_schema":   "new" | "old" | "unknown" | None,
        "teacher_name": str | None,   # None si no se detecta en el archivo
      }
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
    df_general.columns = [
        str(c).strip().lower().replace(" ", "_") for c in df_general.columns
    ]

    missing_gen = [c for c in REQUIRED_COLS_GENERAL if c not in df_general.columns]
    if missing_gen:
        st.warning(
            f"Faltan columnas en {SHEET_GENERAL}: {', '.join(missing_gen)}. "
            f"Algunos indicadores pueden no calcularse."
        )

    # ── BASE_DETALLE_PDF ──────────────────────────────────────────────────────
    df_pdf      = None
    pdf_schema  = None

    if SHEET_PDF in xl.sheet_names:
        df_pdf = xl.parse(SHEET_PDF)
        df_pdf.columns = [
            str(c).strip().lower().replace(" ", "_") for c in df_pdf.columns
        ]
        cols = set(df_pdf.columns)

        if cols & _NEW_SCHEMA_MARKERS:
            pdf_schema = "new"
            # Solo alertar si faltan columnas CRÍTICAS del nuevo esquema
            missing_crit = [c for c in REQUIRED_COLS_PDF_NEW_CRITICAL if c not in cols]
            if missing_crit:
                st.warning(
                    f"BASE_DETALLE_PDF (nuevo esquema) no tiene columnas críticas: "
                    f"{', '.join(missing_crit)}. Revisa la hoja GUIA_ACTUALIZACION."
                )
            # Si todas las críticas están → no mostrar ningún mensaje

        elif cols & _OLD_SCHEMA_MARKERS:
            pdf_schema = "old"
            st.info(
                "BASE_DETALLE_PDF usa el esquema anterior. "
                "Se aplicará normalización automática para compatibilidad."
            )

        else:
            pdf_schema = "unknown"
            st.warning(
                "BASE_DETALLE_PDF tiene un esquema no reconocido. "
                "Se intentará mostrar la información disponible."
            )

    # ── Nombre del docente ────────────────────────────────────────────────────
    teacher_name = _detect_teacher_name(xl, df_general)

    return {
        "df_general":   df_general,
        "df_pdf":       df_pdf,
        "pdf_schema":   pdf_schema,
        "teacher_name": teacher_name,
    }
