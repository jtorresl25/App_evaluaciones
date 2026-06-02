import streamlit as st
import pandas as pd
from app.utils import plots
from app.components.kpi_cards import render_kpi_row_hero, render_kpi_row_secondary

# ── Paleta oscura ─────────────────────────────────────────────────────────────
_BG_CARD      = "#0D2733"
_BG_CARD_HI   = "#112F3E"
_BG_SURFACE   = "#0A2230"
_BORDER       = "#1A3D4E"
_BORDER_STR   = "#245970"
_TEXT_P1      = "#E0EEF2"
_TEXT_P2      = "#8CBECB"
_TEXT_MUTED   = "#537F8A"
_GOLD         = "#D4A843"
_GOLD_TINT    = "rgba(212,168,67,0.13)"
_GREEN        = "#4DB88A"
_GREEN_TINT   = "rgba(77,184,138,0.13)"
_TEAL         = "#3AAFC4"
_FONT         = "'IBM Plex Sans', system-ui, sans-serif"
_FONT_SERIF   = "'Spectral', Georgia, serif"

_CHART_CONFIG = {"displayModeBar": False}


# ── Helpers de estilo ─────────────────────────────────────────────────────────
def _eyebrow(text: str) -> None:
    st.markdown(
        f'<span style="font-size:11px;letter-spacing:.2em;text-transform:uppercase;'
        f'color:{_TEAL};font-weight:500;font-family:{_FONT};display:block;margin-bottom:4px">'
        f'{text}</span>',
        unsafe_allow_html=True,
    )


def _graph_label(text: str) -> None:
    st.markdown(
        f'<p style="font-size:13px;color:{_TEXT_P2};font-weight:500;'
        f'font-family:{_FONT};margin-bottom:2px">{text}</p>',
        unsafe_allow_html=True,
    )


def _model_badge(text: str, active: bool = True) -> None:
    if active:
        style = (
            f"display:inline-flex;align-items:center;gap:8px;"
            f"padding:5px 14px;border-radius:30px;font-size:12px;font-weight:600;"
            f"background:{_TEAL};color:#081C24;font-family:{_FONT};margin-bottom:6px;"
        )
    else:
        style = (
            f"display:inline-flex;align-items:center;gap:8px;"
            f"padding:5px 14px;border-radius:30px;font-size:12px;font-weight:600;"
            f"background:{_BG_CARD_HI};color:{_TEXT_P2};"
            f"border:1px solid {_BORDER_STR};font-family:{_FONT};margin-bottom:6px;"
        )
    st.markdown(f'<span style="{style}">{text}</span>', unsafe_allow_html=True)


def _divider() -> None:
    st.markdown(
        f'<div style="height:1px;background:{_BORDER};margin:1.4rem 0"></div>',
        unsafe_allow_html=True,
    )


def _interpret_box(html_text: str, color: str = _GREEN, tint: str = _GREEN_TINT,
                   border: str = "rgba(77,184,138,0.25)") -> None:
    st.markdown(
        f'<div style="background:{tint};border:1px solid {border};border-radius:12px;'
        f'padding:13px 18px;font-size:13.5px;color:{color};margin-top:6px;'
        f'font-family:{_FONT};line-height:1.55">{html_text}</div>',
        unsafe_allow_html=True,
    )


# ── Nombres cortos de dimensiones (tarjetas y leyendas) ──────────────────────
_DIM_SHORT: dict[str, str] = {
    "Puntaje global": "Global",
    "Coherencia": "Coherencia",
    "Fomento de autonomía": "Autonomía",
    "Fomento de pensamiento crítico, discusión y participación": "Pensamiento crítico",
    "Responsabilidades del profesor": "Responsabilidades",
    "Retroalimentación, monitoreo y criterios de calificación": "Retroalimentación",
    "Trato a estudiantes": "Trato",
}

def _dim_short(asp: str) -> str:
    return _DIM_SHORT.get(asp, asp[:22] + ("…" if len(asp) > 22 else ""))


def _check_periodo_consistency(df: pd.DataFrame) -> str | None:
    """
    Detecta si algún periodo_label tiene más de un periodo_order asignado.
    Retorna mensaje de alerta o None si todo es consistente.
    """
    if df is None or df.empty:
        return None
    if "periodo_label" not in df.columns or "periodo_order" not in df.columns:
        return None
    multi = (
        df[["periodo_label", "periodo_order"]].dropna().drop_duplicates()
        .groupby("periodo_label")["periodo_order"].nunique()
    )
    ambiguous = multi[multi > 1].index.tolist()
    if ambiguous:
        sample = ", ".join(str(p) for p in ambiguous[:3])
        return f"Periodos con orden ambiguo en la fuente: {sample}"
    return None


# ── Hero ──────────────────────────────────────────────────────────────────────
def render_hero(metrics: dict) -> None:
    pct_fac = metrics.get("pct_sobre_facultad_actual")
    pct_uni = metrics.get("pct_sobre_universidad_actual")

    if pct_fac is not None and pct_uni is not None:
        pct_min = min(pct_fac, pct_uni)
        pct_display = f"{pct_min:.0f}%"
        periodos = metrics.get("periodos_validos_modelo_actual", 0)
        sub_text = (
            f"Posición sostenida en los {periodos} periodos evaluados bajo el modelo actual — "
            f"los resultados superan de forma consistente los promedios institucionales disponibles."
            if periodos else
            "Posición sostenida durante todos los periodos evaluados bajo el modelo actual."
        )
        if pct_fac >= 99.9 and pct_uni >= 99.9:
            headline = (
                f"Desempeño actual sobresaliente: en el modelo vigente, "
                f"el profesor se ubica "
                f"<em style='color:{_GOLD}'>por encima de Facultad y Universidad</em> "
                f"en el <em style='color:{_GOLD}'>100%</em> de los periodos válidos."
            )
        elif pct_fac >= 99.9:
            headline = (
                f"En el modelo vigente, el profesor supera a Facultad "
                f"en el <em style='color:{_GOLD}'>100%</em> de los periodos "
                f"y a Universidad en el <em style='color:{_GOLD}'>{pct_uni:.0f}%</em>."
            )
        elif pct_uni >= 99.9:
            headline = (
                f"En el modelo vigente, el profesor supera a Universidad "
                f"en el <em style='color:{_GOLD}'>100%</em> de los periodos "
                f"y a Facultad en el <em style='color:{_GOLD}'>{pct_fac:.0f}%</em>."
            )
        else:
            headline = (
                f"En el modelo vigente, el profesor se ubica sobre Facultad "
                f"en <em style='color:{_GOLD}'>{pct_fac:.0f}%</em> de los periodos y "
                f"sobre Universidad en <em style='color:{_GOLD}'>{pct_uni:.0f}%</em>."
            )
    else:
        pct_display = "—"
        sub_text = "Cargue el Excel para ver el análisis completo."
        headline = "Se analizaron los resultados frente a los benchmarks institucionales disponibles."

    st.markdown(
        f'<div style="'
        f'background:linear-gradient(135deg,#071520 0%,#0A2230 40%,#0E2E40 100%);'
        f'border:1px solid {_BORDER_STR};border-left:4px solid {_GOLD};'
        f'border-radius:18px;padding:34px 38px;position:relative;overflow:hidden;'
        f'margin-bottom:1.2rem;box-shadow:0 12px 40px rgba(0,0,0,0.4)">'
        f'<div style="position:absolute;right:-40px;top:-40px;width:200px;height:200px;'
        f'border-radius:50%;background:radial-gradient(circle,rgba(212,168,67,0.14),transparent 65%);'
        f'pointer-events:none"></div>'
        f'<div style="display:flex;gap:26px;align-items:center;flex-wrap:wrap;'
        f'position:relative;z-index:1">'
        f'<div style="width:96px;height:96px;border-radius:50%;flex-shrink:0;'
        f'background:radial-gradient(circle at 35% 30%,#D4A843,#A9823C 75%);'
        f'display:flex;flex-direction:column;align-items:center;justify-content:center;'
        f'text-align:center;box-shadow:0 0 0 2px rgba(212,168,67,0.3),0 8px 24px rgba(169,130,60,0.5)">'
        f'<span style="font-family:{_FONT_SERIF};font-weight:700;font-size:24px;color:#fff;line-height:1">{pct_display}</span>'
        f'<span style="font-size:7.5px;letter-spacing:.15em;color:rgba(255,255,255,.88);margin-top:3px;text-transform:uppercase">Periodos</span>'
        f'</div>'
        f'<div style="flex:1;min-width:220px">'
        f'<span style="font-size:10.5px;letter-spacing:.2em;text-transform:uppercase;color:{_GOLD};font-weight:500;font-family:{_FONT}">Conclusión ejecutiva</span>'
        f'<h2 style="color:{_TEXT_P1};font-size:clamp(16px,2vw,22px);line-height:1.3;margin:10px 0 0;'
        f'font-family:{_FONT_SERIF};font-weight:600">{headline}</h2>'
        f'<p style="margin-top:10px;color:{_TEXT_P2};font-size:13.5px;font-family:{_FONT};line-height:1.55">{sub_text}</p>'
        f'</div></div></div>',
        unsafe_allow_html=True,
    )


# ── Estado inicial ────────────────────────────────────────────────────────────
def render_upload_state() -> None:
    st.markdown(
        f'<div style="background:{_BG_CARD};border:1.5px dashed {_BORDER_STR};'
        f'border-radius:18px;padding:48px 40px;text-align:center;'
        f'box-shadow:0 4px 20px rgba(0,0,0,0.25);margin-top:2rem">'
        f'<div style="font-size:11px;letter-spacing:.2em;text-transform:uppercase;'
        f'color:{_TEAL};font-weight:500;margin-bottom:12px;font-family:{_FONT}">'
        f'Herramienta de análisis docente</div>'
        f'<h2 style="font-family:{_FONT_SERIF};font-weight:600;color:{_TEXT_P1};'
        f'font-size:28px;margin:0 0 14px;line-height:1.2">Dashboard de evaluaciones docentes</h2>'
        f'<p style="color:{_TEXT_P2};font-size:15px;max-width:540px;margin:0 auto;'
        f'font-family:{_FONT};line-height:1.55">'
        f'Carga un archivo Excel para visualizar el desempeño docente histórico, '
        f'comparar resultados frente a benchmarks institucionales y explorar el detalle por curso.</p>'
        f'<p style="margin-top:12px;font-size:12.5px;color:{_TEXT_MUTED};font-family:{_FONT}">'
        f'La app no almacena ningún dato. El análisis se genera únicamente en tu sesión local.</p>'
        f'<div style="display:inline-flex;align-items:center;gap:8px;margin-top:18px;'
        f'font-size:12.5px;color:{_GREEN};background:{_GREEN_TINT};'
        f'padding:7px 16px;border-radius:30px;font-family:{_FONT};'
        f'border:1px solid rgba(77,184,138,0.2)">'
        f'🔒 Privacidad garantizada — ningún dato sale de tu equipo</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── KPIs ──────────────────────────────────────────────────────────────────────
def render_kpis(metrics: dict) -> None:
    _eyebrow("Resumen ejecutivo")
    st.markdown(
        f'<h3 style="font-family:{_FONT_SERIF};color:{_TEXT_P1};margin:4px 0 4px">Indicadores principales</h3>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p style="font-size:13.5px;color:{_TEXT_P2};font-family:{_FONT};margin-bottom:14px">'
        f'Las dos cifras del modelo actual concentran el mensaje; el resto da contexto sobre '
        f'el volumen y solidez de los datos.</p>',
        unsafe_allow_html=True,
    )
    render_kpi_row_hero(metrics)
    st.write("")
    render_kpi_row_secondary(metrics)


# ── Modelo actual ─────────────────────────────────────────────────────────────
def render_modelo_actual_section(df: pd.DataFrame, metrics: dict) -> None:
    label = metrics.get("label_actual") or "Modelo actual"
    _model_badge(f"● {label} · vigente", active=True)
    st.markdown(
        f'<h3 style="font-family:{_FONT_SERIF};color:{_TEXT_P1};margin:4px 0 4px">'
        f'Modelo actual: desempeño consistentemente superior al benchmark</h3>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p style="font-size:13.5px;color:{_TEXT_P2};font-family:{_FONT};margin-bottom:12px">'
        f'Resultados por periodo · escala del modelo actual. '
        f'Posición sostenida por encima de los promedios institucionales.</p>',
        unsafe_allow_html=True,
    )

    col_left, col_right = st.columns([1.3, 1])
    with col_left:
        _graph_label("Profesor vs. benchmarks institucionales")
        st.plotly_chart(plots.plot_modelo_actual_line(df),
                        use_container_width=True, config=_CHART_CONFIG)
    with col_right:
        _graph_label("Diferencia frente a benchmarks (delta por periodo)")
        st.plotly_chart(plots.plot_modelo_actual_delta(df),
                        use_container_width=True, config=_CHART_CONFIG)

    avg_fac = metrics.get("avg_delta_facultad_actual")
    avg_uni = metrics.get("avg_delta_universidad_actual")
    if avg_fac is not None or avg_uni is not None:
        partes = []
        if avg_fac is not None:
            s = f"+{avg_fac:.2f}" if avg_fac >= 0 else f"{avg_fac:.2f}"
            partes.append(f"<b style='color:{_TEXT_P1}'>{s} pts</b> vs Facultad")
        if avg_uni is not None:
            s = f"+{avg_uni:.2f}" if avg_uni >= 0 else f"{avg_uni:.2f}"
            partes.append(f"<b style='color:{_TEXT_P1}'>{s} pts</b> vs Universidad")
        _interpret_box(f"Diferencia promedio en el modelo actual: {' · '.join(partes)}")


# ── Contexto histórico ────────────────────────────────────────────────────────
def render_modelo_anterior_section(df: pd.DataFrame, metrics: dict) -> None:
    label = metrics.get("label_anterior") or "Modelo anterior"
    _model_badge(f"◎ {label} · contexto histórico", active=False)
    st.markdown(
        f'<h3 style="font-family:{_FONT_SERIF};color:{_TEXT_P1};margin:4px 0 4px">'
        f'Contexto histórico: trayectoria en el modelo anterior</h3>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p style="font-size:13.5px;color:{_TEXT_P2};font-family:{_FONT};margin-bottom:12px">'
        f'Datos en escala original del modelo anterior. '
        f'No se comparan directamente con el modelo actual.</p>',
        unsafe_allow_html=True,
    )

    col_left, col_right = st.columns([1.3, 1])
    with col_left:
        _graph_label("Profesor vs. benchmarks (modelo anterior)")
        st.plotly_chart(plots.plot_modelo_anterior_line(df),
                        use_container_width=True, config=_CHART_CONFIG)
    with col_right:
        _graph_label("Diferencia histórica frente a benchmarks")
        st.plotly_chart(plots.plot_modelo_anterior_delta(df),
                        use_container_width=True, config=_CHART_CONFIG)


# ── Comparación relativa ──────────────────────────────────────────────────────
def render_comparacion_relativa_section(metrics: dict) -> None:
    st.markdown(
        f'<h3 style="font-family:{_FONT_SERIF};color:{_TEXT_P1};margin:4px 0 4px">'
        f'Comparación relativa: posición frente a benchmarks</h3>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p style="font-size:13.5px;color:{_TEXT_P2};font-family:{_FONT};margin-bottom:12px">'
        f'Porcentaje de periodos válidos en que el profesor superó cada benchmark. '
        f'Ambos modelos en sus propias escalas.</p>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([2, 1])
    with col1:
        st.plotly_chart(plots.plot_comparacion_relativa(metrics),
                        use_container_width=True, config=_CHART_CONFIG)
    with col2:
        st.write("")
        _metric_mini("% sobre Facultad (actual)",
                     metrics.get("pct_sobre_facultad_actual"), "%")
        _metric_mini("% sobre Universidad (actual)",
                     metrics.get("pct_sobre_universidad_actual"), "%")
        _divider()
        _metric_mini("% sobre Facultad (anterior)",
                     metrics.get("pct_sobre_facultad_anterior"), "%", muted=True)
        _metric_mini("% sobre Universidad (anterior)",
                     metrics.get("pct_sobre_universidad_anterior"), "%", muted=True)


def _metric_mini(label: str, value, suffix: str = "", muted: bool = False) -> None:
    color = _TEXT_MUTED if muted else _TEXT_P1
    font_size = "22px" if muted else "28px"
    val_str = f"{value:.0f}{suffix}" if value is not None else "—"
    st.markdown(
        f'<div style="margin-bottom:12px;font-family:{_FONT}">'
        f'<div style="font-size:11.5px;color:{_TEXT_MUTED}">{label}</div>'
        f'<div style="font-size:{font_size};font-family:{_FONT_SERIF};'
        f'font-weight:700;color:{color};line-height:1.15">{val_str}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Cursos (BASE_GENERAL_DOCENTE) ─────────────────────────────────────────────
def render_cursos_section(df: pd.DataFrame, metrics: dict) -> None:
    st.markdown(
        f'<h3 style="font-family:{_FONT_SERIF};color:{_TEXT_P1};margin:4px 0 4px">'
        f'Detalle por curso</h3>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p style="font-size:13.5px;color:{_TEXT_P2};font-family:{_FONT};margin-bottom:12px">'
        f'Puntaje promedio por curso individual. '
        f'Se excluyen registros de nivel agregado de periodo y registros sin docencia.</p>',
        unsafe_allow_html=True,
    )

    if df.empty:
        st.info("No hay registros de cursos individuales con datos válidos.")
        return

    label_actual   = metrics.get("label_actual")
    label_anterior = metrics.get("label_anterior")

    if "modelo_evaluacion" in df.columns:
        df_act = df[df["modelo_evaluacion"] == label_actual].copy()   if label_actual   else pd.DataFrame(columns=df.columns)
        df_ant = df[df["modelo_evaluacion"] == label_anterior].copy() if label_anterior else pd.DataFrame(columns=df.columns)
    else:
        df_act = pd.DataFrame(columns=df.columns)
        df_ant = df.copy()

    has_act = not df_act.empty
    has_ant = not df_ant.empty

    tabs_labels = []
    if has_act:
        tabs_labels.append("Modelo actual")
    if has_ant:
        lab_display = label_anterior if label_anterior else "Modelo anterior"
        tabs_labels.append(f"{lab_display}")

    if not tabs_labels:
        st.info("No hay cursos individuales para mostrar.")
        return

    tcursos = st.tabs(tabs_labels)
    tab_idx = 0

    if has_act:
        with tcursos[tab_idx]:
            _render_cursos_tab(df_act, "Escala del modelo actual")
        tab_idx += 1

    if has_ant:
        with tcursos[tab_idx]:
            _render_cursos_tab(df_ant, "Escala /5 — modelo anterior")


def _render_cursos_tab(df: pd.DataFrame, escala_label: str) -> None:
    st.markdown(
        f'<p style="font-size:12px;color:{_TEXT_MUTED};font-family:{_FONT};'
        f'margin-bottom:8px">Escala: {escala_label}</p>',
        unsafe_allow_html=True,
    )
    col1, col2 = st.columns([1.6, 1])
    with col1:
        st.plotly_chart(
            plots.plot_cursos(df, escala_label),
            use_container_width=True, config=_CHART_CONFIG,
        )
    with col2:
        nombre_col = "nombre_curso" if "nombre_curso" in df.columns else "codigo_curso"
        tabla = (
            df.groupby(nombre_col)["puntaje_profesor"]
            .agg(["mean", "count"])
            .reset_index()
            .rename(columns={nombre_col: "Curso", "mean": "Promedio", "count": "Semestres"})
            .sort_values("Promedio", ascending=False)
        )
        tabla["Promedio"] = tabla["Promedio"].round(2)
        st.dataframe(tabla, use_container_width=True, hide_index=True)


# ── Desempeño Detallado (BASE_DETALLE_PDF) ────────────────────────────────────
def _render_page_kpis(pdf_metrics: dict, rubros_evaluados: int) -> None:
    """KPI cards de página para la sección Desempeño Detallado."""
    _eyebrow("Resumen de datos disponibles")
    kpis = [
        ("Cursos únicos",         pdf_metrics.get("cursos_unicos_pdf", 0),   "en la base"),
        ("Cursos con puntaje",    pdf_metrics.get("cursos_con_puntaje", 0),  "calculado OK"),
        ("Rubros evaluados",      rubros_evaluados,                          "dimensiones"),
        ("Periodos con detalle",  pdf_metrics.get("periodos_pdf", 0),        "semestres"),
        ("Registros por revisar", pdf_metrics.get("registros_a_revisar", 0), "marcados para revisión"),
    ]
    cols = st.columns(len(kpis))
    for col, (label, val, foot) in zip(cols, kpis):
        col.markdown(
            f'<div style="background:{_BG_CARD};border:1px solid {_BORDER};'
            f'border-radius:14px;padding:14px 14px 10px;font-family:{_FONT}">'
            f'<div style="font-size:11px;color:{_TEXT_P2};margin-bottom:4px">{label}</div>'
            f'<div style="font-size:28px;font-family:{_FONT_SERIF};font-weight:700;'
            f'color:{_TEXT_P1};line-height:1.1">{"—" if val is None else str(val)}</div>'
            f'<div style="font-size:10.5px;color:{_TEXT_MUTED};margin-top:4px">{foot}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Alerta discreta si hay cursos NC (no como tarjeta principal)
    cursos_nc = pdf_metrics.get("cursos_nc", 0) or 0
    if cursos_nc > 0:
        plural = "curso" if cursos_nc == 1 else "cursos"
        st.markdown(
            f'<div style="margin-top:10px;padding:8px 14px;border-radius:8px;'
            f'background:rgba(212,168,67,0.08);border:1px solid rgba(212,168,67,0.22);'
            f'font-size:12.5px;color:{_GOLD};font-family:{_FONT};line-height:1.5">'
            f'Hay <b>{cursos_nc}</b> {plural} sin cálculo por condiciones de respuesta. '
            f'No se incluyen en promedios ni gráficos.</div>',
            unsafe_allow_html=True,
        )


def render_pdf_detail_section(df_pdf: pd.DataFrame, pdf_metrics: dict) -> None:
    """
    Sección Desempeño Detallado por Curso y Dimensión.
    Análisis a nivel de curso individual: evolución, dimensiones, heatmap.
    No muestra gráficos globales (tendencia ponderada, comparación institucional).
    """
    from app.utils.plots import (
        NIVEL_CURSO_COLORS,
        plot_dimensiones_barras, plot_radar,
        plot_tendencia_curso, plot_heatmap_cursos,
        plot_evolucion_curso,
        _ordered_aspects,
        _sorted_periodos,
    )

    # ── Encabezado ────────────────────────────────────────────────────────────
    _eyebrow("Análisis por curso y dimensión")
    st.markdown(
        f'<h2 style="font-family:{_FONT_SERIF};color:{_TEXT_P1};margin:4px 0 4px;'
        f'font-size:clamp(20px,2.5vw,30px)">'
        f'Desempeño Detallado por Curso y Dimensión</h2>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p style="font-size:14px;color:{_TEXT_P2};font-family:{_FONT};'
        f'margin-bottom:16px;line-height:1.55">'
        f'Explora el comportamiento de cada curso por rubro de docencia, '
        f'periodo y nivel de comparación.</p>',
        unsafe_allow_html=True,
    )

    if df_pdf is None or df_pdf.empty:
        st.info("No hay datos de evaluación detallada disponibles en este archivo.")
        return

    # ── KPIs de página ────────────────────────────────────────────────────────
    rubros_evaluados = 0
    if "aspecto" in df_pdf.columns:
        rubros_evaluados = int(
            df_pdf[
                df_pdf["aspecto"].astype(str).str.strip().str.lower() != "puntaje global"
            ]["aspecto"].dropna().nunique()
        )

    _render_page_kpis(pdf_metrics, rubros_evaluados)

    # Validación discreta de consistencia de periodos (no bloquea la app)
    _alert = _check_periodo_consistency(df_pdf)
    if _alert:
        st.markdown(
            f'<div style="margin-top:8px;padding:7px 13px;border-radius:7px;'
            f'background:rgba(227,109,90,0.09);border:1px solid rgba(227,109,90,0.25);'
            f'font-size:12px;color:#E36D5A;font-family:{_FONT}">'
            f'⚠ {_alert}</div>',
            unsafe_allow_html=True,
        )

    _divider()

    # ── Preparar lista de cursos ──────────────────────────────────────────────
    nombre_col = (
        "curso_nombre_normalizado" if "curso_nombre_normalizado" in df_pdf.columns
        else "curso_nombre_original" if "curso_nombre_original" in df_pdf.columns
        else None
    )

    opciones_cursos: list[str] = []
    map_opcion_codigo: dict[str, str] = {}

    if "curso_codigo_base" in df_pdf.columns and nombre_col:
        df_cu = (
            df_pdf[df_pdf["curso_codigo_base"].notna()]
            .groupby(["curso_codigo_base", nombre_col], sort=False)
            .size().reset_index(name="n")
            .sort_values("n", ascending=False)
        )
        for _, row in df_cu.iterrows():
            key = f"{row['curso_codigo_base']} — {row[nombre_col]}"
            opciones_cursos.append(key)
            map_opcion_codigo[key] = row["curso_codigo_base"]

    if not opciones_cursos:
        st.warning("No se encontraron cursos individuales en los datos.")
        return

    # Default: ICYA3601 si existe; si no, curso con más periodos con puntaje
    default_idx = 0
    found_icya = False
    for i, op in enumerate(opciones_cursos):
        if "ICYA3601" in op:
            default_idx = i
            found_icya = True
            break

    if not found_icya and (
        "tiene_puntaje_calculado" in df_pdf.columns
        and "curso_codigo_base" in df_pdf.columns
        and "periodo_label" in df_pdf.columns
    ):
        per_curso = (
            df_pdf[df_pdf["tiene_puntaje_calculado"] == True]
            .groupby("curso_codigo_base")["periodo_label"].nunique()
        )
        if not per_curso.empty:
            best_cod = per_curso.idxmax()
            for i, op in enumerate(opciones_cursos):
                if map_opcion_codigo.get(op) == best_cod:
                    default_idx = i
                    break

    # ── Selectores ────────────────────────────────────────────────────────────
    col_sel, col_period, col_nivel, col_viz = st.columns([2.5, 1, 1, 1])

    with col_sel:
        sel_op = st.selectbox(
            "Selecciona un curso", opciones_cursos, index=default_idx, key="dd_curso"
        )
    sel_cod = map_opcion_codigo.get(sel_op, "")

    # Periodos del curso seleccionado en orden cronológico descendente (más reciente primero)
    periodos_disp: list[str] = []
    if "periodo_label" in df_pdf.columns and sel_cod:
        df_cur_p = df_pdf[df_pdf["curso_codigo_base"] == sel_cod]
        periodos_disp = list(reversed(_sorted_periodos(df_cur_p)))

    with col_period:
        f_periodo = st.selectbox("Periodo", ["Todos"] + periodos_disp, key="dd_periodo")

    niveles_curso = list(NIVEL_CURSO_COLORS.keys())
    with col_nivel:
        f_nivel_str = st.selectbox(
            "Nivel de comparación",
            ["Todos"] + niveles_curso,
            index=1,
            key="dd_nivel",
        )

    with col_viz:
        f_viz = st.selectbox(
            "Visualización",
            ["Barras", "Radar", "Tendencia"],
            index=0,
            key="dd_viz",
        )

    # ── Filtrar datos del curso ───────────────────────────────────────────────
    df_curso = df_pdf[df_pdf["curso_codigo_base"] == sel_cod].copy()
    if f_periodo != "Todos" and "periodo_label" in df_curso.columns:
        df_curso = df_curso[df_curso["periodo_label"] == f_periodo]

    if "es_resumen_semestre_ponderado" in df_curso.columns:
        df_ind = df_curso[df_curso["es_resumen_semestre_ponderado"] != True].copy()
    else:
        df_ind = df_curso.copy()

    if "tiene_puntaje_calculado" in df_ind.columns:
        df_con_puntaje = df_ind[df_ind["tiene_puntaje_calculado"] == True].copy()
    else:
        df_con_puntaje = df_ind.copy()

    # ── NC check ──────────────────────────────────────────────────────────────
    if df_con_puntaje.empty:
        motivo = ""
        if "motivo_estado" in df_curso.columns:
            m = df_curso["motivo_estado"].dropna()
            if not m.empty:
                motivo = str(m.iloc[0])
        periodos_nc = (
            ", ".join(df_curso["periodo_label"].dropna().unique().tolist())
            if "periodo_label" in df_curso.columns else "—"
        )
        st.markdown(
            f'<div style="background:{_BG_CARD};border:1px solid {_BORDER_STR};'
            f'border-radius:14px;padding:20px 24px;margin-top:12px;font-family:{_FONT}">'
            f'<div style="font-size:14px;color:{_TEXT_P1};font-weight:600;margin-bottom:8px">'
            f'Este curso aparece como dictado, pero no tiene puntaje calculado.</div>'
            f'<div style="font-size:13px;color:{_TEXT_P2};line-height:1.7">'
            f'<b style="color:{_TEXT_P1}">Periodos:</b> {periodos_nc}<br>'
            f'{"<b style=\'color:" + _TEXT_P1 + "\'>Motivo:</b> " + motivo if motivo else "Motivo no disponible."}'
            f'</div></div>',
            unsafe_allow_html=True,
        )
        return

    # ── Nivel y df para gráficos ──────────────────────────────────────────────
    niveles_activos = None if f_nivel_str == "Todos" else [f_nivel_str]
    df_plot = (
        df_con_puntaje[df_con_puntaje["nivel_comparacion"].isin(niveles_activos)].copy()
        if niveles_activos else df_con_puntaje.copy()
    )

    # ── Sub-tabs ──────────────────────────────────────────────────────────────
    tab_res, tab_tend, tab_mapa, tab_datos = st.tabs([
        "📊 Resumen del curso",
        "📈 Tendencia por rubro",
        "🗺️ Mapa de fortalezas",
        "📋 Datos",
    ])

    # ── Resumen del curso ─────────────────────────────────────────────────────
    with tab_res:
        _render_curso_kpis(df_con_puntaje, df_curso)
        _divider()

        # Gráfico principal: evolución puntaje global (todos los niveles curso)
        _graph_label("Evolución del curso seleccionado")
        df_evol = df_pdf[
            (df_pdf["curso_codigo_base"] == sel_cod)
            & (df_pdf["aspecto"].astype(str).str.strip().str.lower() == "puntaje global")
            & df_pdf["valor_central"].notna()
        ].copy()
        if "es_resumen_semestre_ponderado" in df_evol.columns:
            df_evol = df_evol[df_evol["es_resumen_semestre_ponderado"] != True]
        if f_periodo != "Todos" and "periodo_label" in df_evol.columns:
            df_evol = df_evol[df_evol["periodo_label"] == f_periodo]

        st.plotly_chart(
            plot_evolucion_curso(df_evol),
            use_container_width=True, config=_CHART_CONFIG,
        )

        _divider()

        # Gráfico de dimensiones (excluye Puntaje global)
        _graph_label("Perfil por dimensiones del curso")
        df_dims = (
            df_plot[
                df_plot["aspecto"].astype(str).str.strip().str.lower() != "puntaje global"
            ].copy()
            if "aspecto" in df_plot.columns else df_plot.copy()
        )

        if f_viz == "Radar":
            st.plotly_chart(
                plot_radar(df_dims, niveles_activos),
                use_container_width=True, config=_CHART_CONFIG,
            )
        elif f_viz == "Tendencia":
            if "aspecto" in df_con_puntaje.columns:
                asp_disp_r = _ordered_aspects(
                    df_con_puntaje["aspecto"].dropna().unique().tolist()
                )
            else:
                asp_disp_r = []
            _def_r = [
                "Coherencia",
                "Retroalimentación, monitoreo y criterios de calificación",
                "Trato a estudiantes",
            ]
            default_asp_r = [a for a in _def_r if a in asp_disp_r] or asp_disp_r[:3]
            nivel_tend_r = f_nivel_str if f_nivel_str != "Todos" else "Profesor curso"
            st.plotly_chart(
                plot_tendencia_curso(df_con_puntaje, default_asp_r, nivel_tend_r),
                use_container_width=True, config=_CHART_CONFIG,
            )
        else:  # Barras
            st.plotly_chart(
                plot_dimensiones_barras(df_dims, niveles_activos),
                use_container_width=True, config=_CHART_CONFIG,
            )

    # ── Tendencia por rubro ───────────────────────────────────────────────────
    with tab_tend:
        st.markdown(
            f'<h4 style="font-family:{_FONT_SERIF};color:{_TEXT_P1};margin:4px 0 10px">'
            f'Tendencia por rubro</h4>',
            unsafe_allow_html=True,
        )
        if "aspecto" in df_con_puntaje.columns:
            asp_disp = _ordered_aspects(
                df_con_puntaje["aspecto"].dropna().unique().tolist()
            )
        else:
            asp_disp = []

        _defaults = [
            "Coherencia",
            "Retroalimentación, monitoreo y criterios de calificación",
            "Trato a estudiantes",
        ]
        default_asp = [a for a in _defaults if a in asp_disp] or asp_disp[:3]

        sel_asp = st.multiselect(
            "Dimensiones a mostrar",
            options=asp_disp,
            default=default_asp,
            key="dd_asp",
        )
        nivel_tend = f_nivel_str if f_nivel_str != "Todos" else "Profesor curso"
        st.plotly_chart(
            plot_tendencia_curso(df_con_puntaje, sel_asp, nivel_tend),
            use_container_width=True, config=_CHART_CONFIG,
        )

    # ── Mapa de fortalezas ────────────────────────────────────────────────────
    with tab_mapa:
        st.markdown(
            f'<h4 style="font-family:{_FONT_SERIF};color:{_TEXT_P1};margin:4px 0 6px">'
            f'Mapa de fortalezas por curso y dimensión</h4>',
            unsafe_allow_html=True,
        )
        st.caption(
            "Puntaje promedio del Profesor por curso y dimensión · "
            "Nivel: Profesor curso · Sin registros NC ni sin puntaje."
        )
        st.plotly_chart(
            plot_heatmap_cursos(df_pdf),
            use_container_width=True, config=_CHART_CONFIG,
        )

    # ── Datos ─────────────────────────────────────────────────────────────────
    with tab_datos:
        with st.expander("Ver datos utilizados", expanded=False):
            cols_t = [c for c in [
                "periodo_label", "curso_codigo_base", nombre_col,
                "aspecto", "nivel_comparacion", "valor_central",
                "estado_calculo", "confianza_extraccion",
                "requiere_revision", "nota_validacion",
            ] if c and c in df_plot.columns]
            st.dataframe(
                df_plot[cols_t].reset_index(drop=True),
                use_container_width=True, hide_index=True,
            )
            st.caption(f"{len(df_plot)} filas mostradas.")


def _render_curso_kpis(df_con_puntaje: pd.DataFrame, df_curso_full: pd.DataFrame) -> None:
    """KPI cards para el curso seleccionado."""
    per_total = (
        df_curso_full["periodo_label"].nunique()
        if "periodo_label" in df_curso_full.columns else 0
    )
    per_puntaje = (
        df_con_puntaje["periodo_label"].nunique()
        if "periodo_label" in df_con_puntaje.columns else 0
    )

    df_prof = pd.DataFrame()
    if "nivel_comparacion" in df_con_puntaje.columns:
        df_prof = df_con_puntaje[
            df_con_puntaje["nivel_comparacion"] == "Profesor curso"
        ].copy()

    prom_global = None
    ultimo_puntaje = None
    mejor_dim = None
    fortalecer = None

    if not df_prof.empty and "valor_central" in df_prof.columns:
        g_mask = df_prof["aspecto"].astype(str).str.lower() == "puntaje global"
        g_vals = df_prof.loc[g_mask, "valor_central"].dropna()
        if not g_vals.empty:
            prom_global = round(g_vals.mean(), 1)
            if "periodo_order" in df_prof.columns:
                ult = df_prof.loc[g_mask].sort_values("periodo_order")
            else:
                ult = df_prof.loc[g_mask].sort_values("periodo_label")
            if not ult.empty:
                ultimo_puntaje = round(ult["valor_central"].iloc[-1], 1)

        ng_mask = ~(df_prof["aspecto"].astype(str).str.lower() == "puntaje global")
        dim_agg = df_prof[ng_mask].groupby("aspecto")["valor_central"].mean()
        if not dim_agg.empty:
            mejor_dim  = _dim_short(dim_agg.idxmax())
            fortalecer = _dim_short(dim_agg.idxmin())

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    def _k(col, label, val, foot="", highlight=False):
        color_v = _GOLD if highlight else _TEXT_P1
        bg = (f"background:{_BG_CARD_HI};border:1px solid {_BORDER_STR};"
              if highlight else f"background:{_BG_CARD};border:1px solid {_BORDER};")
        col.markdown(
            f'<div style="{bg}border-radius:14px;padding:16px 14px 12px;'
            f'font-family:{_FONT};height:100%">'
            f'<div style="font-size:11px;color:{_TEXT_P2};margin-bottom:5px">{label}</div>'
            f'<div style="font-size:24px;font-family:{_FONT_SERIF};font-weight:700;'
            f'color:{color_v};line-height:1.1">{"—" if val is None else str(val)}</div>'
            f'<div style="font-size:10.5px;color:{_TEXT_MUTED};margin-top:5px">{foot}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    _k(c1, "Periodos dictados",        per_total,      "en la base")
    _k(c2, "Periodos con puntaje",     per_puntaje,    "calculado OK")
    _k(c3, "Promedio global del curso", prom_global,   "puntaje global",   highlight=True)
    _k(c4, "Último puntaje del curso",  ultimo_puntaje, "último periodo")
    _k(c5, "Mejor dimensión",           mejor_dim,      "media más alta",   highlight=True)
    _k(c6, "Dimensión a fortalecer",    fortalecer,     "media más baja")


# ── Metodología ───────────────────────────────────────────────────────────────
def render_metodologia_section() -> None:
    st.markdown(
        f'<h3 style="font-family:{_FONT_SERIF};color:{_TEXT_P1};margin:4px 0 12px">'
        f'Nota metodológica</h3>',
        unsafe_allow_html=True,
    )

    items = [
        ("01", "Separación de modelos",
         "Los modelos usan escalas distintas. Comparar puntajes directamente sería "
         "metodológicamente incorrecto; se presentan por separado."),
        ("02", "Exclusión de registros",
         "Los registros 'Sin docencia / No aplica' y 'NC / No calculado' "
         "no se incluyen en promedios ni gráficas de desempeño."),
        ("03", "Fuente oficial",
         "El archivo Excel cargado es la única fuente de datos. "
         "Los datos de evaluación detallada son referencia auxiliar con indicador de confianza."),
        ("04", "Deltas calculados",
         "Si la columna delta existe en el Excel, se usa directamente. "
         "Si está vacía pero hay puntaje y benchmark, se calcula automáticamente."),
    ]

    cols = st.columns(4)
    for col, (num, titulo, texto) in zip(cols, items):
        with col:
            st.markdown(
                f'<div style="background:{_BG_CARD};border:1px solid {_BORDER};'
                f'border-radius:16px;padding:20px 18px;'
                f'box-shadow:0 2px 8px rgba(0,0,0,0.2);font-family:{_FONT}">'
                f'<div style="font-family:{_FONT_SERIF};font-size:22px;'
                f'font-weight:600;color:{_BORDER_STR};line-height:1">{num}</div>'
                f'<div style="font-size:14px;font-weight:600;color:{_TEXT_P1};'
                f'margin:9px 0 6px">{titulo}</div>'
                f'<div style="font-size:12.5px;color:{_TEXT_P2};line-height:1.5">{texto}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
