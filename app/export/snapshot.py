"""Registro de lo que el dashboard mostró en la ejecución actual.

Mientras Streamlit dibuja la página, cada sección deja aquí una copia de su HTML
y de sus figuras. Las descargas (PDF, HTML, PNG) se construyen desde este
registro, así reflejan exactamente el nombre, los filtros y el curso
seleccionados en pantalla.

Estructura:
  DashboardSnapshot.groups  → bloques que el PDF intenta no partir entre páginas.
  Group.nodes               → elementos en orden: HTML (str), ChartRef o Row.
  Row.cells                 → columnas (mismas proporciones que st.columns).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import plotly.graph_objects as go


@dataclass
class Html:
    html: str
    keep_with_next: bool = False   # títulos/etiquetas: no quedar solos al final de una página
    divider: bool = False          # separador de sección: se omite al inicio/fin de página


@dataclass
class ChartRef:
    key: str


@dataclass
class Row:
    ratios: list[float]
    cells: list[list] = field(default_factory=list)


@dataclass
class Group:
    nodes: list = field(default_factory=list)
    page_break: bool = False       # empezar en una hoja nueva


@dataclass
class ChartSpec:
    key: str
    fig: go.Figure
    title: str
    section: str = ""
    note: str = ""


@dataclass
class DashboardSnapshot:
    teacher: str = ""
    period_range: str = ""
    filters: list[str] = field(default_factory=list)
    generated: date = field(default_factory=date.today)
    groups: list[Group] = field(default_factory=list)
    charts: dict[str, ChartSpec] = field(default_factory=dict)
