"""
Utilidades de exportación — reportes PDF y archivos ZIP de imágenes.

Uso básico desde cualquier página:

    from app.utils.export_report import (
        build_current_view_pdf,
        build_figures_zip,
        format_filters,
        format_kpis_from_metrics,
        build_period_table,
    )

    figures = {
        "Tendencia modelo actual":     plot_modelo_actual_line(df_actual),
        "Deltas vs benchmarks":        plot_modelo_actual_delta(df_actual),
        "Comparación relativa":        plot_comparacion_relativa(metrics),
    }

    pdf_bytes = build_current_view_pdf(
        page_title=f"Resumen ejecutivo — {nombre_docente}",
        filters=format_filters(nombre_docente, filtro_modelo, filtro_periodos, df_clean),
        kpis=format_kpis_from_metrics(metrics_f),
        figures=figures,
        tables=[build_period_table(df_filtered)],
    )

    st.download_button("📄 PDF", data=pdf_bytes, file_name="reporte.pdf",
                       mime="application/pdf")

Requerimientos:
    pip install reportlab>=4.0 kaleido>=0.2.1 Pillow>=10.0
"""

from __future__ import annotations

import io
import re
import zipfile
from datetime import datetime
from typing import Optional

import plotly.graph_objects as go


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Plotly → PNG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def fig_to_png_bytes(
    fig: go.Figure,
    width: int = 960,
    height: int = 460,
    scale: int = 2,
) -> Optional[bytes]:
    """
    Exporta una figura Plotly a PNG bytes usando kaleido.
    Devuelve None si kaleido no está instalado o si la exportación falla.
    La figura se convierte a tema blanco antes de exportar.
    """
    if fig is None:
        return None
    try:
        import kaleido  # noqa: F401 — verificación de presencia
        return _white_theme(fig).to_image(
            format="png", width=width, height=height, scale=scale
        )
    except ImportError:
        return None
    except Exception:
        return None


def _white_theme(fig: go.Figure) -> go.Figure:
    """Copia de la figura con fondo blanco y ejes oscuros, apta para PDF."""
    copy = go.Figure(fig)
    copy.update_layout(
        paper_bgcolor="white",
        plot_bgcolor="#F7FAFB",
        font_color="#1A2A35",
        legend=dict(font=dict(color="#1A2A35")),
    )
    copy.update_xaxes(
        tickfont=dict(color="#2A4A5A"),
        linecolor="#CBD5E0",
        gridcolor="#E8EFF3",
    )
    copy.update_yaxes(
        tickfont=dict(color="#2A4A5A"),
        linecolor="#CBD5E0",
        gridcolor="#E8EFF3",
    )
    return copy


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ZIP de PNGs
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def build_figures_zip(figures: dict) -> bytes:
    """
    Genera un archivo ZIP con un PNG por figura.

    Parameters
    ----------
    figures : dict[str, go.Figure | None]
        Nombre del archivo (sin extensión) → figura Plotly.
        Los None y las figuras que fallen se omiten silenciosamente.

    Returns
    -------
    bytes — archivo ZIP listo para st.download_button.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, fig in (figures or {}).items():
            if fig is None:
                continue
            png = fig_to_png_bytes(fig)
            if png is not None:
                zf.writestr(f"{_safe_filename(name)}.png", png)
    return buf.getvalue()


def _safe_filename(name: str) -> str:
    """Convierte un nombre cualquiera en nombre de archivo ASCII seguro."""
    name = str(name).lower().strip()
    # Normalizar caracteres acentuados
    for src, dst in [
        ("áàâä", "a"), ("éèêë", "e"), ("íìîï", "i"),
        ("óòôö", "o"), ("úùûü", "u"), ("ñ", "n"),
    ]:
        for ch in src:
            name = name.replace(ch, dst)
    name = re.sub(r"[^a-z0-9_\-]", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return (name[:60] or "figura")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PDF principal
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def build_current_view_pdf(
    page_title: str,
    filters: dict,
    kpis: dict,
    figures: dict,
    tables: Optional[list] = None,
    notes: Optional[str] = None,
) -> bytes:
    """
    Construye un PDF profesional con los datos de la vista actual.

    Parameters
    ----------
    page_title : str
        Título de la página en el encabezado del PDF.
    filters : dict[str, str]
        Filtros activos ya formateados.
        Ej.: {"Docente": "Juan Pérez", "Periodos": "2022-1 – 2025-2"}.
    kpis : dict[str, str]
        Métricas clave ya formateadas como strings.
        Ej.: {"% sobre Facultad": "80%"}.
    figures : dict[str, go.Figure | None]
        Nombre visible (usado como encabezado de sección) → figura Plotly.
        Los None se omiten con un aviso.
    tables : list[dict], optional
        Lista de tablas. Cada dict: {"title": str, "headers": list, "rows": list[list]}.
    notes : str, optional
        Texto de notas interpretativas al final del reporte.

    Returns
    -------
    bytes — PDF listo para st.download_button.

    Raises
    ------
    ImportError  Si reportlab no está instalado.
    """
    return _pdf_reportlab(page_title, filters, kpis, figures, tables, notes)


# ── Implementación con ReportLab ──────────────────────────────────────────────

def _s(text) -> str:
    """Convierte a string seguro para ReportLab."""
    return str(text) if text is not None else "—"


def _pdf_reportlab(
    page_title: str,
    filters: dict,
    kpis: dict,
    figures: dict,
    tables: Optional[list],
    notes: Optional[str],
) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer,
        Image as RLImage, Table as RLTable,
        TableStyle, HRFlowable, KeepTogether,
    )
    from reportlab.lib.enums import TA_CENTER

    PAGE_W, PAGE_H = A4
    MARGIN = 2.0 * cm
    CONTENT_W = PAGE_W - 2 * MARGIN

    # ── Colores ───────────────────────────────────────────────────────────────
    C_NAVY   = colors.HexColor("#0D2733")
    C_TEAL   = colors.HexColor("#3AAFC4")
    C_TEXT   = colors.HexColor("#1A2A35")
    C_MUTED  = colors.HexColor("#5A7A87")
    C_LIGHT  = colors.HexColor("#EDF5F8")
    C_BORDER = colors.HexColor("#C4D8E0")
    C_WHITE  = colors.white

    # ── Estilos ───────────────────────────────────────────────────────────────
    _b = dict(fontName="Helvetica", textColor=C_TEXT, leading=15)

    def _sty(**kw) -> ParagraphStyle:
        return ParagraphStyle("_", **{**_b, **kw})

    S_EYEBROW = _sty(fontSize=8,  textColor=C_TEAL, fontName="Helvetica-Bold",
                     letterSpacing=0.8, spaceAfter=3)
    S_TITLE   = _sty(fontSize=20, textColor=C_NAVY, fontName="Helvetica-Bold",
                     leading=24,  spaceAfter=4)
    S_SUB     = _sty(fontSize=10, textColor=C_MUTED, spaceAfter=14)
    S_SEC     = _sty(fontSize=11, textColor=C_TEAL,  fontName="Helvetica-Bold",
                     spaceBefore=12, spaceAfter=7)
    S_BODY    = _sty(fontSize=9,  spaceAfter=4, leading=13)
    S_NOTES   = _sty(fontSize=9,  leading=14, spaceAfter=4,
                     backColor=C_LIGHT, borderPadding=(6, 8, 6, 8))
    S_TH      = _sty(fontSize=9,  textColor=C_WHITE, fontName="Helvetica-Bold", leading=12)
    S_TD      = _sty(fontSize=9,  textColor=C_TEXT, leading=12)
    S_KPI_L   = _sty(fontSize=8,  textColor=C_MUTED, leading=11)
    S_KPI_V   = _sty(fontSize=14, textColor=C_NAVY, fontName="Helvetica-Bold", leading=18)

    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=1.8 * cm,
    )

    story = []

    # ── Encabezado ────────────────────────────────────────────────────────────
    story.append(Paragraph("DASHBOARD DE EVALUACIONES DOCENTES", S_EYEBROW))
    story.append(Paragraph(_s(page_title), S_TITLE))
    story.append(Paragraph(f"Generado el {now}", S_SUB))
    story.append(HRFlowable(width="100%", thickness=2, color=C_TEAL, spaceAfter=12))

    # ── Filtros activos ───────────────────────────────────────────────────────
    active_filters = {k: v for k, v in (filters or {}).items() if v}
    if active_filters:
        story.append(Paragraph("Filtros activos", S_SEC))
        rows = [
            [Paragraph(_s(k), S_KPI_L), Paragraph(_s(v), S_BODY)]
            for k, v in active_filters.items()
        ]
        t = RLTable(rows, colWidths=[4.5 * cm, CONTENT_W - 4.5 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C_LIGHT),
            ("GRID",       (0, 0), (-1, -1), 0.5, C_BORDER),
            ("PADDING",    (0, 0), (-1, -1), 5),
            ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(t)
        story.append(Spacer(1, 10))

    # ── KPIs ─────────────────────────────────────────────────────────────────
    if kpis:
        story.append(Paragraph("Métricas clave", S_SEC))
        kpi_list = [(k, v) for k, v in kpis.items() if v is not None]
        cols_n = 3
        col_w = CONTENT_W / cols_n
        for i in range(0, len(kpi_list), cols_n):
            chunk = kpi_list[i : i + cols_n]
            cells = [
                [Paragraph(_s(lbl), S_KPI_L), Paragraph(_s(val), S_KPI_V)]
                for lbl, val in chunk
            ]
            while len(cells) < cols_n:
                cells.append([Paragraph("", S_KPI_L)])
            t = RLTable([cells], colWidths=[col_w] * cols_n)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), C_LIGHT),
                ("BOX",       (0, 0), (-1, -1), 0.5, C_BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, C_BORDER),
                ("PADDING",   (0, 0), (-1, -1), 9),
                ("VALIGN",    (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(t)
            story.append(Spacer(1, 5))
        story.append(Spacer(1, 6))

    # ── Gráficos ──────────────────────────────────────────────────────────────
    valid_figs = {k: v for k, v in (figures or {}).items() if v is not None}
    if valid_figs:
        story.append(Paragraph("Visualizaciones", S_SEC))
        kaleido_missing = False
        for fig_name, fig in valid_figs.items():
            png = fig_to_png_bytes(fig, width=920, height=440)
            if png is None:
                kaleido_missing = True
                story.append(Paragraph(
                    f"Grafico '{_s(fig_name)}' omitido "
                    f"(kaleido no disponible o error en la exportacion).",
                    S_BODY,
                ))
                continue
            img_buf = io.BytesIO(png)
            img_h = CONTENT_W * (440 / 920)
            rl_img = RLImage(img_buf, width=CONTENT_W, height=img_h)
            story.append(KeepTogether([
                Paragraph(_s(fig_name), S_BODY),
                rl_img,
                Spacer(1, 14),
            ]))
        if kaleido_missing:
            story.append(Paragraph(
                "Para incluir graficos instalar: pip install kaleido",
                S_NOTES,
            ))
            story.append(Spacer(1, 6))

    # ── Tablas ────────────────────────────────────────────────────────────────
    for tbl in (tables or []):
        if not tbl:
            continue
        title   = tbl.get("title", "Tabla")
        headers = tbl.get("headers") or []
        rows    = tbl.get("rows") or []
        if not headers or not rows:
            continue
        story.append(Paragraph(_s(title), S_SEC))
        n_cols = len(headers)
        col_w  = CONTENT_W / n_cols
        header_row = [Paragraph(_s(h), S_TH) for h in headers]
        data_rows  = [[Paragraph(_s(c), S_TD) for c in row] for row in rows]
        all_rows   = [header_row] + data_rows
        t = RLTable(all_rows, colWidths=[col_w] * n_cols)
        # Filas alternadas manualmente para compatibilidad con todas las versiones
        style_cmds = [
            ("BACKGROUND", (0, 0), (-1, 0),  C_NAVY),
            ("GRID",       (0, 0), (-1, -1), 0.4, C_BORDER),
            ("PADDING",    (0, 0), (-1, -1), 5),
            ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ]
        for row_i in range(len(data_rows)):
            bg = C_LIGHT if row_i % 2 == 0 else C_WHITE
            style_cmds.append(("BACKGROUND", (0, row_i + 1), (-1, row_i + 1), bg))
        t.setStyle(TableStyle(style_cmds))
        story.append(t)
        story.append(Spacer(1, 12))

    # ── Notas de interpretación ────────────────────────────────────────────────
    if notes:
        story.append(Paragraph("Notas de interpretacion", S_SEC))
        story.append(Paragraph(_s(notes), S_NOTES))
        story.append(Spacer(1, 8))

    # ── Pie de página dinámico ────────────────────────────────────────────────
    def _footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(C_MUTED)
        canvas.drawCentredString(
            PAGE_W / 2, 1.0 * cm,
            f"Dashboard de evaluaciones docentes  |  {now}  |  Pag. {doc.page}",
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Helpers de formateo — reutilizables en todas las páginas
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def format_filters(
    nombre_docente: str,
    filtro_modelo: list,
    filtro_periodos: list,
    df_clean,
) -> dict:
    """
    Construye el dict de filtros para el PDF a partir del estado del sidebar.

    Parameters
    ----------
    nombre_docente  : str   Nombre del docente (st.text_input).
    filtro_modelo   : list  Modelos seleccionados (multiselect). Vacío = todos.
    filtro_periodos : list  Periodos seleccionados. Vacío = todos.
    df_clean        : DataFrame  Para obtener el rango real de periodos.

    Returns
    -------
    dict[str, str] listo para build_current_view_pdf(..., filters=...).
    """
    modelos_str = ", ".join(filtro_modelo) if filtro_modelo else "Todos los modelos"

    if filtro_periodos:
        periodos_str = ", ".join(filtro_periodos)
    else:
        try:
            _labels = sorted(df_clean["periodo_label"].dropna().unique().tolist())
            if len(_labels) > 1:
                periodos_str = f"{_labels[0]} - {_labels[-1]}"
            elif _labels:
                periodos_str = _labels[0]
            else:
                periodos_str = "Todos"
        except Exception:
            periodos_str = "Todos"

    return {
        "Docente":   _s(nombre_docente),
        "Modelo(s)": modelos_str,
        "Periodos":  periodos_str,
    }


def format_kpis_from_metrics(metrics: dict) -> dict:
    """
    Formatea el dict de métricas para su presentación en el PDF.
    Omite automáticamente las claves con valor None.

    Parameters
    ----------
    metrics : dict  Output de compute() de app/utils/metrics.py.

    Returns
    -------
    dict[str, str] con solo las claves que tienen valor.
    """
    def _pct(v):
        return f"{v:.1f}%" if v is not None else None

    def _delta(v):
        if v is None:
            return None
        sign = "+" if v >= 0 else ""
        return f"{sign}{v:.2f} pts"

    def _int(v):
        return str(int(v)) if v is not None else None

    def _f2(v):
        return f"{v:.2f}" if v is not None else None

    items = {
        "% sobre Facultad (actual)":    _pct(metrics.get("pct_sobre_facultad_actual")),
        "% sobre Univ. (actual)":       _pct(metrics.get("pct_sobre_universidad_actual")),
        "% sobre Facultad (anterior)":  _pct(metrics.get("pct_sobre_facultad_anterior")),
        "% sobre Univ. (anterior)":     _pct(metrics.get("pct_sobre_universidad_anterior")),
        "Delta Fac. prom. (actual)":    _delta(metrics.get("avg_delta_facultad_actual")),
        "Delta Univ. prom. (actual)":   _delta(metrics.get("avg_delta_universidad_actual")),
        "Prom. puntaje (actual)":       _f2(metrics.get("prom_puntaje_actual")),
        "Prom. puntaje (anterior)":     _f2(metrics.get("prom_puntaje_anterior")),
        "Periodos validos (actual)":    _int(metrics.get("periodos_validos_modelo_actual")),
        "Periodos validos (anterior)":  _int(metrics.get("periodos_validos_modelo_anterior")),
        "Cursos unicos":                _int(metrics.get("cursos_unicos")),
    }
    return {k: v for k, v in items.items() if v is not None}


def build_period_table(df, periodo_col: str = "periodo_label") -> Optional[dict]:
    """
    Genera la tabla resumen por periodo para incluir en el PDF.

    Parameters
    ----------
    df          : DataFrame con datos filtrados (output de build_subsets).
    periodo_col : Nombre de la columna de periodos (default "periodo_label").

    Returns
    -------
    dict con keys "title", "headers", "rows", o None si no hay datos suficientes.
    """
    import pandas as pd

    agg_cols = [
        c for c in ["puntaje_profesor", "delta_vs_facultad", "delta_vs_universidad"]
        if c in df.columns
    ]
    if not agg_cols or periodo_col not in df.columns or df.empty:
        return None

    try:
        summary = df.groupby(periodo_col)[agg_cols].mean().round(2).reset_index()

        # Ordenar cronológicamente usando periodo_order si existe
        if "periodo_order" in df.columns:
            order_map = df.groupby(periodo_col)["periodo_order"].min().to_dict()
            summary["_o"] = summary[periodo_col].map(order_map)
            summary = summary.sort_values("_o").drop(columns=["_o"])

        col_names = {
            "periodo_label":       "Periodo",
            "puntaje_profesor":    "Puntaje prof.",
            "delta_vs_facultad":   "Delta Facultad",
            "delta_vs_universidad": "Delta Univ.",
        }
        headers = [col_names.get(c, c) for c in summary.columns]

        rows = []
        for _, row in summary.iterrows():
            r = []
            for col in summary.columns:
                v = row[col]
                if col == periodo_col:
                    r.append(str(v))
                elif pd.isna(v):
                    r.append("N/D")
                elif col.startswith("delta_"):
                    sign = "+" if v >= 0 else ""
                    r.append(f"{sign}{v:.2f}")
                else:
                    r.append(f"{v:.2f}")
            rows.append(r)

        return {"title": "Resumen por periodo", "headers": headers, "rows": rows}
    except Exception:
        return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Reporte completo por cursos
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def build_full_courses_pdf(
    df_general: "pd.DataFrame",
    df_detalle: Optional["pd.DataFrame"],
    general_filters: dict,
    metrics: dict,
    subsets: dict,
    professor_name: str = "",
) -> bytes:
    """
    Genera el PDF completo con una sección por cada curso.

    Estructura del PDF:
      1. Portada
      2. Resumen ejecutivo (KPIs globales + tabla de cursos)
      3. Gráficos globales del modelo actual
      4. Sección individual por cada curso (con gráficos y tabla)
      5. Cierre y nota metodológica

    Parameters
    ----------
    df_general     : DataFrame BASE_GENERAL_DOCENTE ya filtrado.
    df_detalle     : DataFrame BASE_DETALLE o None.
                     Con él: secciones ricas (evolución + dimensiones).
                     Sin él: secciones simples desde df_general.
    general_filters: dict de filtros activos (output de format_filters).
    metrics        : dict de métricas (output de compute).
    subsets        : dict de subsets (output de build_subsets).
    professor_name : Nombre del docente para portada y pie de página.

    Returns
    -------
    bytes — PDF listo para st.download_button.

    Raises
    ------
    ValueError   Si no hay cursos disponibles.
    ImportError  Si reportlab no está instalado.
    """
    return _full_pdf_reportlab(
        df_general, df_detalle, general_filters, metrics, subsets, professor_name
    )


def _full_pdf_reportlab(
    df_general, df_detalle, general_filters, metrics, subsets, professor_name
) -> bytes:
    import pandas as pd
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer,
        Image as RLImage, Table as RLTable,
        TableStyle, HRFlowable, KeepTogether, PageBreak,
    )
    from reportlab.lib.enums import TA_CENTER

    PAGE_W, PAGE_H = A4
    MARGIN = 2.0 * cm
    CW = PAGE_W - 2 * MARGIN

    # ── Paleta ────────────────────────────────────────────────────────────────
    C_NAVY   = colors.HexColor("#0D2733")
    C_TEAL   = colors.HexColor("#3AAFC4")
    C_GOLD   = colors.HexColor("#D4A843")
    C_TEXT   = colors.HexColor("#1A2A35")
    C_MUTED  = colors.HexColor("#5A7A87")
    C_LIGHT  = colors.HexColor("#EDF5F8")
    C_BORDER = colors.HexColor("#C4D8E0")
    C_WHITE  = colors.white
    C_NC_BG  = colors.HexColor("#FDF3E3")
    C_NC_BOR = colors.HexColor("#D4A843")

    # ── Estilos ───────────────────────────────────────────────────────────────
    _b = dict(fontName="Helvetica", textColor=C_TEXT, leading=15)

    def _sty(**kw):
        return ParagraphStyle("_", **{**_b, **kw})

    S_EYE  = _sty(fontSize=8,  textColor=C_TEAL, fontName="Helvetica-Bold",
                  letterSpacing=0.8, spaceAfter=3)
    S_COV  = _sty(fontSize=26, textColor=C_NAVY, fontName="Helvetica-Bold",
                  leading=32, spaceAfter=8, alignment=TA_CENTER)
    S_CNBR = _sty(fontSize=14, textColor=C_TEAL, alignment=TA_CENTER, spaceAfter=4)
    S_CDAT = _sty(fontSize=10, textColor=C_MUTED, alignment=TA_CENTER, spaceAfter=18)
    S_H1   = _sty(fontSize=20, textColor=C_NAVY, fontName="Helvetica-Bold",
                  leading=24, spaceAfter=6)
    S_H2   = _sty(fontSize=14, textColor=C_NAVY, fontName="Helvetica-Bold",
                  leading=18, spaceAfter=4)
    S_H3   = _sty(fontSize=11, textColor=C_TEAL, fontName="Helvetica-Bold",
                  spaceBefore=10, spaceAfter=6)
    S_SUB  = _sty(fontSize=9,  textColor=C_MUTED, spaceAfter=8)
    S_BODY = _sty(fontSize=9,  spaceAfter=4, leading=13)
    S_NOTE = _sty(fontSize=9,  leading=14, spaceAfter=4,
                  backColor=C_LIGHT, borderPadding=(6, 8, 6, 8))
    S_TH   = _sty(fontSize=9,  textColor=C_WHITE, fontName="Helvetica-Bold", leading=12)
    S_TD   = _sty(fontSize=9,  leading=12)
    S_KL   = _sty(fontSize=8,  textColor=C_MUTED, leading=11)
    S_KV   = _sty(fontSize=13, textColor=C_NAVY,  fontName="Helvetica-Bold", leading=17)
    S_CTR  = _sty(fontSize=9,  textColor=C_MUTED, alignment=TA_CENTER)

    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    # ── Helpers internos ──────────────────────────────────────────────────────

    def _hr():
        return HRFlowable(width="100%", thickness=1.5, color=C_TEAL, spaceAfter=10)

    def _hr_light():
        return HRFlowable(width="100%", thickness=0.5, color=C_BORDER, spaceAfter=8)

    def _embed_fig(fig, title=None, w=920, h=380):
        """Convierte figura Plotly a bloque KeepTogether para el story."""
        if fig is None:
            return []
        png = fig_to_png_bytes(fig, width=w, height=h)
        if png is None:
            msg = f"Grafico '{_s(title)}': requiere kaleido instalado." if title else "Grafico omitido."
            return [Paragraph(msg, S_BODY), Spacer(1, 8)]
        img_buf = io.BytesIO(png)
        img_h = CW * (h / w)
        elems = []
        if title:
            elems.append(Paragraph(_s(title), S_BODY))
        elems.append(RLImage(img_buf, width=CW, height=img_h))
        elems.append(Spacer(1, 14))
        return [KeepTogether(elems)]

    def _kpi_row_tbl(items, n_cols=4):
        """Fila de KPIs: lista de (label, valor) → tabla de n_cols celdas."""
        padded = list(items) + [("", "")] * n_cols
        cells = [
            [Paragraph(_s(l), S_KL), Paragraph(_s(v), S_KV)]
            for l, v in padded[:n_cols]
        ]
        cw = CW / n_cols
        t = RLTable([cells], colWidths=[cw] * n_cols)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C_LIGHT),
            ("BOX",       (0, 0), (-1, -1), 0.5, C_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, C_BORDER),
            ("PADDING",   (0, 0), (-1, -1), 9),
            ("VALIGN",    (0, 0), (-1, -1), "TOP"),
        ]))
        return t

    def _data_table(headers, rows, col_widths=None):
        """Tabla con encabezado azul + filas alternadas."""
        if not headers or not rows:
            return []
        n = len(headers)
        cw = col_widths or [CW / n] * n
        hrow = [Paragraph(_s(h), S_TH) for h in headers]
        brows = [[Paragraph(_s(c), S_TD) for c in row] for row in rows]
        cmds = [
            ("BACKGROUND", (0, 0), (-1, 0), C_NAVY),
            ("GRID", (0, 0), (-1, -1), 0.4, C_BORDER),
            ("PADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]
        for i in range(len(brows)):
            cmds.append(("BACKGROUND", (0, i + 1), (-1, i + 1),
                         C_LIGHT if i % 2 == 0 else C_WHITE))
        t = RLTable([hrow] + brows, colWidths=cw, repeatRows=1)
        t.setStyle(TableStyle(cmds))
        return [t, Spacer(1, 12)]

    def _filter_tbl(filt):
        if not filt:
            return []
        rows = [[Paragraph(_s(k), S_KL), Paragraph(_s(v), S_BODY)]
                for k, v in filt.items() if v]
        if not rows:
            return []
        t = RLTable(rows, colWidths=[4.5 * cm, CW - 4.5 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C_LIGHT),
            ("GRID", (0, 0), (-1, -1), 0.5, C_BORDER),
            ("PADDING", (0, 0), (-1, -1), 5),
        ]))
        return [t, Spacer(1, 10)]

    def _nc_card(df_c):
        """Tarjeta para cursos sin puntaje calculado."""
        motivo = ""
        if "motivo_estado" in df_c.columns:
            m = df_c["motivo_estado"].dropna()
            if not m.empty:
                motivo = str(m.iloc[0])
        periodos_nc = "—"
        if "periodo_label" in df_c.columns:
            periodos_nc = ", ".join(df_c["periodo_label"].dropna().unique().tolist())
        texto = (
            f"Sin puntaje calculado. Periodos: {periodos_nc}. "
            + (f"Motivo: {motivo}." if motivo else "Motivo no disponible.")
        )
        t = RLTable([[Paragraph(texto, S_BODY)]], colWidths=[CW])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C_NC_BG),
            ("BOX", (0, 0), (-1, -1), 1, C_NC_BOR),
            ("PADDING", (0, 0), (-1, -1), 12),
        ]))
        return [t, Spacer(1, 8)]

    MAX_PERIODS_TABLE = 7  # umbral: más periodos → tabla resumen en lugar de pivot

    def _aspecto_resumen_tbl(df_cp):
        """Tabla resumen por aspecto para cursos con muchos periodos."""
        if df_cp.empty or "aspecto" not in df_cp.columns or "valor_central" not in df_cp.columns:
            return []
        _df_pr = df_cp.copy()
        if "nivel_comparacion" in _df_pr.columns:
            _df_pr = _df_pr[_df_pr["nivel_comparacion"].isin({"Profesor curso", "Profesor"})]
        if _df_pr.empty:
            return []
        _sort_col = "periodo_order" if "periodo_order" in _df_pr.columns else "periodo_label"
        _rows_data = []
        for asp, g in _df_pr.groupby("aspecto"):
            vals = g["valor_central"].dropna()
            if vals.empty:
                continue
            promedio = round(float(vals.mean()), 1)
            minimo   = round(float(vals.min()), 1)
            maximo   = round(float(vals.max()), 1)
            g_sorted = g.sort_values(_sort_col)
            ult_per  = str(g_sorted["periodo_label"].iloc[-1]) if "periodo_label" in g_sorted.columns else "—"
            ult_vals = g_sorted["valor_central"].dropna()
            ult_val  = round(float(ult_vals.iloc[-1]), 1) if not ult_vals.empty else None
            cambio   = round(ult_val - promedio, 1) if ult_val is not None else None
            _rows_data.append([
                _s(asp),
                f"{promedio:.1f}",
                ult_per,
                f"{ult_val:.1f}" if ult_val is not None else "—",
                f"{minimo:.1f}",
                f"{maximo:.1f}",
                (f"+{cambio:.1f}" if cambio is not None and cambio >= 0
                 else f"{cambio:.1f}" if cambio is not None else "—"),
            ])
        if not _rows_data:
            return []
        _hdrs_r = ["Aspecto", "Promedio", "Ultimo periodo", "Ult. puntaje", "Min.", "Max.", "Cambio"]
        _asp_w  = CW * 0.30
        _per_w  = CW * 0.13
        _num_w  = (CW - _asp_w - _per_w) / 5
        return _data_table(_hdrs_r, _rows_data, [_asp_w, _num_w, _per_w, _num_w, _num_w, _num_w, _num_w])

    def _pivot_periodo_tbl(df_cp):
        """Tabla aspecto × periodo para cursos con pocos periodos (≤ MAX_PERIODS_TABLE)."""
        if (df_cp.empty or "aspecto" not in df_cp.columns
                or "periodo_label" not in df_cp.columns
                or "valor_central" not in df_cp.columns):
            return []
        _df_tab = df_cp.copy()
        if "nivel_comparacion" in _df_tab.columns:
            _df_tab = _df_tab[_df_tab["nivel_comparacion"].isin({"Profesor curso", "Profesor"})]
        if _df_tab.empty:
            return []
        try:
            _piv = (
                _df_tab.groupby(["aspecto", "periodo_label"])["valor_central"]
                .mean().round(1).reset_index()
                .pivot(index="aspecto", columns="periodo_label", values="valor_central")
            )
            if "periodo_order" in _df_tab.columns:
                _om = _df_tab.groupby("periodo_label")["periodo_order"].min().to_dict()
                _piv = _piv[sorted(_piv.columns, key=lambda x: _om.get(x, 9999))]
            _per_n = len(_piv.columns)
            _min_per = 44  # mínimo de puntos por columna de periodo
            _asp_w = max(CW * 0.34, CW - _min_per * _per_n)
            _per_w = (CW - _asp_w) / max(_per_n, 1)
            _hdrs_piv = ["Aspecto"] + list(_piv.columns)
            _rows_piv = []
            for _asp_name, _piv_row in _piv.iterrows():
                _r = [_s(_asp_name)]
                for _v in _piv_row:
                    _r.append(f"{_v:.1f}" if pd.notna(_v) else "—")
                _rows_piv.append(_r)
            return _data_table(_hdrs_piv, _rows_piv, [_asp_w] + [_per_w] * _per_n)
        except Exception:
            return []

    # ─────────────────────────────────────────────────────────────────────────
    # Story build
    # ─────────────────────────────────────────────────────────────────────────
    story = []

    # ── Pre-compute sorted course list (portada + summary table + sections) ───
    _cursos_sorted = None
    _total_cursos = 0
    _nc_det = None

    if df_detalle is not None and not df_detalle.empty and "curso_codigo_base" in df_detalle.columns:
        _nc_det = (
            "curso_nombre_normalizado" if "curso_nombre_normalizado" in df_detalle.columns
            else "curso_nombre_original" if "curso_nombre_original" in df_detalle.columns
            else None
        )
        _df_base = df_detalle[df_detalle["curso_codigo_base"].notna()].copy()

        _nombre_s = (
            _df_base.groupby("curso_codigo_base")[_nc_det].first().rename("nombre")
            if _nc_det
            else _df_base.groupby("curso_codigo_base")["curso_codigo_base"].first().rename("nombre")
        )

        _nper_s = (
            _df_base.groupby("curso_codigo_base")["periodo_label"].nunique().rename("n_periodos")
            if "periodo_label" in _df_base.columns
            else pd.Series(0, index=_nombre_s.index, name="n_periodos")
        )

        _nok_df = (
            _df_base[_df_base["tiene_puntaje_calculado"] == True]
            if "tiene_puntaje_calculado" in _df_base.columns else pd.DataFrame()
        )
        _nok_s = (
            _nok_df.groupby("curso_codigo_base")["periodo_label"].nunique().rename("n_con_puntaje")
            if not _nok_df.empty and "periodo_label" in _nok_df.columns
            else pd.Series(0, index=_nombre_s.index, name="n_con_puntaje")
        )

        _pg_df = _df_base.copy()
        if "tiene_puntaje_calculado" in _pg_df.columns:
            _pg_df = _pg_df[_pg_df["tiene_puntaje_calculado"] == True]
        if "nivel_comparacion" in _pg_df.columns:
            _pg_df = _pg_df[_pg_df["nivel_comparacion"].isin({"Profesor", "Profesor curso"})]
        if "aspecto" in _pg_df.columns:
            _pg_df = _pg_df[_pg_df["aspecto"].astype(str).str.lower() == "puntaje global"]
        _prom_s = (
            _pg_df.groupby("curso_codigo_base")["valor_central"].mean().rename("prom_global")
            if not _pg_df.empty and "valor_central" in _pg_df.columns
            else pd.Series(dtype=float, name="prom_global")
        )

        _cursos_sorted = (
            pd.concat([_nombre_s, _nper_s, _nok_s, _prom_s], axis=1)
            .reset_index()
            .fillna({"n_periodos": 0, "n_con_puntaje": 0})
            .sort_values(
                by=["n_periodos", "n_con_puntaje", "prom_global", "nombre"],
                ascending=[False, False, False, True],
                na_position="last",
            )
            .reset_index(drop=True)
        )
        _total_cursos = len(_cursos_sorted)

    # ── 1. PORTADA ────────────────────────────────────────────────────────────
    story.append(Spacer(1, 3 * cm))
    story.append(Paragraph("EVALUACIONES DOCENTES", S_EYE))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph("Reporte de evaluacion docente", S_COV))
    story.append(Paragraph("Analisis completo por cursos", S_CNBR))
    story.append(HRFlowable(width="55%", thickness=2, color=C_TEAL,
                            spaceBefore=6, spaceAfter=16))
    story.append(Paragraph(_s(professor_name), S_H1))
    story.append(Paragraph(f"Generado el {now}", S_CDAT))
    story.append(Spacer(1, 0.8 * cm))
    story.extend(_filter_tbl(general_filters))

    # Conteo de cursos en portada
    n_cursos_total = 0
    if _total_cursos > 0:
        n_cursos_total = _total_cursos
    elif not df_general.empty:
        _df_ci = subsets.get("df_cursos_individuales", pd.DataFrame())
        if not _df_ci.empty:
            _nc = "nombre_curso" if "nombre_curso" in _df_ci.columns else "codigo_curso"
            n_cursos_total = int(_df_ci[_nc].dropna().nunique()) if _nc in _df_ci.columns else 0

    if n_cursos_total:
        story.append(Paragraph(
            f"Total de cursos incluidos en este reporte: {n_cursos_total}", S_SUB
        ))

    story.append(PageBreak())

    # ── 2. RESUMEN EJECUTIVO ──────────────────────────────────────────────────
    story.append(Paragraph("Resumen ejecutivo", S_EYE))
    story.append(Paragraph("Indicadores globales del periodo", S_H1))
    story.append(_hr())

    kpi_items = list(format_kpis_from_metrics(metrics).items())
    for i in range(0, len(kpi_items), 4):
        story.append(_kpi_row_tbl(kpi_items[i: i + 4], n_cols=4))
        story.append(Spacer(1, 5))
    story.append(Spacer(1, 12))

    # Tabla de cursos (desde get_cursos_summary si df_detalle existe)
    if df_detalle is not None and not df_detalle.empty:
        from app.utils.pdf_analysis import get_cursos_summary
        cursos_sum = get_cursos_summary(df_detalle)
        if not cursos_sum.empty and _cursos_sorted is not None and not _cursos_sorted.empty:
            _order_map = {cod: i for i, cod in enumerate(_cursos_sorted["curso_codigo_base"])}
            cursos_sum = cursos_sum.copy()
            cursos_sum["_sort_key"] = cursos_sum["Código"].map(_order_map).fillna(9999)
            cursos_sum = (
                cursos_sum.sort_values("_sort_key")
                .drop(columns=["_sort_key"])
                .reset_index(drop=True)
            )
        if not cursos_sum.empty:
            story.append(Paragraph("Resumen de cursos disponibles", S_H3))
            # Quitar columna NC si todos son 0 o nulos
            if "NC" in cursos_sum.columns and cursos_sum["NC"].fillna(0).astype(int).eq(0).all():
                cursos_sum = cursos_sum.drop(columns=["NC"])
            _hdrs = list(cursos_sum.columns)
            # Anchos proporcionales: Curso obtiene la mayor parte
            _w_map = {
                "Código": 0.12, "Curso": 0.31, "Periodos": 0.10,
                "Con puntaje": 0.14, "NC": 0.09,
                "Promedio (Profesor)": 0.16, "Último periodo": 0.08,
            }
            _raw = [_w_map.get(h, 0.14) for h in _hdrs]
            _tot = sum(_raw)
            _cw_sum = [CW * w / _tot for w in _raw]
            _rows = []
            for _, row_s in cursos_sum.iterrows():
                r = []
                for col_s in cursos_sum.columns:
                    v = row_s[col_s]
                    if pd.isna(v):
                        r.append("N/D")
                    elif isinstance(v, float):
                        r.append(f"{v:.2f}")
                    else:
                        r.append(str(v))
                _rows.append(r)
            story.extend(_data_table(_hdrs, _rows, _cw_sum))
            story.append(Paragraph(
                "Los cursos se presentan ordenados de mayor a menor segun "
                "la cantidad de periodos evaluados disponibles.",
                S_SUB,
            ))
            story.append(Spacer(1, 8))

    story.append(PageBreak())

    # ── 3. GRÁFICOS GLOBALES ──────────────────────────────────────────────────
    from app.utils.plots import (
        plot_modelo_actual_line, plot_modelo_actual_delta,
        plot_modelo_anterior_line, plot_modelo_anterior_delta,
        plot_comparacion_relativa,
    )

    _df_act = subsets.get("df_modelo_actual", pd.DataFrame())
    _df_ant = subsets.get("df_modelo_anterior", pd.DataFrame())

    if not _df_act.empty:
        story.append(Paragraph("Desempeno historico global", S_EYE))
        story.append(Paragraph("Graficos del resumen ejecutivo", S_H1))
        story.append(_hr())
        story.extend(_embed_fig(plot_modelo_actual_line(_df_act),
                                "Profesor vs. benchmarks institucionales (modelo actual)"))
        story.extend(_embed_fig(plot_modelo_actual_delta(_df_act),
                                "Diferencia frente a benchmarks por periodo"))
        if not _df_ant.empty:
            story.extend(_embed_fig(plot_modelo_anterior_line(_df_ant),
                                    "Tendencia modelo anterior (contexto historico)"))
        story.extend(_embed_fig(plot_comparacion_relativa(metrics),
                                "Comparacion relativa: % de periodos sobre benchmark"))
        story.append(PageBreak())

    # ── 4. SECCIONES POR CURSO ────────────────────────────────────────────────
    from app.utils.plots import plot_evolucion_curso, plot_dimensiones_barras

    story.append(Paragraph("Detalle individual por curso", S_EYE))
    story.append(Paragraph("Analisis por curso", S_H1))
    story.append(_hr())

    # ── Modo A: con BASE_DETALLE ──────────────────────────────────────────────
    if df_detalle is not None and not df_detalle.empty and "curso_codigo_base" in df_detalle.columns:

        # _nc_det and _cursos_sorted built in the pre-sort block above
        _total = _total_cursos

        for _ord, (_, _crow) in enumerate(_cursos_sorted.iterrows(), 1):
            _cod = _crow["curso_codigo_base"]
            _nom = str(_crow.get("nombre", "") or _cod)

            story.append(PageBreak())

            # Encabezado del curso
            story.append(Paragraph(f"Curso {_ord} de {_total}", S_EYE))
            story.append(Paragraph(_s(_nom) if _nom else _s(_cod), S_H2))
            story.append(Paragraph(f"Codigo: {_s(_cod)}", S_SUB))
            story.append(_hr_light())

            # Filtrar datos del curso
            _df_c = df_detalle[df_detalle["curso_codigo_base"] == _cod].copy()
            _df_ind = _df_c.copy()
            if "es_resumen_semestre_ponderado" in _df_ind.columns:
                _df_ind = _df_ind[_df_ind["es_resumen_semestre_ponderado"] != True]
            _df_cp = _df_ind.copy()
            if "tiene_puntaje_calculado" in _df_cp.columns:
                _df_cp = _df_cp[_df_cp["tiene_puntaje_calculado"] == True]

            # KPIs del curso
            _per_tot = _df_c["periodo_label"].nunique() if "periodo_label" in _df_c.columns else 0
            _per_ok  = _df_cp["periodo_label"].nunique() if "periodo_label" in _df_cp.columns and not _df_cp.empty else 0
            _per_nc  = 0
            if "estado_calculo" in _df_c.columns and "periodo_label" in _df_c.columns:
                _per_nc = _df_c[
                    _df_c["estado_calculo"].astype(str).str.upper() == "NC"
                ]["periodo_label"].nunique()

            _prom_g   = None
            _ult_p    = None
            _mej_full = None
            if not _df_cp.empty and "nivel_comparacion" in _df_cp.columns and "valor_central" in _df_cp.columns:
                _df_pr = _df_cp[_df_cp["nivel_comparacion"].isin({"Profesor curso", "Profesor"})]
                if not _df_pr.empty:
                    _gm = _df_pr["aspecto"].astype(str).str.lower() == "puntaje global"
                    _gv = _df_pr.loc[_gm, "valor_central"].dropna()
                    if not _gv.empty:
                        _prom_g = round(_gv.mean(), 1)
                        _sort_c = "periodo_order" if "periodo_order" in _df_pr.columns else "periodo_label"
                        _ult_row = _df_pr[_gm].sort_values(_sort_c)
                        if not _ult_row.empty:
                            _ult_p = round(_ult_row["valor_central"].iloc[-1], 1)
                    _ngm = ~(_df_pr["aspecto"].astype(str).str.lower() == "puntaje global")
                    _da = _df_pr[_ngm].groupby("aspecto")["valor_central"].mean()
                    if not _da.empty:
                        _mej_full = str(_da.idxmax())

            # Periodos en una línea
            _pers_str = "—"
            if "periodo_label" in _df_c.columns:
                _pers_str = ", ".join(sorted(_df_c["periodo_label"].dropna().unique().tolist()))

            story.append(_kpi_row_tbl([
                ("Periodos evaluados", str(_per_tot)),
                ("Con puntaje valido", str(_per_ok)),
                ("Prom. global",       f"{_prom_g:.1f}" if _prom_g is not None else "N/D"),
                ("Ultimo puntaje",     f"{_ult_p:.1f}" if _ult_p is not None else "N/D"),
            ], n_cols=4))
            story.append(Spacer(1, 4))
            _per_line = f"Periodos: {_pers_str}"
            if _per_nc > 0:
                _per_line += f"   |   {_per_nc} periodo(s) sin puntaje calculado (NC)"
            story.append(Paragraph(_per_line, S_SUB))
            story.append(Spacer(1, 6))

            # ── Caso NC ────────────────────────────────────────────────────
            if _df_cp.empty:
                story.extend(_nc_card(_df_c))
                continue

            # ── Gráfico de evolución (solo si hay más de un periodo) ────────
            if _per_tot > 1:
                _df_evol = df_detalle[
                    (df_detalle["curso_codigo_base"] == _cod)
                    & (df_detalle["aspecto"].astype(str).str.lower() == "puntaje global")
                    & df_detalle["valor_central"].notna()
                ].copy()
                if "es_resumen_semestre_ponderado" in _df_evol.columns:
                    _df_evol = _df_evol[_df_evol["es_resumen_semestre_ponderado"] != True]
                story.extend(_embed_fig(
                    plot_evolucion_curso(_df_evol),
                    "Evolucion del puntaje global",
                    w=900, h=360,
                ))
            else:
                story.append(Paragraph(
                    f"Curso evaluado en un unico periodo ({_pers_str}). "
                    "El grafico de evolucion no aplica.",
                    S_SUB,
                ))

            # ── Gráfico por dimensiones ─────────────────────────────────────
            _df_dims = _df_cp.copy()
            if "aspecto" in _df_dims.columns:
                _df_dims = _df_dims[
                    _df_dims["aspecto"].astype(str).str.lower() != "puntaje global"
                ]
            if not _df_dims.empty:
                story.extend(_embed_fig(
                    plot_dimensiones_barras(_df_dims, niveles=None),
                    "Perfil por aspectos docentes",
                    w=900, h=360,
                ))

            # ── Tabla por aspecto (resumen o pivot según cantidad de periodos) ──
            if _per_ok > MAX_PERIODS_TABLE:
                _tbl_elems = _aspecto_resumen_tbl(_df_cp)
                if _tbl_elems:
                    story.append(Paragraph("Resumen historico por aspecto (Profesor)", S_H3))
                    story.extend(_tbl_elems)
            else:
                _tbl_elems = _pivot_periodo_tbl(_df_cp)
                if _tbl_elems:
                    story.append(Paragraph("Puntajes por aspecto y periodo (Profesor)", S_H3))
                    story.extend(_tbl_elems)

            # ── Nota interpretativa ─────────────────────────────────────────
            if _prom_g is not None:
                _nivel_desc = (
                    "desempeno destacado" if _prom_g >= 4.5
                    else "buen desempeno" if _prom_g >= 4.0
                    else "desempeno satisfactorio" if _prom_g >= 3.5
                    else "desempeno a reforzar"
                )
                _nota_parts = [
                    f"El curso presenta un {_nivel_desc}, con un puntaje global "
                    f"promedio de {_prom_g:.1f}."
                ]
                if _mej_full:
                    _nota_parts.append(
                        f"El aspecto con mayor promedio historico es "
                        f"{_mej_full}, lo que sugiere una fortaleza "
                        f"sostenida en esta dimension docente."
                    )
                if _ult_p is not None:
                    _dir = "por encima" if _ult_p >= _prom_g else "por debajo"
                    _nota_parts.append(
                        f"El ultimo puntaje registrado fue {_ult_p:.1f}, "
                        f"{_dir} del promedio historico del curso."
                    )
                story.append(Paragraph(" ".join(_nota_parts), S_NOTE))
                story.append(Spacer(1, 6))

    # ── Modo B: solo df_general (secciones simples) ────────────────────────────
    elif not df_general.empty:
        _df_ci = subsets.get("df_cursos_individuales", pd.DataFrame())
        _nc_g = (
            "nombre_curso" if "nombre_curso" in _df_ci.columns
            else "codigo_curso" if "codigo_curso" in _df_ci.columns
            else None
        )
        if not _df_ci.empty and _nc_g:
            if "periodo_label" in _df_ci.columns:
                _cnt_g = (
                    _df_ci.groupby(_nc_g)["periodo_label"].nunique()
                    .reset_index(name="_nper_g")
                    .sort_values("_nper_g", ascending=False)
                )
                _cursos_g = _cnt_g[_nc_g].tolist()
            else:
                _cursos_g = _df_ci[_nc_g].dropna().unique().tolist()
            _total_g = len(_cursos_g)
            for _ord_g, _nc_val in enumerate(_cursos_g, 1):
                _df_one = _df_ci[_df_ci[_nc_g] == _nc_val].copy()
                if _df_one.empty:
                    continue
                story.append(PageBreak())
                story.append(Paragraph(f"Curso {_ord_g} de {_total_g}", S_EYE))
                story.append(Paragraph(_s(_nc_val), S_H2))
                story.append(_hr_light())

                _prom_s = round(_df_one["puntaje_profesor"].mean(), 2) if "puntaje_profesor" in _df_one.columns else None
                _per_s = _df_one["periodo_label"].nunique() if "periodo_label" in _df_one.columns else 0
                story.append(_kpi_row_tbl([
                    ("Periodos", str(_per_s)),
                    ("Prom. puntaje", f"{_prom_s}" if _prom_s else "N/D"),
                    ("", ""), ("", ""),
                ], n_cols=4))
                story.append(Spacer(1, 8))

                story.extend(_embed_fig(
                    plot_modelo_actual_line(_df_one),
                    "Puntaje vs. benchmarks por periodo",
                    w=900, h=360,
                ))
                story.extend(_embed_fig(
                    plot_modelo_actual_delta(_df_one),
                    "Delta vs. benchmarks",
                    w=900, h=320,
                ))
        else:
            story.append(Paragraph(
                "No se encontraron cursos individuales en los datos.",
                S_NOTE,
            ))

    # ── 5. CIERRE Y METODOLOGÍA ───────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Cierre", S_EYE))
    story.append(Paragraph("Nota metodologica", S_H1))
    story.append(_hr())

    _notas = [
        ("Separacion de modelos",
         "Los modelos de evaluacion usan escalas distintas. "
         "Se presentan por separado sin conversion entre escalas."),
        ("Registros excluidos",
         "Registros 'Sin docencia' y 'NC / No calculado' se excluyen de "
         "promedios y graficos. Solo aparecen periodos con evaluacion valida."),
        ("Fuente de datos",
         "El archivo Excel cargado es la unica fuente. "
         "BASE_DETALLE es informacion auxiliar y no alimenta los KPIs del resumen ejecutivo."),
        ("Calculos automaticos",
         "Si la columna delta no existe se calcula desde puntaje_profesor - benchmark. "
         "Dimensiones de BASE_DETALLE se promedian por aspecto y nivel de comparacion."),
    ]

    _nota_rows = [[Paragraph(_s(t), S_TH), Paragraph(_s(d), S_TD)] for t, d in _notas]
    _t_notas = RLTable(_nota_rows, colWidths=[4.8 * cm, CW - 4.8 * cm])
    _t_notas.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), C_TEAL),
        ("BACKGROUND", (1, 0), (1, -1), C_LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.4, C_BORDER),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(_t_notas)
    story.append(Spacer(1, 16))
    story.append(Paragraph(
        f"Reporte generado el {now}. Dashboard de evaluaciones docentes.", S_CTR
    ))

    # ── Footer ────────────────────────────────────────────────────────────────
    def _footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(C_MUTED)
        canvas.drawCentredString(
            PAGE_W / 2, 1.0 * cm,
            f"Reporte de evaluacion — {_s(professor_name)}  |  {now}  |  Pag. {doc.page}",
        )
        canvas.restoreState()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=1.8 * cm,
    )
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
