"""
Paso 1 de 4 - Diagnóstico inicial (overview first).

Pregunta que responde: ¿cómo está la productividad de la planta en la
selección actual y dónde conviene mirar primero?

Contenido:
- Titular dinámico: la conclusión en una frase (storytelling).
- Tarjetas KPI con la diferencia frente a la planta completa al filtrar.
- Panorámica: productividad real vs. meta por día (posición en eje común).
- Cumplimiento de meta por departamento (longitud de barra, desde 0).
- Detalle a demanda: tabla diaria y notas de calidad de datos.
"""

import altair as alt
import pandas as pd
import streamlit as st

from componentes import (
    COLORES, DEPARTAMENTOS, EJE_FECHA_ES, ESCALA_DEPARTAMENTO, estilo, fecha_es, fmt_pct,
    fmt_prod, fmt_signo,
)
from datos import MINIMO_REPRESENTATIVO, hay_filtro_activo


def _kpis(df: pd.DataFrame) -> dict:
    return {
        "registros": len(df),
        "productividad": df["productividad"].mean(),
        "meta": df["meta"].mean(),
        "cumplimiento": df["cumple_meta"].mean(),
        "brecha": df["brecha"].mean(),
    }


def _titular(df: pd.DataFrame, k: dict) -> str:
    texto = (
        f"En la selección, la productividad real promedio fue **{fmt_prod(k['productividad'])}** "
        f"frente a una meta de **{fmt_prod(k['meta'])}**, y el "
        f"**{fmt_pct(k['cumplimiento'])}** de los registros alcanzó su meta."
    )
    por_depto = df.groupby("departamento")["cumple_meta"].mean()
    if len(por_depto) == 2:
        menor = por_depto.idxmin()
        texto += (
            f" El cumplimiento más bajo está en **{menor}** "
            f"({fmt_pct(por_depto[menor])} frente a {fmt_pct(por_depto.drop(menor).iloc[0])})."
        )
    return texto


def _tarjetas(k: dict, k_total: dict, filtrado: bool) -> None:
    def delta(clave, formato):
        if not filtrado:
            return None
        return f"{formato(k[clave] - k_total[clave])} vs. planta"

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric(
        "Productividad real", fmt_prod(k["productividad"]),
        delta=delta("productividad", fmt_signo), border=True,
        help="Promedio de la productividad real (actual_productivity). Escala de 0 a 1; 37 registros superan 1.",
    )
    c2.metric(
        "Meta", fmt_prod(k["meta"]),
        delta=delta("meta", fmt_signo), delta_color="off", border=True,
        help="Promedio de la meta de productividad (targeted_productivity).",
    )
    c3.metric(
        "Cumplen su meta", fmt_pct(k["cumplimiento"]),
        delta=delta("cumplimiento", lambda v: f"{v * 100:+.1f} pp"), border=True,
        help="Porcentaje de registros con productividad real mayor o igual que su meta.",
    )
    c4.metric(
        "Brecha vs. meta", fmt_signo(k["brecha"]),
        delta=delta("brecha", fmt_signo), border=True,
        help="Promedio de (productividad real − meta). Positivo: por encima de la meta; negativo: por debajo.",
    )
    c5.metric(
        "Registros",
        f"{k['registros']:,} de {k_total['registros']:,}" if filtrado else f"{k['registros']:,}",
        border=True,
        help="Cada registro es un equipo, en un departamento, en una fecha.",
    )


def _panoramica(df: pd.DataFrame) -> alt.Chart:
    diario = (
        df.groupby("fecha")
        .agg(real=("productividad", "mean"), meta=("meta", "mean"),
             registros=("productividad", "size"))
        .reset_index()
    )
    diario["brecha"] = diario["real"] - diario["meta"]
    diario["fecha_txt"] = diario["fecha"].map(fecha_es)
    largo = diario.melt(
        id_vars=["fecha", "registros", "brecha"], value_vars=["real", "meta"],
        var_name="serie", value_name="valor",
    )
    largo["serie"] = largo["serie"].map({"real": "Productividad real", "meta": "Meta"})

    color = alt.Color(
        "serie:N", title=None,
        scale=alt.Scale(domain=["Productividad real", "Meta"],
                        range=[COLORES["real"], COLORES["meta"]]),
        legend=alt.Legend(orient="top", direction="horizontal", symbolType="stroke"),
    )
    trazo = alt.StrokeDash(
        "serie:N", legend=None,
        scale=alt.Scale(domain=["Productividad real", "Meta"], range=[[1, 0], [6, 4]]),
    )
    x = alt.X("fecha:T", title=None, axis=alt.Axis(labelExpr=EJE_FECHA_ES, labelAngle=0, tickCount=8))
    y = alt.Y("valor:Q", title="Productividad promedio del día",
              scale=alt.Scale(zero=False, nice=True))

    base = alt.Chart(largo).encode(x=x)
    lineas = base.mark_line(strokeWidth=2).encode(y=y, color=color, strokeDash=trazo)

    # Hover: regla vertical + tooltip con los dos valores del día
    cercano = alt.selection_point(
        nearest=True, on="pointerover", fields=["fecha"], empty=False, clear="pointerout",
    )
    regla = (
        alt.Chart(diario).mark_rule(color=COLORES["texto_tenue"], strokeWidth=1)
        .encode(
            x="fecha:T",
            opacity=alt.condition(cercano, alt.value(0.6), alt.value(0)),
            tooltip=[
                alt.Tooltip("fecha_txt:N", title="Fecha"),
                alt.Tooltip("real:Q", title="Productividad real", format=".3f"),
                alt.Tooltip("meta:Q", title="Meta", format=".3f"),
                alt.Tooltip("brecha:Q", title="Brecha (real − meta)", format="+.3f"),
                alt.Tooltip("registros:Q", title="Registros del día"),
            ],
        )
        .add_params(cercano)
    )
    puntos = lineas.mark_point(filled=True, size=60).encode(
        opacity=alt.condition(cercano, alt.value(1), alt.value(0)),
    )

    # La identidad no depende solo del color: la meta además va punteada
    return (lineas + puntos + regla).properties(height=320)


def _cumplimiento_departamento(df: pd.DataFrame) -> alt.Chart:
    tabla = (
        df.groupby("departamento")
        .agg(cumplimiento=("cumple_meta", "mean"), registros=("cumple_meta", "size"),
             cumplen=("cumple_meta", "sum"))
        .reindex([d for d in DEPARTAMENTOS if d in df["departamento"].unique()])
        .reset_index()
    )
    tabla["etiqueta"] = tabla.apply(
        lambda f: f"{f['cumplimiento']:.0%}  ({int(f['cumplen'])} de {int(f['registros'])})", axis=1,
    )
    base = alt.Chart(tabla).encode(
        y=alt.Y("departamento:N", title=None, sort=DEPARTAMENTOS,
                axis=alt.Axis(labelFontSize=13, labelColor=COLORES["texto"])),
    )
    barras = base.mark_bar(cornerRadiusEnd=4, height=28).encode(
        x=alt.X("cumplimiento:Q", title="Registros que cumplen su meta",
                scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format="%", tickCount=5)),
        color=alt.Color("departamento:N", scale=ESCALA_DEPARTAMENTO, legend=None),
        tooltip=[
            alt.Tooltip("departamento:N", title="Departamento"),
            alt.Tooltip("cumplimiento:Q", title="Cumplimiento", format=".1%"),
            alt.Tooltip("cumplen:Q", title="Registros que cumplen"),
            alt.Tooltip("registros:Q", title="Registros totales"),
        ],
    )
    texto = base.mark_text(align="left", dx=8, fontSize=12, color=COLORES["texto"]).encode(
        x="cumplimiento:Q", text="etiqueta:N",
    )
    return (barras + texto).properties(height=60 * len(tabla) + 40)


def _tabla_diaria(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("fecha")
        .agg(registros=("productividad", "size"), productividad=("productividad", "mean"),
             meta=("meta", "mean"), cumplimiento=("cumple_meta", "mean"))
        .reset_index()
        .assign(brecha=lambda t: t["productividad"] - t["meta"])
    )


def mostrar(df: pd.DataFrame, df_total: pd.DataFrame) -> None:
    st.caption("PASO 1 DE 4 · DIAGNÓSTICO INICIAL")
    st.title("¿Cómo está la productividad de la planta?")

    k, k_total = _kpis(df), _kpis(df_total)
    st.markdown(_titular(df, k))
    if len(df) < MINIMO_REPRESENTATIVO:
        st.warning(
            f"La selección tiene solo {len(df)} registros: los promedios pueden ser poco "
            "representativos. Amplía el periodo o los equipos.",
            icon=":material/info:",
        )

    _tarjetas(k, k_total, hay_filtro_activo(df, df_total))

    st.subheader("Productividad real frente a la meta, por día")
    st.altair_chart(estilo(_panoramica(df)), width="stretch", theme=None)
    st.caption(
        "Promedio diario de los registros seleccionados. El eje vertical no inicia en 0 "
        "para mostrar la variación diaria: en una línea se compara la posición, no la longitud."
    )

    st.subheader("¿Qué departamento cumple su meta con más frecuencia?")
    st.altair_chart(estilo(_cumplimiento_departamento(df)), width="stretch", theme=None)
    st.caption("Porcentaje de registros cuya productividad real alcanzó o superó su meta.")

    with st.expander("Ver los datos diarios de la selección", icon=":material/table:"):
        st.dataframe(
            _tabla_diaria(df), hide_index=True, width="stretch",
            column_config={
                "fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
                "registros": st.column_config.NumberColumn("Registros"),
                "productividad": st.column_config.NumberColumn("Productividad real", format="%.3f"),
                "meta": st.column_config.NumberColumn("Meta", format="%.3f"),
                "cumplimiento": st.column_config.NumberColumn("Cumplimiento", format="percent"),
                "brecha": st.column_config.NumberColumn("Brecha", format="%+.3f"),
            },
        )

    with st.expander("Notas de calidad de los datos (Fase I)", icon=":material/fact_check:"):
        st.markdown(
            f"""
- **wip sin registrar:** {int(df['wip_faltante'].sum())} registros de la selección,
  todos de Acabado. Se conservaron sin imputar (decisión de la Fase I).
- **Productividad mayor que 1:** {int(df['productividad_mayor_1'].sum())} registros,
  fuera del rango documentado (0 a 1). Se conservan como discrepancia.
- **Personal fraccionario:** {int(df['personal_fraccionario'].sum())} registros
  con decimales en el personal asignado.
- **Atípicos (criterio IQR):** {int(df['atipico_wip'].sum())} en wip,
  {int(df['atipico_tiempo_extra'].sum())} en tiempo extra y
  {int(df['atipico_incentivo'].sum())} en incentivo. Se conservaron.
"""
        )

    st.page_link("vistas/patrones.py", label="Siguiente: patrones y anomalías",
                 icon=":material/arrow_forward:")


# Cada vista es una página de st.navigation: app.py deja en session_state
# la selección filtrada y la planta completa.
mostrar(st.session_state["seleccion"], st.session_state["planta"])
