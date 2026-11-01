"""
Carga de la vista analítica y filtros globales sincronizados.

Los filtros se dibujan una sola vez en la barra lateral y el mismo
DataFrame filtrado se entrega a todas las vistas, así que cualquier
filtro afecta a todo el dashboard (zoom and filter de Shneiderman).
"""

from pathlib import Path

import pandas as pd
import streamlit as st

from componentes import DEPARTAMENTOS

RUTA_DATOS = Path(__file__).resolve().parent / "data" / "garments_dashboard.csv"
EQUIPOS = list(range(1, 13))

# Minimo de registros para que un promedio sea representativo en la vista
MINIMO_REPRESENTATIVO = 30


@st.cache_data
def cargar_datos() -> pd.DataFrame:
    """Lee la vista analítica generada por preparar_datos.py."""
    df = pd.read_csv(RUTA_DATOS, parse_dates=["fecha"])
    return df


def _valores_iniciales(df: pd.DataFrame) -> dict:
    return {
        "f_periodo": (df["fecha"].min().date(), df["fecha"].max().date()),
        "f_departamentos": DEPARTAMENTOS,
        "f_equipos": [],
    }


def _restablecer(df: pd.DataFrame) -> None:
    for clave, valor in _valores_iniciales(df).items():
        st.session_state[clave] = valor


def filtros_globales(df: pd.DataFrame) -> dict:
    """Dibuja los filtros en la barra lateral y devuelve la selección."""
    for clave, valor in _valores_iniciales(df).items():
        st.session_state.setdefault(clave, valor)

    fecha_min, fecha_max = df["fecha"].min().date(), df["fecha"].max().date()

    with st.sidebar:
        st.header("Filtros")
        st.caption("Aplican a todas las vistas del dashboard.")

        periodo = st.slider(
            "Periodo",
            min_value=fecha_min,
            max_value=fecha_max,
            key="f_periodo",
            format="DD/MM/YYYY",
        )
        departamentos = st.pills(
            "Departamento",
            DEPARTAMENTOS,
            selection_mode="multi",
            key="f_departamentos",
        )
        equipos = st.multiselect(
            "Equipo",
            EQUIPOS,
            key="f_equipos",
            placeholder="Todos los equipos",
            format_func=lambda e: f"Equipo {e}",
        )
        st.button(
            "Restablecer filtros",
            on_click=_restablecer,
            args=(df,),
            icon=":material/restart_alt:",
            width="stretch",
        )

    return {
        "periodo": periodo,
        "departamentos": departamentos or [],
        "equipos": equipos or EQUIPOS,
    }


def aplicar_filtros(df: pd.DataFrame, filtros: dict) -> pd.DataFrame:
    inicio, fin = filtros["periodo"]
    mascara = (
        df["fecha"].dt.date.between(inicio, fin)
        & df["departamento"].isin(filtros["departamentos"])
        & df["equipo"].isin(filtros["equipos"])
    )
    return df.loc[mascara]


def hay_filtro_activo(df_filtrado: pd.DataFrame, df_total: pd.DataFrame) -> bool:
    return len(df_filtrado) < len(df_total)
