"""
Fase II - Preparación de la vista analítica del dashboard.

Por qué existe este script
--------------------------
El CSV limpio de la Fase I (garments_worker_productivity_clean.csv) está
codificado y escalado con RobustScaler: es la representación pensada para un
modelo futuro. Para un dashboard no sirve, porque una persona no puede leer
"productividad = -0.19" ni "tiempo extra = 0.11".

Este script reproduce el MISMO pipeline de la Fase I (mismas decisiones, sin
eliminar filas ni imputar) pero conserva las unidades originales y agrega
etiquetas en español y métricas derivadas para la interfaz.

Al final verifica que, si se aplicara el escalado de la Fase I a esta vista,
se obtendría exactamente el CSV limpio publicado. Así el dashboard queda
conectado a la data limpia y es trazable.

Uso (desde la raíz del repositorio):
    py dashboard/preparar_datos.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Rutas y fuente de datos
# ---------------------------------------------------------------------------
RAIZ_REPO = Path(__file__).resolve().parent.parent
CSV_ORIGINAL = RAIZ_REPO / "garments_worker_productivity.csv"
CSV_LIMPIO = RAIZ_REPO / "garments_worker_productivity_clean.csv"
CSV_SALIDA = Path(__file__).resolve().parent / "data" / "garments_dashboard.csv"

# Misma fuente fijada a commit que usa el notebook (por si no hay copia local)
URL_ORIGINAL = (
    "https://raw.githubusercontent.com/feeerr04/proyecto-da/"
    "2d011cc1f0f1cd23e9476221cbb8d6ac71b72126/garments_worker_productivity.csv"
)

# Columnas que la Fase I escaló con RobustScaler (mismo orden del notebook)
VARIABLES_ESCALADAS = [
    "team", "targeted_productivity", "smv", "over_time", "incentive",
    "idle_time", "idle_men", "no_of_style_change", "no_of_workers",
    "actual_productivity",
]

MESES = {1: "Enero", 2: "Febrero", 3: "Marzo"}
DIAS = {
    "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
    "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado",
    "Sunday": "Domingo",
}
ORDEN_DIAS = ["Sábado", "Domingo", "Lunes", "Martes", "Miércoles", "Jueves"]
DEPARTAMENTOS = {"sweing": "Costura", "finishing": "Acabado"}


def cargar_original() -> pd.DataFrame:
    """Carga el CSV original (copia local del repo o URL fijada a commit)."""
    if CSV_ORIGINAL.exists():
        return pd.read_csv(CSV_ORIGINAL)
    return pd.read_csv(URL_ORIGINAL)


def limites_iqr(serie: pd.Series) -> tuple[float, float]:
    """Cercas IQR de la Fase I: Q1 - 1.5*IQR y Q3 + 1.5*IQR (nulos excluidos)."""
    q1, q3 = serie.quantile(0.25), serie.quantile(0.75)
    iqr = q3 - q1
    return q1 - 1.5 * iqr, q3 + 1.5 * iqr


def marcar_atipicos(serie: pd.Series) -> pd.Series:
    lim_inf, lim_sup = limites_iqr(serie)
    return ((serie < lim_inf) | (serie > lim_sup)).fillna(False)


def preparar(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica la limpieza de la Fase I y construye la vista analítica."""
    df = df.copy()

    # --- Limpieza de la Fase I (sección 3.1 y 4.3 del notebook) ---
    df["department"] = df["department"].str.strip()  # "finishing " -> "finishing"
    df["date"] = pd.to_datetime(df["date"], format="%m/%d/%Y")

    # --- Vista analítica: nombres y etiquetas legibles ---
    vista = pd.DataFrame({
        "fecha": df["date"],
        "mes_num": df["date"].dt.month,
        "mes": df["date"].dt.month.map(MESES),
        "semana_mes": df["quarter"].str.replace("Quarter", "", regex=False).astype(int),
        "dia": df["day"].map(DIAS),
        "departamento": df["department"].map(DEPARTAMENTOS),
        "equipo": df["team"].astype(int),
        "meta": df["targeted_productivity"],
        "productividad": df["actual_productivity"],
        "tiempo_estandar_min": df["smv"],
        "wip": df["wip"],
        "tiempo_extra_min": df["over_time"],
        "incentivo_bdt": df["incentive"],
        "tiempo_inactivo": df["idle_time"],
        "personal_inactivo": df["idle_men"],
        "cambios_estilo": df["no_of_style_change"],
        "personal_asignado": df["no_of_workers"],
    })

    # --- Métricas derivadas para el storytelling ---
    vista["brecha"] = (vista["productividad"] - vista["meta"]).round(9)
    vista["cumple_meta"] = vista["productividad"] >= vista["meta"]
    vista["hubo_inactividad"] = vista["tiempo_inactivo"] > 0
    vista["hubo_cambio_estilo"] = vista["cambios_estilo"] > 0

    # --- Banderas de calidad (mismos criterios de la Fase I) ---
    vista["wip_faltante"] = vista["wip"].isna()
    vista["productividad_mayor_1"] = vista["productividad"] > 1
    vista["personal_fraccionario"] = vista["personal_asignado"] % 1 != 0
    vista["atipico_wip"] = marcar_atipicos(vista["wip"])
    vista["atipico_tiempo_extra"] = marcar_atipicos(vista["tiempo_extra_min"])
    vista["atipico_incentivo"] = marcar_atipicos(vista["incentivo_bdt"])

    return vista


def verificar(df_original: pd.DataFrame, vista: pd.DataFrame) -> None:
    """Comprueba que la vista coincide con la Fase I y con el CSV limpio publicado."""
    # 1) Mismas cifras del artículo (Tablas II y V)
    assert len(vista) == 1197, "Se esperaban 1,197 registros"
    assert vista["wip_faltante"].sum() == 506, "Se esperaban 506 nulos en wip"
    assert (vista.loc[vista["wip_faltante"], "departamento"] == "Acabado").all()
    assert vista["departamento"].value_counts().to_dict() == {"Costura": 691, "Acabado": 506}
    assert vista["productividad_mayor_1"].sum() == 37
    assert vista["personal_fraccionario"].sum() == 140
    assert vista[["atipico_wip", "atipico_tiempo_extra", "atipico_incentivo"]].sum().tolist() == [22, 1, 11]

    # 2) Trazabilidad con el CSV limpio: reaplicar el RobustScaler de la Fase I
    #    sobre las unidades originales debe reproducir el CSV publicado.
    if CSV_LIMPIO.exists():
        from sklearn.preprocessing import RobustScaler

        limpio = pd.read_csv(CSV_LIMPIO)
        reescalado = RobustScaler().fit_transform(df_original[VARIABLES_ESCALADAS])
        diferencia = np.abs(reescalado - limpio[VARIABLES_ESCALADAS].to_numpy()).max()
        assert diferencia < 1e-6, f"La vista no coincide con el CSV limpio (dif. máx. {diferencia})"
        assert (limpio["month"].to_numpy() == vista["mes_num"].to_numpy()).all()
        assert limpio["wip"].isna().sum() == 506
        print(f"  - Coincide con el CSV limpio de la Fase I (diferencia máx. {diferencia:.1e})")


def main() -> None:
    original = cargar_original()
    vista = preparar(original)
    print("Verificando contra la Fase I...")
    verificar(original, vista)

    CSV_SALIDA.parent.mkdir(parents=True, exist_ok=True)
    vista.to_csv(CSV_SALIDA, index=False, date_format="%Y-%m-%d")
    print(f"  - Vista analítica exportada: {CSV_SALIDA.name} "
          f"({vista.shape[0]} filas x {vista.shape[1]} columnas)")


if __name__ == "__main__":
    main()
