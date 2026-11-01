"""
Paso 2 de 4 - Detección de patrones y anomalías.  >>> PARTE 2 <<<

Pregunta: ¿dónde y cuándo se aleja la productividad de la meta?

Datos disponibles (ver columnas en data/garments_dashboard.csv):
    df = st.session_state["seleccion"]   # ya filtrado por la barra lateral
    planta = st.session_state["planta"]  # 1,197 registros, sin filtrar

Vistas sugeridas (usar COLORES / ESCALA_DEPARTAMENTO / estilo() de componentes.py):
1. Tendencia semanal por departamento: líneas, color por departamento.
2. Pequeños múltiples por equipo (12 paneles, misma escala): productividad
   real vs. meta por semana. alt.Chart(...).facet(facet="equipo:O", columns=4)
3. Ranking de equipos por brecha promedio: barras horizontales desde 0,
   azul por encima de la meta y rojo por debajo (paleta divergente), con la
   cifra escrita en cada barra.
4. Atípicos en el tiempo: usar atipico_wip / atipico_tiempo_extra /
   atipico_incentivo. En la Fase I, 10 de 22 atípicos de wip cayeron el
   2 feb 2015 y 10 de 11 de incentivo el 9 mar 2015.
5. Detalle a demanda: tooltips en cada marca y una tabla del equipo elegido.

Pista para la narrativa: Acabado tiene mayor productividad promedio (0.753)
pero cumple su meta en menos registros (60% vs. 83% de Costura): su
productividad es más dispersa. Vale la pena mostrarlo aquí.
"""

import streamlit as st

from componentes import en_construccion

df = st.session_state["seleccion"]

st.caption("PASO 2 DE 4 · PATRONES Y ANOMALÍAS")
st.title("¿Dónde y cuándo se aleja la productividad de la meta?")

en_construccion("Parte 2", [
    "Tendencia semanal por departamento",
    "Pequeños múltiples por equipo",
    "Ranking de equipos por brecha frente a la meta",
    "Atípicos en el tiempo",
])

st.page_link("vistas/causa_raiz.py", label="Siguiente: causa raíz",
             icon=":material/arrow_forward:")
