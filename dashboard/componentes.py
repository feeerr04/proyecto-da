"""
Componentes visuales compartidos: paleta semántica y estilo de los gráficos.

Todas las vistas deben usar estas constantes y funciones para que el
dashboard se vea como un solo sistema (ley de similitud de la Gestalt).

Reglas de color (no romperlas al agregar vistas):
- Departamento = color de identidad fijo: Costura azul, Acabado naranja.
  El color sigue a la entidad: si un filtro deja un solo departamento,
  conserva su color.
- La meta es una referencia, no una serie: gris neutro y línea punteada.
- Cumple / no cumple usa colores de estado, siempre acompañados de texto.
- El color nunca decora: si no codifica un dato o una alerta, va en gris.

La paleta azul/naranja se validó para daltonismo (ΔE 24.7, mínimo 8).
"""

import altair as alt

COLORES = {
    "Costura": "#2a78d6",
    "Acabado": "#eb6834",
    "real": "#2a78d6",
    "meta": "#52514e",
    "cumple": "#0ca30c",
    "no_cumple": "#d03b3b",
    "texto": "#0b0b0b",
    "texto_secundario": "#52514e",
    "texto_tenue": "#6f6e69",
    "rejilla": "#e8e7e3",
    "superficie": "#fcfcfb",
}

DEPARTAMENTOS = ["Costura", "Acabado"]

ESCALA_DEPARTAMENTO = alt.Scale(
    domain=DEPARTAMENTOS,
    range=[COLORES["Costura"], COLORES["Acabado"]],
)

FUENTE = "Source Sans Pro, Source Sans 3, sans-serif"


def estilo(grafico: alt.Chart) -> alt.Chart:
    """Aplica el estilo común: rejilla y ejes recesivos, sin bordes (data-ink)."""
    return (
        grafico.configure(font=FUENTE, background=COLORES["superficie"])
        .configure_view(strokeWidth=0)
        .configure_axis(
            labelColor=COLORES["texto_secundario"],
            titleColor=COLORES["texto_secundario"],
            labelFontSize=12,
            titleFontSize=12,
            titleFontWeight="normal",
            gridColor=COLORES["rejilla"],
            domainColor=COLORES["rejilla"],
            tickColor=COLORES["rejilla"],
        )
        .configure_legend(
            labelColor=COLORES["texto"],
            titleColor=COLORES["texto_secundario"],
            labelFontSize=12,
            titleFontSize=12,
            orient="top",
            direction="horizontal",
            symbolStrokeWidth=2,
        )
    )


def en_construccion(parte: str, pendientes: list[str]) -> None:
    """Aviso temporal para las vistas que completan las Partes 2 y 3."""
    import streamlit as st

    st.info(f"Vista en construcción · {parte}", icon=":material/construction:")
    st.markdown("\n".join(f"- {p}" for p in pendientes))


MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun",
                "jul", "ago", "sep", "oct", "nov", "dic"]

# Etiquetas de fecha en español para ejes temporales de Altair (Vega usa inglés)
EJE_FECHA_ES = (
    "timeFormat(datum.value, '%d') + ' ' + "
    "['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic']"
    "[month(datum.value)]"
)


def fecha_es(fecha) -> str:
    """'2015-02-02' -> '02 feb 2015' (para tooltips y textos)."""
    return f"{fecha.day:02d} {MESES_CORTOS[fecha.month - 1]} {fecha.year}"


def fmt_prod(valor: float) -> str:
    """Productividad con 3 decimales (misma precisión del artículo)."""
    return f"{valor:.3f}"


def fmt_pct(valor: float) -> str:
    return f"{valor:.1%}"


def fmt_signo(valor: float, decimales: int = 3) -> str:
    return f"{valor:+.{decimales}f}"
