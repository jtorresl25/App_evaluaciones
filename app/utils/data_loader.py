import pandas as pd
import streamlit as st

SHEET_GENERAL        = "BASE_GENERAL_DOCENTE"
SHEET_DETALLE        = "BASE_DETALLE"          # hoja oficial desde ahora
SHEET_DETALLE_LEGACY = "BASE_DETALLE_PDF"      # fallback: hoja anterior

# ── Columnas verdaderamente críticas (sin estas la app no puede calcular KPIs) ─
REQUIRED_COLS_GENERAL_CRITICAL = [
    "periodo", "modelo_evaluacion", "nivel_analisis", "codigo_curso",
    "nombre_curso", "puntaje_profesor", "benchmark_universidad",
    "benchmark_facultad", "estado_registro",
]
# Columnas opcionales: si no existen se crean vacías internamente sin avisar al usuario
REQUIRED_COLS_GENERAL_OPTIONAL = [
    "id_registro", "anio", "semestre", "escala_original", "benchmark_departamento",
    "delta_vs_universidad", "delta_vs_facultad", "delta_vs_departamento",
    "calidad_dato", "fuente", "nota",
]

# ── Columnas mínimas para mostrar BASE_DETALLE ────────────────────────────────
# Solo estas tres son necesarias para que la sección funcione
REQUIRED_COLS_DETALLE_MIN = [
    "aspecto", "nivel_comparacion", "valor_central",
]
# Marcadores que identifican inequívocamente el nuevo esquema v2
# (se usan para detección de esquema, no para validación de completitud)
_NEW_SCHEMA_MARKERS = frozenset({
    "valor_central", "nivel_comparacion", "es_resumen_semestre_ponderado",
    "id_pdf", "curso_codigo_base",
})
_OLD_SCHEMA_MARKERS = frozenset({"id_detalle", "puntaje", "estado_revision"})


def _detect_teacher_name(xl: pd.ExcelFile, df_general: pd.DataFrame) -> str | None:
    """
    Busca el nombre del docente en el archivo:
    1. Hoja CONFIG_APP → campo nombre_docente / docente / profesor
    2. Columna de BASE_GENERAL_DOCENTE → docente / profesor / nombre_docente
    Retorna None si no encuentra nada (el llamador usa el default).
    """
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
    Lee BASE_GENERAL_DOCENTE y (opcionalmente) BASE_DETALLE.
    Si BASE_DETALLE no existe pero sí BASE_DETALLE_PDF, usa esta última como
    fallback y muestra una advertencia suave.
    La app NO se rompe si la hoja de detalle no existe: simplemente la oculta.

    Retorna:
      {
        "df_general":     DataFrame,
        "df_detalle":     DataFrame | None,
        "detalle_schema": "new" | "old" | "unknown" | None,
        "teacher_name":   str | None,
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

    # Solo advertir si faltan columnas verdaderamente críticas para los KPIs
    missing_critical = [c for c in REQUIRED_COLS_GENERAL_CRITICAL if c not in df_general.columns]
    if missing_critical:
        st.warning(
            f"Faltan columnas en {SHEET_GENERAL}: {', '.join(missing_critical)}. "
            f"Algunos indicadores no se calcularán correctamente."
        )
    # Las columnas opcionales (fuente, nota, calidad_dato, delta, etc.) se crean
    # internamente en data_cleaning.clean() si no existen — sin mostrar mensaje.

    # ── BASE_DETALLE (con fallback silencioso a BASE_DETALLE_PDF) ────────────
    df_detalle     = None
    detalle_schema = None
    sheet_leida    = None

    if SHEET_DETALLE in xl.sheet_names:
        sheet_leida = SHEET_DETALLE
    elif SHEET_DETALLE_LEGACY in xl.sheet_names:
        sheet_leida = SHEET_DETALLE_LEGACY
        st.info(
            f"Se detectó la hoja antigua **{SHEET_DETALLE_LEGACY}**. "
            f"Se recomienda renombrarla a **{SHEET_DETALLE}**."
        )
    # Si ninguna existe, df_detalle queda en None → sección de detalle se oculta

    if sheet_leida:
        df_detalle = xl.parse(sheet_leida)
        df_detalle.columns = [
            str(c).strip().lower().replace(" ", "_") for c in df_detalle.columns
        ]
        cols = set(df_detalle.columns)

        if cols & _NEW_SCHEMA_MARKERS:
            detalle_schema = "new"
            # Advertir solo si faltan las columnas mínimas para mostrar datos
            missing_min = [c for c in REQUIRED_COLS_DETALLE_MIN if c not in cols]
            if missing_min:
                st.caption(
                    f"BASE_DETALLE fue cargada con campos incompletos "
                    f"({', '.join(missing_min)} no encontradas); "
                    f"se mostrarán los campos disponibles."
                )
            # Columnas opcionales (confianza_extraccion, requiere_revision, etc.)
            # se rellenan automáticamente en clean_detalle() — sin mostrar mensaje.
        elif cols & _OLD_SCHEMA_MARKERS:
            detalle_schema = "old"
            st.info(
                f"{sheet_leida} usa el esquema anterior. "
                "Se aplicará normalización automática para compatibilidad."
            )
        else:
            detalle_schema = "unknown"
            st.caption(
                f"{sheet_leida} tiene columnas no reconocidas. "
                "Se mostrará la información disponible."
            )

    # ── Nombre del docente ────────────────────────────────────────────────────
    teacher_name = _detect_teacher_name(xl, df_general)

    return {
        "df_general":     df_general,
        "df_detalle":     df_detalle,
        "detalle_schema": detalle_schema,
        "teacher_name":   teacher_name,
    }
