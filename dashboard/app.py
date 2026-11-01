"""
Dashboard - Fase II del proyecto de Data Analysis.
Productividad en equipos de confección (UCI, 1,197 registros).

Ejecutar desde la raíz del repositorio:
    py -m streamlit run dashboard/app.py

El flujo de páginas sigue la narrativa pedida en la guía:
Diagnóstico inicial -> Patrones y anomalías -> Causa raíz -> Recomendación.
"""

import streamlit as st

from datos import aplicar_filtros, cargar_datos, filtros_globales

st.set_page_config(
    page_title="Productividad en confección",
    page_icon=":material/factory:",
    layout="wide",
)

paginas = [
    st.Page("vistas/diagnostico.py", title="1 · Diagnóstico inicial",
            icon=":material/monitoring:", default=True),
    st.Page("vistas/patrones.py", title="2 · Patrones y anomalías",
            icon=":material/insights:"),
    st.Page("vistas/causa_raiz.py", title="3 · Causa raíz",
            icon=":material/troubleshoot:"),
    st.Page("vistas/recomendacion.py", title="4 · Recomendación",
            icon=":material/task_alt:"),
]
navegacion = st.navigation({"Flujo de análisis": paginas})

# Filtros globales: se dibujan aquí una vez y alimentan a todas las páginas
planta = cargar_datos()
filtros = filtros_globales(planta)
seleccion = aplicar_filtros(planta, filtros)

st.session_state["planta"] = planta
st.session_state["seleccion"] = seleccion

with st.sidebar:
    st.caption(
        f"**{len(seleccion):,}** de {len(planta):,} registros seleccionados  \n"
        "Fuente: UCI Machine Learning Repository, limpiado en la Fase I."
    )

if not filtros["departamentos"]:
    st.warning("Selecciona al menos un departamento en los filtros.", icon=":material/filter_alt:")
    st.stop()
if seleccion.empty:
    st.warning(
        "Ningún registro coincide con los filtros. Amplía el periodo o los equipos, "
        "o usa «Restablecer filtros».",
        icon=":material/filter_alt_off:",
    )
    st.stop()

navegacion.run()
