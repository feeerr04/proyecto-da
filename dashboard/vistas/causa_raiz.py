"""
Paso 3 de 4 - Análisis de causa raíz.  >>> PARTE 2 <<<

Pregunta: ¿qué condiciones acompañan a los registros que no cumplen su meta?

Datos disponibles:
    df = st.session_state["seleccion"]

Vistas sugeridas:
1. Cumple vs. no cumple: comparar promedios de tiempo_extra_min, incentivo_bdt,
   cambios_estilo, tiempo_inactivo y personal_asignado (barras agrupadas o
   tabla con barras de datos).
2. Cumplimiento según hubo_cambio_estilo y hubo_inactividad (barras con %).
   En la Fase I, cambios de estilo fue la asociación negativa más marcada
   (r = -0.207; Spearman -0.266).
3. Dispersión productividad vs. incentivo o tiempo extra, color por
   departamento (2 colores como máximo), con tooltip por punto.

Importante: el artículo es descriptivo. Hablar de "condiciones asociadas",
nunca de causas demostradas.
"""

import streamlit as st

from componentes import en_construccion

df = st.session_state["seleccion"]

st.caption("PASO 3 DE 4 · CAUSA RAÍZ")
st.title("¿Qué condiciones acompañan a los incumplimientos?")

en_construccion("Parte 2", [
    "Cumple vs. no cumple: condiciones operativas promedio",
    "Cumplimiento con y sin cambios de estilo o inactividad",
    "Relación entre productividad, incentivo y tiempo extra",
])

st.page_link("vistas/recomendacion.py", label="Siguiente: recomendación",
             icon=":material/arrow_forward:")
