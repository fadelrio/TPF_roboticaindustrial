"""Consola, historias independientes y barridos coordinados de etapa 7."""

import os
from pathlib import Path
import re
import subprocess
import sys
import textwrap
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest

from main import comparar_control, comparar_variantes
from pendulo.control import ControladorPD
from pendulo.parametros import Friccion


def ejecutar_cli_digital(argumentos: list[str]) -> str:
    """Ejecutar main.py sin ventanas/exportaciones y comprobar retención digital.

    Usa el intérprete actual en un subproceso. Los gráficos, reproductores y
    guardados se sustituyen por llamadas que fallan. Un wrapper conserva la
    integración real y verifica ambos torques registrados frente a las trazas
    de actualización digital, incluida la última muestra. Retorna stdout.
    """
    proyecto = Path(__file__).resolve().parents[1]
    codigo = textwrap.dedent('''
        from contextlib import ExitStack
        import runpy
        import sys
        from unittest.mock import patch

        import numpy as np
        from pendulo.simulacion import simular_seguimiento

        def comprobar_retencion(*args, **kwargs):
            """Ejecutar seguimiento real y contrastar torques con sus actualizaciones."""
            resultado = simular_seguimiento(*args, **kwargs)
            if resultado.modo == "digital":
                # La retención usa la última actualización disponible, incluso
                # cuando Ts no coincide con la grilla de salida de 1 ms.
                indice = np.searchsorted(resultado.tiempos_control,
                                         resultado.simulacion.t, side="right") - 1
                np.testing.assert_array_equal(resultado.simulacion.torque_solicitado,
                                               resultado.torque_control_solicitado[indice])
                np.testing.assert_array_equal(resultado.simulacion.torque_aplicado,
                                               resultado.torque_control_aplicado[indice])
                print("Retención digital comprobada en todas las muestras")
            return resultado

        sys.argv = ["main.py", *sys.argv[1:]]
        prohibidas = [
            "matplotlib.pyplot.show",
            "pendulo.visualizacion.crear_animacion",
            "pendulo.visualizacion.crear_animacion_comparada",
            "pendulo.visualizacion.graficar_resultado",
            "pendulo.visualizacion.graficar_seguimientos",
            "numpy.save", "numpy.savez", "numpy.savetxt",
            "matplotlib.figure.Figure.savefig",
            "matplotlib.animation.Animation.save",
        ]
        with ExitStack() as contextos:
            # Los resultados permanecen en memoria; las caches normales de
            # las dependencias no se confunden con exportaciones del proyecto.
            for nombre in prohibidas:
                contextos.enter_context(patch(
                    nombre, side_effect=AssertionError("Llamada inesperada: " + nombre)))
            contextos.enter_context(patch("pendulo.simulacion.simular_seguimiento",
                                         side_effect=comprobar_retencion))
            runpy.run_path("main.py", run_name="__main__")
    ''')
    # Agg asegura independencia del escritorio; los sustitutos detectan si
    # --sin-graficos aun así intenta solicitar alguna salida gráfica.
    ejecucion = subprocess.run(
        [sys.executable, "-c", codigo, *argumentos, "--sin-graficos"],
        cwd=proyecto, env={**os.environ, "MPLBACKEND": "Agg"},
        capture_output=True, text=True, timeout=120,
    )
    assert ejecucion.returncode == 0, ejecucion.stdout + ejecucion.stderr
    return ejecucion.stdout


def test_cli_compara_dos_leyes_y_dos_modos() -> None:
    """Ejecutar un recorrido interior con PD/PD+G continuo y digital de 1 ms.

    Exige cuatro informes con identificadores únicos, dos por ley y modo,
    aceptación nominal PD+G en ambos modos y retención verificada en los
    digitales. No solicita gráficos ni exporta resultados.
    """
    salida = ejecutar_cli_digital([
        "--control", "comparar", "--modo", "comparar", "--escenario", "interior_a"])
    assert "Etapa 7 — Control digital y comparación completa" in salida
    assert salida.count("Escenario: interior_a") == 1
    assert salida.count("Controlador: PD;") == 2
    assert salida.count("Controlador: PD+G;") == 2
    assert salida.count("Modo: continuo") == 2
    assert salida.count("Modo: digital; período [s]=0.001") == 2
    identificadores = [linea.removeprefix("Comparación: ") for linea in salida.splitlines()
                       if linea.startswith("Comparación: ")]
    assert identificadores == ["PD — continuo", "PD — digital 1 ms",
                               "PD+G — continuo", "PD+G — digital 1 ms"]
    for informe in salida.split("Controlador: ")[1:]:
        if informe.startswith("PD+G;"):
            # El PD puro sirve de comparación; su precisión no tiene el mismo
            # criterio de aceptación nominal que el compensado por gravedad.
            assert "Precisión nominal (máximo 2°, final 0.2°): True" in informe
    assert salida.count("Retención digital comprobada en todas las muestras") == 2
    assert "Caso: " not in salida
    print("CLI interior_a: cuatro resultados con dos leyes y dos modos; "
          "PD+G aceptado en ambos; retención exacta y sin salidas gráficas.")


def test_cli_periodo_no_alineado_sostiene_horizontal() -> None:
    """Verificar PD+G digital de 7,3 ms en horizontal nulo durante 3 s.

    Exige 411 actualizaciones, período solicitado explícito y errores máximo
    y final ≤1e-10 grados en cada eje. El wrapper contrasta la retención aun
    cuando el período digital no es múltiplo de la salida de 1 ms.
    """
    salida = ejecutar_cli_digital([
        "--control", "pd_gravedad", "--modo", "digital", "--periodo", "0.0073",
        "--escenario", "nulo_horizontal"])
    assert salida.count("Controlador: PD+G;") == 1
    assert "Modo: digital; período [s]=0.0073" in salida
    assert "Actualizaciones digitales: 411" in salida
    assert salida.count("Retención digital comprobada en todas las muestras") == 1
    errores = re.search(r"Error máximo/final por eje \[°\]: \[([^]]+)\] / \[([^]]+)\]", salida)
    assert errores is not None
    # Leer los valores informados permite contrastar el equilibrio conocido
    # sin depender del número de decimales elegidos para imprimir los arrays.
    for valores in errores.groups():
        vector = np.fromstring(valores, sep=" ")
        assert vector.shape == (2,) and np.max(np.abs(vector)) <= 1e-10
    assert "Precisión nominal (máximo 2°, final 0.2°): True" in salida
    print("CLI horizontal digital 7,3 ms: 411 actualizaciones, equilibrio a "
          "1e-10 grados y retención comprobada; sin gráficos ni exportaciones.")


def test_comparacion_ida_vuelta_conserva_cuatro_historias() -> None:
    """Comprobar dos instancias por dos modos, con ocho llamadas sintéticas.

    Cada combinación debe heredar posición y velocidad reales de su propia
    ida. Ambas leyes conservan sus ganancias originales, la misma planta y
    fricción. Las referencias son comunes; esta coordinación no integra.
    """
    dinamica, friccion = object(), Friccion(escala=0.5)
    controladores = [ControladorPD("primero"), ControladorPD(
        "segundo", kp=(15.0, 4.0), kd=(0.8, 0.15), gravedad=True)]
    ganancias = [(c.kp.copy(), c.kd.copy()) for c in controladores]
    sinteticos = []
    for indice in range(8):
        extremo = np.pi / 2 if indice % 2 == 0 else -np.pi / 2
        q = np.array([extremo + 0.002 * (indice + 1), -0.003 * (indice + 1)])
        v = np.array([0.005 * (indice + 1), -0.004 * (indice + 1)])
        # Valores residuales distintos detectan resets y transferencias del
        # final de otra instancia o modo, sin pretender un resultado físico.
        sinteticos.append(SimpleNamespace(simulacion=SimpleNamespace(
            q=np.array([[0, 0], q]), qd=np.array([[0, 0], v]))))
    with patch("pendulo.simulacion.solve_ivp", side_effect=AssertionError("No integrar")), \
            patch("main.simular_seguimiento", side_effect=sinteticos) as simular:
        resultados = comparar_control(dinamica, "ida_vuelta", controladores,
                                       friccion, ("continuo", "digital"), 0.0073)
    identificadores = ["primero — continuo", "primero — digital 7.3 ms",
                       "segundo — continuo", "segundo — digital 7.3 ms"]
    assert simular.call_count == 8
    assert list(resultados) == ["abajo_arriba", "arriba_abajo"]
    for casos in resultados.values():
        assert list(casos) == identificadores
    for indice, llamada in enumerate(simular.call_args_list):
        d, trayectoria, controlador = llamada.args
        assert d is dinamica and controlador is controladores[indice // 4]
        assert llamada.kwargs["friccion"] is friccion
        assert llamada.kwargs["modo"] == ("continuo" if indice % 4 < 2 else "digital")
        assert llamada.kwargs["periodo"] == 0.0073
        if indice % 2 == 0:
            assert llamada.kwargs["q0"] is None and llamada.kwargs["qd0"] is None
            esperado_i, esperado_f = [-np.pi / 2, 0], [np.pi / 2, 0]
        else:
            # Se conservan tanto el error residual como la velocidad de la
            # combinación inmediatamente anterior, no el destino ideal.
            np.testing.assert_array_equal(llamada.kwargs["q0"], sinteticos[indice - 1].simulacion.q[-1])
            np.testing.assert_array_equal(llamada.kwargs["qd0"], sinteticos[indice - 1].simulacion.qd[-1])
            esperado_i, esperado_f = [np.pi / 2, 0], [-np.pi / 2, 0]
        np.testing.assert_array_equal(trayectoria.qi, esperado_i)
        np.testing.assert_array_equal(trayectoria.qf, esperado_f)
    for indice, identificador in enumerate(identificadores):
        assert resultados["abajo_arriba"][identificador] is sinteticos[2 * indice]
        assert resultados["arriba_abajo"][identificador] is sinteticos[2 * indice + 1]
    for controlador, (kp, kd) in zip(controladores, ganancias):
        np.testing.assert_array_equal(controlador.kp, kp)
        np.testing.assert_array_equal(controlador.kd, kd)
    print("Coordinación de cuatro historias: ocho llamadas, finales independientes, "
          "misma planta/fricción y ganancias intactas; sin integrador.")


@pytest.mark.parametrize("barrido", ["friccion", "periodo"])
def test_barridos_reunen_variantes_sin_repetir_continuo(barrido: str) -> None:
    """Verificar composición de barridos sin ejecutar sus integraciones.

    Fricción requiere cuatro comparaciones con escalas 0/0,5/1/2, ambas leyes
    y modos; período requiere un continuo y cinco digitales 0,5/1/5/10/20 ms.
    Exige orden, identificadores únicos y conservación de todos los objetos.
    """
    dinamica, friccion = object(), Friccion()
    controladores = [ControladorPD("PD"), ControladorPD("PD+G", gravedad=True)]
    nombres = [c.nombre for c in controladores]
    entradas = []
    if barrido == "friccion":
        nombres_base = ["PD — continuo", "PD — digital 1 ms",
                        "PD+G — continuo", "PD+G — digital 1 ms"]
        esperados = [f"{nombre} — fricción ×{escala:g}"
                     for escala in (0, 0.5, 1, 2) for nombre in nombres_base]
        for _ in range(4):
            entradas.append({"interior_a": {nombre: object() for nombre in nombres_base}})
    else:
        nombres_base = nombres
        esperados = [f"{nombre} — continuo" for nombre in nombres]
        esperados += [f"{nombre} — digital {periodo:g} ms"
                      for periodo in (0.5, 1, 5, 10, 20) for nombre in nombres]
        for _ in range(6):
            entradas.append({"interior_a": {nombre: object() for nombre in nombres}})
    with patch("pendulo.simulacion.solve_ivp", side_effect=AssertionError("No integrar")), \
            patch("main.comparar_control", side_effect=entradas) as comparar:
        resultados = comparar_variantes(dinamica, "interior_a", controladores,
                                         friccion, ("continuo", "digital"), 0.001, barrido)
    assert list(resultados) == ["interior_a"]
    assert list(resultados["interior_a"]) == esperados
    assert len(esperados) == len(set(esperados))
    originales = [valor for entrada in entradas for valor in entrada["interior_a"].values()]
    assert list(resultados["interior_a"].values()) == originales
    for indice, llamada in enumerate(comparar.call_args_list):
        args = llamada.args
        assert args[0] is dinamica and args[1] == "interior_a" and args[2] is controladores
        if barrido == "friccion":
            assert comparar.call_count == 4
            assert args[3].escala == (0, 0.5, 1, 2)[indice]
            assert args[3].B == friccion.B and args[3].Tc == friccion.Tc
            assert args[3].epsilon == friccion.epsilon
            assert args[4] == ("continuo", "digital") and args[5] == 0.001
        else:
            assert comparar.call_count == 6
            assert args[3] is friccion
            if indice == 0:
                # La primera llamada conserva el continuo por defecto una
                # sola vez; ninguna variante digital vuelve a calcularlo.
                assert len(args) == 4
            else:
                assert args[4] == ("digital",)
                assert args[5] == (0.0005, 0.001, 0.005, 0.01, 0.02)[indice - 1]
    print(f"Barrido {barrido}: {comparar.call_count} comparaciones coordinadas, "
          f"{len(esperados)} resultados íntegros y con nombres únicos; sin integrador.")
