import streamlit as st

# ── Paleta oscura ─────────────────────────────────────────────────────────────
_BG_CARD      = "#0D2733"
_BG_CARD_HERO = "#112F3E"
_BORDER       = "#1A3D4E"
_BORDER_HERO  = "#245970"
_TEXT_P1      = "#E0EEF2"
_TEXT_P2      = "#8CBECB"
_TEXT_MUTED   = "#537F8A"
_GOLD         = "#D4A843"
_GOLD_TINT    = "rgba(212,168,67,0.13)"
_GREEN        = "#4DB88A"
_GREEN_TINT   = "rgba(77,184,138,0.13)"
_FONT         = "'IBM Plex Sans', system-ui, sans-serif"

# ── Bloques de estilo reutilizables ───────────────────────────────────────────
_BASE = (
    f"border-radius:16px;"
    f"padding:22px 22px 18px;"
    f"position:relative;"
    f"font-family:{_FONT};"
    f"box-sizing:border-box;"
    f"height:100%;"
)
_CARD_NORMAL = (
    _BASE
    + f"background:{_BG_CARD};"
    + f"border:1px solid {_BORDER};"
    + "box-shadow:0 2px 8px rgba(0,0,0,0.25);"
)
_CARD_HERO = (
    _BASE
    + f"background:{_BG_CARD_HERO};"
    + f"border:1px solid {_BORDER_HERO};"
    + "box-shadow:0 4px 20px rgba(0,0,0,0.35);"
    + f"border-left:4px solid {_GOLD};"
    + "padding-left:18px;"
)

_LBL_NORMAL = f"font-size:12px;color:{_TEXT_P2};font-weight:500;letter-spacing:.01em;display:block;margin-bottom:6px;"
_LBL_HERO   = _LBL_NORMAL + "padding-left:8px;"

_VAL_NORMAL = f"font-family:'Spectral',Georgia,serif;font-weight:700;font-size:42px;color:{_TEXT_P1};line-height:1;letter-spacing:-.02em;display:block;"
_VAL_HERO   = f"font-family:'Spectral',Georgia,serif;font-weight:700;font-size:56px;color:{_TEXT_P1};line-height:1;letter-spacing:-.02em;display:block;padding-left:8px;"

_FOOT_NORMAL = f"font-size:11.5px;color:{_TEXT_MUTED};margin-top:9px;display:block;line-height:1.4;"
_FOOT_HERO   = _FOOT_NORMAL + "padding-left:8px;"

_RIBBON_STYLE = (
    f"position:absolute;top:15px;right:16px;"
    f"font-size:9.5px;letter-spacing:.14em;text-transform:uppercase;"
    f"color:#0D2733;background:{_GOLD};"
    f"padding:3px 9px;border-radius:20px;font-weight:600;"
    f"font-family:{_FONT};"
)
_CHIP_STYLE = (
    f"display:inline-flex;align-items:center;gap:5px;"
    f"font-size:11px;font-weight:600;color:{_GREEN};background:{_GREEN_TINT};"
    f"padding:3px 10px;border-radius:20px;margin-top:8px;"
    f"font-family:{_FONT};"
)


def _fmt(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        if value == int(value):
            return str(int(value))
        return f"{value:.1f}"
    return str(value)


def render_kpi_card(
    label: str,
    value,
    footer: str | None = None,
    highlight: bool = False,
    ribbon: str | None = None,
    chip: str | None = None,
    suffix: str = "",
) -> None:
    """
    Tarjeta KPI con estilos inline completos — tema oscuro.
    Funciona independientemente de si el CSS externo carga.
    """
    card_style = _CARD_HERO if highlight else _CARD_NORMAL
    lbl_style  = _LBL_HERO  if highlight else _LBL_NORMAL
    val_style  = _VAL_HERO  if highlight else _VAL_NORMAL
    foot_style = _FOOT_HERO if highlight else _FOOT_NORMAL

    ribbon_html = (
        f'<span style="{_RIBBON_STYLE}">{ribbon}</span>' if ribbon else ""
    )
    chip_html = (
        f'<span style="{_CHIP_STYLE}">↑ {chip}</span>' if chip else ""
    )
    foot_html = (
        f'<span style="{foot_style}">{footer}</span>' if footer else ""
    )

    display_value = (_fmt(value) + suffix) if value is not None else "—"

    html = (
        f'<div style="{card_style}">'
        f'{ribbon_html}'
        f'<span style="{lbl_style}">{label}</span>'
        f'<span style="{val_style}">{display_value}</span>'
        f'{chip_html}'
        f'{foot_html}'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# ── Filas de KPIs ─────────────────────────────────────────────────────────────
def render_kpi_row_hero(metrics: dict) -> None:
    pct_fac  = metrics.get("pct_sobre_facultad_actual")
    pct_uni  = metrics.get("pct_sobre_universidad_actual")
    periodos = metrics.get("periodos_validos_modelo_actual", 0)

    col1, col2, col3 = st.columns([2, 2, 1.5])
    with col1:
        render_kpi_card(
            label="Posición sobre Facultad",
            value=pct_fac, suffix="%",
            footer="de periodos válidos por encima del promedio de Facultad",
            highlight=True, ribbon="Modelo actual",
        )
    with col2:
        render_kpi_card(
            label="Posición sobre Universidad",
            value=pct_uni, suffix="%",
            footer="de periodos válidos por encima del promedio de Universidad",
            highlight=True, ribbon="Modelo actual",
        )
    with col3:
        render_kpi_card(
            label="Periodos válidos · modelo actual",
            value=periodos,
            footer="registros con evaluación completa",
            chip="serie continua",
        )


def render_kpi_row_secondary(metrics: dict) -> None:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_kpi_card(
            label="Cursos únicos",
            value=metrics.get("cursos_unicos"),
            footer="con datos individuales",
        )
    with col2:
        render_kpi_card(
            label="Registros válidos",
            value=metrics.get("registros_validos"),
            footer="en la base general",
        )
    with col3:
        render_kpi_card(
            label="Sin docencia / N.A.",
            value=metrics.get("registros_sin_docencia"),
            footer="excluido de promedios y gráficas",
        )
    with col4:
        render_kpi_card(
            label="Periodos válidos total",
            value=metrics.get("total_periodos_validos"),
            footer="ambos modelos combinados",
        )
