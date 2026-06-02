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

st.markdown(
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,400;0,600;0,700;1,400'
    '&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">',
    unsafe_allow_html=True,
)

# ── Importaciones del proyecto ────────────────────────────────────────────────
from app.utils.data_loader import load_excel
from app.utils.data_cleaning import clean, build_subsets, clean_detalle
from app.utils.metrics import compute
from app.utils.pdf_analysis import compute_pdf_metrics as compute_detalle_metrics
from app.components import sections

_DEFAULT_TEACHER = "el profesor"


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
        help="Sube el archivo de evaluaciones docentes (.xlsx)",
        label_visibility="visible",
    )

    st.markdown("---")

    # Valores por defecto para cuando no hay archivo cargado
    filtro_modelo   = None
    filtro_periodos = []
    mostrar_detalle = True

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
        df_detalle_raw = raw["df_detalle"]

        df_clean       = clean(df_general_raw)
        subsets        = build_subsets(df_clean)
        df_detalle     = clean_detalle(df_detalle_raw)
        metrics        = compute(subsets, df_clean)

        detalle_metrics = compute_detalle_metrics(df_detalle) if df_detalle is not None else {}
        teacher_name_detected = raw.get("teacher_name") or _DEFAULT_TEACHER

    # ── Sidebar: nombre del docente + checkbox detalle + filtros avanzados ────
    with sidebar_filtros_placeholder.container():
        nombre_docente = st.text_input(
            "Nombre del docente",
            value=teacher_name_detected,
            key="nombre_docente",
            help="Puedes editar el nombre que aparece en el dashboard.",
        )

        st.markdown("---")

        # Checkbox para mostrar u ocultar la pestaña de detalle auxiliar
        tiene_detalle = df_detalle is not None
        mostrar_detalle = st.checkbox(
            "Mostrar datos auxiliares",
            value=tiene_detalle,
            key="mostrar_detalle",
            disabled=not tiene_detalle,
            help=(
                "Muestra la pestaña con datos de BASE_DETALLE."
                if tiene_detalle
                else "El Excel no contiene la hoja BASE_DETALLE."
            ),
        )

        # Filtros avanzados — colapsados por defecto para no saturar la vista
        with st.expander("Filtros avanzados", expanded=False):
            st.caption(
                "Por defecto la app muestra toda la información. "
                "Usa estos filtros solo si quieres enfocar el análisis."
            )

            modelos_disp = sorted(
                df_clean["modelo_evaluacion"].dropna().unique().tolist()
            ) if "modelo_evaluacion" in df_clean.columns else []

            filtro_modelo = st.multiselect(
                "Modelo de evaluación",
                options=modelos_disp,
                default=modelos_disp,
                key="filtro_modelo",
            )

            # Periodos en orden cronológico real (no alfabético)
            if "periodo_label" in df_clean.columns and "periodo_order" in df_clean.columns:
                _pmap = (
                    df_clean[["periodo_label", "periodo_order"]]
                    .dropna().drop_duplicates()
                    .set_index("periodo_label")["periodo_order"]
                    .to_dict()
                )
                periodos_disp = sorted(
                    df_clean["periodo_label"].dropna().unique().tolist(),
                    key=lambda p: _pmap.get(p, 999_999),
                )
            elif "periodo_label" in df_clean.columns:
                periodos_disp = sorted(df_clean["periodo_label"].dropna().unique().tolist())
            else:
                periodos_disp = []

            filtro_periodos = st.multiselect(
                "Periodos",
                options=periodos_disp,
                default=[],
                key="filtro_periodos",
                placeholder="Todos los periodos",
            )

    # ── Aplicar filtros (solo los avanzados que aún existen) ─────────────────
    df_filtered = df_clean.copy()
    if filtro_modelo:
        df_filtered = df_filtered[df_filtered["modelo_evaluacion"].isin(filtro_modelo)]
    if filtro_periodos:
        df_filtered = df_filtered[df_filtered["periodo_label"].isin(filtro_periodos)]

    # Guardia: si los filtros vaciaron el df, mostrar aviso y usar datos completos
    if df_filtered[df_filtered["es_valido_desempeno"]].empty and not df_clean[df_clean["es_valido_desempeno"]].empty:
        st.warning(
            "La combinación de filtros seleccionada no devuelve registros válidos. "
            "Se muestran todos los datos disponibles.",
            icon="⚠️",
        )
        df_filtered = df_clean.copy()

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
        f"<h1 style='font-family:Spectral,Georgia,serif;color:#E0EEF2;"
        f"font-size:clamp(22px,3.5vw,40px);margin:4px 0 0;line-height:1.1'>"
        f"Evaluaciones docentes — {nombre_docente}</h1>",
        unsafe_allow_html=True,
    )
    anio_min = anio_max = ""
    if "anio" in df_clean.columns:
        anos_num = pd.to_numeric(df_clean["anio"], errors="coerce").dropna().astype(int)
        if not anos_num.empty:
            anio_min, anio_max = int(anos_num.min()), int(anos_num.max())
    rango = f"{anio_min}–{anio_max}" if anio_min and anio_min != anio_max else str(anio_min)
    st.markdown(
        f"<p style='font-size:15px;color:#8CBECB;margin-bottom:1.2rem'>"
        f"Análisis de desempeño y benchmarks institucionales · {rango}</p>",
        unsafe_allow_html=True,
    )

    # ── Navegación por tabs ───────────────────────────────────────────────────
    tab_labels = ["📊 Resumen ejecutivo"]
    if df_detalle is not None and mostrar_detalle:
        tab_labels.append("📋 Datos auxiliares")

    tabs = st.tabs(tab_labels)

    # ── Tab 1: Resumen ejecutivo ──────────────────────────────────────────────
    with tabs[0]:
        sections.render_hero(metrics_f)

        st.markdown('<div class="sec-divider"></div>', unsafe_allow_html=True)
        sections.render_kpis(metrics_f)

        st.markdown('<div class="sec-divider"></div>', unsafe_allow_html=True)
        df_actual_f = subsets_f.get("df_modelo_actual", pd.DataFrame())
        sections.render_modelo_actual_section(df_actual_f, metrics_f)

        df_anterior_f = subsets_f.get("df_modelo_anterior", pd.DataFrame())
        if not df_anterior_f.empty:
            st.markdown('<div class="sec-divider"></div>', unsafe_allow_html=True)
            sections.render_modelo_anterior_section(df_anterior_f, metrics_f)

        st.markdown('<div class="sec-divider"></div>', unsafe_allow_html=True)
        sections.render_comparacion_relativa_section(metrics_f)

        st.markdown('<div class="sec-divider"></div>', unsafe_allow_html=True)
        sections.render_metodologia_section()

        st.markdown(
            '<div style="margin-top:3rem;padding:22px 0;border-top:1px solid #1A3D4E;'
            'font-size:12px;color:#537F8A;text-align:center;'
            'font-family:IBM Plex Sans,system-ui,sans-serif">'
            'Dashboard generado desde el archivo Excel cargado · '
            'Ningún dato es almacenado por la aplicación.'
            '</div>',
            unsafe_allow_html=True,
        )

    # ── Tab 2: Datos auxiliares (BASE_DETALLE) ────────────────────────────────
    if df_detalle is not None and mostrar_detalle and len(tabs) > 1:
        with tabs[1]:
            sections.render_detalle_section(df_detalle, detalle_metrics)
