import pandas as pd
import numpy as np

EXCLUIR_ESTADO = {"Sin docencia / No aplica", "NC / No calculado"}

# Patrones de nivel agregado (substring, case-insensitive)
_AGG_NIVEL_PATTERN = "agregado|global|total general|promedio general"
# Códigos de curso que indican registro agregado
_AGG_CODIGOS = {"agregado", "total", "global", "agg", "promedio"}


# ── Helpers de periodo ────────────────────────────────────────────────────────

def _sem_to_int(semestre_val) -> int:
    """
    Convierte un valor de semestre a entero ordenable.
    - 1, "1" → 1
    - 2, "2" → 2
    - "V", "v", "Verano" → 5  (verano, entre 2 y siguiente año)
    - 10 → 1, 20 → 2 (formatos YYYYSS)
    - Cualquier otro → 9 (último dentro del año)
    """
    s = str(semestre_val).strip().upper()
    if s in ("1", "1.0"):    return 1
    if s in ("2", "2.0"):    return 2
    if s in ("10",):         return 1
    if s in ("20",):         return 2
    if s in ("V", "VERANO"): return 5
    try:
        n = int(float(s))
        return n if 1 <= n <= 9 else 9
    except (ValueError, TypeError):
        return 9


def _build_periodo_cols(df: pd.DataFrame) -> pd.DataFrame:
    """
    Crea / sobreescribe las columnas:
      - periodo_label  (str)  "YYYY-S"   — se usa como etiqueta categórica en gráficos
      - periodo_order  (int)  YYYY * 10 + sem_int — para ordenación cronológica correcta

    Fuente prioritaria: columnas anio + semestre si existen.
    Fallback: parsear columna periodo.
    """
    if "anio" in df.columns and "semestre" in df.columns:
        anio_num = pd.to_numeric(df["anio"], errors="coerce")
        sem_int  = df["semestre"].apply(_sem_to_int)
        df["periodo_label"] = (
            anio_num.fillna(0).astype(int).astype(str)
            + "-"
            + df["semestre"].astype(str).str.strip()
        )
        df["periodo_order"] = (anio_num * 10 + sem_int).astype("Int64")

    elif "periodo" in df.columns:
        def _parse(p):
            s = str(p).strip()
            if "-" in s:
                parts = s.split("-", 1)
                if len(parts) == 2:
                    try:
                        anio = int(parts[0])
                        sem  = _sem_to_int(parts[1])
                        return s, anio * 10 + sem
                    except ValueError:
                        pass
            return s, 0

        parsed = df["periodo"].apply(_parse)
        df["periodo_label"] = parsed.apply(lambda x: x[0])
        df["periodo_order"] = parsed.apply(lambda x: x[1]).astype("Int64")

    else:
        df["periodo_label"] = df.index.astype(str)
        df["periodo_order"] = pd.array([0] * len(df), dtype="Int64")

    return df


# ── Filtros públicos reutilizables ────────────────────────────────────────────

def filter_period_aggregates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Retorna solo registros de nivel AGREGADO de periodo.
    Estos son los registros apropiados para gráficos de benchmark y delta general.
    Si no se encuentra ninguno, retorna el df completo como fallback.
    """
    if df.empty:
        return df

    mask = pd.Series(False, index=df.index)

    if "nivel_analisis" in df.columns:
        nivel_low = df["nivel_analisis"].astype(str).str.strip().str.lower()
        mask |= nivel_low.str.contains(_AGG_NIVEL_PATTERN, na=False, regex=True)

    if "codigo_curso" in df.columns:
        codigo_low = df["codigo_curso"].astype(str).str.strip().str.lower()
        mask |= codigo_low.isin(_AGG_CODIGOS)

    result = df[mask].copy()
    return result if not result.empty else df.copy()


def filter_course_details(df: pd.DataFrame) -> pd.DataFrame:
    """Retorna solo cursos individuales (excluye registros agregados)."""
    mask = _mask_individual(df)
    return df[mask].copy()


# ── Pipeline principal ────────────────────────────────────────────────────────

def _to_numeric(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _fill_deltas(df: pd.DataFrame) -> pd.DataFrame:
    pairs = [
        ("delta_vs_facultad",     "puntaje_profesor", "benchmark_facultad"),
        ("delta_vs_universidad",  "puntaje_profesor", "benchmark_universidad"),
        ("delta_vs_departamento", "puntaje_profesor", "benchmark_departamento"),
    ]
    for delta_col, p_col, b_col in pairs:
        if all(c in df.columns for c in [delta_col, p_col, b_col]):
            mask = df[delta_col].isna() & df[p_col].notna() & df[b_col].notna()
            df.loc[mask, delta_col] = df.loc[mask, p_col] - df.loc[mask, b_col]
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Pipeline completo de limpieza para BASE_GENERAL_DOCENTE."""
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

    numeric_cols = [
        "puntaje_profesor", "benchmark_universidad", "benchmark_facultad",
        "benchmark_departamento", "delta_vs_universidad", "delta_vs_facultad",
        "delta_vs_departamento",
    ]
    df = _to_numeric(df, numeric_cols)
    df = _fill_deltas(df)

    # Crear periodo_label y periodo_order de forma centralizada y robusta
    df = _build_periodo_cols(df)

    if "estado_registro" in df.columns:
        df["estado_registro"] = df["estado_registro"].astype(str).str.strip()
    else:
        df["estado_registro"] = ""

    df["es_valido_desempeno"] = (
        df["puntaje_profesor"].notna()
        & ~df["estado_registro"].isin(EXCLUIR_ESTADO)
    )

    if "modelo_evaluacion" in df.columns:
        df["modelo_evaluacion"] = df["modelo_evaluacion"].astype(str).str.strip()

    return df


def _mask_individual(df_validos: pd.DataFrame) -> pd.Series:
    """True = curso individual (no es registro agregado de periodo)."""
    mask = pd.Series(True, index=df_validos.index)

    if "nivel_analisis" in df_validos.columns:
        nivel_low = df_validos["nivel_analisis"].astype(str).str.strip().str.lower()
        mask &= ~nivel_low.str.contains(_AGG_NIVEL_PATTERN, na=False, regex=True)

    if "codigo_curso" in df_validos.columns:
        codigo_low = df_validos["codigo_curso"].astype(str).str.strip().str.lower()
        mask &= ~codigo_low.isin(_AGG_CODIGOS)

    return mask


def build_subsets(df: pd.DataFrame) -> dict:
    """Construye todos los subconjuntos necesarios para la app."""
    df_validos = df[df["es_valido_desempeno"]].copy()

    label_actual = None
    label_anterior = None
    if "modelo_evaluacion" in df.columns:
        for m in df["modelo_evaluacion"].dropna().unique():
            m_low = str(m).lower()
            if any(k in m_low for k in ("anterior", "previo", "antiguo", "/5", "old")):
                label_anterior = m
            else:
                label_actual = m

    def _subset_modelo(label):
        if label and "modelo_evaluacion" in df_validos.columns:
            return df_validos[df_validos["modelo_evaluacion"] == label].copy()
        return pd.DataFrame(columns=df.columns)

    df_modelo_actual   = _subset_modelo(label_actual)
    df_modelo_anterior = _subset_modelo(label_anterior)

    ind_mask = _mask_individual(df_validos)
    df_cursos_individuales = df_validos[ind_mask].copy()
    df_agregados_periodo   = df_validos[~ind_mask].copy()

    return {
        "df_validos":             df_validos,
        "df_modelo_actual":       df_modelo_actual,
        "df_modelo_anterior":     df_modelo_anterior,
        "df_cursos_individuales": df_cursos_individuales,
        "df_agregados_periodo":   df_agregados_periodo,
        "label_actual":           label_actual,
        "label_anterior":         label_anterior,
    }


# ── Helpers para BASE_DETALLE_PDF ────────────────────────────────────────────

def _to_bool(series: pd.Series) -> pd.Series:
    """
    Convierte a booleano robusto desde: True/False, 'TRUE'/'FALSE',
    'Verdadero'/'Falso', 'SÍ'/'NO', 1/0, y sus variantes.
    Valores nulos → False.
    """
    if series.dtype == bool:
        return series

    def _cvt(val):
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return False
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return bool(val)
        v = str(val).strip().upper()
        return v in ("TRUE", "VERDADERO", "SI", "SÍ", "YES", "1", "V", "CIERTO")

    return series.apply(_cvt)


def _normalize_pdf_old_to_new(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remapea el esquema antiguo de BASE_DETALLE_PDF al nuevo.
    Crea columnas derivadas que no existían en el esquema anterior.
    Solo actúa si se detectan columnas del esquema antiguo.
    """
    # Renombrar columnas antiguas → nuevas (solo si la nueva no existe ya)
    _REMAP = {
        "id_detalle":    "id_pdf",
        "periodo":       "periodo_label",
        "codigo_curso":  "curso_codigo_base",
        "nombre_curso":  "curso_nombre_normalizado",
        "nivel_analisis":"ambito",
        "puntaje":       "valor_central",
        "serie":         "nivel_comparacion",
        "confianza":     "confianza_extraccion",
    }
    for old, new in _REMAP.items():
        if old in df.columns and new not in df.columns:
            df = df.rename(columns={old: new})

    # Derivar periodo_id si falta
    if "periodo_label" in df.columns and "periodo_id" not in df.columns:
        def _pid(lbl):
            parts = str(lbl).split("-")
            if len(parts) == 2:
                try:
                    y = int(parts[0])
                    s = parts[1].strip().upper()
                    sm = 10 if s == "1" else (20 if s == "2" else 0)
                    return y * 100 + sm
                except ValueError:
                    pass
            return None
        df["periodo_id"] = df["periodo_label"].apply(_pid)

    # Derivar anio / semestre si faltan
    if "periodo_label" in df.columns:
        if "anio" not in df.columns:
            df["anio"] = df["periodo_label"].apply(
                lambda x: int(str(x).split("-")[0]) if "-" in str(x) else None
            )
        if "semestre" not in df.columns:
            df["semestre"] = df["periodo_label"].apply(
                lambda x: str(x).split("-")[1].strip() if "-" in str(x) else None
            )

    # Derivar es_resumen_semestre_ponderado
    if "es_resumen_semestre_ponderado" not in df.columns:
        if "aspecto" in df.columns and "nivel_comparacion" in df.columns:
            _niveles = {"Profesor", "Facultad", "Universidad"}
            mask = (
                df["aspecto"].astype(str).str.lower().str.strip() == "puntaje global"
            ) & (
                df["nivel_comparacion"].isin(_niveles)
            )
            if "curso_codigo_base" in df.columns:
                mask &= df["curso_codigo_base"].isna()
            df["es_resumen_semestre_ponderado"] = mask
        else:
            df["es_resumen_semestre_ponderado"] = False

    # Derivar tiene_puntaje_calculado
    if "tiene_puntaje_calculado" not in df.columns:
        if "valor_central" in df.columns:
            nc_mask = pd.Series(False, index=df.index)
            if "estado_calculo" in df.columns:
                nc_mask = df["estado_calculo"].astype(str).str.upper() == "NC"
            df["tiene_puntaje_calculado"] = df["valor_central"].notna() & ~nc_mask
        else:
            df["tiene_puntaje_calculado"] = False

    # estado_calculo: si no existe, derivar de estado_revision (esquema antiguo)
    if "estado_calculo" not in df.columns and "estado_revision" in df.columns:
        df["estado_calculo"] = df["estado_revision"]

    return df


def clean_pdf(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpieza completa de BASE_DETALLE_PDF.
    Acepta tanto el nuevo esquema (v2) como el antiguo.
    """
    if df is None:
        return None
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

    # Detectar y normalizar esquema antiguo
    _old_markers = {"id_detalle", "puntaje", "estado_revision"}
    _new_markers = {"valor_central", "nivel_comparacion", "es_resumen_semestre_ponderado"}
    if (_old_markers & set(df.columns)) and not (_new_markers & set(df.columns)):
        df = _normalize_pdf_old_to_new(df)

    # Columnas numéricas
    for col in ("valor_central", "inscritos", "evaluaciones",
                "limite_inferior", "limite_superior"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Columnas booleanas — manejo robusto de TRUE/FALSE/1/0/texto
    for col in ("es_resumen_semestre_ponderado",
                "tiene_puntaje_calculado",
                "requiere_revision"):
        if col in df.columns:
            df[col] = _to_bool(df[col])

    # periodo_label asegurado como string limpio
    if "periodo_label" in df.columns:
        df["periodo_label"] = df["periodo_label"].astype(str).str.strip()
    elif "periodo" in df.columns:
        df["periodo_label"] = df["periodo"].astype(str).str.strip()

    # periodo_order para ordenación cronológica
    if "periodo_label" in df.columns and "periodo_order" not in df.columns:
        df = _build_periodo_cols(df)

    return df
