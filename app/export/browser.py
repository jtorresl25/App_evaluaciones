"""Render de HTML con un navegador Chromium sin interfaz (headless).

Convierte el reporte en PDF y captura cada gráfico como PNG usando el mismo motor
que dibuja el dashboard, así el resultado se ve igual que en pantalla.

El navegador se localiza con choreographer (la librería que usa Kaleido/Plotly):
en Windows sirve Chrome o Edge; en macOS, Chrome; en Linux —por ejemplo
Streamlit Community Cloud— el paquete `chromium` declarado en packages.txt.
La variable de entorno BROWSER_PATH permite indicar una ruta manualmente.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import os
import tempfile
import threading
import time
from collections import OrderedDict
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

_LOCK = threading.Lock()          # un Chrome a la vez: cada instancia usa ~200 MB
_TIMEOUT_S = 90
# Resultados recientes en memoria (clave = hash del documento), para que un
# segundo clic sobre la misma descarga sea inmediato. Nada se escribe a disco.
_CACHE: OrderedDict[str, object] = OrderedDict()
_CACHE_MAX = 8

# choreographer registra como WARNING el cierre forzado del navegador; no es un error.
logging.getLogger("choreographer").setLevel(logging.ERROR)


@lru_cache(maxsize=1)
def browser_path() -> str | None:
    """Ruta del navegador Chromium disponible, o None si no hay ninguno."""
    try:
        from choreographer.browsers.chromium import Chromium
    except ImportError:
        return None
    try:
        path = os.environ.get("BROWSER_PATH") or Chromium.find_browser(skip_local=False)
    except Exception:
        return None
    return path if path and Path(path).is_file() else None


def available() -> bool:
    return browser_path() is not None


def print_pdf(html: str) -> bytes:
    """PDF del documento, respetando su CSS de impresión (@page, saltos de página)."""
    return _cached(("pdf", html), _print_pdf, html)


def capture_elements(html: str, selector: str, *, scale: float = 3.0) -> list[bytes]:
    """PNG de cada elemento que coincide con `selector`, a `scale`× la resolución CSS."""
    return _cached(("png", html, selector, scale), _capture, html, selector, scale)


# ── Internos ──────────────────────────────────────────────────────────────────
def _cached(key: tuple, render, *args):
    """Ejecuta `render(*args)` en un navegador nuevo, o devuelve el resultado reciente.

    Streamlit ejecuta cada descarga en su propio hilo: el candado serializa los
    renders y protege la caché.
    """
    if not available():
        raise RuntimeError("No se encontró Chrome, Chromium ni Edge para generar el archivo.")
    digest = hashlib.sha256(repr(key).encode("utf-8")).hexdigest()
    with _LOCK:
        if digest in _CACHE:
            _CACHE.move_to_end(digest)
            return _CACHE[digest]
        result = asyncio.run(asyncio.wait_for(render(*args), _TIMEOUT_S))
        _CACHE[digest] = result
        while len(_CACHE) > _CACHE_MAX:
            _CACHE.popitem(last=False)
        return result


@contextmanager
def _temp_html(html: str):
    """Archivo temporal con el documento; se borra siempre, aunque falle el render."""
    fd, name = tempfile.mkstemp(prefix="dashboard_", suffix=".html")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(html)
        yield Path(name)
    finally:
        try:
            Path(name).unlink(missing_ok=True)
        except OSError:
            pass


async def _open(browser, path: Path, *, width: int, height: int, scale: float = 1.0):
    """Abre el documento y espera a que la página avise que está lista."""
    tab = await browser.create_tab("")
    await tab.send_command("Page.enable")
    await tab.send_command("Emulation.setDeviceMetricsOverride", params={
        "width": width, "height": height, "deviceScaleFactor": scale, "mobile": False,
    })
    loaded = tab.subscribe_once("Page.loadEventFired")
    await tab.send_command("Page.navigate", params={"url": path.as_uri()})
    await loaded
    # El documento marca window.__exportReady cuando cargó fuentes, dibujó los
    # gráficos y (en el reporte) terminó de paginar.
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        if await _eval(tab, "window.__exportReady === true"):
            break
        await asyncio.sleep(0.1)
    else:
        raise TimeoutError("El documento de exportación no terminó de dibujarse.")
    return tab


async def _eval(tab, expression: str):
    res = await tab.send_command("Runtime.evaluate", params={
        "expression": expression, "returnByValue": True, "awaitPromise": True,
    })
    return res.get("result", {}).get("result", {}).get("value")


async def _print_pdf(html: str) -> bytes:
    import choreographer as choreo

    with _temp_html(html) as path:
        async with choreo.Browser(path=browser_path(), headless=True) as browser:
            tab = await _open(browser, path, width=1280, height=1000)
            res = await tab.send_command("Page.printToPDF", params={
                "printBackground": True,
                "preferCSSPageSize": True,
            })
            return base64.b64decode(res["result"]["data"])


async def _capture(html: str, selector: str, scale: float) -> list[bytes]:
    import choreographer as choreo

    with _temp_html(html) as path:
        async with choreo.Browser(path=browser_path(), headless=True) as browser:
            tab = await _open(browser, path, width=1100, height=900, scale=scale)
            rects = await _eval(tab, f"""
                Array.from(document.querySelectorAll({selector!r})).map(el => {{
                    const r = el.getBoundingClientRect();
                    return {{x: r.left + scrollX, y: r.top + scrollY,
                             width: r.width, height: r.height}};
                }})""") or []
            images = []
            for rect in rects:
                shot = await tab.send_command("Page.captureScreenshot", params={
                    "format": "png",
                    "clip": {**rect, "scale": 1},
                    "captureBeyondViewport": True,
                })
                images.append(base64.b64decode(shot["result"]["data"]))
            return images
