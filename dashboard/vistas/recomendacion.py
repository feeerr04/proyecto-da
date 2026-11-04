import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Recuperación del contexto de datos filtrados desde el estado global de la sesión
df = st.session_state["seleccion"]

# 2. Renderizado de encabezados y contexto de la vista
st.caption("PASO 4 DE 4 · RECOMENDACIÓN")
st.title("¿Qué debería hacer la planta?")
st.markdown("Basado en los cuellos de botella detectados, ajusta las variables operativas para proyectar escenarios de mejora en la productividad.")

# 3. Simulación What-If (Implementación de heurística de Shneiderman: interactividad)
st.subheader("Simulador de Escenarios (What-If)")
col1, col2 = st.columns(2)

with col1:
    st.markdown("**Variables de Control Operativo**")
    ajuste_horas = st.slider("Reducción de Horas Extras (%)", min_value=0, max_value=50, value=15, step=5)
    reasignacion = st.slider("Reasignación de Operarios", min_value=0, max_value=10, value=2, step=1)

with col2:
    st.markdown("**Proyección de Impacto Global**")
    
    # Modelo lineal de estimación de impacto sobre la productividad base
    mejora_estimada = (ajuste_horas * 0.002) + (reasignacion * 0.005)
    productividad_base = df['actual_productivity'].mean() if 'actual_productivity' in df.columns else 0.735
    
    st.metric(
        label="Nueva Productividad Proyectada", 
        value=f"{productividad_base + mejora_estimada:.3f}", 
        delta=f"+{mejora_estimada:.3f} de incremento estimado"
    )

st.divider()

# 4. Tarjetas de Acción Directa (Patrón "Overview first" para reducción de carga cognitiva)
st.subheader("Directrices de Acción Inmediata")
t1, t2, t3 = st.columns(3)

with t1:
    st.info("**Líneas de Costura Críticas**\n\nCongelar sobretiempos los sábados para mitigar fatiga. Retorno estimado: +2% productividad.")
with t2:
    st.warning("**Ajuste de Metas en Acabado**\n\nReducir la meta diaria en un 5% para equipos con alta varianza para estabilizar entregas.")
with t3:
    st.success("**Retención e Incentivos**\n\nAplicar bono dinámico al Equipo 8, el cual sostiene la mayor eficiencia sin horas extras.")

st.divider()

# 5. Matriz de Priorización de Intervención (Codificación visual y principios de Tufte)
st.subheader("Matriz de Priorización de Intervención")

# Validación de dimensionalidad antes de renderizar la visualización
if 'team' in df.columns and 'over_time' in df.columns and 'actual_productivity' in df.columns:
    
    # Agregación de métricas a nivel de equipo
    df_resumen = df.groupby('team').agg({'actual_productivity': 'mean', 'over_time': 'mean'}).reset_index()
    
    fig = px.scatter(
        df_resumen, 
        x='over_time', 
        y='actual_productivity', 
        text='team',
        title='Identificación de equipos críticos: Productividad vs Horas Extras',
        labels={'over_time': 'Horas Extras Promedio', 'actual_productivity': 'Productividad Real'}
    )
    
    # Optimización del Data-to-Ink ratio: supresión de fondos y cuadrículas no esenciales
    fig.update_traces(textposition='top center', marker=dict(size=12, color='#1f77b4'))
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=True, gridcolor='#e5e5e5', zeroline=False),
        yaxis=dict(showgrid=True, gridcolor='#e5e5e5', zeroline=False),
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)

    # Exportación de datos operativos (Details-on-demand)
    st.download_button(
        label="📥 Descargar Plan de Intervención (CSV)",
        data=df_resumen.to_csv(index=False),
        file_name="recomendaciones_confeccion.csv",
        mime="text/csv"
    )
else:
    st.warning("Advertencia: Seleccione al menos un equipo en los filtros globales para visualizar la matriz de priorización.")

# Navegación
st.page_link("vistas/diagnostico.py", label="Volver al diagnóstico", icon=":material/restart_alt:")