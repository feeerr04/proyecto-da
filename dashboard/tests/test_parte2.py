"""Validación de agregaciones y navegación real con los filtros compartidos.

Ejecutar desde la raíz: python -m unittest discover -s dashboard/tests -v
"""

from datetime import date
from pathlib import Path
import sys
import unittest

import pandas as pd
from streamlit.testing.v1 import AppTest

DASHBOARD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DASHBOARD))

from componentes import estilo
from vistas import causa_raiz, patrones


class CalculosParte2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df = pd.read_csv(DASHBOARD / "data/garments_dashboard.csv", parse_dates=["fecha"])

    def test_equipos_no_se_mezclan_entre_departamentos(self):
        resumen = patrones.resumen_equipos(self.df)
        self.assertEqual(len(resumen), 24)
        self.assertEqual(resumen["registros"].sum(), 1197)
        self.assertEqual(resumen["identidad"].nunique(), 24)
        self.assertAlmostEqual(
            (resumen["brecha"] * resumen["registros"]).sum() / 1197,
            self.df["brecha"].mean(),
        )

    def test_semana_calendario_y_promedio_por_registro(self):
        # Tres observaciones en dos días: no promediar las medias diarias.
        ejemplo = pd.DataFrame({
            "fecha": pd.to_datetime(["2015-01-30", "2015-02-01", "2015-02-01", "2015-02-02"]),
            "departamento": ["Costura"] * 4, "productividad": [0.2, 0.8, 0.8, 0.4],
            "meta": [0.5] * 4, "brecha": [-0.3, 0.3, 0.3, -0.1],
        })
        resumen = patrones.resumen_semanal(ejemplo)
        self.assertEqual(resumen["semana"].dt.strftime("%Y-%m-%d").tolist(), ["2015-01-26", "2015-02-02"])
        self.assertAlmostEqual(resumen.iloc[0]["productividad"], 0.6)
        self.assertEqual(resumen.iloc[0]["registros"], 3)

    def test_anomalias_conocidas_y_wip_ausente(self):
        diario = patrones.anomalias_diarias(self.df)
        totales = diario.groupby("variable")["atipicos"].sum().to_dict()
        self.assertEqual(totales, {"Trabajo en proceso (WIP)": 22, "Tiempo extra": 1, "Incentivo": 11})
        wip = diario.loc[diario["variable"].eq("Trabajo en proceso (WIP)")]
        self.assertEqual(wip["observados"].sum(), 691)
        self.assertEqual(wip.loc[wip["fecha"].eq("2015-02-02"), "atipicos"].iloc[0], 10)
        acabado = patrones.anomalias_diarias(self.df.loc[self.df["departamento"].eq("Acabado")])
        self.assertNotIn("Trabajo en proceso (WIP)", acabado["variable"].tolist())
        # Los límites globales no se recalculan sobre este único día.
        dia = patrones.anomalias_diarias(self.df.loc[self.df["fecha"].eq("2015-03-09")])
        self.assertEqual(dia.loc[dia["variable"].eq("Incentivo"), "atipicos"].sum(), 10)

    def test_comparacion_usa_denominadores_de_cada_grupo(self):
        tabla = causa_raiz.resumen_condicion(self.df, "hubo_inactividad")
        fila = tabla.loc[tabla["departamento"].eq("Costura") & tabla["hubo_inactividad"]].iloc[0]
        self.assertEqual(fila["registros"], 18)
        self.assertEqual(fila["cumplen"], 4)
        self.assertAlmostEqual(fila["cumplimiento"], 4 / 18)
        diferencias = causa_raiz.contrastes(self.df)
        self.assertEqual(len(diferencias), 2)
        self.assertTrue(all(d["departamento"] == "Costura" for d in diferencias))
        acabado = self.df.loc[self.df["departamento"].eq("Acabado")]
        self.assertEqual(causa_raiz.contrastes(acabado), [])

    def test_falta_de_grupo_no_se_inventa_como_cero(self):
        cumplen = self.df.loc[self.df["cumple_meta"]]
        tabla = causa_raiz.promedios_por_cumplimiento(cumplen)
        self.assertEqual(set(tabla["resultado"]), {"Cumple"})
        self.assertEqual(tabla["registros"].sum(), 875)
        self.assertEqual(causa_raiz.contrastes(self.df.iloc[:1]), [])

    def test_graficos_validos_y_datos_originales_intactos(self):
        antes = self.df.copy(deep=True)
        casos = [self.df, self.df.iloc[:1], self.df.loc[self.df["departamento"].eq("Acabado")]]
        for df in casos:
            with self.subTest(n=len(df)):
                graficos = [
                    patrones._tendencia(patrones.resumen_semanal(df)),
                    patrones._ranking(patrones.resumen_equipos(df)),
                    patrones._anomalias(patrones.anomalias_diarias(df)),
                ]
                for departamento in df["departamento"].unique():
                    graficos.append(patrones._equipos(patrones.resumen_semanal(df, True), departamento, [0, 1.2]))
                for condicion in causa_raiz.CONDICIONES:
                    graficos.append(causa_raiz._barras_condicion(causa_raiz.resumen_condicion(df, condicion), condicion))
                for variable in ["incentivo_bdt", "tiempo_extra_min"]:
                    graficos.append(causa_raiz._dispersion(df, variable))
                for grafico in graficos:
                    estilo(grafico).to_dict(validate=True)
        pd.testing.assert_frame_equal(self.df, antes)


class NavegacionParte2(unittest.TestCase):
    def nueva_app(self):
        app = AppTest.from_file(str(DASHBOARD / "app.py"), default_timeout=30).run()
        self.assertFalse(app.exception)
        return app

    def comprobar_paginas(self, app, n):
        for pagina, titulo in [
            ("patrones", "¿Dónde y cuándo se aleja la productividad de la meta?"),
            ("causa_raiz", "¿Qué condiciones acompañan a los incumplimientos?"),
        ]:
            app.switch_page(f"vistas/{pagina}.py").run()
            self.assertFalse(app.exception, [e.message for e in app.exception])
            self.assertEqual(len(app.session_state["seleccion"]), n)
            self.assertEqual(app.title[0].value, titulo)
            self.assertEqual(len(app.metric), 3)
            self.assertNotIn("Vista en construcción", " ".join(e.value for e in app.info))

    def test_navegacion_y_persistencia_filtros(self):
        app = self.nueva_app()
        self.comprobar_paginas(app, 1197)
        app.session_state["f_departamentos"] = ["Acabado"]
        self.comprobar_paginas(app, 506)
        self.assertIn("No hay grupos", app.markdown[0].value)
        app.session_state["f_equipos"] = [1]
        app.session_state["f_periodo"] = (date(2015, 1, 1), date(2015, 1, 1))
        self.comprobar_paginas(app, 1)
        self.assertTrue(app.warning)
        self.assertIn("No aplica", [m.value for m in app.metric])

    def test_selecciones_vacias_se_detienen_en_la_base(self):
        app = self.nueva_app()
        app.session_state["f_departamentos"] = []
        for pagina in ["patrones", "causa_raiz"]:
            app.switch_page(f"vistas/{pagina}.py").run()
            self.assertFalse(app.exception)
            self.assertTrue(app.warning)
            self.assertFalse(app.metric)
        app.session_state["f_departamentos"] = ["Costura"]
        # Viernes sin registros en la fuente.
        app.session_state["f_periodo"] = (date(2015, 1, 2), date(2015, 1, 2))
        app.run()
        self.assertEqual(len(app.session_state["seleccion"]), 0)
        self.assertFalse(app.exception)
        self.assertFalse(app.metric)


if __name__ == "__main__":
    unittest.main()
