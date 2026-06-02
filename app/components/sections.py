import streamlit as st
import pandas as pd
from app.utils import plots
from app.components.kpi_cards import render_kpi_row_hero, render_kpi_row_secondary

# ── Paleta oscura (coherente con kpi_cards y plots) ───────────────────────────
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


# ── Hero / Conclusión ejecutiva ───────────────────────────────────────────────
def render_hero(metrics: dict) -> None:
    pct_fac = metrics.get("pct_sobre_facultad_actual")
    pct_uni = metrics.get("pct_sobre_universidad_actual")

    # ── Construcción dinámica del mensaje ────────────────────────────────────
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
        f"""
        <div style="
          background:linear-gradient(135deg,#071520 0%,#0A2230 40%,#0E2E40 100%);
          border:1px solid {_BORDER_STR};
          border-left:4px solid {_GOLD};
          border-radius:18px;
          padding:34px 38px;
          position:relative;
          overflow:hidden;
          margin-bottom:1.2rem;
          box-shadow:0 12px 40px rgba(0,0,0,0.4);
        ">
          <div style="
            position:absolute;right:-40px;top:-40px;
            width:200px;height:200px;border-radius:50%;
            background:radial-gradient(circle,rgba(212,168,67,0.14),transparent 65%);
            pointer-events:none;
          "></div>
          <div style="display:flex;gap:26px;align-items:center;flex-wrap:wrap;position:relative;z-index:1">
            <div style="
              width:96px;height:96px;border-radius:50%;flex-shrink:0;
              background:radial-gradient(circle at 35% 30%,#D4A843,#A9823C 75%);
              display:flex;flex-direction:column;align-items:center;justify-content:center;
              text-align:center;
              box-shadow:0 0 0 2px rgba(212,168,67,0.3),0 8px 24px rgba(169,130,60,0.5);
            ">
              <span style="font-family:{_FONT_SERIF};font-weight:700;font-size:24px;color:#fff;line-height:1">{pct_display}</span>
              <span style="font-size:7.5px;letter-spacing:.15em;color:rgba(255,255,255,.88);margin-top:3px;text-transform:uppercase">Periodos</span>
            </div>
            <div style="flex:1;min-width:220px">
              <span style="font-size:10.5px;letter-spacing:.2em;text-transform:uppercase;color:{_GOLD};font-weight:500;font-family:{_FONT}">Conclusión ejecutiva</span>
              <h2 style="
                color:{_TEXT_P1};font-size:clamp(16px,2vw,22px);
                line-height:1.3;margin:10px 0 0;
                font-family:{_FONT_SERIF};font-weight:600;
              ">{headline}</h2>
              <p style="margin-top:10px;color:{_TEXT_P2};font-size:13.5px;font-family:{_FONT};line-height:1.55">{sub_text}</p>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Estado inicial (sin archivo) ──────────────────────────────────────────────
def render_upload_state() -> None:
    st.markdown(
        f"""
        <div style="
          background:{_BG_CARD};border:1.5px dashed {_BORDER_STR};
          border-radius:18px;padding:48px 40px;text-align:center;
          box-shadow:0 4px 20px rgba(0,0,0,0.25);margin-top:2rem;
        ">
          <div style="font-size:11px;letter-spacing:.2em;text-transform:uppercase;
            color:{_TEAL};font-weight:500;margin-bottom:12px;font-family:{_FONT}">
            Herramienta de análisis docente
          </div>
          <h2 style="font-family:{_FONT_SERIF};font-weight:600;color:{_TEXT_P1};
            font-size:28px;margin:0 0 14px;line-height:1.2">
            Dashboard de evaluaciones docentes
          </h2>
          <p style="color:{_TEXT_P2};font-size:15px;max-width:540px;margin:0 auto;font-family:{_FONT};line-height:1.55">
            Carga un archivo Excel para visualizar el desempeño docente histórico,
            comparar resultados frente a benchmarks institucionales y explorar el detalle por curso.
          </p>
          <p style="margin-top:12px;font-size:12.5px;color:{_TEXT_MUTED};font-family:{_FONT}">
            La app no almacena ningún dato. El análisis se genera únicamente en tu sesión local.
          </p>
          <div style="
            display:inline-flex;align-items:center;gap:8px;margin-top:18px;
            font-size:12.5px;color:{_GREEN};background:{_GREEN_TINT};
            padding:7px 16px;border-radius:30px;font-family:{_FONT};
            border:1px solid rgba(77,184,138,0.2);
          ">
            🔒 Privacidad garantizada — ningún dato sale de tu equipo
          </div>
        </div>
        """,
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
        st.plotly_chart(
            plots.plot_modelo_actual_line(df),
            use_container_width=True, config=_CHART_CONFIG,
        )
    with col_right:
        _graph_label("Diferencia frente a benchmarks (Δ por periodo)")
        st.plotly_chart(
            plots.plot_modelo_actual_delta(df),
            use_container_width=True, config=_CHART_CONFIG,
        )

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
        _interpret_box(f"📊 Diferencia promedio en el modelo actual: {' · '.join(partes)}")


# ── Contexto histórico (modelo anterior) ─────────────────────────────────────
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
        st.plotly_chart(
            plots.plot_modelo_anterior_line(df),
            use_container_width=True, config=_CHART_CONFIG,
        )
    with col_right:
        _graph_label("Diferencia histórica frente a benchmarks")
        st.plotly_chart(
            plots.plot_modelo_anterior_delta(df),
            use_container_width=True, config=_CHART_CONFIG,
        )


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
        st.plotly_chart(
            plots.plot_comparacion_relativa(metrics),
            use_container_width=True, config=_CHART_CONFIG,
        )
    with col2:
        st.write("")
        _metric_mini("% sobre Facultad (actual)",      metrics.get("pct_sobre_facultad_actual"),      "%")
        _metric_mini("% sobre Universidad (actual)",   metrics.get("pct_sobre_universidad_actual"),   "%")
        _divider()
        _metric_mini("% sobre Facultad (anterior)",    metrics.get("pct_sobre_facultad_anterior"),    "%", muted=True)
        _metric_mini("% sobre Universidad (anterior)", metrics.get("pct_sobre_universidad_anterior"), "%", muted=True)


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


# ── Cursos ────────────────────────────────────────────────────────────────────
def render_cursos_section(df: pd.DataFrame, metrics: dict) -> None:
    """
    Muestra ranking de cursos individuales.
    - Separa por modelo (escalas incomparables).
    - Nunca incluye registros de nivel agregado/periodo.
    - El modelo actual en este dataset solo tiene registros agregados → se informa.
    """
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

    # Construir tabs solo para los modelos que tienen datos individuales
    tabs_labels = []
    if has_act:
        tabs_labels.append("Modelo actual")
    if has_ant:
        lab_display = label_anterior if label_anterior else "Modelo anterior"
        tabs_labels.append(f"{lab_display}")

    if not tabs_labels:
        st.info("No hay cursos individuales para mostrar.")
        return

    tabs = st.tabs(tabs_labels)
    tab_idx = 0

    if has_act:
        with tabs[tab_idx]:
            _render_cursos_tab(df_act, "Escala del modelo actual")
        tab_idx += 1

    if has_ant:
        with tabs[tab_idx]:
            escala_txt = "Escala /5 — modelo anterior"
            _render_cursos_tab(df_ant, escala_txt)


def _render_cursos_tab(df: pd.DataFrame, escala_label: str) -> None:
    st.markdown(
        f'<p style="font-size:12px;color:{_TEXT_MUTED};font-family:{_FONT};'
        f'margin-bottom:8px">📐 {escala_label}</p>',
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
            .rename(columns={
                nombre_col: "Curso",
                "mean": "Promedio",
                "count": "Semestres",
            })
            .sort_values("Promedio", ascending=False)
        )
        tabla["Promedio"] = tabla["Promedio"].round(2)
        st.dataframe(tabla, use_container_width=True, hide_index=True)


# ── Detalle PDF ───────────────────────────────────────────────────────────────
def render_pdf_detail_section(df_pdf: pd.DataFrame) -> None:
    st.markdown(
        f'<h3 style="font-family:{_FONT_SERIF};color:{_TEXT_P1};margin:4px 0 8px">'
        f'Detalle auxiliar — datos extraídos de PDF</h3>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div style="background:{_BG_CARD};border:1px solid {_BORDER};border-radius:12px;'
        f'padding:13px 18px;font-size:13px;color:{_TEXT_P2};margin-bottom:14px;font-family:{_FONT};line-height:1.5">'
        f'ℹ️ Datos de extracción automática — referencia auxiliar únicamente. '
        f'No alimentan KPIs principales. Verifique <em>confianza</em> y <em>estado_revision</em> '
        f'antes de citar cifras individuales.</div>',
        unsafe_allow_html=True,
    )

    if df_pdf is None or df_pdf.empty:
        st.info("No hay datos PDF disponibles en este archivo.")
        return

    cols_show = [c for c in [
        "periodo", "nombre_curso", "aspecto", "puntaje",
        "limite_inferior", "limite_superior", "lectura_cualitativa",
        "confianza", "estado_revision",
    ] if c in df_pdf.columns]

    filtro_curso = "Todos"
    if "nombre_curso" in df_pdf.columns:
        opciones = ["Todos"] + sorted(df_pdf["nombre_curso"].dropna().unique().tolist())
        filtro_curso = st.selectbox("Filtrar por curso (PDF)", opciones, key="pdf_curso")

    df_show = df_pdf[cols_show].copy()
    if filtro_curso != "Todos" and "nombre_curso" in df_show.columns:
        df_show = df_show[df_show["nombre_curso"] == filtro_curso]

    st.dataframe(df_show, use_container_width=True, hide_index=True)
    st.caption(f"{len(df_show)} filas mostradas de {len(df_pdf)} en BASE_DETALLE_PDF.")


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
         "BASE_DETALLE_PDF es referencia auxiliar con indicador de confianza."),
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
