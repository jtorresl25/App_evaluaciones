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


# ── Función de exportación del sidebar ────────────────────────────────────────
def _export_section(
    placeholder,
    nombre_docente: str,
    filtro_modelo: list,
    filtro_periodos: list,
    df_clean,
    df_filtered,
    subsets_f: dict,
    metrics_f: dict,
    uploaded_file_name: str,
    df_detalle=None,
) -> None:
    """
    Renderiza la sección de exportación en el placeholder del sidebar.

    Patrón de replicación para otras páginas:
        1. Ajustar figures_dict con las figuras de tu página.
        2. Ajustar la llamada a build_period_table si tu DataFrame es distinto.
        3. Pasar el placeholder y los datos correspondientes.
    """
    import re as _re
    from app.utils.export_report import (
        build_current_view_pdf,
        build_figures_zip,
        format_filters,
        format_kpis_from_metrics,
        build_period_table,
    )
    from app.utils.plots import (
        plot_modelo_actual_line,
        plot_modelo_actual_delta,
        plot_modelo_anterior_line,
        plot_modelo_anterior_delta,
        plot_comparacion_relativa,
    )

    with placeholder.container():
        st.markdown("---")
        st.markdown(
            '<div style="font-size:12px;font-weight:600;color:#3AAFC4;margin-bottom:2px">'
            "📄 Exportar reporte"
            "</div>",
            unsafe_allow_html=True,
        )
        st.caption("Resumen ejecutivo · vista actual")

        # Invalidar caché cuando cambian los filtros o el archivo
        _fhash = hash((
            uploaded_file_name,
            tuple(sorted(filtro_modelo or [])),
            tuple(sorted(filtro_periodos or [])),
        ))
        if st.session_state.get("_export_fhash") != _fhash:
            st.session_state.pop("_pdf_bytes", None)
            st.session_state.pop("_zip_bytes", None)
            st.session_state["_export_fhash"] = _fhash

        if st.button("Preparar reporte", use_container_width=True, key="btn_prep_report"):
            # ── Recolectar figuras de la vista actual ─────────────────────────
            # Para otras páginas: reemplaza este dict con las figuras de tu tab.
            _df_act = subsets_f.get("df_modelo_actual", pd.DataFrame())
            _df_ant = subsets_f.get("df_modelo_anterior", pd.DataFrame())

            _figs: dict = {}
            if not _df_act.empty:
                _figs["Tendencia modelo actual"]      = plot_modelo_actual_line(_df_act)
                _figs["Deltas vs benchmarks (actual)"] = plot_modelo_actual_delta(_df_act)
            if not _df_ant.empty:
                _figs["Tendencia modelo anterior"]         = plot_modelo_anterior_line(_df_ant)
                _figs["Deltas vs benchmarks (anterior)"]   = plot_modelo_anterior_delta(_df_ant)
            if metrics_f:
                _figs["Comparacion relativa"] = plot_comparacion_relativa(metrics_f)

            _filters = format_filters(nombre_docente, filtro_modelo, filtro_periodos, df_clean)
            _kpis    = format_kpis_from_metrics(metrics_f)
            _table   = build_period_table(df_filtered)

            try:
                with st.spinner("Generando PDF…"):
                    st.session_state["_pdf_bytes"] = build_current_view_pdf(
                        page_title=f"Resumen ejecutivo — {nombre_docente}",
                        filters=_filters,
                        kpis=_kpis,
                        figures=_figs,
                        tables=[_table] if _table else None,
                    )
                with st.spinner("Generando PNGs…"):
                    st.session_state["_zip_bytes"] = build_figures_zip(_figs)
            except ImportError as _e:
                st.error(f"Falta instalar: {_e}")
            except Exception as _e:
                st.error(f"Error al generar: {_e}")

        _pdf = st.session_state.get("_pdf_bytes")
        _zip = st.session_state.get("_zip_bytes")

        if _pdf or _zip:
            # Nombre de archivo seguro (sin tildes ni espacios)
            _fn = _re.sub(r"[^a-z0-9]", "_",
                          nombre_docente.lower().encode("ascii", "ignore").decode())
            _fn = _re.sub(r"_+", "_", _fn).strip("_")[:30] or "docente"
            _date = pd.Timestamp.now().strftime("%Y%m%d")

            if _pdf:
                st.download_button(
                    label="📄 Descargar reporte PDF",
                    data=_pdf,
                    file_name=f"reporte_{_fn}_{_date}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key="btn_dl_pdf",
                )

            # Solo mostrar ZIP si tiene contenido real (ZIP vacío ≈ 22 bytes)
            if _zip and len(_zip) > 50:
                st.download_button(
                    label="📦 Descargar gráficos PNG",
                    data=_zip,
                    file_name=f"graficos_{_fn}_{_date}.zip",
                    mime="application/zip",
                    use_container_width=True,
                    key="btn_dl_zip",
                )
            elif _zip and len(_zip) <= 50:
                st.caption(
                    "Los gráficos PNG requieren kaleido instalado: "
                    "`pip install kaleido`"
                )
        else:
            st.caption("Haz clic en 'Preparar reporte' para activar las descargas.")

        # ── Reporte completo por cursos ───────────────────────────────────────
        st.markdown("---")
        st.markdown(
            '<div style="font-size:12px;font-weight:600;color:#3AAFC4;margin-bottom:2px">'
            "📚 Reporte completo por cursos"
            "</div>",
            unsafe_allow_html=True,
        )

        # Determinar si hay cursos disponibles y cuántos
        _n_cursos = 0
        _tiene_detalle = df_detalle is not None and not df_detalle.empty
        _df_ci = subsets_f.get("df_cursos_individuales", pd.DataFrame())

        if _tiene_detalle and "curso_codigo_base" in df_detalle.columns:
            _n_cursos = int(df_detalle["curso_codigo_base"].dropna().nunique())
        elif not _df_ci.empty:
            _nc_col = "nombre_curso" if "nombre_curso" in _df_ci.columns else "codigo_curso"
            _n_cursos = int(_df_ci[_nc_col].dropna().nunique()) if _nc_col in _df_ci.columns else 0

        if _n_cursos == 0:
            st.caption("Sin cursos individuales disponibles en los datos actuales.")
        else:
            fuente = "BASE_DETALLE" if _tiene_detalle else "BASE_GENERAL"
            st.caption(f"{_n_cursos} curso{'s' if _n_cursos != 1 else ''} · fuente: {fuente}")

            if st.button(
                "Generar reporte completo",
                use_container_width=True,
                key="btn_gen_full",
                help="Genera un PDF con secciones detalladas por cada curso.",
            ):
                from app.utils.export_report import build_full_courses_pdf, format_filters

                _f_full = format_filters(nombre_docente, filtro_modelo, filtro_periodos, df_clean)
                try:
                    with st.spinner(f"Generando reporte de {_n_cursos} cursos…"):
                        st.session_state["_full_pdf_bytes"] = build_full_courses_pdf(
                            df_general=df_filtered,
                            df_detalle=df_detalle if _tiene_detalle else None,
                            general_filters=_f_full,
                            metrics=metrics_f,
                            subsets=subsets_f,
                            professor_name=nombre_docente,
                        )
                    st.session_state["_full_pdf_fhash"] = _fhash
                except ImportError as _e:
                    st.error(f"Falta instalar: {_e}")
                except Exception as _e:
                    st.error(f"Error al generar: {_e}")

            # Invalidar reporte completo cuando cambian filtros
            if st.session_state.get("_full_pdf_fhash") != _fhash:
                st.session_state.pop("_full_pdf_bytes", None)

            _full_pdf = st.session_state.get("_full_pdf_bytes")
            if _full_pdf:
                _fn_f = _re.sub(r"[^a-z0-9]", "_",
                                nombre_docente.lower().encode("ascii", "ignore").decode())
                _fn_f = _re.sub(r"_+", "_", _fn_f).strip("_")[:30] or "docente"
                _date_f = pd.Timestamp.now().strftime("%Y%m%d")
                st.download_button(
                    label="📚 Descargar reporte completo PDF",
                    data=_full_pdf,
                    file_name=f"reporte_completo_{_fn_f}_{_date_f}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key="btn_dl_full",
                )
            else:
                st.caption("Genera el reporte para activar la descarga.")


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
    sidebar_export_placeholder  = st.empty()  # llenado después de cargar datos

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

    # ── Sidebar: sección de exportación ──────────────────────────────────────
    # Se rellena aquí (después de procesar datos) para tener acceso a
    # metrics_f, subsets_f, df_filtered, nombre_docente y filtros activos.
    # Para replicarlo en otras páginas: copiar este bloque y ajustar
    # las figuras (figures_dict) y la tabla (build_period_table(df_tu_pagina)).
    _export_section(
        placeholder=sidebar_export_placeholder,
        nombre_docente=nombre_docente,
        filtro_modelo=filtro_modelo,
        filtro_periodos=filtro_periodos,
        df_clean=df_clean,
        df_filtered=df_filtered,
        subsets_f=subsets_f,
        metrics_f=metrics_f,
        uploaded_file_name=uploaded_file.name,
        df_detalle=df_detalle,
    )
