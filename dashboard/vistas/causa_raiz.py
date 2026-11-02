"""Paso 3: condiciones asociadas al incumplimiento; no inferencia causal."""

import altair as alt
import pandas as pd
import streamlit as st

from componentes import (
    COLORES, DEPARTAMENTOS, ESCALA_DEPARTAMENTO,
    estilo, fecha_es, fmt_pct, fmt_signo,
)
from datos import MINIMO_REPRESENTATIVO

CONDICIONES = {
    "hubo_cambio_estilo": ("cambios de estilo", "Sin cambios", "Con cambios"),
    "hubo_inactividad": ("inactividad", "Sin inactividad", "Con inactividad"),
}
VARIABLES = {
    "tiempo_extra_min": "Tiempo extra del equipo (min)",
    "incentivo_bdt": "Incentivo (BDT)",
    "cambios_estilo": "Cambios de estilo",
    "tiempo_inactivo": "Tiempo inactivo (unidad original)",
    "personal_asignado": "Personal asignado",
}


def promedios_por_cumplimiento(df: pd.DataFrame) -> pd.DataFrame:
    """Mantiene separados departamentos y estados, con denominadores visibles."""
    tabla = df.groupby(["departamento", "cumple_meta"]).agg(
        registros=("cumple_meta", "size"),
        **{variable: (variable, "mean") for variable in VARIABLES},
    ).reset_index()
    tabla["resultado"] = tabla["cumple_meta"].map({True: "Cumple", False: "No cumple"})
    return tabla[["departamento", "resultado", "registros", *VARIABLES]]


def resumen_condicion(df: pd.DataFrame, condicion: str) -> pd.DataFrame:
    _, sin, con = CONDICIONES[condicion]
    tabla = df.groupby(["departamento", condicion]).agg(
        registros=("cumple_meta", "size"), cumplen=("cumple_meta", "sum"),
        cumplimiento=("cumple_meta", "mean"),
    ).reset_index()
    tabla["grupo"] = tabla[condicion].map({False: sin, True: con})
    tabla["etiqueta"] = tabla.apply(
        lambda f: f"{f['cumplimiento']:.1%} · {int(f['cumplen'])}/{int(f['registros'])}", axis=1
    )
    return tabla


def contrastes(df: pd.DataFrame) -> list[dict]:
    """Diferencias descriptivas solo donde existen ambos grupos del departamento."""
    resultados = []
    for condicion, (nombre, _, _) in CONDICIONES.items():
        tabla = resumen_condicion(df, condicion)
        for departamento, grupos in tabla.groupby("departamento"):
            grupos = grupos.set_index(condicion)
            if True in grupos.index and False in grupos.index:
                con, sin = grupos.loc[True], grupos.loc[False]
                resultados.append({
                    "departamento": departamento, "condicion": nombre,
                    "con": float(con["cumplimiento"]), "sin": float(sin["cumplimiento"]),
                    "n_con": int(con["registros"]), "n_sin": int(sin["registros"]),
                    "diferencia": float(con["cumplimiento"] - sin["cumplimiento"]),
                })
    return sorted(resultados, key=lambda r: abs(r["diferencia"]), reverse=True)


def _titular(df: pd.DataFrame, diferencias: list[dict]) -> str:
    texto = f"En la selección, **{int((~df['cumple_meta']).sum())} de {len(df)} registros** no alcanzaron su meta. "
    if diferencias:
        mayor = diferencias[0]
        texto += (
            f"La mayor diferencia descriptiva entre los grupos comparados aparece en "
            f"**{mayor['departamento']}**, con y sin **{mayor['condicion']}**: "
            f"**{fmt_pct(mayor['con'])}** de cumplimiento (n={mayor['n_con']}) frente a "
            f"**{fmt_pct(mayor['sin'])}** (n={mayor['n_sin']}); "
            f"diferencia de **{mayor['diferencia'] * 100:+.1f} puntos porcentuales**."
        )
    else:
        texto += "No hay grupos con y sin cambios de estilo o inactividad dentro de un mismo departamento para estimar esas diferencias."
    return texto


def _barras_condicion(tabla: pd.DataFrame, condicion: str) -> alt.Chart:
    _, sin, con = CONDICIONES[condicion]
    base = alt.Chart(tabla).encode(
        y=alt.Y("grupo:N", title=None, sort=[sin, con]),
        x=alt.X("cumplimiento:Q", title="Registros que cumplen su meta",
                scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format="%", tickCount=5)),
        tooltip=[
            alt.Tooltip("departamento:N", title="Departamento"),
            alt.Tooltip("grupo:N", title="Condición"),
            alt.Tooltip("cumplimiento:Q", title="Cumplimiento", format=".1%"),
            alt.Tooltip("cumplen:Q", title="Registros que cumplen"),
            alt.Tooltip("registros:Q", title="Registros del grupo"),
        ],
    )
    barras = base.mark_bar(height=24).encode(
        color=alt.Color("departamento:N", scale=ESCALA_DEPARTAMENTO, legend=None)
    )
    # Referencia al extremo de la escala para evitar texto cortado al llegar al 100%.
    etiquetas = base.mark_text(align="right", dx=-3, dy=-20, fontSize=12, color=COLORES["texto"]).encode(
        x=alt.datum(1), text="etiqueta:N"
    )
    return (barras + etiquetas).properties(width=300, height=140).facet(
        row=alt.Row("departamento:N", title=None, sort=DEPARTAMENTOS,
                    header=alt.Header(labelAngle=0)),
    ).resolve_scale(y="independent")


def _dispersion(df: pd.DataFrame, variable: str) -> alt.Chart:
    datos = df.assign(fecha_txt=df["fecha"].map(fecha_es),
                      resultado=df["cumple_meta"].map({True: "Cumple", False: "No cumple"}))
    return alt.Chart(datos).mark_circle(size=45, opacity=0.45).encode(
        x=alt.X(f"{variable}:Q", title=VARIABLES[variable], scale=alt.Scale(zero=True),
                axis=alt.Axis(tickCount=5, format=",.0f")),
        y=alt.Y("productividad:Q", title="Productividad real", scale=alt.Scale(zero=True)),
        color=alt.Color("departamento:N", title=None, scale=ESCALA_DEPARTAMENTO),
        tooltip=[
            alt.Tooltip("fecha_txt:N", title="Fecha"),
            alt.Tooltip("departamento:N", title="Departamento"),
            alt.Tooltip("equipo:O", title="Equipo"),
            alt.Tooltip(f"{variable}:Q", title=VARIABLES[variable], format=",.1f"),
            alt.Tooltip("productividad:Q", title="Productividad real", format=".3f"),
            alt.Tooltip("meta:Q", title="Meta", format=".3f"),
            alt.Tooltip("brecha:Q", title="Brecha", format="+.3f"),
            alt.Tooltip("resultado:N", title="Resultado"),
        ],
    ).properties(height=300)


def mostrar(df: pd.DataFrame) -> None:
    st.caption("PASO 3 DE 4 · CAUSA RAÍZ")
    st.title("¿Qué condiciones acompañan a los incumplimientos?")
    if df.empty:
        st.info("No hay registros para los filtros seleccionados.")
        return

    diferencias = contrastes(df)
    st.markdown(_titular(df, diferencias))
    st.caption(
        "Exploración de condiciones asociadas: las diferencias no prueban causas ni controlan "
        "simultáneamente metas, fechas, tamaño de equipo u otras condiciones."
    )
    if len(df) < MINIMO_REPRESENTATIVO:
        st.warning(f"Solo {len(df)} registros seleccionados. Las diferencias pueden ser inestables.")

    incumplen = df.loc[~df["cumple_meta"]]
    c1, c2, c3 = st.columns(3)
    c1.metric("Registros analizados", f"{len(df):,}", border=True)
    c2.metric("No cumplen su meta", fmt_pct(1 - df["cumple_meta"].mean()), border=True,
              help="Registros con productividad real menor que su propia meta, sobre todos los seleccionados.")
    c3.metric("Brecha media al incumplir", fmt_signo(incumplen["brecha"].mean()) if len(incumplen) else "No aplica",
              border=True, help="Promedio de real menos meta únicamente entre los registros que no cumplen.")

    st.subheader("¿Qué condiciones cambian entre cumplimiento e incumplimiento?")
    st.dataframe(promedios_por_cumplimiento(df), hide_index=True, width="stretch", column_config={
        "departamento": "Departamento", "resultado": "Resultado", "registros": "Registros (n)",
        **{variable: st.column_config.NumberColumn(nombre, format="%.2f")
           for variable, nombre in VARIABLES.items()},
    })
    st.caption(
        "Cada fila resume registros del mismo departamento y estado. Las unidades se conservan por columna. "
        "El tiempo extra corresponde al equipo completo; no equivale a minutos por trabajador. "
        "El tiempo inactivo conserva la unidad del dato original, sin conversión."
    )
    for departamento, datos in df.groupby("departamento"):
        if datos["cumple_meta"].nunique() == 1:
            resultado = "cumplen" if datos["cumple_meta"].iloc[0] else "incumplen"
            st.info(f"En {departamento}, todos los registros seleccionados {resultado}: no hay otro grupo para contrastar esos promedios.")

    st.subheader("¿Cambia el cumplimiento con los cambios de estilo o la inactividad?")
    columnas = st.columns(2)
    for columna, (condicion, (nombre, _, _)) in zip(columnas, CONDICIONES.items()):
        with columna:
            st.markdown(f"**{nombre.capitalize()}**")
            tabla = resumen_condicion(df, condicion)
            st.altair_chart(estilo(_barras_condicion(tabla, condicion)), width="stretch", theme=None)
            for departamento, grupos in tabla.groupby("departamento"):
                if len(grupos) < 2:
                    presencia = "con" if grupos[condicion].iloc[0] else "sin"
                    st.caption(f"{departamento}: solo hay registros {presencia} {nombre}; no se puede comparar presencia frente a ausencia.")
            pequenos = tabla.loc[tabla["registros"].lt(MINIMO_REPRESENTATIVO)]
            if not pequenos.empty:
                grupos_txt = "; ".join(
                    f"{f.departamento}, {f.grupo.lower()}: n={f.registros}"
                    for f in pequenos.itertuples()
                )
                st.caption(f"Grupos pequeños (menos de {MINIMO_REPRESENTATIVO} registros): {grupos_txt}. Interpreta sus porcentajes con cautela.")
    st.caption("Las etiquetas muestran porcentaje y registros que cumplen / total del grupo. Los grupos ausentes no se presentan como 0%.")

    st.subheader("¿Cómo se relacionan incentivo y tiempo extra con la productividad?")
    izquierda, derecha = st.columns(2)
    for columna, variable in [(izquierda, "incentivo_bdt"), (derecha, "tiempo_extra_min")]:
        with columna:
            st.altair_chart(estilo(_dispersion(df, variable)), width="stretch", theme=None)
            if df[variable].nunique() < 2:
                st.caption(f"{VARIABLES[variable]} no varía en esta selección; no permite explorar una asociación.")
    st.caption(
        "Cada punto representa un registro; la transparencia ayuda a ver superposiciones. "
        "Los ejes incluyen los valores extremos conservados. Consulta fecha, equipo, meta y brecha "
        "al pasar el cursor y usa los filtros globales para inspeccionar un departamento o equipo. "
        "La dispersión no permite concluir que aumentar incentivos o tiempo extra mejore la productividad."
    )

    with st.expander("Ver las diferencias entre grupos comparables", icon=":material/table:"):
        if diferencias:
            tabla = pd.DataFrame(diferencias)
            tabla["diferencia"] *= 100
            st.dataframe(tabla, hide_index=True, width="stretch", column_config={
                "departamento": "Departamento", "condicion": "Condición",
                "con": st.column_config.NumberColumn("Cumplimiento con", format="percent"),
                "sin": st.column_config.NumberColumn("Cumplimiento sin", format="percent"),
                "n_con": "Registros con", "n_sin": "Registros sin",
                "diferencia": st.column_config.NumberColumn("Diferencia (con − sin, pp)", format="%+.1f"),
            })
            st.caption("Diferencias descriptivas de cumplimiento, no efectos causales ni pruebas de significancia estadística.")
        else:
            st.info("No existen ambos grupos en un mismo departamento con los filtros actuales.")

    with st.expander("Inspeccionar las condiciones de cada registro", icon=":material/table:"):
        detalle = df.sort_values(["fecha", "departamento", "equipo"])[[
            "fecha", "departamento", "equipo", "cumple_meta", "productividad", "meta", "brecha", *VARIABLES,
        ]]
        st.dataframe(detalle, hide_index=True, width="stretch", column_config={
            "fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
            "departamento": "Departamento", "equipo": "Equipo", "cumple_meta": "Cumple su meta",
            "productividad": st.column_config.NumberColumn("Productividad real", format="%.3f"),
            "meta": st.column_config.NumberColumn("Meta", format="%.3f"),
            "brecha": st.column_config.NumberColumn("Brecha", format="%+.3f"),
            **{v: st.column_config.NumberColumn(n, format="%.2f") for v, n in VARIABLES.items()},
        })
    st.page_link("vistas/recomendacion.py", label="Siguiente: recomendación", icon=":material/arrow_forward:")


if __name__ == "__main__":
    mostrar(st.session_state["seleccion"])
