"""Tema Plotly para exportar los gráficos con el mismo aspecto que en pantalla.

Al importarse, Streamlit define la plantilla por defecto de Plotly ("streamlit")
con colores marcadores (#000001, #000036…) que solo su frontend traduce a colores
reales, y además aplica en el navegador el tema de .streamlit/config.toml. Fuera
de Streamlit (PDF, PNG, HTML descargable) esos marcadores saldrían casi negros.

Esta plantilla es la versión ya resuelta para el tema oscuro de la app, copiada
del layout que Plotly calcula en pantalla (gd.layout.template). Las figuras
conservan sus propios estilos explícitos: la plantilla solo completa lo que ellas
no definen (margen interno, ejes, leyenda), igual que ocurre en el dashboard.
Si se cambia el tema en config.toml, hay que actualizar estos valores.
"""
import plotly.graph_objects as go

_BG = "#081C24"
_TEXT = "#e6eaf1"
_LINE = "#31333F"
_FONT = '"Source Sans", sans-serif'

_SEQUENTIAL = [
    [0.0, "#004280"], [0.1111111111111111, "#0054a3"], [0.2222222222222222, "#0068c9"],
    [0.3333333333333333, "#1c83e1"], [0.4444444444444444, "#3d9df3"],
    [0.5555555555555556, "#60b4ff"], [0.6666666666666666, "#83c9ff"],
    [0.7777777777777778, "#a6dcff"], [0.8888888888888888, "#c7ebff"], [1.0, "#e4f5ff"],
]
_DIVERGING = [
    [0.0, "#7d353b"], [0.1111111111111111, "#bd4043"], [0.2222222222222222, "#ff4b4b"],
    [0.3333333333333333, "#ff8c8c"], [0.4444444444444444, "#ffc7c7"],
    [0.5555555555555556, "#a6dcff"], [0.6666666666666666, "#60b4ff"],
    [0.7777777777777778, "#1c83e1"], [0.8888888888888888, "#0054a3"], [1.0, "#004280"],
]

STREAMLIT_DARK = go.layout.Template(
    data=dict(
        heatmap=[dict(colorscale=_SEQUENTIAL)],
        scatter=[dict(marker=dict(line=dict(width=0)))],
    ),
    layout=dict(
        font=dict(color=_TEXT, family=_FONT, size=12),
        colorway=["#83c9ff", "#0068c9", "#ffabab", "#ff2b2b", "#7defa1",
                  "#29b09d", "#ffd16a", "#ff8700", "#6d3fc0", "#d5dae5"],
        colorscale=dict(sequential=_SEQUENTIAL, sequentialminus=_SEQUENTIAL,
                        diverging=_DIVERGING),
        coloraxis=dict(
            colorscale=_SEQUENTIAL,
            colorbar=dict(thickness=16, xpad=24, ticklabelposition="outside",
                          outlinecolor="rgba(0,0,0,0)", outlinewidth=8, len=0.75,
                          y=0.5745, title=dict(font=dict(color=_TEXT, size=14)),
                          tickfont=dict(color=_TEXT, size=12)),
        ),
        title=dict(font=dict(family=_FONT, size=16, color="#E0EEF2"),
                   pad=dict(l=4), xanchor="left", x=0),
        legend=dict(title=dict(font=dict(size=12, color=_TEXT), side="top"),
                    valign="top", bordercolor="rgba(0,0,0,0)", borderwidth=0,
                    font=dict(size=12, color="#fafafa")),
        paper_bgcolor=_BG,
        plot_bgcolor=_BG,
        xaxis=dict(zerolinecolor=_LINE, gridcolor=_LINE, showgrid=False, zeroline=False,
                   automargin=True, tickcolor=_LINE, tickfont=dict(color=_TEXT, size=12),
                   title=dict(font=dict(color=_TEXT, size=14), standoff=20),
                   minor=dict(gridcolor=_LINE)),
        yaxis=dict(ticklabelposition="outside", zerolinecolor=_LINE, gridcolor=_LINE,
                   automargin=True, tickcolor=_LINE, tickfont=dict(color=_TEXT, size=12),
                   title=dict(font=dict(color=_TEXT, size=14), standoff=24),
                   minor=dict(gridcolor=_LINE)),
        margin=dict(pad=8, r=0, l=0),
        hoverlabel=dict(bgcolor=_BG, bordercolor="rgba(224, 238, 242, 0.2)",
                        font=dict(color=_TEXT, family=_FONT, size=12)),
    ),
)


def export_figure(fig: go.Figure) -> go.Figure:
    """Copia de la figura con el tema de pantalla ya resuelto (no modifica la original)."""
    out = go.Figure(fig)
    out.update_layout(template=STREAMLIT_DARK)
    return out
