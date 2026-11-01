"""
Paso 4 de 4 - Recomendación de acción.  >>> PARTE 3 <<<

Pregunta: ¿qué debería hacer la planta con esta información?

Datos disponibles:
    df = st.session_state["seleccion"]

Contenido sugerido:
1. 3 o 4 recomendaciones, cada una con la cifra que la respalda (calculada
   con df, para que cambie con los filtros) y un st.page_link a la vista
   donde está la evidencia.
2. Ejemplos: priorizar los equipos con mayor brecha negativa; revisar la
   planificación de cambios de estilo; validar con la planta wip en Acabado,
   productividad > 1 y personal fraccionario antes de entrenar un modelo.
3. Cerrar con las limitaciones (datos descriptivos, 1,197 registros).
"""

import streamlit as st

from componentes import en_construccion

df = st.session_state["seleccion"]

st.caption("PASO 4 DE 4 · RECOMENDACIÓN")
st.title("¿Qué debería hacer la planta?")

en_construccion("Parte 3", [
    "Recomendaciones respaldadas por cifras de la selección",
    "Enlaces a la evidencia en las vistas anteriores",
    "Limitaciones de los datos",
])

st.page_link("vistas/diagnostico.py", label="Volver al diagnóstico",
             icon=":material/restart_alt:")
