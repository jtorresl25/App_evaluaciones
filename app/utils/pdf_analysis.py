"""
Funciones de análisis para BASE_DETALLE (antes BASE_DETALLE_PDF).
No mezclan datos con BASE_GENERAL_DOCENTE ni alimentan KPIs principales.
Los datos pueden provenir de PDFs, carga manual o consolidaciones futuras.
"""
from __future__ import annotations
import pandas as pd
import numpy as np

# Niveles de comparación que representan al profesor y los benchmarks
_NIVELES_RESUMEN  = {"Profesor", "Facultad", "Universidad"}
_ASPECTO_GLOBAL   = "puntaje global"


# ── Filtros base ──────────────────────────────────────────────────────────────

def _resumen_semestral(df: pd.DataFrame) -> pd.DataFrame:
    """Registros de resumen semestral ponderado (nivel comparable)."""
    if df is None or df.empty:
        return pd.DataFrame()
    if "es_resumen_semestre_ponderado" not in df.columns:
        return pd.DataFrame()
    mask = df["es_resumen_semestre_ponderado"] == True
    return df[mask].copy()


def _sort_periodos(df: pd.DataFrame) -> pd.DataFrame:
    if "periodo_order" in df.columns:
        return df.sort_values("periodo_order")
    if "periodo_label" in df.columns:
        return df.sort_values("periodo_label")
    return df


# ── Métricas KPI ──────────────────────────────────────────────────────────────

def compute_pdf_metrics(df: pd.DataFrame) -> dict:
    """
    Calcula KPIs desde BASE_DETALLE.
    Retorna dict con todos los indicadores para la sección de detalle.
    """
    empty = {
        "periodos_pdf": 0, "cursos_unicos_pdf": 0,
        "cursos_con_puntaje": 0, "cursos_nc": 0,
        "resumenes_semestrales": 0, "registros_a_revisar": 0,
        "ultimo_periodo": None, "puntaje_profesor_ultimo": None,
        "delta_facultad_ultimo": None, "delta_universidad_ultimo": None,
    }
    if df is None or df.empty:
        return empty

    # Periodos únicos
    periodos_pdf = (
        df["periodo_label"].nunique() if "periodo_label" in df.columns else 0
    )

    # Cursos únicos (excluir NaN que corresponden a registros de resumen global)
    cursos_unicos_pdf = 0
    if "curso_codigo_base" in df.columns:
        cursos_unicos_pdf = df["curso_codigo_base"].dropna().nunique()

    # Cursos con puntaje calculado
    cursos_con_puntaje = 0
    if "tiene_puntaje_calculado" in df.columns and "curso_codigo_base" in df.columns:
        mask_t = df["tiene_puntaje_calculado"] == True
        cursos_con_puntaje = df[mask_t]["curso_codigo_base"].dropna().nunique()

    # Cursos NC
    cursos_nc = 0
    if "estado_calculo" in df.columns and "curso_codigo_base" in df.columns:
        mask_nc = df["estado_calculo"].astype(str).str.strip().str.upper() == "NC"
        cursos_nc = df[mask_nc]["curso_codigo_base"].dropna().nunique()

    # Resúmenes semestrales (nivel global ponderado)
    resumenes_semestrales = 0
    if "es_resumen_semestre_ponderado" in df.columns:
        resumenes_semestrales = int((df["es_resumen_semestre_ponderado"] == True).sum())

    # Registros que requieren revisión
    registros_a_revisar = 0
    if "requiere_revision" in df.columns:
        registros_a_revisar = int((df["requiere_revision"] == True).sum())

    # Último periodo y puntajes
    ultimo_periodo         = None
    puntaje_prof_ultimo    = None
    delta_fac_ultimo       = None
    delta_uni_ultimo       = None

    df_res = _resumen_semestral(df)
    if not df_res.empty:
        df_res = _sort_periodos(df_res)
        ultimo_periodo = df_res["periodo_label"].iloc[-1]

        df_last = df_res[df_res["periodo_label"] == ultimo_periodo]
        if "nivel_comparacion" in df_last.columns and "valor_central" in df_last.columns:
            def _avg(nivel):
                vals = df_last.loc[
                    df_last["nivel_comparacion"] == nivel, "valor_central"
                ].dropna()
                return float(vals.mean()) if not vals.empty else None

            prof = _avg("Profesor")
            fac  = _avg("Facultad")
            uni  = _avg("Universidad")

            if prof is not None:
                puntaje_prof_ultimo = round(prof, 1)
            if prof is not None and fac is not None:
                delta_fac_ultimo = round(prof - fac, 1)
            if prof is not None and uni is not None:
                delta_uni_ultimo = round(prof - uni, 1)

    return {
        "periodos_pdf":           periodos_pdf,
        "cursos_unicos_pdf":      cursos_unicos_pdf,
        "cursos_con_puntaje":     cursos_con_puntaje,
        "cursos_nc":              cursos_nc,
        "resumenes_semestrales":  resumenes_semestrales,
        "registros_a_revisar":    registros_a_revisar,
        "ultimo_periodo":         ultimo_periodo,
        "puntaje_profesor_ultimo": puntaje_prof_ultimo,
        "delta_facultad_ultimo":  delta_fac_ultimo,
        "delta_universidad_ultimo": delta_uni_ultimo,
    }


# ── Data para gráficos ────────────────────────────────────────────────────────

def get_resumen_profesor(df: pd.DataFrame) -> pd.DataFrame:
    """
    Retorna serie semestral del profesor (puntaje global ponderado).
    Fuente: es_resumen_semestre_ponderado=True, nivel_comparacion='Profesor',
            aspecto='Puntaje global'.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    df_res = _resumen_semestral(df)
    if df_res.empty:
        return pd.DataFrame()

    if "nivel_comparacion" not in df_res.columns or "aspecto" not in df_res.columns:
        return pd.DataFrame()

    mask = (
        (df_res["nivel_comparacion"] == "Profesor") &
        (df_res["aspecto"].astype(str).str.strip().str.lower() == _ASPECTO_GLOBAL)
    )
    result = df_res[mask].copy()
    return _sort_periodos(result)


def get_resumen_comparacion(df: pd.DataFrame) -> pd.DataFrame:
    """
    Retorna serie semestral de Profesor + Facultad + Universidad (puntaje global).
    Para gráfico de comparación de benchmarks.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    df_res = _resumen_semestral(df)
    if df_res.empty:
        return pd.DataFrame()

    if "nivel_comparacion" not in df_res.columns or "aspecto" not in df_res.columns:
        return pd.DataFrame()

    mask = (
        df_res["nivel_comparacion"].isin(_NIVELES_RESUMEN) &
        (df_res["aspecto"].astype(str).str.strip().str.lower() == _ASPECTO_GLOBAL)
    )
    result = df_res[mask].copy()
    return _sort_periodos(result)


def get_cursos_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tabla resumen de cursos individuales:
    - Periodos dictado
    - Periodos con puntaje
    - Periodos NC
    - Promedio valor_central del Profesor
    - Último periodo disponible
    """
    if df is None or df.empty:
        return pd.DataFrame()

    # Solo registros de curso individual (tiene curso_codigo_base)
    if "curso_codigo_base" not in df.columns:
        return pd.DataFrame()

    df_c = df[df["curso_codigo_base"].notna()].copy()
    if df_c.empty:
        return pd.DataFrame()

    nombre_col = (
        "curso_nombre_normalizado" if "curso_nombre_normalizado" in df_c.columns
        else "curso_nombre_original" if "curso_nombre_original" in df_c.columns
        else "curso_codigo_base"
    )

    # Periodos únicos por curso (nivel Profesor, solo una fila por periodo)
    df_prof = df_c.copy()
    if "nivel_comparacion" in df_prof.columns:
        df_prof = df_prof[df_prof["nivel_comparacion"].isin(
            {"Profesor", "Profesor curso"}
        )]

    grp = df_c.groupby(["curso_codigo_base", nombre_col])

    rows = []
    for (codigo, nombre), g in grp:
        periodos_total = g["periodo_label"].nunique() if "periodo_label" in g.columns else 0

        periodos_con_puntaje = 0
        if "tiene_puntaje_calculado" in g.columns:
            periodos_con_puntaje = int(
                g[g["tiene_puntaje_calculado"] == True]["periodo_label"].nunique()
            ) if "periodo_label" in g.columns else 0

        periodos_nc = 0
        if "estado_calculo" in g.columns:
            periodos_nc = int(
                g[g["estado_calculo"].astype(str).str.upper() == "NC"]["periodo_label"].nunique()
            ) if "periodo_label" in g.columns else 0

        # Promedio solo con puntaje válido
        promedio = None
        if "valor_central" in g.columns and "tiene_puntaje_calculado" in g.columns:
            vals = g.loc[g["tiene_puntaje_calculado"] == True, "valor_central"].dropna()
            if not vals.empty:
                promedio = round(vals.mean(), 2)

        ultimo = None
        if "periodo_label" in g.columns:
            if "periodo_order" in g.columns:
                ultimo = g.sort_values("periodo_order")["periodo_label"].iloc[-1]
            else:
                ultimo = g.sort_values("periodo_label")["periodo_label"].iloc[-1]

        rows.append({
            "Código":              codigo,
            "Curso":               nombre,
            "Periodos":            periodos_total,
            "Con puntaje":         periodos_con_puntaje,
            "NC":                  periodos_nc,
            "Promedio (Profesor)": promedio,
            "Último periodo":      ultimo,
        })

    result = pd.DataFrame(rows)
    if not result.empty:
        result = result.sort_values("Promedio (Profesor)", ascending=False, na_position="last")
    return result
