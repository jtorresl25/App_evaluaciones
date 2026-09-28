"""Dibuja en Streamlit y, a la vez, registra lo dibujado para las descargas.

Las secciones usan `rec.html(...)`, `rec.columns(...)` y `rec.chart(...)` en
lugar de st.markdown / st.columns / st.plotly_chart: en pantalla el resultado es
el mismo, y el DashboardSnapshot queda con la misma estructura para armar el
PDF, la página HTML y las imágenes.
"""
from __future__ import annotations

import streamlit as st

from app import export
from app.export.snapshot import ChartRef, ChartSpec, DashboardSnapshot, Group, Html, Row

_PAGE_BG = "#081C24"
_CHART_CONFIG = {"displayModeBar": False}


class Recorder:
    def __init__(self, snap: DashboardSnapshot | None = None, dg=None,
                 nodes: list | None = None):
        self.snap = snap
        self.dg = st if dg is None else dg     # contenedor de Streamlit donde se dibuja
        self._nodes = nodes                    # lista donde se registra (None = no registrar)

    # ── Estructura ────────────────────────────────────────────────────────────
    def section(self, *, page_break: bool = False) -> Recorder:
        """Abre un bloque que el PDF mantiene junto en una hoja siempre que quepa."""
        nodes: list = []
        if self.snap is not None:
            self.snap.groups.append(Group(nodes, page_break))
        return Recorder(self.snap, self.dg, nodes)

    def columns(self, spec, **kwargs) -> list[Recorder]:
        cols = self.dg.columns(spec, **kwargs)
        ratios = [1.0] * spec if isinstance(spec, int) else [float(r) for r in spec]
        row = Row(ratios, [[] for _ in cols])
        self._append(row)
        return [Recorder(self.snap, col, cell) for col, cell in zip(cols, row.cells)]

    # ── Contenido ─────────────────────────────────────────────────────────────
    def html(self, fragment: str, *, keep_with_next: bool = False) -> None:
        self.dg.markdown(fragment, unsafe_allow_html=True)
        self.record(fragment, keep_with_next=keep_with_next)

    def divider(self, fragment: str = '<div class="sec-divider"></div>') -> None:
        self.dg.markdown(fragment, unsafe_allow_html=True)
        self._append(Html(fragment, divider=True))

    def spacer(self) -> None:
        self.dg.write("")
        self.record("")

    def record(self, fragment: str, *, keep_with_next: bool = False) -> None:
        """Registra HTML solo para las descargas (p. ej. el curso elegido en un selector)."""
        self._append(Html(fragment, keep_with_next=keep_with_next))

    def chart(self, fig, *, key: str, title: str, label_html: str | None = None,
              section: str = "", note: str = "") -> None:
        """Gráfico Plotly con botón de descarga PNG.

        title:      título del gráfico en la imagen descargada.
        label_html: etiqueta visible sobre el gráfico en el dashboard (None si
                    el gráfico ya queda bajo un título de sección).
        section/note: contexto que acompaña al título en la imagen.
        """
        can_export = export.available() and self.snap is not None
        box = self.dg.container(key=f"chartbox_{key}")
        if can_export:
            # Con etiqueta: etiqueta a la izquierda y botón a la derecha, en la misma
            # línea. Sin etiqueta: el botón flota en la esquina del gráfico (CSS en
            # main.css), así el gráfico no se desplaza.
            head = box.container(
                horizontal=True, vertical_alignment="top", gap="small",
                horizontal_alignment="distribute" if label_html else "right",
                key=f"charthead_{key}" if label_html else f"charttools_{key}",
            )
            if label_html:
                head.markdown(label_html, unsafe_allow_html=True)
            snap = self.snap
            head.download_button(
                "PNG", data=lambda: export.chart_png(snap, key),
                file_name=export.chart_filename(title), mime="image/png",
                icon=":material/download:", type="tertiary", on_click="ignore",
                key=f"dlpng_{key}",
                help="Descargar este gráfico como imagen PNG de alta resolución",
            )
        elif label_html:
            box.markdown(label_html, unsafe_allow_html=True)

        config = _CHART_CONFIG
        if not export.available():
            # Sin navegador para exportar: queda el ícono de cámara de Plotly.
            # Fondo sólido (igual al de la página) para que el PNG no salga transparente.
            fig.update_layout(paper_bgcolor=_PAGE_BG)
            config = {
                "displayModeBar": True, "displaylogo": False,
                "modeBarButtons": [["toImage"]],
                "toImageButtonOptions": {"format": "png", "scale": 3,
                                         "filename": export.slug(title)},
            }
        box.plotly_chart(fig, width="stretch", config=config)

        if self.snap is not None:
            self.snap.charts[key] = ChartSpec(key, fig, title, section, note)
        if label_html:
            self.record(label_html, keep_with_next=True)
        self._append(ChartRef(key))

    # ── Interno ───────────────────────────────────────────────────────────────
    def _append(self, node) -> None:
        if self._nodes is not None:
            self._nodes.append(node)
