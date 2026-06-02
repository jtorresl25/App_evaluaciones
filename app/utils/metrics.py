import pandas as pd
import numpy as np


def _pct_sobre_benchmark(df: pd.DataFrame, delta_col: str) -> float | None:
    """
    Porcentaje de registros (por periodo único) en que el delta es positivo.
    Usa registros donde el delta no es nulo.
    """
    if delta_col not in df.columns or df.empty:
        return None
    # Operar a nivel de periodo (un delta positivo por periodo cuenta una vez)
    if "periodo_label" in df.columns:
        por_periodo = (
            df.dropna(subset=[delta_col])
            .groupby("periodo_label")[delta_col]
            .mean()
        )
    else:
        por_periodo = df[delta_col].dropna()

    if por_periodo.empty:
        return None
    return round((por_periodo > 0).sum() / len(por_periodo) * 100, 1)


def _promedio_delta(df: pd.DataFrame, delta_col: str) -> float | None:
    if delta_col not in df.columns or df.empty:
        return None
    vals = df[delta_col].dropna()
    return round(vals.mean(), 3) if not vals.empty else None


def compute(subsets: dict, df_full: pd.DataFrame) -> dict:
    """
    Recibe subsets (output de build_subsets) y el df completo original.
    Retorna un dict con todas las métricas para la app.
    """
    df_validos = subsets.get("df_validos", pd.DataFrame())
    df_actual = subsets.get("df_modelo_actual", pd.DataFrame())
    df_anterior = subsets.get("df_modelo_anterior", pd.DataFrame())

    # ── Conteos globales ──────────────────────────────────────────────────────
    registros_sin_docencia = int(
        df_full["estado_registro"]
        .astype(str)
        .str.strip()
        .isin({"Sin docencia / No aplica"})
        .sum()
    ) if "estado_registro" in df_full.columns else 0

    registros_nc = int(
        df_full["estado_registro"]
        .astype(str)
        .str.strip()
        .isin({"NC / No calculado"})
        .sum()
    ) if "estado_registro" in df_full.columns else 0

    registros_validos = len(df_validos)

    cursos_unicos = (
        df_validos["codigo_curso"].nunique()
        if "codigo_curso" in df_validos.columns
        else df_validos["nombre_curso"].nunique()
        if "nombre_curso" in df_validos.columns
        else 0
    )

    # Periodos válidos por modelo
    if "periodo_label" in df_actual.columns:
        periodos_actual = df_actual["periodo_label"].nunique()
    else:
        periodos_actual = 0

    if "periodo_label" in df_anterior.columns:
        periodos_anterior = df_anterior["periodo_label"].nunique()
    else:
        periodos_anterior = 0

    total_periodos_validos = (
        df_validos["periodo_label"].nunique()
        if "periodo_label" in df_validos.columns
        else 0
    )

    # ── Porcentajes sobre benchmark ───────────────────────────────────────────
    pct_fac_actual = _pct_sobre_benchmark(df_actual, "delta_vs_facultad")
    pct_uni_actual = _pct_sobre_benchmark(df_actual, "delta_vs_universidad")
    pct_fac_anterior = _pct_sobre_benchmark(df_anterior, "delta_vs_facultad")
    pct_uni_anterior = _pct_sobre_benchmark(df_anterior, "delta_vs_universidad")

    # ── Promedios de delta ────────────────────────────────────────────────────
    avg_delta_fac_actual = _promedio_delta(df_actual, "delta_vs_facultad")
    avg_delta_uni_actual = _promedio_delta(df_actual, "delta_vs_universidad")
    avg_delta_fac_anterior = _promedio_delta(df_anterior, "delta_vs_facultad")
    avg_delta_uni_anterior = _promedio_delta(df_anterior, "delta_vs_universidad")

    # ── Puntaje promedio ──────────────────────────────────────────────────────
    prom_actual = (
        round(df_actual["puntaje_profesor"].mean(), 2)
        if not df_actual.empty and "puntaje_profesor" in df_actual.columns
        else None
    )
    prom_anterior = (
        round(df_anterior["puntaje_profesor"].mean(), 2)
        if not df_anterior.empty and "puntaje_profesor" in df_anterior.columns
        else None
    )

    # ── Escala del modelo actual ───────────────────────────────────────────────
    escala_actual = None
    if not df_actual.empty and "escala_original" in df_actual.columns:
        escala_actual = df_actual["escala_original"].dropna().iloc[0] if not df_actual["escala_original"].dropna().empty else None

    return {
        "total_periodos_validos": total_periodos_validos,
        "periodos_validos_modelo_actual": periodos_actual,
        "periodos_validos_modelo_anterior": periodos_anterior,
        "cursos_unicos": cursos_unicos,
        "registros_validos": registros_validos,
        "registros_sin_docencia": registros_sin_docencia,
        "registros_nc": registros_nc,
        "pct_sobre_facultad_actual": pct_fac_actual,
        "pct_sobre_universidad_actual": pct_uni_actual,
        "pct_sobre_facultad_anterior": pct_fac_anterior,
        "pct_sobre_universidad_anterior": pct_uni_anterior,
        "avg_delta_facultad_actual": avg_delta_fac_actual,
        "avg_delta_universidad_actual": avg_delta_uni_actual,
        "avg_delta_facultad_anterior": avg_delta_fac_anterior,
        "avg_delta_universidad_anterior": avg_delta_uni_anterior,
        "prom_puntaje_actual": prom_actual,
        "prom_puntaje_anterior": prom_anterior,
        "escala_actual": escala_actual,
        "label_actual": subsets.get("label_actual"),
        "label_anterior": subsets.get("label_anterior"),
    }
