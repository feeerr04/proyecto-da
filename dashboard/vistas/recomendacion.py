"""
Paso 4 de 4 - Recomendación de acción.

Pregunta: ¿qué debería hacer la planta con esta información?

Cada recomendación se calcula con la selección actual (cambia con los
filtros) y cita la cifra que la respalda. El análisis es descriptivo: no se
proyectan efectos causales, porque los datos no los sostienen (por ejemplo,
la correlación entre tiempo extra y productividad es r = -0.054).
"""

import altair as alt
import pandas as pd
import streamlit as st

from componentes import COLORES, ESCALA_DEPARTAMENTO, estilo, fecha_es, fmt_pct, fmt_signo
from datos import MINIMO_REPRESENTATIVO

# Mínimo de registros para que un equipo entre a la priorización
MINIMO_EQUIPO = 20


def _resumen_equipos(df: pd.DataFrame) -> pd.DataFrame:
    tabla = (
        df.groupby(["departamento", "equipo"])
        .agg(
            registros=("productividad", "size"),
            productividad=("productividad", "mean"),
            meta=("meta", "mean"),
            brecha=("brecha", "mean"),
            cumplimiento=("cumple_meta", "mean"),
            tiempo_extra_min=("tiempo_extra_min", "mean"),
        )
        .reset_index()
    )
    tabla["nombre"] = tabla["departamento"] + " · equipo " + tabla["equipo"].astype(str)
    return tabla


def _cumplimiento_por_grupo(df: pd.DataFrame, columna: str) -> pd.Series | None:
    """Cumplimiento con/sin una condición, solo si ambos grupos existen."""
    grupos = df.groupby(columna)["cumple_meta"].agg(["mean", "size"])
    if len(grupos) < 2:
        return None
    return grupos


def _tarjeta(numero: int, titulo: str, evidencia: str, accion: str, enlace: str | None) -> None:
    with st.container(border=True):
        st.markdown(f"**{numero}. {titulo}**")
        st.markdown(evidencia)
        st.markdown(f"*Acción:* {accion}")
        if enlace:
            st.page_link(enlace, label="Ver la evidencia", icon=":material/arrow_outward:")


def _matriz(equipos: pd.DataFrame, cumplimiento_planta: float) -> alt.Chart:
    base = alt.Chart(equipos)
    puntos = base.mark_circle(size=140, opacity=0.9, stroke=COLORES["superficie"], strokeWidth=2).encode(
        x=alt.X("cumplimiento:Q", title="Registros que cumplen su meta",
                scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format="%")),
        y=alt.Y("brecha:Q", title="Brecha media (real − meta)"),
        color=alt.Color("departamento:N", scale=ESCALA_DEPARTAMENTO, title=None),
        tooltip=[
            alt.Tooltip("nombre:N", title="Equipo"),
            alt.Tooltip("cumplimiento:Q", title="Cumplimiento", format=".1%"),
            alt.Tooltip("brecha:Q", title="Brecha media", format="+.3f"),
            alt.Tooltip("productividad:Q", title="Productividad real", format=".3f"),
            alt.Tooltip("registros:Q", title="Registros"),
        ],
    )
    cero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(
        color=COLORES["meta"], strokeDash=[6, 4]).encode(y="y:Q")
    referencia = alt.Chart(pd.DataFrame({"x": [cumplimiento_planta]})).mark_rule(
        color=COLORES["meta"], strokeDash=[6, 4]).encode(x="x:Q")
    etiqueta = alt.Chart(pd.DataFrame({"x": [0.02], "y": [equipos["brecha"].min()],
                                       "t": ["Prioridad: abajo a la izquierda"]})).mark_text(
        align="left", baseline="bottom", fontSize=12, color=COLORES["texto_secundario"],
    ).encode(x="x:Q", y="y:Q", text="t:N")
    return (cero + referencia + puntos + etiqueta).properties(height=380)


st.caption("PASO 4 DE 4 · RECOMENDACIÓN")
st.title("¿Qué debería hacer la planta?")

df = st.session_state["seleccion"]
equipos = _resumen_equipos(df)
evaluables = equipos[equipos["registros"] >= MINIMO_EQUIPO]
cumplimiento_planta = df["cumple_meta"].mean()

st.markdown(
    "Las recomendaciones se calculan con la selección actual y cada una cita la cifra que la "
    "respalda. Son descriptivas: señalan **dónde mirar primero**, no cuánto mejoraría la "
    "productividad al cambiar una variable."
)
if len(df) < MINIMO_REPRESENTATIVO:
    st.warning(f"La selección tiene solo {len(df)} registros: amplía los filtros para recomendar con respaldo.",
               icon=":material/info:")

recomendaciones = []

# 1. Equipos prioritarios
if not evaluables.empty:
    criticos = evaluables[evaluables["brecha"] < 0].nsmallest(3, "brecha")
    if not criticos.empty:
        lista = "; ".join(
            f"**{f.nombre}** (brecha {fmt_signo(f.brecha)}, cumple {fmt_pct(f.cumplimiento)})"
            for f in criticos.itertuples()
        )
        recomendaciones.append((
            "Priorizar a los equipos con mayor brecha negativa",
            f"Los equipos más alejados de su meta son: {lista}.",
            "revisar con sus supervisores las condiciones de esos equipos antes de aplicar "
            "medidas generales a toda la planta.",
            "vistas/patrones.py",
        ))

# 2. Inactividad
inactividad = _cumplimiento_por_grupo(df, "hubo_inactividad")
if inactividad is not None:
    con, sin = inactividad.loc[True], inactividad.loc[False]
    recomendaciones.append((
        "Registrar y atender las causas de inactividad",
        f"Con tiempo inactivo cumple su meta el **{fmt_pct(con['mean'])}** de los registros "
        f"(n = {int(con['size'])}), frente al **{fmt_pct(sin['mean'])}** sin inactividad "
        f"(n = {int(sin['size'])}).",
        "documentar el motivo de cada interrupción para distinguir fallas de máquina, "
        "falta de material o cambios de orden. El grupo con inactividad es pequeño, así que "
        "la diferencia debe confirmarse con más datos.",
        "vistas/causa_raiz.py",
    ))

# 3. Semana más débil
semanal = (
    df.assign(semana=df["fecha"].dt.to_period("W-SUN").dt.start_time)
    .groupby("semana")
    .agg(cumplimiento=("cumple_meta", "mean"), registros=("cumple_meta", "size"))
)
semanal = semanal[semanal["registros"] >= MINIMO_REPRESENTATIVO]
if len(semanal) >= 2:
    peor = semanal["cumplimiento"].idxmin()
    recomendaciones.append((
        "Revisar qué ocurrió en la semana más débil",
        f"La semana que inicia el **{fecha_es(peor)}** tuvo el cumplimiento más bajo: "
        f"**{fmt_pct(semanal.loc[peor, 'cumplimiento'])}** "
        f"({int(semanal.loc[peor, 'registros'])} registros), frente al "
        f"{fmt_pct(cumplimiento_planta)} de toda la selección.",
        "contrastar esas fechas con la programación de pedidos y cambios de estilo de la planta.",
        "vistas/patrones.py",
    ))

# 4. Calidad de datos antes de modelar
recomendaciones.append((
    "Validar los datos antes de entrenar un modelo",
    f"La selección incluye **{int(df['wip_faltante'].sum())}** registros sin wip, "
    f"**{int(df['productividad_mayor_1'].sum())}** con productividad mayor que 1 y "
    f"**{int(df['personal_fraccionario'].sum())}** con personal fraccionario.",
    "confirmar con la planta el significado de esos casos y separar entrenamiento y "
    "validación por fechas antes de imputar o escalar.",
    "vistas/diagnostico.py",
))

st.subheader("Recomendaciones")
columnas = st.columns(2)
for i, (titulo, evidencia, accion, enlace) in enumerate(recomendaciones):
    with columnas[i % 2]:
        _tarjeta(i + 1, titulo, evidencia, accion, enlace)

st.subheader("Matriz de priorización de equipos")
if evaluables.empty:
    st.info(f"Ningún equipo tiene al menos {MINIMO_EQUIPO} registros en la selección.",
            icon=":material/info:")
else:
    st.altair_chart(estilo(_matriz(evaluables, cumplimiento_planta)), width="stretch", theme=None)
    st.caption(
        f"Cada punto es un equipo con al menos {MINIMO_EQUIPO} registros. Línea horizontal: brecha 0 "
        f"(productividad igual a la meta). Línea vertical: cumplimiento de la selección "
        f"({fmt_pct(cumplimiento_planta)}). Los equipos abajo a la izquierda son la prioridad."
    )

    plan = evaluables.sort_values("brecha")[
        ["departamento", "equipo", "registros", "productividad", "meta", "brecha", "cumplimiento"]
    ]
    with st.expander("Ver la tabla de priorización", icon=":material/table:"):
        st.dataframe(
            plan, hide_index=True, width="stretch",
            column_config={
                "departamento": "Departamento",
                "equipo": st.column_config.NumberColumn("Equipo"),
                "registros": st.column_config.NumberColumn("Registros"),
                "productividad": st.column_config.NumberColumn("Productividad real", format="%.3f"),
                "meta": st.column_config.NumberColumn("Meta", format="%.3f"),
                "brecha": st.column_config.NumberColumn("Brecha", format="%+.3f"),
                "cumplimiento": st.column_config.NumberColumn("Cumplimiento", format="percent"),
            },
        )
    st.download_button(
        "Descargar plan de priorización (CSV)",
        data=plan.round(4).to_csv(index=False).encode("utf-8-sig"),
        file_name="plan_priorizacion_equipos.csv",
        mime="text/csv",
        icon=":material/download:",
    )

with st.expander("Limitaciones", icon=":material/info:"):
    st.markdown(
        "- El análisis es descriptivo: las diferencias no prueban causas ni controlan metas, "
        "fechas o tamaño de equipo al mismo tiempo.\n"
        "- No se incluye un simulador de escenarios: la correlación entre tiempo extra y "
        "productividad es casi nula (r = −0.054), así que cualquier \"productividad proyectada\" "
        "sería una suposición, no un resultado de los datos.\n"
        "- Son 1,197 registros de enero a marzo de 2015; algunos cruces de equipo y fecha "
        "quedan con pocos datos."
    )

st.page_link("vistas/diagnostico.py", label="Volver al diagnóstico", icon=":material/restart_alt:")
