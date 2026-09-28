"""Descargas del dashboard: reporte PDF, página HTML interactiva y gráficos PNG.

Todo se genera en el equipo o servidor donde corre la app; ningún dato sale a
servicios externos.
"""
from __future__ import annotations

import io
import re
import unicodedata
import zipfile

from app.export import browser, report
from app.export.snapshot import DashboardSnapshot


def available() -> bool:
    """True si hay un navegador Chromium (Chrome, Edge, Chromium) para PDF y PNG."""
    return browser.available()


def report_pdf(snap: DashboardSnapshot) -> bytes:
    return browser.print_pdf(report.report_document(snap, interactive=False))


def report_html(snap: DashboardSnapshot) -> bytes:
    return report.report_document(snap, interactive=True).encode("utf-8")


def chart_png(snap: DashboardSnapshot, key: str) -> bytes:
    images = browser.capture_elements(report.cards_document(snap, [key]), ".card")
    if not images:
        raise KeyError(f"No hay un gráfico registrado con la clave {key!r}")
    return images[0]


def charts_zip(snap: DashboardSnapshot) -> bytes:
    keys = list(snap.charts)
    images = browser.capture_elements(report.cards_document(snap, keys), ".card")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, (key, png) in enumerate(zip(keys, images), start=1):
            zf.writestr(f"{i:02d}_{chart_filename(snap.charts[key].title)}", png)
    return buffer.getvalue()


def slug(text: str) -> str:
    """Texto apto para nombre de archivo: sin tildes ni espacios."""
    text = unicodedata.normalize("NFKD", str(text).replace("–", "-").replace("—", "-"))
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^A-Za-z0-9-]+", "_", text).strip("_") or "dashboard"


def report_filename(snap: DashboardSnapshot, extension: str, *, suffix: str = "") -> str:
    parts = ["Evaluaciones_docentes", slug(snap.teacher)]
    if snap.period_range:
        parts.append(slug(snap.period_range))
    if suffix:
        parts.append(suffix)
    return "_".join(parts) + f".{extension}"


def chart_filename(title: str) -> str:
    return f"{slug(title)}.png"
