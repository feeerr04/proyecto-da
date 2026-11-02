"""Paso 2: localizar brechas y anomalías con los filtros globales."""

import altair as alt
import pandas as pd
import streamlit as st

from componentes import (
    COLORES, DEPARTAMENTOS, EJE_FECHA_ES, ESCALA_DEPARTAMENTO,
    estilo, fecha_es, fmt_signo,
)
from datos import MINIMO_REPRESENTATIVO

ATIPICOS = {
    "atipico_wip": ("Trabajo en proceso (WIP)", "wip"),
    "atipico_tiempo_extra": ("Tiempo extra", "tiempo_extra_min"),
    "atipico_incentivo": ("Incentivo", "incentivo_bdt"),
}


def resumen_semanal(df: pd.DataFrame, por_equipo: bool = False) -> pd.DataFrame:
    """Semanas lunes-domingo; promedios por registro, sin completar ausencias."""
    datos = df.assign(semana=df["fecha"].dt.to_period("W-SUN").dt.start_time)
    claves = ["departamento", "semana"] + (["equipo"] if por_equipo else [])
    tabla = datos.groupby(claves).agg(
        productividad=("productividad", "mean"), meta=("meta", "mean"),
        brecha=("brecha", "mean"), registros=("productividad", "size"),
        dias=("fecha", "nunique"),
    ).reset_index()
    tabla["semana_txt"] = tabla["semana"].map(fecha_es)
    return tabla


def resumen_equipos(df: pd.DataFrame) -> pd.DataFrame:
    tabla = df.groupby(["departamento", "equipo"]).agg(
        brecha=("brecha", "mean"), registros=("brecha", "size"),
        productividad=("productividad", "mean"), meta=("meta", "mean"),
        cumplimiento=("cumple_meta", "mean"),
    ).reset_index()
    tabla["identidad"] = tabla["departamento"] + " · equipo " + tabla["equipo"].astype(str)
    tabla["estado"] = tabla["brecha"].map(
        lambda v: "Brecha media ≥ 0" if v >= 0 else "Brecha media < 0"
    )
    tabla["etiqueta"] = tabla["brecha"].map(fmt_signo)
    return tabla.sort_values(["brecha", "departamento", "equipo"])


def anomalias_diarias(df: pd.DataFrame) -> pd.DataFrame:
    tablas = []
    for bandera, (nombre, variable) in ATIPICOS.items():
        # Un WIP sin registrar no es una observación normal ni un cero.
        observados = df.loc[df[variable].notna()]
        tabla = observados.groupby("fecha").agg(
            atipicos=(bandera, "sum"), observados=(bandera, "size")
        ).reset_index()
        tabla["variable"] = nombre
        tablas.append(tabla)
    resultado = pd.concat(tablas, ignore_index=True)
    resultado["fecha_txt"] = resultado["fecha"].map(fecha_es)
    return resultado


def _tendencia(tabla: pd.DataFrame) -> alt.Chart:
    lineas = alt.Chart(tabla).mark_line(point=True, strokeWidth=2).encode(
        x=alt.X("semana:T", title="Inicio de semana (lunes)",
                axis=alt.Axis(labelExpr=EJE_FECHA_ES, labelAngle=0, tickCount=8, grid=False)),
        y=alt.Y("brecha:Q", title="Brecha media (real − meta)", scale=alt.Scale(zero=True)),
        color=alt.Color("departamento:N", title=None, scale=ESCALA_DEPARTAMENTO),
        tooltip=[
            alt.Tooltip("departamento:N", title="Departamento"),
            alt.Tooltip("semana_txt:N", title="Semana desde"),
            alt.Tooltip("brecha:Q", title="Brecha media", format="+.3f"),
            alt.Tooltip("productividad:Q", title="Productividad", format=".3f"),
            alt.Tooltip("meta:Q", title="Meta", format=".3f"),
            alt.Tooltip("registros:Q", title="Registros"),
            alt.Tooltip("dias:Q", title="Días observados"),
        ],
    )
    cero = alt.Chart(pd.DataFrame({"referencia": [0]})).mark_rule(
        color=COLORES["meta"], strokeDash=[6, 4]
    ).encode(y="referencia:Q", tooltip=alt.Tooltip("referencia:Q", title="Real = meta"))
    return (lineas + cero).properties(height=290)


def _ranking(tabla: pd.DataFrame) -> alt.Chart:
    limite = max(float(tabla["brecha"].abs().max()) * 1.3, 0.03)
    base = alt.Chart(tabla).encode(
        y=alt.Y("identidad:N", title=None, sort=tabla["identidad"].tolist(),
                axis=alt.Axis(labelLimit=200)),
        x=alt.X("brecha:Q", title="Brecha media (real − meta)",
                scale=alt.Scale(domain=[-limite, limite], zero=True), axis=alt.Axis(tickCount=7)),
        tooltip=[
            alt.Tooltip("identidad:N", title="Departamento y equipo"),
            alt.Tooltip("brecha:Q", title="Brecha media", format="+.3f"),
            alt.Tooltip("registros:Q", title="Registros"),
            alt.Tooltip("cumplimiento:Q", title="Cumplen su meta", format=".1%"),
        ],
    )
    barras = base.mark_bar(height=16).encode(color=alt.Color(
        "estado:N", title=None, scale=alt.Scale(
            domain=["Brecha media ≥ 0", "Brecha media < 0"],
            range=[COLORES["cumple"], COLORES["no_cumple"]]),
    ))
    positivos = base.transform_filter(alt.datum.brecha >= 0).mark_text(
        align="left", dx=5, fontSize=12, color=COLORES["texto"]
    ).encode(text="etiqueta:N")
    negativos = base.transform_filter(alt.datum.brecha < 0).mark_text(
        align="right", dx=-5, fontSize=12, color=COLORES["texto"]
    ).encode(text="etiqueta:N")
    cero = alt.Chart(pd.DataFrame({"referencia": [0]})).mark_rule(
        color=COLORES["meta"]
    ).encode(x="referencia:Q", tooltip=alt.Tooltip("referencia:Q", title="Real = meta"))
    return (barras + positivos + negativos + cero).properties(height=26 * len(tabla) + 20)


def _equipos(tabla: pd.DataFrame, departamento: str, dominio: list[float]) -> alt.Chart:
    largo = tabla.loc[tabla["departamento"].eq(departamento)].melt(
        id_vars=["equipo", "semana", "semana_txt", "registros", "dias"],
        value_vars=["productividad", "meta"], var_name="serie", value_name="valor",
    )
    largo["serie"] = largo["serie"].map({"productividad": "Productividad real", "meta": "Meta"})
    grafico = alt.Chart(largo).mark_line(point=True, strokeWidth=2).encode(
        x=alt.X("semana:T", title=None,
                axis=alt.Axis(labelExpr=EJE_FECHA_ES, tickCount=3, labelAngle=0, grid=False)),
        y=alt.Y("valor:Q", title="Productividad", scale=alt.Scale(domain=dominio, zero=True)),
        color=alt.Color("serie:N", title=None, scale=alt.Scale(
            domain=["Productividad real", "Meta"], range=[COLORES[departamento], COLORES["meta"]])),
        strokeDash=alt.StrokeDash("serie:N", legend=None, scale=alt.Scale(
            domain=["Productividad real", "Meta"], range=[[1, 0], [6, 4]])),
        tooltip=[
            alt.Tooltip("equipo:O", title="Equipo"),
            alt.Tooltip("semana_txt:N", title="Semana desde"),
            alt.Tooltip("serie:N", title="Medida"),
            alt.Tooltip("valor:Q", title="Promedio", format=".3f"),
            alt.Tooltip("registros:Q", title="Registros"),
            alt.Tooltip("dias:Q", title="Días observados"),
        ],
    ).properties(width=205, height=130)
    return grafico.facet(facet=alt.Facet("equipo:O", title="Equipo"), columns=3)


def _anomalias(tabla: pd.DataFrame) -> alt.Chart:
    return alt.Chart(tabla).mark_bar(color=COLORES["no_cumple"], size=7).encode(
        x=alt.X("fecha:T", title=None,
                axis=alt.Axis(labelExpr=EJE_FECHA_ES, labelAngle=0, tickCount=8, grid=False)),
        y=alt.Y("atipicos:Q", title="Registros atípicos",
                scale=alt.Scale(zero=True), axis=alt.Axis(tickMinStep=1)),
        tooltip=[
            alt.Tooltip("variable:N", title="Variable"),
            alt.Tooltip("fecha_txt:N", title="Fecha"),
            alt.Tooltip("atipicos:Q", title="Registros atípicos"),
            alt.Tooltip("observados:Q", title="Registros con valor observado"),
        ],
    ).properties(height=90).facet(row=alt.Row(
        "variable:N", title=None, header=alt.Header(labelAngle=0)))


def _detalle(df: pd.DataFrame) -> pd.DataFrame:
    tabla = df.copy()
    tabla["señales"] = tabla.apply(
        lambda fila: ", ".join(nombre for bandera, (nombre, _) in ATIPICOS.items() if fila[bandera]) or "Ninguna",
        axis=1,
    )
    return tabla.sort_values(["fecha", "departamento", "equipo"])[[
        "fecha", "departamento", "equipo", "productividad", "meta", "brecha",
        "cumple_meta", "wip", "tiempo_extra_min", "incentivo_bdt", "señales",
    ]]


def mostrar(df: pd.DataFrame) -> None:
    st.caption("PASO 2 DE 4 · PATRONES Y ANOMALÍAS")
    st.title("¿Dónde y cuándo se aleja la productividad de la meta?")
    if df.empty:
        st.info("No hay registros para los filtros seleccionados.")
        return

    semanal, equipos = resumen_semanal(df), resumen_equipos(df)
    peor = semanal.loc[semanal["brecha"].idxmin()]
    texto = (
        f"La menor brecha semanal de la selección corresponde a **{peor['departamento']}**, "
        f"en la semana que inicia el **{peor['semana_txt']}**: "
        f"**{fmt_signo(peor['brecha'])}** ({int(peor['registros'])} registros). "
    )
    texto += (
        "Su productividad media quedó por debajo de su meta media." if peor["brecha"] < 0 else
        "Todas las medias semanales observadas alcanzaron o superaron su meta media."
    )
    st.markdown(texto)
    if len(df) < MINIMO_REPRESENTATIVO:
        st.warning(f"Solo {len(df)} registros en la selección. Interpreta sus promedios con cautela.")

    con_atipicos = df[list(ATIPICOS)].any(axis=1)
    c1, c2, c3 = st.columns(3)
    c1.metric("Brecha media", fmt_signo(df["brecha"].mean()), border=True,
              help="Promedio de productividad real menos meta; cada registro tiene el mismo peso.")
    c2.metric("Equipos con brecha media negativa", f"{int(equipos['brecha'].lt(0).sum())} de {len(equipos)}",
              border=True, help="Cada combinación de departamento y número de equipo se cuenta por separado.")
    c3.metric("Registros con algún atípico", f"{int(con_atipicos.sum())} de {len(df)}", border=True,
              help="Un registro se cuenta una sola vez aunque tenga varias señales: WIP, tiempo extra o incentivo.")

    st.subheader("¿En qué semanas se abre la brecha?")
    st.altair_chart(estilo(_tendencia(semanal)), width="stretch", theme=None)
    st.caption(
        "Semanas de lunes a domingo; cero significa que la productividad media igualó la meta media. "
        "Se promedian solo los registros seleccionados: los extremos del periodo pueden ser semanas parciales. "
        "Las líneas unen semanas observadas; las ausencias no se rellenan con ceros."
    )
    st.subheader("¿Qué equipos se alejan más de su meta?")
    st.altair_chart(estilo(_ranking(equipos)), width="stretch", theme=None)
    st.caption(
        "Orden de menor a mayor brecha media, separando departamento y equipo. "
        "Una media positiva no implica que todos sus registros cumplan. "
        "Consulta el número de registros y el cumplimiento al pasar el cursor."
    )
    pequenos = int(equipos["registros"].lt(MINIMO_REPRESENTATIVO).sum())
    if pequenos:
        st.caption(f"{pequenos} de {len(equipos)} equipos tienen menos de {MINIMO_REPRESENTATIVO} registros en esta selección; su posición requiere cautela.")

    por_equipo = resumen_semanal(df, por_equipo=True)
    dominio = [0, max(1.0, float(por_equipo[["productividad", "meta"]].max().max())) * 1.05]
    for departamento in DEPARTAMENTOS:
        if departamento in df["departamento"].values:
            with st.expander(f"Ver evolución de los equipos de {departamento}", icon=":material/monitoring:"):
                st.altair_chart(estilo(_equipos(por_equipo, departamento, dominio)), width="stretch", theme=None)
                st.caption("Promedios semanales. Todos los paneles usan la misma escala vertical; la meta es gris y punteada. Usa los filtros globales para inspeccionar un equipo.")

    st.subheader("¿Cuándo se concentran los valores atípicos?")
    anomalias = anomalias_diarias(df)
    if con_atipicos.any():
        pico = anomalias.loc[anomalias["atipicos"].idxmax()]
        st.markdown(f"La mayor concentración diaria es de **{pico['variable']}**, el **{pico['fecha_txt']}**: **{int(pico['atipicos'])}** registros atípicos.")
        st.altair_chart(estilo(_anomalias(anomalias)), width="stretch", theme=None)
    else:
        st.info("No hay valores atípicos marcados de WIP, tiempo extra o incentivo en esta selección.")
    st.caption(
        "Se conservan las marcas calculadas con el conjunto completo: valores fuera de "
        "[Q1 − 1.5 × IQR, Q3 + 1.5 × IQR]. Filtrar no recalcula los límites. "
        "Un valor atípico requiere inspección, pero no demuestra un error ni una causa de incumplimiento."
    )
    sin_wip = int(df["wip"].isna().sum())
    if sin_wip:
        st.caption(f"WIP no está registrado en {sin_wip} de {len(df)} registros seleccionados; estos no se clasifican como normales ni como atípicos de WIP.")

    with st.expander("Inspeccionar los registros seleccionados", icon=":material/table:"):
        st.dataframe(_detalle(df), hide_index=True, width="stretch", column_config={
            "fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
            "departamento": "Departamento", "equipo": "Equipo",
            "productividad": st.column_config.NumberColumn("Productividad real", format="%.3f"),
            "meta": st.column_config.NumberColumn("Meta", format="%.3f"),
            "brecha": st.column_config.NumberColumn("Brecha", format="%+.3f"),
            "cumple_meta": "Cumple su meta", "wip": "WIP (unidades)",
            "tiempo_extra_min": "Tiempo extra del equipo (min)",
            "incentivo_bdt": "Incentivo (BDT)", "señales": "Señales atípicas",
        })
    st.page_link("vistas/causa_raiz.py", label="Siguiente: causa raíz", icon=":material/arrow_forward:")


if __name__ == "__main__":
    mostrar(st.session_state["seleccion"])
