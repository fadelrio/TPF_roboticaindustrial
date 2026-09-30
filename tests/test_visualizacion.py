"""Correspondencia de curvas y fotogramas con estados calculados en memoria."""

import matplotlib

# Las pruebas se ejecutan sin ventanas y sin depender del backend del IDE.
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest

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
