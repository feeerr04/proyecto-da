# Dashboard · Fase II

Interfaz analítica sobre los datos limpios de la Fase I (productividad en
equipos de confección, UCI, 1,197 registros). Modalidad A: mismo dataset.

**Enlace público:** _(pegar aquí la URL de Streamlit Community Cloud)_

## Estructura

```
.streamlit/config.toml       Tema visual (va en la RAÍZ del repositorio)
dashboard/
├── app.py                   Punto de entrada: navegación y filtros globales
├── datos.py                 Carga de datos y filtros sincronizados
├── componentes.py           Paleta semántica y estilo común de los gráficos
├── preparar_datos.py        Genera data/garments_dashboard.csv desde la Fase I
├── data/garments_dashboard.csv
├── requirements.txt
└── vistas/
    ├── diagnostico.py       Paso 1 · Diagnóstico inicial      (Parte 1, listo)
    ├── patrones.py          Paso 2 · Patrones y anomalías     (Parte 2)
    ├── causa_raiz.py        Paso 3 · Causa raíz               (Parte 2)
    └── recomendacion.py     Paso 4 · Recomendación            (Parte 3)
```

## Ejecutar en local (Windows)

Desde la raíz del repositorio:

```
py -m pip install -r dashboard/requirements.txt
py -m streamlit run dashboard/app.py
```

Se abre en el navegador (http://localhost:8501). Al guardar un archivo, la
app ofrece "Rerun" para ver los cambios.

## Por qué hay un CSV propio del dashboard

`garments_worker_productivity_clean.csv` está codificado y escalado
(RobustScaler): sirve para un modelo, pero no se puede leer en un gráfico
(una productividad de −0.19 no significa nada para quien lo ve).

`preparar_datos.py` aplica la misma limpieza de la Fase I conservando las
unidades originales, y agrega etiquetas en español y métricas derivadas
(`brecha`, `cumple_meta` y banderas de atípicos). Al final comprueba que,
si se aplica el escalado de la Fase I, se obtiene exactamente el CSV
limpio publicado. Para regenerarlo (requiere scikit-learn):

```
py dashboard/preparar_datos.py
```

## Publicar en Streamlit Community Cloud

1. Entrar a https://share.streamlit.io con la cuenta de GitHub `feeerr04`.
2. **Create app** → *Deploy a public app from GitHub*.
3. Repository: `feeerr04/proyecto-da` · Branch: `main` ·
   Main file path: `dashboard/app.py`.
4. **Deploy**. Cada push a `main` actualiza la app automáticamente.

## Reparto del trabajo

| Parte | Responsable | Archivos | Contenido |
|---|---|---|---|
| 1 | Luis | todo lo de arriba + `vistas/diagnostico.py` | Datos, filtros globales, KPIs, panorámica, despliegue |
| 2 | _(compañero 2)_ | `vistas/patrones.py`, `vistas/causa_raiz.py` | Patrones, anomalías y causa raíz |
| 3 | _(compañero 3)_ | `vistas/recomendacion.py`, adenda IEEE | Recomendación, pulido final, capturas anotadas, Sección V-B |

Cada vista pendiente trae en su encabezado qué gráficos construir.

## Reglas para que el dashboard se vea como un solo sistema

- Usar los datos ya filtrados: `df = st.session_state["seleccion"]`.
  **No** agregar filtros dentro de una vista; los filtros globales van en `datos.py`.
- Colores solo desde `componentes.py`. Departamento: `ESCALA_DEPARTAMENTO`
  (Costura azul, Acabado naranja). Meta: gris punteado. El color nunca decora.
- Envolver cada gráfico con `estilo(...)` y mostrarlo con
  `st.altair_chart(estilo(grafico), width="stretch", theme=None)`.
- Barras siempre desde 0. Sin 3D, sin gráficos circulares, sin doble eje.
- Cada marca con `tooltip`. Las fechas, en español: `EJE_FECHA_ES` en el eje
  y `fecha_es()` en los tooltips.
- Cada página: pregunta como título, un texto con la conclusión y un
  `st.page_link` al siguiente paso.

## Hallazgos para la narrativa (verificados con los datos)

- **Acabado** tiene mayor productividad promedio (0.753 frente a 0.722), pero
  cumple su meta en menos registros (60% frente a 83% de Costura).
- **Del 10 de febrero al 1 de marzo**, la productividad diaria quedó por
  debajo de la meta en 14 de 16 días (cumplimiento del 62%, frente a 77%
  en el resto del periodo).
- Cumplimiento por mes: enero 78%, febrero 66%, marzo 75%.
