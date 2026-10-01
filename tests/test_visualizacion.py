"""Correspondencia de curvas y fotogramas con estados calculados en memoria."""

import matplotlib

# Las pruebas se ejecutan sin ventanas y sin depender del backend del IDE.
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.backend_bases import MouseEvent
from unittest.mock import patch

from pendulo.dinamica import Dinamica
from pendulo.modelo import crear_robot, posiciones_toolbox
from pendulo.simulacion import simular_libre
from pendulo.visualizacion import crear_animacion, graficar_resultado


@pytest.fixture(scope="module")
def movimiento_grafico() -> tuple:
    """Calcular un recorrido de 0,105 s y conservar su robot como contraste.

    Usa q=(−pi/2+0,3; −0,2), qd=(0,4; −0,1), salida de 1 ms y
    tolerancias nominales. La duración deja un último fotograma parcial.
    """
    robot = crear_robot()
    # La integración se realiza antes de dibujar; las funciones gráficas
    # reciben solamente los resultados ya disponibles.
    r = simular_libre(Dinamica(robot), [-np.pi / 2 + 0.3, -0.2], [0.4, -0.1], 0.105)
    return r, robot


def test_curvas_coinciden_con_resultados(movimiento_grafico: tuple) -> None:
    """Verificar datos exactos de las ocho curvas y renderizar la figura en Agg.

    Se contrasta cada abscisa con t y cada ordenada con q, qd o energía
    correspondiente. No se exporta el lienzo a archivos.
    """
    r, _ = movimiento_grafico
    figura = graficar_resultado(r, "Prueba de correspondencia")
    esperadas = [[r.q[:, 0], r.q[:, 1]], [r.qd[:, 0], r.qd[:, 1]],
                [r.cinetica, r.potencial, r.energia], [r.energia - r.energia[0]]]
    try:
        # Los datos de las curvas deben corresponder a las muestras originales,
        # sin remuestreo ni un segundo cálculo de movimiento.
        assert len(figura.axes) == 4
        for eje, ordenadas in zip(figura.axes, esperadas):
            assert len(eje.lines) == len(ordenadas)
            for linea, y in zip(eje.lines, ordenadas):
                np.testing.assert_array_equal(linea.get_xdata(), r.t)
                np.testing.assert_array_equal(linea.get_ydata(), y)
        figura.canvas.draw()
        assert np.asarray(figura.canvas.buffer_rgba()).shape[2] == 4
    finally:
        plt.close(figura)


def pulsar_reproducir(figura) -> None:
    """Emitir un clic completo en el centro del botón mediante eventos de canvas."""
    boton = figura._reproduccion["boton"]
    x, y = boton.ax.transAxes.transform((0.5, 0.5))
    # Pasar por los eventos de ratón verifica la conexión real del widget,
    # además del funcionamiento del callback al que está asociado.
    for nombre in ("button_press_event", "button_release_event"):
        evento = MouseEvent(nombre, figura.canvas, x, y, button=1)
        figura.canvas.callbacks.process(nombre, evento)


@pytest.mark.parametrize("momento", ["durante", "despues"])
def test_volver_a_reproducir_sin_integrar(
    movimiento_grafico: tuple, monkeypatch, momento: str
) -> None:
    """Reiniciar durante el movimiento o después del final y completar dos ciclos.

    Emite clics reales de canvas. Cada nueva reproducción debe mostrar t=0,
    recorrer los mismos índices y terminar en 0,105 s. Se intercepta solve_ivp
    para impedir reintegraciones y se exige igualdad exacta de los resultados
    antes/después; geometría de cada cuadro a 1e-12 m frente a Toolbox.
    """
    r, robot = movimiento_grafico
    figura, primera = crear_animacion(r, "Prueba de volver a reproducir")
    originales = [campo.copy() for campo in (r.t, r.q, r.qd, r.cinetica, r.potencial)]
    evaluaciones = r.evaluaciones

    def impedir_integracion(*args, **kwargs) -> None:
        """Fallar si la reproducción intenta resolver otra ecuación diferencial."""
        # El resultado ya existe: pulsar el botón solo debe volver a dibujarlo.
        pytest.fail("Volver a reproducir llamó al integrador")

    monkeypatch.setattr("pendulo.simulacion.solve_ivp", impedir_integracion)
    try:
        figura.canvas.draw()
        assert figura._reproduccion["animacion"] is primera
        indices = list(primera.new_frame_seq())
        linea, texto = figura.axes[0].lines[0], figura.axes[0].texts[0]
        # Avanzar solo dos cuadros o completar la primera reproducción
        # prepara las dos condiciones de reinicio especificadas.
        if momento == "durante":
            assert primera._step() and primera._step()
            timer = primera.event_source
            with patch.object(timer, "stop", wraps=timer.stop) as detener:
                pulsar_reproducir(figura)
                detener.assert_called_once()
            assert figura._reproduccion["animacion"].event_source is not timer
        else:
            for _ in indices:
                assert primera._step()
            assert not primera._step()
            assert primera.event_source is None
            pulsar_reproducir(figura)

        # Completar dos ciclos consecutivos comprueba que el botón siga
        # disponible incluso cuando Matplotlib haya descartado su timer.
        anterior = primera
        for ciclo in range(2):
            actual = figura._reproduccion["animacion"]
            assert actual is not anterior
            assert texto.get_text() == "t = 0.000 s"
            np.testing.assert_allclose(
                np.column_stack(linea.get_data()), posiciones_toolbox(robot, r.q[0])[:, :2],
                rtol=0, atol=1e-12)
            np.testing.assert_array_equal(list(actual.new_frame_seq()), indices)
            for indice in indices:
                assert actual._step()
                np.testing.assert_allclose(
                    np.column_stack(linea.get_data()), posiciones_toolbox(robot, r.q[indice])[:, :2],
                    rtol=0, atol=1e-12)
                assert texto.get_text() == f"t = {r.t[indice]:.3f} s"
            assert not actual._step()
            assert texto.get_text() == "t = 0.105 s"
            anterior = actual
            if ciclo == 0:
                pulsar_reproducir(figura)
        for campo, copia in zip((r.t, r.q, r.qd, r.cinetica, r.potencial), originales):
            np.testing.assert_array_equal(campo, copia)
        assert r.evaluaciones == evaluaciones
    finally:
        actual = figura._reproduccion["animacion"]
        if actual.event_source is not None:
            actual.pause()
        plt.close(figura)


def test_fotogramas_tiempo_y_geometria(movimiento_grafico: tuple) -> None:
    """Verificar selección a 20 ms y geometría de todos los fotogramas con DH.

    Para 105 ms se esperan índices 0,20,40,60,80,100,105. Cada cuadro
    usa el estado y tiempo de ese índice, con error geométrico ≤1e-12 m.
    También se comprueba que la reproducción termine y el timer use 20 ms.
    """
    r, robot = movimiento_grafico
    figura, animacion = crear_animacion(r, "Prueba de fotogramas")
    try:
        # El dibujo inicial permite iniciar la animación sin reproducirla ni
        # depender del temporizador de una ventana durante las pruebas.
        figura.canvas.draw()
        indices = list(animacion.new_frame_seq())
        np.testing.assert_array_equal(indices, [0, 20, 40, 60, 80, 100, 105])
        assert animacion.event_source.interval == 20
        linea, texto = figura.axes[0].lines[0], figura.axes[0].texts[0]
        for indice in indices:
            # _step reproduce el avance del temporizador de Matplotlib sin
            # esperar una ventana; así se verifica también el callback conectado.
            assert animacion._step()
            coordenadas = np.column_stack([linea.get_xdata(), linea.get_ydata()])
            np.testing.assert_allclose(coordenadas, posiciones_toolbox(robot, r.q[indice])[:, :2],
                                       rtol=0, atol=1e-12)
            assert texto.get_text() == f"t = {r.t[indice]:.3f} s"
            figura.canvas.draw()
        assert texto.get_text() == "t = 0.105 s"
        assert not animacion._step()
    finally:
        if animacion.event_source is not None:
            animacion.event_source.stop()
        plt.close(figura)
