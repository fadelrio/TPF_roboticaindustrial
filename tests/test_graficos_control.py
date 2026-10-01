"""Correspondencia de gráficos de control con resultados disponibles en RAM."""

import matplotlib

# El lienzo Agg permite comprobar curvas y renderizado sin abrir ventanas.
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.figure import Figure

from pendulo.control import ControladorPD
from pendulo.parametros import LIMITES_TORQUE
from pendulo.simulacion import ResultadoSeguimiento, ResultadoSimulacion
from pendulo.trayectorias import TrayectoriaQuintica
from pendulo.visualizacion import graficar_seguimientos


@pytest.fixture
def comparacion_en_memoria() -> dict:
    """Construir dos registros gráficos artificiales, sin integrar la planta.

    Usa tiempos (0;0,4;1,3;2) s y una referencia común. Posiciones y torques
    distintos por controlador y eje, con saturación explícita, permiten
    detectar mezcla de curvas. No son resultados físicos de seguimiento.
    """
    tiempos = np.array([0.0, 0.4, 1.3, 2.0])
    deseada = np.array([[0.1, -0.2], [0.15, -0.16], [0.68, 0.21], [0.8, 0.3]])
    errores = [np.array([[0.5, -1.0], [1.1, -0.8], [-0.3, 0.4], [0.05, -0.02]]),
               np.array([[-0.3, 0.7], [0.4, 0.3], [0.1, -0.2], [-0.03, 0.01]])]
    pedidos = [np.array([[0.9, -0.2], [1.5, -0.5], [-1.1, 0.7], [0.4, -0.1]]),
               np.array([[0.8, -0.1], [1.7, -0.4], [0.3, 0.4], [-0.2, 0.2]])]
    aplicados = [np.array([[0.9, -0.2], [1.2, -0.31], [-1.1, 0.31], [0.4, -0.1]]),
                 np.array([[0.8, -0.1], [1.2, -0.31], [0.3, 0.31], [-0.2, 0.2]])]
    trayectoria = TrayectoriaQuintica(deseada[0], deseada[-1])
    resultados = {}
    for indice, nombre in enumerate(("PD", "PD+G")):
        # La construcción directa separa la verificación gráfica de la
        # dinámica y asegura que no se necesite llamar al integrador.
        q = deseada - np.deg2rad(errores[indice])
        simulacion = ResultadoSimulacion(
            tiempos.copy(), q, np.zeros((4, 2)), np.zeros(4), np.zeros(4), 0,
            pedidos[indice], aplicados[indice], np.zeros((4, 2)))
        resultados[nombre] = ResultadoSeguimiento(
            simulacion, trayectoria, ControladorPD(nombre, gravedad=indice == 1),
            deseada.copy(), np.zeros((4, 2)), np.zeros((4, 2)), np.zeros((4, 2)))
    return resultados


def test_curvas_referencia_error_torques_y_colores(comparacion_en_memoria: dict) -> None:
    """Verificar referencia única, datos originales y color por controlador.

    Cada eje recibe posiciones en rad, errores en grados y ambos torques
    en N·m, con la grilla original exacta. Errores a 1e-12 grados; el resto
    de datos coincide exactamente. Se renderiza el canvas Agg en memoria.
    """
    figura = graficar_seguimientos(comparacion_en_memoria, "Comparación de prueba")
    try:
        assert len(figura.axes) == 6
        assert figura._suptitle.get_text() == "Comparación de prueba"
        colores_por_controlador = {}
        errores_manual = {
            "PD": np.array([[0.5, -1.0], [1.1, -0.8], [-0.3, 0.4], [0.05, -0.02]]),
            "PD+G": np.array([[-0.3, 0.7], [0.4, 0.3], [0.1, -0.2], [-0.03, 0.01]]),
        }
        for articulacion in range(2):
            posicion, error, torque = [figura.axes[2 * fila + articulacion] for fila in range(3)]
            # Identificar por leyenda evita depender del orden de inserción
            # de líneas auxiliares, manteniendo el contraste de cada señal.
            curvas_q = {linea.get_label(): linea for linea in posicion.lines}
            curvas_e = {linea.get_label(): linea for linea in error.lines}
            curvas_t = {linea.get_label(): linea for linea in torque.lines}
            referencias = [linea for linea in posicion.lines if linea.get_label() == "Referencia"]
            assert len(referencias) == 1
            referencia = referencias[0]
            np.testing.assert_array_equal(referencia.get_xdata(), comparacion_en_memoria["PD"].simulacion.t)
            np.testing.assert_array_equal(referencia.get_ydata(), comparacion_en_memoria["PD"].q_d[:, articulacion])
            assert referencia.get_color() == "black" and referencia.get_linestyle() == "--"
            colores = []
            for nombre, resultado in comparacion_en_memoria.items():
                r = resultado.simulacion
                q, e = curvas_q[nombre], curvas_e[nombre]
                solicitado, aplicado = curvas_t[f"{nombre}: solicitado"], curvas_t[f"{nombre}: aplicado"]
                for linea in (q, e, solicitado, aplicado):
                    np.testing.assert_array_equal(linea.get_xdata(), r.t)
                    assert linea.get_color() == q.get_color()
                if articulacion == 0:
                    colores_por_controlador[nombre] = q.get_color()
                else:
                    assert q.get_color() == colores_por_controlador[nombre]
                np.testing.assert_array_equal(q.get_ydata(), r.q[:, articulacion])
                np.testing.assert_allclose(e.get_ydata(), errores_manual[nombre][:, articulacion],
                                           rtol=0, atol=1e-12)
                np.testing.assert_array_equal(solicitado.get_ydata(), r.torque_solicitado[:, articulacion])
                np.testing.assert_array_equal(aplicado.get_ydata(), r.torque_aplicado[:, articulacion])
                assert solicitado.get_linestyle() == "-" and aplicado.get_linestyle() == "--"
                colores.append(q.get_color())
            assert colores[0] != colores[1]
            assert posicion.get_ylabel() == "Ángulo [rad]"
            assert error.get_ylabel() == "Error [°]"
            assert torque.get_ylabel() == "Torque [N·m]"
            assert torque.get_xlabel() == "Tiempo [s]"
        figura.canvas.draw()
        assert np.asarray(figura.canvas.buffer_rgba()).shape[2] == 4
    finally:
        plt.close(figura)


@pytest.mark.parametrize("limite_error", [2.0, 0.2], ids=["seguimiento", "recuperacion"])
def test_guias_de_error_y_limites_fisicos(comparacion_en_memoria: dict, limite_error: float) -> None:
    """Contrastar las dos guías de error y torque por eje, sin recortar datos.

    Para seguimiento se espera ±2°; para recuperación ±0,2°. Los límites
    de torque deben ser ±1,2 y ±0,31 N·m, aunque una solicitud los exceda.
    """
    figura = graficar_seguimientos(comparacion_en_memoria, limite_error=limite_error)
    try:
        for articulacion in range(2):
            error, torque = figura.axes[2 + articulacion], figura.axes[4 + articulacion]
            # Las líneas punteadas se reservan para límites; las señales
            # controladas conservan todos sus valores originales visibles.
            error_guias = [linea for linea in error.lines if linea.get_linestyle() == ":"]
            torque_guias = [linea for linea in torque.lines if linea.get_linestyle() == ":"]
            assert len(error_guias) == len(torque_guias) == 2
            for linea, valor in zip(error_guias, [limite_error, -limite_error]):
                np.testing.assert_array_equal(linea.get_ydata(), [valor, valor])
            for linea, valor in zip(torque_guias, [LIMITES_TORQUE[articulacion], -LIMITES_TORQUE[articulacion]]):
                np.testing.assert_array_equal(linea.get_ydata(), [valor, valor])
            solicitado = next(linea for linea in torque.lines if linea.get_label() == "PD: solicitado")
            assert np.max(np.abs(solicitado.get_ydata())) > LIMITES_TORQUE[articulacion]
    finally:
        plt.close(figura)


def test_graficar_no_integra_muestra_exporta_ni_modifica(
    comparacion_en_memoria: dict, monkeypatch,
) -> None:
    """Impedir integración, show y savefig, y exigir datos intactos al dibujar.

    Copia antes de graficar tiempos, estados, referencia y ambos torques.
    Después del renderizado se exige igualdad exacta, sin archivos ni ventanas.
    """
    originales = []
    for resultado in comparacion_en_memoria.values():
        r = resultado.simulacion
        for campo in (r.t, r.q, r.qd, r.torque_solicitado, r.torque_aplicado, resultado.q_d):
            originales.append((campo, campo.copy()))

    def impedir_accion(*args, **kwargs) -> None:
        """Fallar si dibujar reintegra, abre ventanas o exporta archivos."""
        # Los resultados en RAM bastan para generar los seis paneles.
        pytest.fail("Graficar intentó integrar, mostrar o exportar resultados")

    monkeypatch.setattr("pendulo.simulacion.solve_ivp", impedir_accion)
    monkeypatch.setattr(plt, "show", impedir_accion)
    monkeypatch.setattr(Figure, "savefig", impedir_accion)
    figura = graficar_seguimientos(comparacion_en_memoria)
    try:
        figura.canvas.draw()
        for campo, copia in originales:
            np.testing.assert_array_equal(campo, copia)
        assert all(r.simulacion.evaluaciones == 0 for r in comparacion_en_memoria.values())
    finally:
        plt.close(figura)


def test_rechaza_comparacion_vacia() -> None:
    """Exigir diagnóstico explícito cuando falta todo resultado para graficar."""
    # La referencia común requiere al menos una trayectoria disponible.
    with pytest.raises(ValueError, match="al menos un resultado"):
        graficar_seguimientos({})
