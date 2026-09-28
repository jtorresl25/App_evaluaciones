"""Menú "Descargar" del encabezado: reporte PDF, página HTML y todos los gráficos."""
import streamlit as st

from app import export
from app.export.snapshot import DashboardSnapshot


def render_download_menu(snap: DashboardSnapshot, *, incluye_detalle: bool) -> None:
    """Los archivos se generan al hacer clic (no en cada recarga de la página),
    a partir de lo que el dashboard muestra en ese momento."""
    con_navegador = export.available()
    with st.popover("Descargar", icon=":material/download:", key="menu_descargas"):
        st.markdown("**Descargar el dashboard**")
        if con_navegador:
            st.download_button(
                "Reporte completo (PDF)", data=lambda: export.report_pdf(snap),
                file_name=export.report_filename(snap, "pdf"), mime="application/pdf",
                icon=":material/picture_as_pdf:", type="primary", on_click="ignore",
                width="stretch", key="dl_reporte_pdf",
            )
            detalle = " Incluye los datos auxiliares del curso seleccionado." if incluye_detalle else ""
            st.caption(f"Todas las secciones en hojas tamaño carta, sin gráficos ni tarjetas cortados.{detalle}")

        st.download_button(
            "Página interactiva (HTML)", data=lambda: export.report_html(snap),
            file_name=export.report_filename(snap, "html"), mime="text/html",
            icon=":material/language:", on_click="ignore", width="stretch",
            key="dl_reporte_html",
        )
        pdf_manual = "" if con_navegador else " Para obtener un PDF, ábrela y usa «Guardar como PDF»."
        st.caption("Se abre en cualquier navegador, incluso sin internet, y muestra el detalle "
                   f"de cada punto al pasar el mouse.{pdf_manual}")

        if con_navegador:
            st.download_button(
                "Todos los gráficos (ZIP)", data=lambda: export.charts_zip(snap),
                file_name=export.report_filename(snap, "zip", suffix="graficos"),
                mime="application/zip", icon=":material/photo_library:", on_click="ignore",
                width="stretch", key="dl_graficos_zip",
            )
            st.caption("Cada gráfico en PNG de alta resolución. Para uno solo, usa el botón "
                       "PNG junto a cada gráfico.")
        else:
            st.caption("Para PDF e imágenes en un clic se necesita Google Chrome, Chromium o "
                       "Microsoft Edge en el equipo donde corre la app. Mientras tanto, cada "
                       "gráfico tiene un ícono de cámara (arriba a la derecha) para bajarlo en PNG.")
