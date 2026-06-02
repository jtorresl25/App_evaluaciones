import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ── Paleta ────────────────────────────────────────────────────────────────────
C_PROFESOR     = "#5AD7E8"
C_FACULTAD     = "#D6B36A"
C_UNIVERSIDAD  = "#9CC7D5"
C_DEPARTAMENTO = "#6FCF97"
C_DELTA_POS    = "#6FCF97"
C_DELTA_NEG    = "#E26D5A"

_C_BG        = "rgba(0,0,0,0)"
_C_TEXT      = "#9DC8D4"
_C_GRID      = "rgba(255,255,255,0.07)"
_C_ZERO      = "rgba(255,255,255,0.18)"
_C_AXIS      = "#1A3D4E"
_C_HOVER_BG  = "#0A1E2A"
_C_HOVER_BOR = "#245970"
_C_LEG       = "#C0D8E0"

_XAXIS_DEF = dict(
    showgrid=False, zeroline=False,
    tickfont=dict(size=12, color=_C_TEXT),
    linecolor=_C_AXIS, linewidth=1,
)
_YAXIS_DEF = dict(
    showgrid=True, gridcolor=_C_GRID,
    zeroline=False,
    tickfont=dict(size=12, color=_C_TEXT),
    linecolor="rgba(0,0,0,0)",
)

_LAYOUT_BASE = dict(
    paper_bgcolor=_C_BG,
    plot_bgcolor=_C_BG,
    font=dict(family="IBM Plex Sans, system-ui, sans-serif", color=_C_TEXT, size=13),
    legend=dict(
        orientation="h",
        yanchor="bottom", y=1.04,
        xanchor="left", x=0,
        bgcolor="rgba(0,0,0,0)",
        font=dict(size=13, color=_C_LEG),
        borderwidth=0,
    ),
    hoverlabel=dict(
        bgcolor=_C_HOVER_BG,
        bordercolor=_C_HOVER_BOR,
        font=dict(color="#E8F4F7", size=13,
                  family="IBM Plex Sans, system-ui, sans-serif"),
        namelength=-1,
    ),
)

# ── Patrones para detectar registros agregados de periodo ─────────────────────
_AGG_NIVEL_PAT = "agregado|periodo-agregado"
_AGG_CODIGOS   = {"agregado", "total"}


# ── Helpers internos ──────────────────────────────────────────────────────────

def _apply_layout(fig, *, height=460, xaxis=None, yaxis=None,
                  barmode=None, bargap=None, bargroupgap=None):
    """Aplica layout base oscuro + overrides sin duplicar claves."""
    layout = dict(_LAYOUT_BASE)
    layout["height"] = height
    layout["margin"] = dict(l=12, r=24, t=30, b=58)
    layout["xaxis"] = {**_XAXIS_DEF, **(xaxis or {})}
    layout["yaxis"] = {**_YAXIS_DEF, **(yaxis or {})}
    if barmode:
        layout["barmode"] = barmode
    if bargap is not None:
        layout["bargap"] = bargap
    if bargroupgap is not None:
        layout["bargroupgap"] = bargroupgap
    fig.update_layout(**layout)
    return fig


def _to_period_agg(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filtra a registros de nivel AGREGADO de periodo.
    Para gráficos de benchmark / delta: excluye cursos individuales.
    Retorna el df completo como fallback si no hay agregados.
    """
    if df.empty:
        return df
    mask = pd.Series(False, index=df.index)
    if "nivel_analisis" in df.columns:
        mask |= df["nivel_analisis"].astype(str).str.strip().str.lower() \
                  .str.contains(_AGG_NIVEL_PAT, na=False)
    if "codigo_curso" in df.columns:
        mask |= df["codigo_curso"].astype(str).str.strip().str.lower() \
                  .isin(_AGG_CODIGOS)
    result = df[mask]
    return result.copy() if not result.empty else df.copy()


def _sort_by_order(df: pd.DataFrame) -> pd.DataFrame:
    """Ordena cronológicamente usando periodo_order si existe."""
    if "periodo_order" in df.columns:
        return df.sort_values("periodo_order")
    if "periodo_label" in df.columns:
        return df.sort_values("periodo_label")
    return df


def _agg_por_periodo(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """
    Agrupa por periodo_label (y periodo_order si existe), calcula media.
    Retorna ordenado cronológicamente.
    """
    if df.empty or col not in df.columns or "periodo_label" not in df.columns:
        return pd.DataFrame(columns=["periodo_label", col])

    if "periodo_order" in df.columns:
        grp = df.groupby(
            ["periodo_order", "periodo_label"], sort=False
        )[col].mean().reset_index()
        return grp.sort_values("periodo_order")
    else:
        grp = df.groupby("periodo_label", sort=False)[col].mean().reset_index()
        return grp.sort_values("periodo_label")


def _categorical_x(fig: go.Figure, periods: list) -> go.Figure:
    """
    Fuerza el eje X a categorías con orden explícito.
    CRÍTICO: evita que Plotly interprete "2011-1" como "enero 2011".
    """
    fig.update_xaxes(
        type="category",
        categoryorder="array",
        categoryarray=periods,
    )
    return fig


def _hline_zero(fig: go.Figure) -> None:
    fig.add_hline(y=0, line_color=_C_ZERO, line_width=1.5, line_dash="dot")


def _empty_fig(msg: str, height: int = 280) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=msg, xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=13, color="#537F8A"),
    )
    _apply_layout(fig, height=height)
    return fig


# ── 1. Modelo actual — Línea ──────────────────────────────────────────────────
def plot_modelo_actual_line(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return _empty_fig("Sin datos para el modelo actual")

    # Filtrar a agregados de periodo y ordenar cronológicamente
    df_plot = _sort_by_order(_to_period_agg(df))
    fig = go.Figure()

    def _trace(col, color, name, dash="solid", width=2.5, size=7):
        serie = _agg_por_periodo(df_plot, col)
        if serie.empty:
            return
        is_prof = (name == "Profesor")
        fig.add_trace(go.Scatter(
            x=serie["periodo_label"], y=serie[col],
            mode="lines+markers", name=name,
            line=dict(color=color, width=width, dash=dash,
                      shape="spline", smoothing=0.85),
            marker=dict(size=size, color=color,
                        line=dict(width=2.5 if is_prof else 1.5,
                                  color="#081C24")),
            hovertemplate=(
                f"<b>{name}</b><br>Periodo: %{{x}}<br>"
                f"Puntaje: %{{y:.2f}}<extra></extra>"
            ),
        ))

    _trace("puntaje_profesor",       C_PROFESOR,     "Profesor",     width=4,   size=9)
    _trace("benchmark_facultad",     C_FACULTAD,     "Facultad",     dash="dash",    width=2.5, size=7)
    _trace("benchmark_universidad",  C_UNIVERSIDAD,  "Universidad",  dash="dot",     width=2.5, size=7)
    _trace("benchmark_departamento", C_DEPARTAMENTO, "Departamento", dash="dashdot", width=2,   size=6)

    _apply_layout(fig, height=460)

    # Eje X categórico — previene interpretación como fecha
    periodos = df_plot["periodo_label"].drop_duplicates().tolist()
    _categorical_x(fig, periodos)
    return fig


# ── 2. Modelo actual — Deltas ─────────────────────────────────────────────────
def plot_modelo_actual_delta(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return _empty_fig("Sin datos de delta para el modelo actual")

    # Solo agregados de periodo; ordenar cronológicamente
    df_agg = _sort_by_order(_to_period_agg(df))
    fig = go.Figure()

    def _delta_trace(col, name, c_pos, opacity=0.92):
        serie = _agg_por_periodo(df_agg, col)
        if serie.empty:
            return
        serie = serie.dropna(subset=[col])
        if serie.empty:
            return
        # Color por benchmark (positivo) o rojo (negativo) — coherente con gráfico de líneas
        colors = [c_pos if v >= 0 else C_DELTA_NEG for v in serie[col]]
        fig.add_trace(go.Bar(
            x=serie["periodo_label"], y=serie[col],
            name=name, marker_color=colors,
            marker_line_color="rgba(0,0,0,0)",
            opacity=opacity,
            hovertemplate=(
                f"<b>{name}</b><br>"
                f"Periodo: %{{x}}<br>"
                f"Δ: %{{y:+.2f}} pts<extra></extra>"
            ),
        ))

    # Colores coherentes con gráfico de líneas:
    # Facultad → dorado  |  Universidad → azul claro
    _delta_trace("delta_vs_facultad",    "Δ vs Facultad",    c_pos=C_FACULTAD,    opacity=0.92)
    _delta_trace("delta_vs_universidad", "Δ vs Universidad", c_pos=C_UNIVERSIDAD, opacity=0.88)
    _hline_zero(fig)

    _apply_layout(fig, height=430, barmode="group", bargap=0.12, bargroupgap=0.04)

    periodos = df_agg["periodo_label"].drop_duplicates().tolist()
    _categorical_x(fig, periodos)
    return fig


# ── 3. Modelo anterior — Línea ────────────────────────────────────────────────
def plot_modelo_anterior_line(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return _empty_fig("Sin datos para el modelo anterior")

    df_plot = _sort_by_order(_to_period_agg(df))
    fig = go.Figure()

    def _trace(col, color, name, dash="solid", width=2.5, size=7):
        serie = _agg_por_periodo(df_plot, col)
        if serie.empty:
            return
        is_prof = (name == "Profesor")
        fig.add_trace(go.Scatter(
            x=serie["periodo_label"], y=serie[col],
            mode="lines+markers", name=name, opacity=0.92,
            line=dict(color=color, width=width, dash=dash,
                      shape="spline", smoothing=0.85),
            marker=dict(size=size, color=color,
                        line=dict(width=2 if is_prof else 1.5,
                                  color="#081C24")),
            hovertemplate=(
                f"<b>{name}</b><br>Periodo: %{{x}}<br>"
                f"Puntaje: %{{y:.2f}}<extra></extra>"
            ),
        ))

    _trace("puntaje_profesor",       C_PROFESOR,     "Profesor",     width=3.5, size=8)
    _trace("benchmark_facultad",     C_FACULTAD,     "Facultad",     dash="dash",    width=2.5, size=7)
    _trace("benchmark_universidad",  C_UNIVERSIDAD,  "Universidad",  dash="dot",     width=2.5, size=7)
    _trace("benchmark_departamento", C_DEPARTAMENTO, "Departamento", dash="dashdot", width=2,   size=6)

    _apply_layout(fig, height=460)

    periodos = df_plot["periodo_label"].drop_duplicates().tolist()
    _categorical_x(fig, periodos)
    return fig


# ── 4. Modelo anterior — Deltas ───────────────────────────────────────────────
def plot_modelo_anterior_delta(df: pd.DataFrame) -> go.Figure:
    """
    BUG FIX: usa SOLO registros Periodo-Agregado del modelo anterior.
    Los cursos individuales (2000-2010) no tienen benchmark comparable
    y distorsionaban el eje X con periodos irrelevantes.
    """
    if df.empty:
        return _empty_fig("Sin datos de delta para el modelo anterior")

    # CRÍTICO: filtrar a agregados ANTES de calcular deltas por periodo
    df_agg = _sort_by_order(_to_period_agg(df))
    fig = go.Figure()

    def _delta_trace(col, name, c_pos, opacity=0.88):
        serie = _agg_por_periodo(df_agg, col)
        if serie.empty:
            return
        serie = serie.dropna(subset=[col])
        if serie.empty:
            return
        colors = [c_pos if v >= 0 else C_DELTA_NEG for v in serie[col]]
        fig.add_trace(go.Bar(
            x=serie["periodo_label"], y=serie[col],
            name=name, marker_color=colors,
            marker_line_color="rgba(0,0,0,0)",
            opacity=opacity,
            hovertemplate=(
                f"<b>{name}</b><br>"
                f"Periodo: %{{x}}<br>"
                f"Δ: %{{y:+.2f}} pts<extra></extra>"
            ),
        ))

    _delta_trace("delta_vs_facultad",    "Δ vs Facultad",    c_pos=C_FACULTAD,    opacity=0.88)
    _delta_trace("delta_vs_universidad", "Δ vs Universidad", c_pos=C_UNIVERSIDAD, opacity=0.84)
    _hline_zero(fig)

    _apply_layout(fig, height=430, barmode="group", bargap=0.12, bargroupgap=0.04)

    periodos = df_agg["periodo_label"].drop_duplicates().tolist()
    _categorical_x(fig, periodos)
    return fig


# ── 5. Comparación relativa ───────────────────────────────────────────────────
def plot_comparacion_relativa(metrics: dict) -> go.Figure:
    entries = [
        ("Anterior\nvs Facultad",    metrics.get("pct_sobre_facultad_anterior"),    "#537F8A"),
        ("Anterior\nvs Universidad", metrics.get("pct_sobre_universidad_anterior"), "#537F8A"),
        ("Actual\nvs Facultad",      metrics.get("pct_sobre_facultad_actual"),       C_PROFESOR),
        ("Actual\nvs Universidad",   metrics.get("pct_sobre_universidad_actual"),    C_PROFESOR),
    ]
    data = [(l, v, c) for l, v, c in entries if v is not None]
    if not data:
        return _empty_fig("Sin datos de comparación disponibles")

    lbls, vals, cols = zip(*data)

    fig = go.Figure(go.Bar(
        x=list(lbls), y=list(vals),
        marker_color=list(cols),
        marker_line_color="rgba(0,0,0,0)",
        text=[f"{v:.0f}%" for v in vals],
        textposition="outside",
        textfont=dict(color="#E8F4F7", size=14,
                      family="IBM Plex Sans, system-ui, sans-serif"),
        hovertemplate=(
            "<b>%{x}</b><br>%{y:.1f}% de periodos válidos sobre benchmark"
            "<extra></extra>"
        ),
    ))
    fig.add_hline(
        y=100, line_dash="dot", line_color=C_FACULTAD, line_width=1.5,
        annotation_text="100 %",
        annotation_font=dict(color=C_FACULTAD, size=12),
        annotation_position="top right",
    )

    _apply_layout(
        fig, height=420, bargap=0.28,
        yaxis=dict(range=[0, 120], ticksuffix="%",
                   tickfont=dict(color=_C_TEXT, size=12)),
    )
    return fig


# ── 6. Ranking de cursos ──────────────────────────────────────────────────────
def plot_cursos(df: pd.DataFrame, escala_label: str = "") -> go.Figure:
    if df.empty or "puntaje_profesor" not in df.columns:
        return _empty_fig("Sin datos de cursos individuales para este modelo")

    nombre_col = "nombre_curso" if "nombre_curso" in df.columns else "codigo_curso"
    ranking = (
        df.groupby(nombre_col)["puntaje_profesor"]
        .mean()
        .reset_index()
        .sort_values("puntaje_profesor", ascending=True)
        .tail(15)
    )

    max_v = ranking["puntaje_profesor"].max() or 1
    min_v = ranking["puntaje_profesor"].min() or 0
    rng   = max_v - min_v if max_v != min_v else 1

    colors = [
        f"rgba(90,215,232,{0.38 + 0.62 * ((v - min_v) / rng):.2f})"
        for v in ranking["puntaje_profesor"]
    ]

    def _trunc(s, n=44):
        s = str(s)
        return s if len(s) <= n else s[:n - 1] + "…"

    labels_y = [_trunc(n) for n in ranking[nombre_col]]

    fig = go.Figure(go.Bar(
        y=labels_y,
        x=ranking["puntaje_profesor"],
        orientation="h",
        marker_color=colors,
        marker_line_color="rgba(0,0,0,0)",
        text=[f"  {v:.2f}" for v in ranking["puntaje_profesor"]],
        textposition="outside",
        textfont=dict(color="#E8F4F7", size=12,
                      family="IBM Plex Sans, system-ui, sans-serif"),
        hovertext=[str(n) for n in ranking[nombre_col]],
        hovertemplate=(
            "<b>%{hovertext}</b><br>Promedio: %{x:.2f}<extra></extra>"
        ),
    ))

    n_rows = max(len(ranking), 4)
    _apply_layout(
        fig,
        height=max(380, n_rows * 50),
        bargap=0.32,
        xaxis=dict(showgrid=True, gridcolor=_C_GRID,
                   tickfont=dict(color=_C_TEXT, size=12)),
        yaxis=dict(showgrid=False,
                   tickfont=dict(color="#C8E0E8", size=12)),
    )
    fig.update_layout(margin=dict(l=16, r=80, t=28, b=32))
    return fig
