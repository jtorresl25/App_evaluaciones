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


def _periodo_key(label: str) -> int:
    """
    Convierte un periodo_label en entero comparable para orden cronológico.
    Acepta: "2025-2" → 20252, "202520" → 202520, "20251" → 20251.
    Retorna 0 si no puede parsear (fallback seguro).
    """
    s = str(label).strip()
    if "-" in s:
        parts = s.split("-", 1)
        try:
            return int(parts[0]) * 100 + int(parts[1])
        except (ValueError, IndexError):
            pass
    try:
        return int(s)
    except ValueError:
        return 0


def _sorted_periodos(df: pd.DataFrame) -> list[str]:
    """
    Retorna lista de periodo_label únicos en orden cronológico.
    Usa periodo_order si existe (fuente canónica); sino parsea periodo_label.
    CRÍTICO: todas las trazas de un gráfico deben compartir este orden.
    """
    if df is None or df.empty or "periodo_label" not in df.columns:
        return []
    labels = df["periodo_label"].dropna().unique().tolist()
    if not labels:
        return []
    if "periodo_order" in df.columns:
        order_map = (
            df.dropna(subset=["periodo_label", "periodo_order"])
            .groupby("periodo_label")["periodo_order"]
            .min()
            .to_dict()
        )
        return sorted(labels, key=lambda p: order_map.get(p, 999_999))
    return sorted(labels, key=_periodo_key)


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


# ── 7. PDF — Tendencia semestral del Profesor ─────────────────────────────────
def plot_pdf_tendencia(df: pd.DataFrame) -> go.Figure:
    """
    Línea de evolución semestral del puntaje ponderado del Profesor.
    Fuente: get_resumen_profesor(df_pdf) desde pdf_analysis.
    df ya debe estar filtrado a nivel=Profesor, aspecto=Puntaje global,
    es_resumen_semestre_ponderado=True.
    """
    if df is None or df.empty or "valor_central" not in df.columns:
        return _empty_fig("Sin datos de tendencia del Profesor en PDF")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["periodo_label"], y=df["valor_central"],
        mode="lines+markers",
        name="Profesor (ponderado)",
        line=dict(color=C_PROFESOR, width=3.5, shape="spline", smoothing=0.85),
        marker=dict(size=9, color=C_PROFESOR,
                    line=dict(width=2.5, color="#081C24")),
        hovertemplate=(
            "<b>Profesor (ponderado)</b><br>"
            "Periodo: %{x}<br>"
            "Puntaje: %{y:.1f}<extra></extra>"
        ),
    ))

    _apply_layout(fig, height=380)

    periodos = df["periodo_label"].drop_duplicates().tolist()
    _categorical_x(fig, periodos)
    return fig


# ── 8. PDF — Comparación Profesor vs benchmarks por semestre ─────────────────
def plot_pdf_benchmarks(df: pd.DataFrame) -> go.Figure:
    """
    Líneas de Profesor / Facultad / Universidad por semestre desde PDF.
    df ya debe estar filtrado a es_resumen_semestre_ponderado=True,
    aspecto=Puntaje global, nivel_comparacion en [Profesor,Facultad,Universidad].
    """
    if df is None or df.empty or "nivel_comparacion" not in df.columns:
        return _empty_fig("Sin datos de comparación en PDF")

    fig = go.Figure()

    # Definición de series: (nivel, color, grosor, dash, tamaño marker)
    _series = [
        ("Profesor",    C_PROFESOR,    3.5, "solid",    9),
        ("Facultad",    C_FACULTAD,    2.5, "dash",     7),
        ("Universidad", C_UNIVERSIDAD, 2.5, "dot",      7),
    ]

    # Recopilar todos los periodos para el eje categórico
    all_periodos: list[str] = []

    for nivel, color, width, dash, msize in _series:
        sub = df[df["nivel_comparacion"] == nivel].copy()
        if sub.empty:
            continue
        if "periodo_order" in sub.columns:
            sub = sub.sort_values("periodo_order")
        elif "periodo_label" in sub.columns:
            sub = sub.sort_values("periodo_label")

        # Agregar por periodo (por si hay duplicados)
        if "periodo_order" in sub.columns:
            agg = (sub.groupby(["periodo_order", "periodo_label"], sort=False)
                   ["valor_central"].mean().reset_index()
                   .sort_values("periodo_order"))
        else:
            agg = (sub.groupby("periodo_label", sort=False)
                   ["valor_central"].mean().reset_index()
                   .sort_values("periodo_label"))

        if agg.empty:
            continue

        if not all_periodos:
            all_periodos = agg["periodo_label"].tolist()

        is_prof = (nivel == "Profesor")
        fig.add_trace(go.Scatter(
            x=agg["periodo_label"], y=agg["valor_central"],
            mode="lines+markers", name=nivel,
            line=dict(color=color, width=width, dash=dash,
                      shape="spline", smoothing=0.85),
            marker=dict(size=msize, color=color,
                        line=dict(width=2.5 if is_prof else 1.5,
                                  color="#081C24")),
            hovertemplate=(
                f"<b>{nivel}</b><br>"
                f"Periodo: %{{x}}<br>"
                f"Puntaje: %{{y:.1f}}<extra></extra>"
            ),
        ))

    _apply_layout(fig, height=400)
    if all_periodos:
        _categorical_x(fig, all_periodos)
    return fig


# ── Constantes para sección Desempeño Detallado ───────────────────────────────
# Orden preferido de aspectos (completos como vienen en la BD)
ASPECT_ORDER_PREF = [
    "Puntaje global",
    "Coherencia",
    "Fomento de autonomía",
    "Fomento de pensamiento crítico, discusión y participación",
    "Responsabilidades del profesor",
    "Retroalimentación, monitoreo y criterios de calificación",
    "Trato a estudiantes",
]
# Etiquetas cortas para ejes y radar
ASPECT_SHORT: dict[str, str] = {
    "Puntaje global": "Global",
    "Coherencia": "Coherencia",
    "Fomento de autonomía": "Autonomía",
    "Fomento de pensamiento crítico, discusión y participación": "Pensam. crítico",
    "Responsabilidades del profesor": "Responsabilidades",
    "Retroalimentación, monitoreo y criterios de calificación": "Retroalimentación",
    "Trato a estudiantes": "Trato",
}
# Colores para los niveles de comparación a nivel de curso individual
NIVEL_CURSO_COLORS: dict[str, str] = {
    "Profesor curso":   C_PROFESOR,    # cyan
    "Tipo curso":       C_FACULTAD,    # dorado
    "Otras secciones":  C_UNIVERSIDAD, # azul
}


def _ordered_aspects(aspects_in_data: list[str]) -> list[str]:
    """Ordena aspectos: primero los del orden preferido, luego el resto."""
    known = [a for a in ASPECT_ORDER_PREF if a in aspects_in_data]
    rest  = sorted(set(aspects_in_data) - set(known))
    return known + rest


def _short(asp: str) -> str:
    return ASPECT_SHORT.get(asp, asp[:20] + ("…" if len(asp) > 20 else ""))


# ── 9. Barras agrupadas por dimensión (curso seleccionado) ────────────────────
def plot_dimensiones_barras(df: pd.DataFrame, niveles: list[str] | None = None) -> go.Figure:
    """
    Barras agrupadas: eje X = aspecto, color = nivel_comparacion.
    df ya está filtrado al curso seleccionado (sin resúmenes globales).
    niveles: lista de nivel_comparacion a mostrar; None = todos.
    """
    if df is None or df.empty or "valor_central" not in df.columns:
        return _empty_fig("Sin datos de dimensiones para este curso")

    # Agregamos por aspecto + nivel
    df_v = df[df["valor_central"].notna()].copy()
    if not df_v.empty and "aspecto" in df_v.columns and "nivel_comparacion" in df_v.columns:
        agg = (df_v.groupby(["aspecto", "nivel_comparacion"], sort=False)
               ["valor_central"].mean().reset_index())
    else:
        return _empty_fig("Sin datos de dimensiones para este curso")

    if niveles:
        agg = agg[agg["nivel_comparacion"].isin(niveles)]
    if agg.empty:
        return _empty_fig("Sin datos para el nivel seleccionado")

    aspectos = _ordered_aspects(agg["aspecto"].unique().tolist())
    short_map = {a: _short(a) for a in aspectos}
    agg["aspecto_short"] = agg["aspecto"].map(short_map)
    short_ordered = [short_map[a] for a in aspectos]

    fig = go.Figure()
    for nivel, color in NIVEL_CURSO_COLORS.items():
        sub = agg[agg["nivel_comparacion"] == nivel].copy()
        if sub.empty:
            continue
        # Mantener solo aspectos presentes
        sub["aspecto_short"] = sub["aspecto"].map(short_map)
        fig.add_trace(go.Bar(
            x=sub["aspecto_short"],
            y=sub["valor_central"],
            name=nivel,
            marker_color=color,
            marker_line_color="rgba(0,0,0,0)",
            opacity=0.92,
            hovertemplate=(
                f"<b>{nivel}</b><br>"
                f"Dimensión: %{{x}}<br>"
                f"Puntaje promedio: %{{y:.1f}}<extra></extra>"
            ),
        ))

    _apply_layout(
        fig, height=420, barmode="group", bargap=0.20, bargroupgap=0.04,
        xaxis=dict(
            type="category", categoryorder="array", categoryarray=short_ordered,
            showgrid=False, zeroline=False,
            tickfont=dict(size=11, color=_C_TEXT),
            linecolor=_C_AXIS,
        ),
    )
    return fig


# ── 10. Radar por dimensión (curso seleccionado) ──────────────────────────────
def plot_radar(df: pd.DataFrame, niveles: list[str] | None = None) -> go.Figure:
    """
    Radar chart de dimensiones para el curso seleccionado.
    Excluye 'Puntaje global' para que solo aparezcan los rubros.
    """
    if df is None or df.empty or "valor_central" not in df.columns:
        return _empty_fig("Sin datos para radar")

    df_v = df[
        df["valor_central"].notna() &
        (df["aspecto"].astype(str).str.lower().str.strip() != "puntaje global")
    ].copy()

    if df_v.empty or "aspecto" not in df_v.columns:
        return _empty_fig("No hay suficientes dimensiones calculadas para radar")

    agg = (df_v.groupby(["aspecto", "nivel_comparacion"], sort=False)
           ["valor_central"].mean().reset_index())

    if niveles:
        agg = agg[agg["nivel_comparacion"].isin(niveles)]
    if agg.empty:
        return _empty_fig("Sin datos para el nivel seleccionado en radar")

    aspectos = _ordered_aspects(agg["aspecto"].unique().tolist())
    if len(aspectos) < 3:
        return _empty_fig("No hay suficientes dimensiones calculadas para radar (mínimo 3)")

    short_labels = [_short(a) for a in aspectos]
    # Cerrar el polígono
    short_closed = short_labels + [short_labels[0]]

    fig = go.Figure()
    for nivel, color in NIVEL_CURSO_COLORS.items():
        sub = agg[agg["nivel_comparacion"] == nivel]
        if sub.empty:
            continue
        values = [sub.loc[sub["aspecto"] == a, "valor_central"].mean()
                  for a in aspectos]
        values_closed = values + [values[0]]
        fig.add_trace(go.Scatterpolar(
            r=values_closed,
            theta=short_closed,
            fill="toself",
            fillcolor=color.replace(")", ",0.15)").replace("rgb", "rgba"),
            name=nivel,
            line=dict(color=color, width=2.5),
            marker=dict(size=7, color=color),
            hovertemplate=(
                f"<b>{nivel}</b><br>"
                f"Dimensión: %{{theta}}<br>"
                f"Puntaje: %{{r:.1f}}<extra></extra>"
            ),
        ))

    fig.update_layout(
        polar=dict(
            bgcolor="rgba(13,39,51,0.6)",
            radialaxis=dict(
                visible=True,
                showgrid=True,
                gridcolor=_C_GRID,
                tickfont=dict(size=10, color=_C_TEXT),
                linecolor=_C_AXIS,
            ),
            angularaxis=dict(
                tickfont=dict(size=11, color=_C_LEG),
                linecolor=_C_AXIS,
            ),
        ),
        paper_bgcolor=_C_BG,
        height=440,
        font=dict(family="IBM Plex Sans, system-ui, sans-serif", color=_C_TEXT, size=12),
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.15,
            xanchor="center", x=0.5,
            font=dict(size=12, color=_C_LEG),
            bgcolor="rgba(0,0,0,0)",
        ),
        hoverlabel=dict(
            bgcolor=_C_HOVER_BG, bordercolor=_C_HOVER_BOR,
            font=dict(color="#E8F4F7", size=12),
        ),
        margin=dict(l=40, r=40, t=40, b=60),
    )
    return fig


# ── 11. Tendencia temporal por dimensión (curso seleccionado) ─────────────────
def plot_tendencia_curso(
    df: pd.DataFrame,
    aspectos: list[str],
    nivel: str = "Profesor curso",
) -> go.Figure:
    """
    Líneas temporales por aspecto para el curso seleccionado.
    nivel: filtrar a un nivel específico (default 'Profesor curso').
    """
    if df is None or df.empty or "valor_central" not in df.columns:
        return _empty_fig("Sin datos de tendencia para este curso")

    df_v = df[df["valor_central"].notna()].copy()
    if nivel and nivel != "Todos":
        df_v = df_v[df_v["nivel_comparacion"] == nivel]
    if aspectos:
        df_v = df_v[df_v["aspecto"].isin(aspectos)]
    if df_v.empty:
        return _empty_fig("Sin datos para los aspectos y nivel seleccionados")

    df_v = _sort_by_order(df_v)

    fig = go.Figure()
    colors_cycle = [C_PROFESOR, C_FACULTAD, C_UNIVERSIDAD, C_DEPARTAMENTO,
                    "#B8DCE8", "#D4A843", "#9CC7D5"]

    for i, asp in enumerate(_ordered_aspects(aspectos)):
        sub = df_v[df_v["aspecto"] == asp]
        if sub.empty:
            continue
        # Agregar por periodo (si hay múltiples secciones)
        if "periodo_order" in sub.columns:
            sub_agg = (sub.groupby(["periodo_order", "periodo_label"], sort=False)
                       ["valor_central"].mean().reset_index()
                       .sort_values("periodo_order"))
        else:
            sub_agg = (sub.groupby("periodo_label", sort=False)
                       ["valor_central"].mean().reset_index())

        color = colors_cycle[i % len(colors_cycle)]
        label = _short(asp)
        fig.add_trace(go.Scatter(
            x=sub_agg["periodo_label"],
            y=sub_agg["valor_central"],
            mode="lines+markers",
            name=label,
            line=dict(color=color, width=2.5, shape="spline", smoothing=0.8),
            marker=dict(size=7, color=color, line=dict(width=1.5, color="#081C24")),
            hovertemplate=(
                f"<b>{label}</b><br>"
                f"Periodo: %{{x}}<br>"
                f"Puntaje: %{{y:.1f}}<extra></extra>"
            ),
        ))

    periodos = _sorted_periodos(df_v)
    _apply_layout(fig, height=420)
    if periodos:
        _categorical_x(fig, periodos)
    return fig


# ── 12. Heatmap general cursos × dimensiones ─────────────────────────────────
def plot_heatmap_cursos(df: pd.DataFrame) -> go.Figure:
    """
    Heatmap: filas = cursos, columnas = aspectos,
    valores = promedio valor_central para nivel_comparacion == 'Profesor curso'.
    Excluye registros de resumen semestral y cursos sin puntaje.
    """
    if df is None or df.empty:
        return _empty_fig("Sin datos para heatmap")

    req = ["curso_nombre_normalizado", "aspecto", "valor_central",
           "nivel_comparacion", "tiene_puntaje_calculado"]
    if not all(c in df.columns for c in req):
        return _empty_fig("Faltan columnas para construir el mapa")

    df_h = df[
        (df["nivel_comparacion"] == "Profesor curso") &
        (df["tiene_puntaje_calculado"] == True) &
        df["valor_central"].notna()
    ].copy()

    if "es_resumen_semestre_ponderado" in df_h.columns:
        df_h = df_h[df_h["es_resumen_semestre_ponderado"] != True]

    if df_h.empty:
        return _empty_fig("Sin datos de nivel 'Profesor curso' para heatmap")

    pivot = df_h.pivot_table(
        index="curso_nombre_normalizado",
        columns="aspecto",
        values="valor_central",
        aggfunc="mean",
    )

    # Ordenar columnas
    cols_ordered = _ordered_aspects(pivot.columns.tolist())
    pivot = pivot[[c for c in cols_ordered if c in pivot.columns]]
    short_cols = [_short(c) for c in pivot.columns]

    # Truncar nombres de cursos en el eje Y
    def _trunc(s, n=36):
        s = str(s)
        return s if len(s) <= n else s[:n - 1] + "…"

    row_labels = [_trunc(r) for r in pivot.index]

    # Colorscale teal oscuro → brillante
    colorscale = [
        [0.0,  "#0A2230"],
        [0.3,  "#1A3D4E"],
        [0.6,  "#2A8CA0"],
        [0.8,  "#4EC8E0"],
        [1.0,  "#C8F0F7"],
    ]

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=short_cols,
        y=row_labels,
        colorscale=colorscale,
        text=[[f"{v:.1f}" if not pd.isna(v) else "—" for v in row] for row in pivot.values],
        texttemplate="%{text}",
        textfont=dict(size=11, color="#E0EEF2"),
        hoverongaps=False,
        customdata=[[f"{full_col}" for full_col in pivot.columns]
                    for _ in range(len(pivot))],
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Dimensión: %{x}<br>"
            "Puntaje promedio: %{z:.1f}<extra></extra>"
        ),
        colorbar=dict(
            tickfont=dict(color=_C_TEXT, size=11),
            outlinecolor="rgba(0,0,0,0)",
        ),
    ))

    fig.update_layout(
        paper_bgcolor=_C_BG,
        plot_bgcolor=_C_BG,
        height=max(320, len(pivot) * 55 + 80),
        margin=dict(l=14, r=14, t=20, b=50),
        font=dict(family="IBM Plex Sans, system-ui, sans-serif",
                  color=_C_TEXT, size=12),
        xaxis=dict(
            tickfont=dict(size=11, color=_C_TEXT),
            side="bottom",
        ),
        yaxis=dict(
            tickfont=dict(size=11, color=_C_LEG),
            autorange="reversed",
        ),
        hoverlabel=dict(
            bgcolor=_C_HOVER_BG, bordercolor=_C_HOVER_BOR,
            font=dict(color="#E8F4F7", size=12),
        ),
    )
    return fig


# ── 13. Evolución del puntaje global del curso seleccionado ──────────────────
def plot_evolucion_curso(df_evol: pd.DataFrame) -> go.Figure:
    """
    Líneas por nivel_comparacion para el puntaje global del curso seleccionado.
    df_evol: ya filtrado a curso_codigo_base + aspecto='Puntaje global' +
             valor_central notna + excl. es_resumen_semestre_ponderado.

    CRÍTICO: all_periodos se computa ANTES del loop para capturar la unión
    de todos los periodos de todas las series y ordenarlos cronológicamente.
    Cada traza se alinea a ese eje global con None donde no tiene dato
    (connectgaps=False muestra huecos reales en lugar de falsa continuidad).
    Eje Y controlado: [min(145, floor(min-2)), max(165, ceil(max+2))].
    """
    import math
    if df_evol is None or df_evol.empty or "valor_central" not in df_evol.columns:
        return _empty_fig("Sin datos de evolución para este curso")

    df_v = df_evol[df_evol["valor_central"].notna()].copy()
    if df_v.empty:
        return _empty_fig("Sin datos de evolución para este curso")

    val_min = df_v["valor_central"].min()
    val_max = df_v["valor_central"].max()
    y_min = min(145, math.floor(val_min - 2))
    y_max = max(165, math.ceil(val_max + 2))

    # ── CRÍTICO: orden cronológico global antes del loop ─────────────────────
    all_periodos = _sorted_periodos(df_v)   # unión de periodos de todas las series

    # Info estática del curso para tooltip (igual para todos los puntos)
    _cod = (df_v["curso_codigo_base"].dropna().iloc[0]
            if "curso_codigo_base" in df_v.columns and not df_v["curso_codigo_base"].dropna().empty
            else "")
    _nom = (df_v["curso_nombre_normalizado"].dropna().iloc[0]
            if "curso_nombre_normalizado" in df_v.columns and not df_v["curso_nombre_normalizado"].dropna().empty
            else "")
    _nom_short = (_nom[:45] + "…") if len(_nom) > 45 else _nom
    _header = f"<b>{_cod}</b>" + (f"<br><i>{_nom_short}</i>" if _nom_short else "")

    _dash_map = {"Profesor curso": "solid", "Otras secciones": "dot", "Tipo curso": "dash"}

    fig = go.Figure()
    for nivel, color in NIVEL_CURSO_COLORS.items():
        sub = df_v[df_v["nivel_comparacion"] == nivel].copy()
        if sub.empty:
            continue

        # Agregar por periodo si hay duplicados dentro de la misma serie
        agg = (sub.groupby("periodo_label", sort=False)["valor_central"]
               .mean().reset_index())
        if agg.empty:
            continue

        # Alinear con el eje global → None donde la serie no tiene dato
        # Esto permite que connectgaps=False muestre huecos reales
        period_val: dict[str, float | None] = dict(zip(agg["periodo_label"], agg["valor_central"]))
        y_vals = [period_val.get(p) for p in all_periodos]

        # estado_calculo por periodo para tooltip
        period_estado: dict[str, str] = {}
        if "estado_calculo" in sub.columns:
            for _, row in agg.iterrows():
                p = row["periodo_label"]
                e = sub[sub["periodo_label"] == p]["estado_calculo"].dropna()
                period_estado[p] = str(e.iloc[0]) if not e.empty else "—"
        estado_vals = [period_estado.get(p, "—") for p in all_periodos]

        is_prof = nivel == "Profesor curso"
        fig.add_trace(go.Scatter(
            x=all_periodos,
            y=y_vals,
            mode="lines+markers",
            name=nivel,
            connectgaps=False,
            customdata=estado_vals,
            line=dict(
                color=color,
                width=4 if is_prof else 2.5,
                shape="linear",
                dash=_dash_map.get(nivel, "solid"),
            ),
            marker=dict(
                size=9 if is_prof else 7,
                color=color,
                line=dict(width=2.5 if is_prof else 1.5, color="#081C24"),
            ),
            hovertemplate=(
                f"{_header}<br>"
                f"<b>{nivel}</b><br>"
                f"Periodo: %{{x}}<br>"
                f"Puntaje global: %{{y:.1f}}<br>"
                f"Estado: %{{customdata}}<extra></extra>"
            ),
        ))

    _apply_layout(
        fig, height=400,
        yaxis=dict(
            range=[y_min, y_max],
            showgrid=True, gridcolor=_C_GRID,
            tickfont=dict(size=12, color=_C_TEXT),
            zeroline=False,
        ),
    )
    if all_periodos:
        _categorical_x(fig, all_periodos)
    return fig
