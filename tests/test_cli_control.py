"""Entrada por consola y coordinación de comparaciones continuas de etapa 6."""

import os
from pathlib import Path
import subprocess
import sys
import textwrap
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from main import comparar_continuo
from pendulo.control import ControladorPD
from pendulo.parametros import Friccion


def test_cli_ida_vuelta_compara_sin_graficos_ni_exportaciones() -> None:
    """Ejecutar main.py con comparación ida-vuelta en el mismo intérprete.

    El subproceso ejecuta las cuentas reales y exige dos tramos, dos informes
    por controlador y aceptación nominal PD+G en ambos. Sustitutos que fallan
    impiden show, gráficos, animación y guardado de resultados/figuras/videos;
    no se recorre el sistema de archivos ni se depende de una ventana gráfica.
    """
    proyecto = Path(__file__).resolve().parents[1]
    codigo = textwrap.dedent('''
        import runpy
        import sys
        from unittest.mock import patch

        # Reproducir los argumentos de la entrada real, conservando un
        # proceso independiente para el diagnóstico y las integraciones.
        sys.argv = ["main.py", *sys.argv[1:]]
        llamadas_prohibidas = [
            "matplotlib.pyplot.show",
            "pendulo.visualizacion.crear_animacion",
            "pendulo.visualizacion.graficar_resultado",
            "pendulo.visualizacion.graficar_seguimientos",
            "numpy.save", "numpy.savez", "numpy.savetxt",
            "matplotlib.figure.Figure.savefig",
            "matplotlib.animation.Animation.save",
        ]
        from contextlib import ExitStack
        with ExitStack() as contextos:
            # Cualquier llamada convierte el subproceso en una prueba fallida;
            # las librerías pueden conservar sus caches normales de importación.
            for nombre in llamadas_prohibidas:
                contextos.enter_context(patch(
                    nombre, side_effect=AssertionError("Llamada inesperada: " + nombre)))
            runpy.run_path("main.py", run_name="__main__")
    ''')
    # Agg evita depender del servidor gráfico; los sustitutos comprueban que
    # --sin-graficos ni siquiera solicita las figuras ni su reproducción.
    ejecucion = subprocess.run(
        [sys.executable, "-c", codigo, "--control", "comparar", "--escenario",
         "ida_vuelta", "--sin-graficos"],
        cwd=proyecto, env={**os.environ, "MPLBACKEND": "Agg"},
        capture_output=True, text=True, timeout=120,
    )
    assert ejecucion.returncode == 0, ejecucion.stdout + ejecucion.stderr
    salida = ejecucion.stdout
    assert "Etapa 6 — Trayectorias y control continuo" in salida
    assert salida.count("Escenario: abajo_arriba") == 1
    assert salida.count("Escenario: arriba_abajo") == 1
    assert salida.count("Controlador: PD;") == 2
    assert salida.count("Controlador: PD+G;") == 2
    for informe in salida.split("Controlador: ")[1:]:
        if informe.startswith("PD+G;"):
            assert "Precisión nominal (máximo 2°, final 0.2°): True" in informe
            # La descripción de capacidad puede precisar sus supuestos;
            # exigir el estado del informe sin fijar toda su redacción.
            capacidad = [linea for linea in informe.splitlines()
                         if linea.startswith("Capacidad")]
            assert len(capacidad) == 1 and capacidad[0].endswith(": True")
    assert "Caso: " not in salida
    print("CLI ida-vuelta: dos tramos, cuatro informes, PD+G aceptado en ambos; "
          "sin llamadas gráficas ni exportaciones de resultados.")


def test_comparacion_hereda_estado_real_y_conserva_condiciones() -> None:
    """Comprobar coordinación de ida-vuelta sin integrar la planta.

    Dos instancias distintas comparten dinámica y fricción. Los finales
    sintéticos tienen errores y velocidades residuales diferentes; cada
    vuelta debe recibir exclusivamente el final real de su propia ida.
    Las referencias de ida/vuelta conservan sus destinos teóricos en reposo.
    """
    dinamica = object()
    friccion = Friccion(escala=0.5)
    controladores = [ControladorPD("primero"),
                     ControladorPD("segundo con G", gravedad=True)]
    finales_q = [np.array([np.pi / 2 - 0.03, 0.02]),
                 np.array([-np.pi / 2 + 0.01, -0.02]),
                 np.array([np.pi / 2 + 0.04, -0.01]),
                 np.array([-np.pi / 2 - 0.02, 0.03])]
    finales_v = [np.array([0.07, -0.04]), np.array([-0.02, 0.01]),
                 np.array([-0.05, 0.03]), np.array([0.01, -0.02])]
    sinteticos = [SimpleNamespace(simulacion=SimpleNamespace(
        q=np.array([[0.0, 0.0], q]), qd=np.array([[0.0, 0.0], v])))
        for q, v in zip(finales_q, finales_v)]
    # Fallar si se invoca la integración distingue esta prueba de coordinación
    # de las verificaciones físicas realizadas en los tests de seguimiento.
    with patch("pendulo.simulacion.solve_ivp", side_effect=AssertionError("No integrar")), \
            patch("main.simular_seguimiento", side_effect=sinteticos) as simular:
        resultados = comparar_continuo(dinamica, "ida_vuelta", controladores, friccion)
    assert simular.call_count == 4
    assert list(resultados) == ["abajo_arriba", "arriba_abajo"]
    for indice, llamada in enumerate(simular.call_args_list):
        d, trayectoria, controlador = llamada.args
        assert d is dinamica
        assert controlador is controladores[indice // 2]
        assert llamada.kwargs["friccion"] is friccion
        if indice % 2 == 0:
            assert llamada.kwargs["q0"] is None
            assert llamada.kwargs["qd0"] is None
            esperado_i, esperado_f = [-np.pi / 2, 0], [np.pi / 2, 0]
        else:
            # No reemplazar el final obtenido por el destino ideal ni por
            # velocidad cero; tampoco cruzar finales entre controladores.
            np.testing.assert_array_equal(llamada.kwargs["q0"], finales_q[indice - 1])
            np.testing.assert_array_equal(llamada.kwargs["qd0"], finales_v[indice - 1])
            esperado_i, esperado_f = [np.pi / 2, 0], [-np.pi / 2, 0]
        np.testing.assert_array_equal(trayectoria.qi, esperado_i)
        np.testing.assert_array_equal(trayectoria.qf, esperado_f)
    for indice, controlador in enumerate(controladores):
        assert resultados["abajo_arriba"][controlador.nombre] is sinteticos[2 * indice]
        assert resultados["arriba_abajo"][controlador.nombre] is sinteticos[2 * indice + 1]
    print("Coordinación ida-vuelta: cuatro llamadas, referencias comunes y "
          "herencia exacta de q/qd reales por instancia; sin integrador.")
