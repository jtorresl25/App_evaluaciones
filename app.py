import streamlit as st
import pandas as pd
from pathlib import Path

# ── Configuración de página ───────────────────────────────────────────────────
st.set_page_config(
    page_title="Dashboard de evaluaciones docentes",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
_CSS_PATH = Path(__file__).parent / "app" / "styles" / "main.css"
if _CSS_PATH.exists():
    css = _CSS_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

# Google Fonts (Spectral + IBM Plex Sans)
st.markdown(
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,400;0,600;0,700;1,400'
    '&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">',
    unsafe_allow_html=True,
)

# ── Importaciones del proyecto ────────────────────────────────────────────────
from app.utils.data_loader import load_excel
from app.utils.data_cleaning import clean, build_subsets, clean_pdf
from app.utils.metrics import compute
from app.components import sections


# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div style="font-family:Spectral,Georgia,serif;font-size:19px;font-weight:600;'
        'color:#E0EEF2;margin-bottom:2px">📊 Dashboard docente</div>',
        unsafe_allow_html=True,
    )
    st.caption("Análisis de evaluaciones históricas")
    st.markdown("---")

    uploaded_file = st.file_uploader(
        "Cargar archivo Excel",
        type=["xlsx", "xls"],
        help="Sube el archivo Evaluaciones_Docentes_VF_base_streamlit.xlsx",
        label_visibility="visible",
    )

    st.markdown("---")

    # Filtros (se activan solo con datos)
    filtro_modelo = None
    filtro_cursos = []
    filtro_periodos = []
    mostrar_pdf = False

    if uploaded_file is not None:
        st.markdown("**Filtros**")

    # Placeholder para filtros dinámicos (llenados más abajo tras cargar datos)
    sidebar_filtros_placeholder = st.empty()

    st.markdown("---")
    st.markdown(
        '<div style="font-size:12px;color:#537F8A;line-height:1.5">'
        '🔒 La app no almacena datos. El análisis se genera desde el archivo cargado.'
        '</div>',
        unsafe_allow_html=True,
    )


# ── MAIN ──────────────────────────────────────────────────────────────────────
if uploaded_file is None:
    # ── Estado inicial — sin archivo ──────────────────────────────────────────
    st.markdown(
        '<span style="font-size:11px;letter-spacing:.2em;text-transform:uppercase;'
        'color:#3AAFC4;font-weight:500;margin-top:2rem;display:block">Herramienta de análisis</span>',
        unsafe_allow_html=True,
    )
    st.markdown(
        "<h1 style='font-family:Spectral,Georgia,serif;color:#E0EEF2;"
        "font-size:clamp(26px,4vw,44px);margin:4px 0 0;line-height:1.1'>"
        "Dashboard de evaluaciones docentes</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='font-size:15px;color:#8CBECB;margin-bottom:1.5rem'>"
        "Carga un Excel para comenzar el análisis.</p>",
        unsafe_allow_html=True,
    )
    sections.render_upload_state()

else:
    # ── Cargar y limpiar datos ────────────────────────────────────────────────
    with st.spinner("Procesando el archivo…"):
        try:
            raw = load_excel(uploaded_file)
        except RuntimeError as e:
            st.error(str(e))
            st.stop()

        df_general_raw = raw["df_general"]
        df_pdf_raw = raw["df_pdf"]

        df_clean = clean(df_general_raw)
        subsets = build_subsets(df_clean)
        df_pdf = clean_pdf(df_pdf_raw)
        metrics = compute(subsets, df_clean)

    # ── Filtros dinámicos en sidebar ──────────────────────────────────────────
    with sidebar_filtros_placeholder.container():
        modelos_disp = sorted(
            df_clean["modelo_evaluacion"].dropna().unique().tolist()
        ) if "modelo_evaluacion" in df_clean.columns else []

        filtro_modelo = st.multiselect(
            "Modelo de evaluación",
            options=modelos_disp,
            default=modelos_disp,
            key="filtro_modelo",
        )

        cursos_disp = sorted(
            df_clean[df_clean["es_valido_desempeno"]]["nombre_curso"].dropna().unique().tolist()
        ) if "nombre_curso" in df_clean.columns else []

        filtro_cursos = st.multiselect(
            "Cursos (opcional)",
            options=cursos_disp,
            default=[],
            key="filtro_cursos",
            placeholder="Todos los cursos",
        )

        periodos_disp = sorted(
            df_clean["periodo_label"].dropna().unique().tolist()
        ) if "periodo_label" in df_clean.columns else []

        filtro_periodos = st.multiselect(
            "Periodos (opcional)",
            options=periodos_disp,
            default=[],
            key="filtro_periodos",
            placeholder="Todos los periodos",
        )

        if df_pdf is not None:
            mostrar_pdf = st.checkbox("Mostrar detalle PDF", value=False, key="mostrar_pdf")

    # ── Aplicar filtros ───────────────────────────────────────────────────────
    df_filtered = df_clean.copy()

    if filtro_modelo:
        df_filtered = df_filtered[df_filtered["modelo_evaluacion"].isin(filtro_modelo)]

    if filtro_cursos:
        df_filtered = df_filtered[df_filtered["nombre_curso"].isin(filtro_cursos)]

    if filtro_periodos:
        df_filtered = df_filtered[df_filtered["periodo_label"].isin(filtro_periodos)]

    # Recalcular subsets y métricas con datos filtrados
    subsets_f = build_subsets(df_filtered)
    metrics_f = compute(subsets_f, df_filtered)

    # ── Header de la página ───────────────────────────────────────────────────
    st.markdown(
        '<span style="font-size:11px;letter-spacing:.2em;text-transform:uppercase;'
        'color:#3AAFC4;font-weight:500;margin-top:1.5rem;display:block">'
        'Dashboard de evaluaciones docentes</span>',
        unsafe_allow_html=True,
    )
    st.markdown(
        "<h1 style='font-family:Spectral,Georgia,serif;color:#E0EEF2;"
        "font-size:clamp(22px,3.5vw,40px);margin:4px 0 0;line-height:1.1'>"
        "Evaluaciones docentes históricas</h1>",
        unsafe_allow_html=True,
    )
    # Detectar rango de años desde los datos para hacer el subtítulo dinámico
    anio_min = anio_max = ""
    if "anio" in df_clean.columns:
        anos = df_clean["anio"].dropna().astype(int)
        if not anos.empty:
            anio_min, anio_max = int(anos.min()), int(anos.max())
    rango = f"{anio_min}–{anio_max}" if anio_min and anio_min != anio_max else str(anio_min)
    st.markdown(
        f"<p style='font-size:15px;color:#8CBECB;margin-bottom:1.2rem'>"
        f"Análisis de desempeño y benchmarks institucionales · {rango}</p>",
        unsafe_allow_html=True,
    )

    # ── 1. Hero / Conclusión ejecutiva ────────────────────────────────────────
    sections.render_hero(metrics_f)

    # ── 2. KPIs ───────────────────────────────────────────────────────────────
    st.markdown('<div class="sec-divider"></div>', unsafe_allow_html=True)
    sections.render_kpis(metrics_f)

    # ── 3. Modelo actual ──────────────────────────────────────────────────────
    st.markdown('<div class="sec-divider"></div>', unsafe_allow_html=True)
    df_actual_f = subsets_f.get("df_modelo_actual", pd.DataFrame())
    sections.render_modelo_actual_section(df_actual_f, metrics_f)

    # ── 4. Contexto histórico — modelo anterior ───────────────────────────────
    df_anterior_f = subsets_f.get("df_modelo_anterior", pd.DataFrame())
    if not df_anterior_f.empty:
        st.markdown('<div class="sec-divider"></div>', unsafe_allow_html=True)
        sections.render_modelo_anterior_section(df_anterior_f, metrics_f)

    # ── 5. Comparación relativa ───────────────────────────────────────────────
    st.markdown('<div class="sec-divider"></div>', unsafe_allow_html=True)
    sections.render_comparacion_relativa_section(metrics_f)

    # ── 6. Cursos individuales ────────────────────────────────────────────────
    st.markdown('<div class="sec-divider"></div>', unsafe_allow_html=True)
    df_cursos_f = subsets_f.get("df_cursos_individuales", pd.DataFrame())
    sections.render_cursos_section(df_cursos_f, metrics_f)

    # ── 7. Detalle PDF (solo si existe y el checkbox está activo) ─────────────
    if df_pdf is not None and mostrar_pdf:
        st.markdown('<div class="sec-divider"></div>', unsafe_allow_html=True)
        sections.render_pdf_detail_section(df_pdf)

    # ── 8. Metodología ────────────────────────────────────────────────────────
    st.markdown('<div class="sec-divider"></div>', unsafe_allow_html=True)
    sections.render_metodologia_section()

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown(
        '<div style="margin-top:3rem;padding:22px 0;border-top:1px solid #1A3D4E;'
        'font-size:12px;color:#537F8A;text-align:center;font-family:IBM Plex Sans,system-ui,sans-serif">'
        'Dashboard generado desde el archivo Excel cargado · '
        'Ningún dato es almacenado por la aplicación.'
        '</div>',
        unsafe_allow_html=True,
    )
