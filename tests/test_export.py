"""Pruebas de las descargas (PDF, HTML, PNG) con datos sintéticos.

Las que necesitan un navegador Chromium (Chrome/Edge/Chromium) se omiten si no
hay uno instalado. Ejecutar con:  python -m pytest tests
"""
import io
import re
import zipfile

import pandas as pd
import plotly.io as pio
import pytest

from app import export
from app.export import report
from app.export.plotly_theme import export_figure
from app.export.snapshot import ChartRef, ChartSpec, DashboardSnapshot, Group, Html, Row
from app.utils import plots

# Colores marcadores de la plantilla "streamlit" (#000001 … #000040)
_PLACEHOLDER = re.compile(r"#0000[0-4]\d\b")


def _df_modelo():
    return pd.DataFrame({
        "periodo_label": ["2023-1", "2023-2", "2024-1", "2024-2"],
        "periodo_order": [20231, 20232, 20241, 20242],
        "nivel_analisis": ["Periodo-Agregado"] * 4,
        "codigo_curso": ["AGREGADO"] * 4,
        "puntaje_profesor": [4.5, 4.6, 4.7, 4.8],
        "benchmark_facultad": [4.2, 4.3, 4.3, 4.4],
        "benchmark_universidad": [4.1, 4.2, 4.2, 4.3],
        "delta_vs_facultad": [0.3, 0.3, 0.4, 0.4],
        "delta_vs_universidad": [0.4, 0.4, 0.5, 0.5],
    })


def _snapshot(n_bloques_altos: int = 0) -> DashboardSnapshot:
    df = _df_modelo()
    snap = DashboardSnapshot(teacher="Docente de prueba", period_range="2023–2024")
    snap.charts["linea"] = ChartSpec("linea", plots.plot_modelo_actual_line(df),
                                     "Profesor vs. benchmarks", "Modelo actual", "Nota")
    snap.charts["delta"] = ChartSpec("delta", plots.plot_modelo_actual_delta(df),
                                     "Diferencia frente a benchmarks")
    snap.groups.append(Group([Html('<span style="display:block">Eyebrow</span>', True),
                              Html("<h1>Evaluaciones docentes — Docente de prueba</h1>")]))
    snap.groups.append(Group([
        Html('<div class="sec-divider"></div>', divider=True),
        Html("<h3>Modelo actual</h3>", keep_with_next=True),
        Row([1.3, 1], [[Html("<p>Etiqueta</p>", True), ChartRef("linea")],
                       [ChartRef("delta")]]),
    ]))
    for i in range(n_bloques_altos):   # bloques más altos que una hoja
        snap.groups.append(Group([Html(f'<div style="height:{report.BODY_H + 300}px">'
                                       f'Bloque alto {i}</div>')]))
    return snap


def test_figura_exportada_sin_colores_marcadores_de_streamlit():
    from streamlit.elements.lib.streamlit_plotly_theme import configure_streamlit_plotly_theme

    configure_streamlit_plotly_theme()          # lo que hace Streamlit al importarse
    try:
        fig = plots.plot_modelo_actual_line(_df_modelo())
        assert _PLACEHOLDER.search(pio.to_json(fig))                  # el problema existe…
        assert not _PLACEHOLDER.search(pio.to_json(export_figure(fig)))  # …y se corrige
    finally:
        pio.templates.default = "plotly"


def test_export_figure_no_modifica_la_original():
    fig = plots.plot_modelo_actual_line(_df_modelo())
    antes = fig.to_json()
    export_figure(fig)
    assert fig.to_json() == antes


def test_reporte_html_autocontenido():
    html = export.report_html(_snapshot()).decode("utf-8")
    assert html.startswith("<!doctype html>")
    assert html.count("Plotly.newPlot(id, fig.data") == 1    # un único arranque para todos
    assert len(re.findall(r'id="chart-\d+-(linea|delta)"', html)) == 2
    assert "font/woff2;base64," in html                      # fuentes incrustadas
    assert "https://" not in html.split("<script>", 1)[0]    # sin recursos externos en <head>
    assert "Guardar como PDF" in html
    assert "clamp(" not in html.split("<main", 1)[1]         # tamaños fluidos → fijos


def test_nombres_de_archivo_sin_tildes_ni_espacios():
    snap = DashboardSnapshot(teacher="María José Pérez", period_range="2010–2027")
    assert export.report_filename(snap, "pdf") == "Evaluaciones_docentes_Maria_Jose_Perez_2010-2027.pdf"
    assert export.chart_filename("Diferencia frente a benchmarks (delta)") == \
        "Diferencia_frente_a_benchmarks_delta.png"


requiere_navegador = pytest.mark.skipif(not export.available(),
                                        reason="No hay Chrome/Chromium/Edge instalado")


@requiere_navegador
def test_pdf_pagina_bloques_mas_altos_que_una_hoja():
    pdf = export.report_pdf(_snapshot(n_bloques_altos=2))
    assert pdf.startswith(b"%PDF")
    paginas = len(re.findall(rb"/Type\s*/Page[^s]", pdf))
    assert paginas >= 3        # contenido inicial + un bloque alto por hoja


@requiere_navegador
def test_png_y_zip():
    snap = _snapshot()
    png = export.chart_png(snap, "linea")
    assert png.startswith(b"\x89PNG")
    ancho = int.from_bytes(png[16:20], "big")
    assert ancho == report.CARD_W * 3          # captura a 3× la resolución CSS

    nombres = zipfile.ZipFile(io.BytesIO(export.charts_zip(snap))).namelist()
    assert nombres == ["01_Profesor_vs_benchmarks.png", "02_Diferencia_frente_a_benchmarks.png"]
