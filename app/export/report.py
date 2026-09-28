"""Documentos HTML para exportar el dashboard.

- report_document(): la página completa en hojas tamaño carta (base del PDF y de
  la página HTML interactiva). Un pequeño script reparte los bloques en hojas
  sin partir ningún gráfico ni tarjeta.
- cards_document(): una "tarjeta" por gráfico (título + gráfico + pie) que se
  captura como PNG.

El CSS reproduce las reglas de Streamlit que afectan al HTML de las secciones
(tipografía base, títulos, separación de 16 px entre elementos, columnas), así
el reporte usa exactamente los mismos fragmentos HTML que el dashboard.
"""
from __future__ import annotations

import base64
import html as html_lib
import json
import re
from functools import lru_cache
from pathlib import Path

import plotly.io as pio
from plotly.offline import get_plotlyjs

from app.export.plotly_theme import export_figure
from app.export.snapshot import ChartRef, DashboardSnapshot, Html, Row

# ── Geometría de la hoja ──────────────────────────────────────────────────────
# Carta vertical (8.5 × 11 in = 816 × 1056 px CSS). El contenido se diseña a
# 1200 px de ancho —como el dashboard en un monitor de escritorio— y se escala
# al papel con `zoom` al imprimir.
PAGE_W = 1200
PAGE_ZOOM = 816 / PAGE_W
PAGE_H = int(1056 / PAGE_ZOOM)            # 1552 px de diseño
PAD_X, PAD_TOP, FOOT_H = 75, 56, 64
BODY_H = PAGE_H - PAD_TOP - FOOT_H        # alto útil por hoja
CONTENT_W = PAGE_W - 2 * PAD_X            # 1050 px

CARD_W = 880                              # ancho de las imágenes PNG (× 3 al capturar)

_BG = "#081C24"
_FONTS_DIR = Path(__file__).parent / "fonts"
_FONT_FILES = [
    # (familia, estilo, peso, archivo) — mismas familias y pesos que carga el dashboard
    ("IBM Plex Sans", "normal", "400 700", "IBMPlexSans-normal-400-700.woff2"),
    ("Spectral", "normal", "400", "Spectral-normal-400.woff2"),
    ("Spectral", "normal", "600", "Spectral-normal-600.woff2"),
    ("Spectral", "normal", "700", "Spectral-normal-700.woff2"),
    ("Spectral", "italic", "400", "Spectral-italic-400.woff2"),
    ("Source Sans", "normal", "200 900", "SourceSans3-normal-200-900.woff2"),
]
_MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
           "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

# st.markdown envuelve en <p> el HTML que empieza con una etiqueta en línea.
_INLINE_START = re.compile(r"\s*<(span|b|strong|em|i|a|small|code)\b", re.I)
# Tamaños fluidos (clamp con vw) → tamaño de escritorio: al imprimir, vw cambia.
_CLAMP_VW = re.compile(r"clamp\(\s*[\d.]+px\s*,\s*[\d.]+vw\s*,\s*([\d.]+px)\s*\)")


@lru_cache(maxsize=1)
def _font_css() -> str:
    rules = []
    for family, style, weight, filename in _FONT_FILES:
        data = base64.b64encode((_FONTS_DIR / filename).read_bytes()).decode("ascii")
        rules.append(
            f'@font-face{{font-family:"{family}";font-style:{style};font-weight:{weight};'
            f'font-display:block;src:url(data:font/woff2;base64,{data}) format("woff2");}}'
        )
    return "\n".join(rules)


_BASE_CSS = f"""
:root {{ color-scheme: dark; }}
*, *::before, *::after {{ box-sizing: border-box; }}
html, body {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
body {{
  margin: 0; background: {_BG}; color: #E0EEF2;
  font-family: "Source Sans", sans-serif; font-size: 16px; line-height: 1.6;
  -webkit-font-smoothing: antialiased; text-rendering: optimizeLegibility;
}}
/* Contenedores verticales de Streamlit: 16 px entre elementos */
.stack {{ display: flex; flex-direction: column; gap: 16px; }}
.el {{ min-width: 0; }}
/* st.markdown: margen inferior negativo que compensa el de los párrafos */
.md {{ margin-bottom: -16px; overflow-wrap: break-word; }}
.md p {{ margin: 0 0 16px; }}
.md h1, .md h2, .md h3, .md h4 {{ margin: 0; line-height: 1.2; color: #E0EEF2; }}
.md h1 {{ font-size: 2.75rem; font-weight: 700; padding: 1.25rem 0 1rem; }}
.md h2 {{ font-size: 2.25rem; font-weight: 600; padding: 1rem 0; letter-spacing: -0.005em; }}
.md h3 {{ font-size: 1.75rem; font-weight: 600; padding: .75rem 0 1rem; letter-spacing: -0.005em; }}
.md h4 {{ font-size: 1.5rem; font-weight: 600; padding: .5rem 0 1rem; }}
.md b, .md strong {{ font-weight: 600; }}
/* st.columns: 16 px entre columnas, ancho proporcional */
.row {{ display: flex; gap: 16px; align-items: flex-start; }}
.col {{ min-width: 0; }}
.plot {{ width: 100%; }}
.sec-divider {{ height: 1px; background: #1A3D4E; margin: 1.6rem 0; }}
"""

_REPORT_CSS = f"""
html {{ background: #04121A; }}
body {{ background: #04121A; }}
#flow {{ width: {CONTENT_W}px; }}
#pages {{ padding: 24px 0 48px; }}
.page {{
  position: relative; width: {PAGE_W}px; height: {PAGE_H}px; margin: 0 auto 24px;
  padding: {PAD_TOP}px {PAD_X}px 0; background: {_BG}; overflow: hidden;
  box-shadow: 0 12px 40px rgba(0,0,0,.45);
}}
.page-body {{ height: {BODY_H}px; overflow: hidden; }}
.page-foot {{
  position: absolute; left: {PAD_X}px; right: {PAD_X}px; bottom: 26px;
  display: flex; justify-content: space-between; gap: 24px;
  padding-top: 10px; border-top: 1px solid #1A3D4E;
  font: 400 11.5px/1.4 "IBM Plex Sans", system-ui, sans-serif; color: #537F8A;
}}
.toolbar {{
  position: fixed; top: 16px; right: 20px; z-index: 10; display: flex; gap: 10px;
  align-items: center; font: 500 12.5px/1 "IBM Plex Sans", system-ui, sans-serif;
}}
.toolbar button {{
  font: inherit; cursor: pointer; border-radius: 30px; padding: 9px 16px;
  background: #3AAFC4; color: #081C24; border: 0; font-weight: 600;
  box-shadow: 0 4px 16px rgba(0,0,0,.4);
}}
.toolbar button:hover {{ background: #5AD7E8; }}
@media print {{
  @page {{ size: 8.5in 11in; margin: 0; }}
  html {{ zoom: {PAGE_ZOOM:.6f}; background: {_BG}; }}
  body {{ background: {_BG}; }}
  #pages {{ padding: 0; }}
  .page {{ margin: 0; box-shadow: none; break-after: page; }}
  .page:last-child {{ break-after: auto; }}
  .toolbar {{ display: none !important; }}
}}
"""

_CARDS_CSS = f"""
body {{ padding: 0; }}
.card {{ width: {CARD_W}px; padding: 30px 34px 22px; background: {_BG}; margin-bottom: 40px; }}
.card-eyebrow {{
  font: 500 11px/1.4 "IBM Plex Sans", system-ui, sans-serif; letter-spacing: .2em;
  text-transform: uppercase; color: #3AAFC4; margin-bottom: 6px;
}}
.card-title {{
  font: 600 24px/1.25 "Spectral", Georgia, serif; color: #E0EEF2; letter-spacing: -0.005em;
}}
.card-note {{
  font: 400 13px/1.5 "IBM Plex Sans", system-ui, sans-serif; color: #8CBECB; margin-top: 6px;
}}
.card .plot {{ margin-top: 14px; }}
.card-foot {{
  margin-top: 10px; padding-top: 10px; border-top: 1px solid #1A3D4E;
  display: flex; justify-content: space-between; gap: 24px;
  font: 400 11px/1.4 "IBM Plex Sans", system-ui, sans-serif; color: #537F8A;
}}
"""

# Reparte los bloques (<section class="grp">) en hojas de alto fijo. Un bloque
# que no cabe en lo que queda de la hoja pasa entero a la siguiente. Si ni solo
# cabe en una hoja: cuando lo ocupa casi todo un elemento (un gráfico alto), ese
# elemento se reduce para caber junto a su título; si no, el bloque se divide
# entre elementos sin dejar títulos huérfanos. Nada queda cortado.
_PAGINATE_JS = """
function paginate(limit) {
  const flow = document.getElementById('flow');
  const pagesEl = document.getElementById('pages');
  const tpl = document.getElementById('page-tpl');
  let body;
  const newPage = () => {
    pagesEl.appendChild(tpl.content.firstElementChild.cloneNode(true));
    body = pagesEl.lastElementChild.querySelector('.page-body');
  };
  const fits = () => body.scrollHeight <= limit + 1;
  const height = el => el.getBoundingClientRect().height;
  const hideLeadingDivider = grp => {
    const first = grp.firstElementChild;
    if (first && first.classList.contains('divider')) first.style.display = 'none';
  };
  const place = grp => {
    if (!body.children.length) hideLeadingDivider(grp);
    body.appendChild(grp);
  };
  const shrink = (el, minZoom) => {
    for (let i = 0; i < 4 && !fits(); i++) {
      const h = height(el), over = body.scrollHeight - limit;
      if (h <= 0) return;
      const z = (el.style.zoom ? parseFloat(el.style.zoom) : 1) * (h - over - 2) / h;
      if (z < minZoom) return;
      el.style.zoom = z;
      el.style.alignSelf = 'center';
    }
  };
  const shrinkTallest = grp => {
    const kids = Array.from(grp.children);
    const tallest = kids.reduce((a, b) => (height(b) > height(a) ? b : a), kids[0]);
    if (!tallest || height(tallest) < 0.6 * limit) return false;
    shrink(tallest, 0.5);
    if (fits()) return true;
    tallest.style.zoom = '';
    tallest.style.alignSelf = '';
    return false;
  };
  const split = grp => {
    let cur = grp;
    for (let guard = 0; guard < 50 && !fits(); guard++) {
      const rest = document.createElement('section');
      rest.className = cur.className;
      while (!fits() && cur.children.length > 1) rest.prepend(cur.lastElementChild);
      while (cur.children.length > 1 && cur.lastElementChild.classList.contains('keep')) {
        rest.prepend(cur.lastElementChild);
      }
      if (!fits()) shrink(cur.lastElementChild, 0.3);
      if (!rest.children.length) return;
      newPage(); place(rest); cur = rest;
      if (!fits() && shrinkTallest(cur)) return;
    }
  };
  newPage();
  for (const grp of Array.from(flow.children)) {
    if (grp.dataset.break === '1' && body.children.length) newPage();
    place(grp);
    if (fits()) continue;
    if (body.children.length > 1) {
      body.removeChild(grp);
      newPage(); place(grp);
      if (fits()) continue;
    }
    if (!shrinkTallest(grp)) split(grp);
  }
  flow.remove();
  const pages = Array.from(pagesEl.querySelectorAll('.page'));
  pages.filter(p => !p.querySelector('.page-body').children.length).forEach(p => p.remove());
  const kept = Array.from(pagesEl.querySelectorAll('.page'));
  kept.forEach((p, i) => {
    p.querySelector('.pn').textContent = i + 1;
    p.querySelector('.pt').textContent = kept.length;
  });
}
"""

_BOOT_JS = """
async function boot(charts, config, paginateLimit) {
  try {
    await Promise.all(FONT_PROBES.map(f => document.fonts.load(f)));
    await document.fonts.ready;
    await Promise.all(charts.map(([id, fig]) => Plotly.newPlot(id, fig.data, fig.layout, config)));
    if (paginateLimit) paginate(paginateLimit);
  } catch (err) {
    console.error(err);
  } finally {
    window.__exportReady = true;
  }
}
"""

_FONT_PROBES = [
    '400 16px "Source Sans"', '500 16px "Source Sans"',
    '400 13px "IBM Plex Sans"', '500 13px "IBM Plex Sans"',
    '600 13px "IBM Plex Sans"', '700 13px "IBM Plex Sans"',
    '400 16px "Spectral"', '600 16px "Spectral"', '700 16px "Spectral"',
    'italic 400 16px "Spectral"',
]


# ── Helpers ───────────────────────────────────────────────────────────────────
def _esc(text: str) -> str:
    return html_lib.escape(str(text), quote=True)


def _script_json(payload: str) -> str:
    """JSON seguro dentro de <script> (evita cerrar la etiqueta desde los datos)."""
    return payload.replace("</", "<\\/").replace("<!--", "<\\!--")


def format_date(snap: DashboardSnapshot) -> str:
    d = snap.generated
    return f"{d.day} de {_MONTHS[d.month - 1]} de {d.year}"


def _markdown_fragment(fragment: str) -> str:
    fragment = _CLAMP_VW.sub(r"\1", fragment)
    if _INLINE_START.match(fragment):
        fragment = f"<p>{fragment}</p>"
    return fragment


class _ChartCollector:
    """Convierte ChartRef en <div> y acumula las figuras para Plotly.newPlot."""

    def __init__(self, snap: DashboardSnapshot):
        self.snap = snap
        self.items: list[str] = []

    def div(self, key: str, extra_class: str = "") -> str:
        spec = self.snap.charts.get(key)
        if spec is None:
            return ""
        fig = export_figure(spec.fig)
        height = int(fig.layout.height or 450)
        div_id = f"chart-{len(self.items)}-{re.sub(r'[^A-Za-z0-9_-]', '-', key)}"
        payload = pio.to_json(fig, validate=False, remove_uids=True)
        self.items.append(f'["{div_id}",{_script_json(payload)}]')
        return f'<div id="{div_id}" class="plot {extra_class}" style="height:{height}px"></div>'

    def script_array(self) -> str:
        return "[" + ",\n".join(self.items) + "]"


def _render_node(node, charts: _ChartCollector) -> str:
    if isinstance(node, Html):
        classes = "el md" + (" keep" if node.keep_with_next else "") + (
            " divider" if node.divider else "")
        return f'<div class="{classes}">{_markdown_fragment(node.html)}</div>'
    if isinstance(node, ChartRef):
        return f'<div class="el chart">{charts.div(node.key)}</div>'
    if isinstance(node, Row):
        cols = "".join(
            f'<div class="col stack" style="flex:{ratio} 1 0%">'
            + "".join(_render_node(n, charts) for n in cell) + "</div>"
            for ratio, cell in zip(node.ratios, node.cells)
        )
        return f'<div class="el row">{cols}</div>'
    return ""


def _document(title: str, css: str, body: str, charts: _ChartCollector,
              config: dict, paginate_limit: int | None) -> str:
    return (
        "<!doctype html>\n<html lang=\"es\"><head><meta charset=\"utf-8\">"
        f"<title>{_esc(title)}</title>"
        f"<style>{_font_css()}\n{_BASE_CSS}\n{css}</style>"
        f"<script>{get_plotlyjs()}</script>"
        f"</head><body>{body}"
        "<script>"
        f"const FONT_PROBES = {json.dumps(_FONT_PROBES)};\n"
        f"{_PAGINATE_JS}\n{_BOOT_JS}\n"
        f"boot({charts.script_array()}, {json.dumps(config)}, {json.dumps(paginate_limit)});"
        "</script></body></html>"
    )


# ── Documentos ────────────────────────────────────────────────────────────────
def report_document(snap: DashboardSnapshot, *, interactive: bool) -> str:
    """Reporte paginado. interactive=True añade detalle al pasar el mouse y el
    botón para guardar como PDF desde el navegador."""
    charts = _ChartCollector(snap)
    groups = "".join(
        f'<section class="grp stack" data-break="{1 if g.page_break else 0}">'
        + "".join(_render_node(n, charts) for n in g.nodes) + "</section>"
        for g in snap.groups
    )
    title = f"Evaluaciones docentes — {snap.teacher}"
    if snap.period_range:
        title += f" · {snap.period_range}"
    foot_left = _esc(title)
    foot_right = (f"Generado el {_esc(format_date(snap))} · "
                  'Página <span class="pn"></span> de <span class="pt"></span>')
    toolbar = (
        '<div class="toolbar"><button type="button" onclick="window.print()" '
        'title="Imprimir o guardar como PDF (tamaño carta, sin márgenes)">'
        "Guardar como PDF</button></div>"
        if interactive else ""
    )
    body = (
        f"{toolbar}<div id=\"pages\"></div>"
        f"<template id=\"page-tpl\"><div class=\"page\"><div class=\"page-body stack\"></div>"
        f"<footer class=\"page-foot\"><span>{foot_left}</span><span>{foot_right}</span>"
        f"</footer></div></template>"
        f"<main id=\"flow\" class=\"stack\">{groups}</main>"
    )
    config = ({"displayModeBar": False, "responsive": False} if interactive
              else {"staticPlot": True})
    return _document(title, _REPORT_CSS, body, charts, config, BODY_H)


def cards_document(snap: DashboardSnapshot, keys: list[str]) -> str:
    """Una tarjeta por gráfico, lista para capturar como imagen."""
    charts = _ChartCollector(snap)
    who = f"Evaluaciones docentes — {snap.teacher}"
    if snap.period_range:
        who += f" · {snap.period_range}"
    filtros = (f'<div class="card-note">Filtros aplicados: {_esc("; ".join(snap.filters))}</div>'
               if snap.filters else "")
    cards = []
    for key in keys:
        spec = snap.charts.get(key)
        if spec is None:
            continue
        eyebrow = f'<div class="card-eyebrow">{_esc(spec.section)}</div>' if spec.section else ""
        note = (f'<div class="card-note">{_esc(spec.note)}</div>' if spec.note else "") + filtros
        cards.append(
            f'<div class="card">{eyebrow}<div class="card-title">{_esc(spec.title)}</div>'
            f"{note}{charts.div(key)}"
            f'<div class="card-foot"><span>{_esc(who)}</span>'
            f"<span>Generado el {_esc(format_date(snap))}</span></div></div>"
        )
    return _document(who, _CARDS_CSS, "".join(cards), charts, {"staticPlot": True}, None)
