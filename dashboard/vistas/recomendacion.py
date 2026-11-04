import streamlit as st
import pandas as pd
import altair as alt
from componentes import estilo

df = st.session_state["seleccion"]

st.caption("PASO 4 DE 4 · RECOMENDACIÓN")
st.title("¿Qué debería hacer la planta?")
st.markdown("Basado en los cuellos de botella detectados, ajusta las variables operativas para proyectar escenarios de mejora en la productividad.")

st.subheader("Simulador de Escenarios (What-If)")
col1, col2 = st.columns(2)

with col1:
    st.markdown("**Variables de Control Operativo**")
    ajuste_horas = st.slider("Reducción de Horas Extras (%)", min_value=0, max_value=50, value=15, step=5)
    reasignacion = st.slider("Reasignación de Operarios", min_value=0, max_value=10, value=2, step=1)

# Buscador ampliado de columnas
col_equipo = next((c for c in df.columns if 'equip' in c.lower() or 'team' in c.lower()), None)
col_tiempo = next((c for c in df.columns if 'extra' in c.lower() or 'over' in c.lower() or 'hora' in c.lower()), None)
col_prod = next((c for c in df.columns if 'real' in c.lower() or 'actual' in c.lower() or 'productividad' in c.lower()), None)

with col2:
    st.markdown("**Proyección de Impacto Global**")
    mejora_estimada = (ajuste_horas * 0.002) + (reasignacion * 0.005)
    productividad_base = df[col_prod].mean() if col_prod else 0.735
    
    st.metric(
        label="Nueva Productividad Proyectada", 
        value=f"{productividad_base + mejora_estimada:.3f}", 
        delta=f"+{mejora_estimada:.3f} de incremento estimado"
    )

st.divider()

st.subheader("Directrices de Acción Inmediata")
t1, t2, t3 = st.columns(3)

with t1:
    st.info("**Líneas de Costura Críticas**\n\nCongelar sobretiempos los sábados para mitigar fatiga. Retorno estimado: +2% productividad.")
with t2:
    st.warning("**Ajuste de Metas en Acabado**\n\nReducir la meta diaria en un 5% para equipos con alta varianza para estabilizar entregas.")
with t3:
    st.success("**Retención e Incentivos**\n\nAplicar bono dinámico al Equipo 8, el cual sostiene la mayor eficiencia sin horas extras.")

st.divider()

st.subheader("Matriz de Priorización de Intervención")

if col_equipo and col_tiempo and col_prod:
    df_resumen = df.groupby(col_equipo).agg({col_prod: 'mean', col_tiempo: 'mean'}).reset_index()
    
    grafico = alt.Chart(df_resumen).mark_circle(size=100).encode(
        x=alt.X(f'{col_tiempo}:Q', title='Horas Extras Promedio'),
        y=alt.Y(f'{col_prod}:Q', title='Productividad Real', scale=alt.Scale(zero=False)),
        tooltip=[col_equipo, col_tiempo, col_prod]
    ).properties(
        title='Equipos críticos: Productividad vs Horas Extras'
    )
    
    st.altair_chart(estilo(grafico), use_container_width=True, theme=None)

    st.download_button(
        label="Descargar Plan de Intervención (CSV)",
        data=df_resumen.to_csv(index=False),
        file_name="recomendaciones_confeccion.csv",
        mime="text/csv"
    )
else:
    st.error(f"No se detectaron las columnas. Nombres reales en la base de datos: {list(df.columns)}")

st.page_link("vistas/diagnostico.py", label="Volver al diagnóstico", icon=":material/restart_alt:")