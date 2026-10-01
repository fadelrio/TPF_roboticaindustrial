"""Reproducción simultánea de datos en memoria, sin nueva integración."""

import matplotlib

# Agg permite verificar fotogramas y eventos de botón sin abrir ventanas.
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.backend_bases import MouseEvent
from matplotlib.figure import Figure
import numpy as np
import pytest
from unittest.mock import patch

from pendulo.control import ControladorPD
from pendulo.modelo import crear_robot, posiciones_toolbox
from pendulo.simulacion import ResultadoSeguimiento, ResultadoSimulacion
from pendulo.trayectorias import TrayectoriaQuintica
from pendulo.visualizacion import crear_animacion_comparada, graficar_seguimientos


@pytest.fixture
def comparacion_animada() -> dict:
    """Crear tres estados distintos sobre la grilla común 0..105 ms de 1 ms.

    Las posiciones varían linealmente y sus velocidades se corresponden
    con esas pendientes. Referencia común, energías y torques sintéticos
    evitan integrar: estos registros sirven para comprobar dibujo y tiempos,
    sin atribuirles comportamiento físico de seguimiento.
    """
    tiempos = np.arange(106, dtype=float) / 1000
    trayectoria = TrayectoriaQuintica([0.0, 0.0], [0.1, 0.2])
    referencias = np.array([trayectoria.evaluar(t) for t in tiempos])
    configuraciones = [([0.0, 0.0], [0.6, -0.4]),
                       ([-0.8, 0.4], [0.3, 0.5]),
                       ([1.2, -1.0], [-0.4, 0.2])]
    nombres = ["PD continuo", "PD+G continuo", "PD+G digital 1 ms"]
    resultados = {}
    for indice, (nombre, (q0, v)) in enumerate(zip(nombres, configuraciones)):
        # Usar estados deliberadamente separados hace visible un intercambio
        # de resultados, aunque todos compartan el reloj de reproducción.
        q = np.array(q0) + tiempos[:, None] * np.array(v)
        simulacion = ResultadoSimulacion(
            tiempos.copy(), q, np.tile(v, (len(tiempos), 1)),
            np.zeros(len(tiempos)), np.zeros(len(tiempos)), 0,
            np.zeros_like(q), np.zeros_like(q), np.zeros_like(q))
        resultados[nombre] = ResultadoSeguimiento(
            simulacion, trayectoria, ControladorPD(nombre, gravedad=indice > 0),
            referencias[:, 0].copy(), referencias[:, 1].copy(),
            referencias[:, 2].copy(), np.zeros_like(q))
    return resultados


def pulsar_boton_comparado(figura: Figure) -> None:
    """Emitir un clic de canvas en el centro del botón de reproducción."""
    boton = figura._reproduccion["boton"]
    x, y = boton.ax.transAxes.transform((0.5, 0.5))
    # El par de eventos recorre la conexión real del widget y su callback.
    for nombre in ("button_press_event", "button_release_event"):
        evento = MouseEvent(nombre, figura.canvas, x, y, button=1)
        figura.canvas.callbacks.process(nombre, evento)


def verificar_cuadro_comparado(figura: Figure, resultados: dict, robot, indice: int) -> None:
    """Contrastar todas las geometrías del mismo índice con Toolbox a 1e-12 m.

    La cinemática DH aporta un contraste independiente de las expresiones
    geométricas utilizadas al dibujar. Verifica además el reloj común exacto.
    """
    eje = figura.axes[0]
    assert len(eje.lines) == len(resultados)
    for linea, (nombre, resultado) in zip(eje.lines, resultados.items()):
        # Ningún controlador debe dibujar el estado de otra instancia ni
        # anticiparse un índice respecto de las demás polilíneas.
        assert linea.get_label() == nombre
        esperado = posiciones_toolbox(robot, resultado.simulacion.q[indice])[:, :2]
        np.testing.assert_allclose(np.column_stack(linea.get_data()), esperado,
                                   rtol=0, atol=1e-12)
    tiempo = next(iter(resultados.values())).simulacion.t[indice]
    assert len(eje.texts) == 1
    assert eje.texts[0].get_text() == f"t = {tiempo:.3f} s"


@pytest.mark.parametrize(
    "periodo,indices_esperados",
    [(0.020, [0, 20, 40, 60, 80, 100, 105]),
     (0.030, [0, 30, 60, 90, 105]), (0.150, [0, 105])],
)
def test_fotogramas_sincronizados_y_colores_de_graficos(
    comparacion_animada: dict, periodo: float, indices_esperados: list,
) -> None:
    """Verificar todos los fotogramas, reloj y color coherente por instancia.

    Compara los tres robots contra DH a 1e-12 m en cada cuadro, incluye el
    final parcial de 105 ms y exige detener allí el temporizador. Los colores
    coinciden con los gráficos 3×2 y las leyendas conservan sus identificadores.
    """
    robot = crear_robot()
    figura, animacion = crear_animacion_comparada(comparacion_animada, periodo=periodo)
    graficos = graficar_seguimientos(comparacion_animada)
    try:
        figura.canvas.draw()
        verificar_cuadro_comparado(figura, comparacion_animada, robot, 0)
        indices = list(animacion.new_frame_seq())
        np.testing.assert_array_equal(indices, indices_esperados)
        assert animacion.event_source.interval == int(1000 * periodo)
        assert len(figura.axes) == 2
        assert figura.axes[0].get_xlabel() == "X [m]"
        assert figura.axes[0].get_ylabel() == "Y [m]"
        assert figura.axes[0].get_aspect() == 1.0
        assert [texto.get_text() for texto in figura.axes[0].get_legend().get_texts()] == list(comparacion_animada)
        for linea in figura.axes[0].lines:
            curva = next(curva for curva in graficos.axes[0].lines
                         if curva.get_label() == linea.get_label())
            assert linea.get_color() == curva.get_color()
        assert len({linea.get_color() for linea in figura.axes[0].lines}) == 3
        # Avanzar _step reproduce el callback del timer sin esperas de pared.
        for indice in indices:
            assert animacion._step()
            verificar_cuadro_comparado(figura, comparacion_animada, robot, indice)
        assert not animacion._step()
        assert animacion.event_source is None
        assert figura.axes[0].texts[0].get_text() == "t = 0.105 s"
        figura.canvas.draw()
        assert np.asarray(figura.canvas.buffer_rgba()).shape[2] == 4
        print(f"Comparación animada: tres robots; período={periodo:g} s; "
              f"índices={indices}; geometrías DH a 1e-12 m; final=0,105 s.")
    finally:
        if animacion.event_source is not None:
            animacion.pause()
        plt.close(figura)
        plt.close(graficos)


@pytest.mark.parametrize("momento", ["durante", "despues"])
def test_reiniciar_tres_robots_dos_veces_sin_integrar_ni_mutar(
    comparacion_animada: dict, monkeypatch, momento: str,
) -> None:
    """Reiniciar durante/después y completar dos repeticiones sincronizadas.

    Clics reales de canvas deben detener el timer anterior cuando existe,
    crear otro reproductor y volver a t=0. Bloquea integración, show y
    exportación; exige todos los arrays originales y evaluaciones intactos.
    """
    originales = []
    for resultado in comparacion_animada.values():
        r = resultado.simulacion
        for campo in (r.t, r.q, r.qd, r.cinetica, r.potencial, r.torque_solicitado,
                      r.torque_aplicado, r.rozamiento, resultado.q_d, resultado.qd_d,
                      resultado.qdd_d, resultado.torque_referencia):
            originales.append((campo, campo.copy()))

    def impedir_accion(*args, **kwargs) -> None:
        """Fallar si reproducir intenta integrar, mostrar o guardar resultados."""
        # Los estados y las referencias ya existen en memoria.
        pytest.fail("La animación comparada intentó integrar, mostrar o exportar")

    monkeypatch.setattr("pendulo.simulacion.solve_ivp", impedir_accion)
    monkeypatch.setattr(plt, "show", impedir_accion)
    monkeypatch.setattr(Figure, "savefig", impedir_accion)
    figura, primera = crear_animacion_comparada(comparacion_animada)
    robot = crear_robot()
    try:
        figura.canvas.draw()
        assert figura._reproduccion["animacion"] is primera
        assert figura._reproduccion["boton"].label.get_text() == "Volver a reproducir"
        indices = list(primera.new_frame_seq())
        artistas = tuple(figura.axes[0].lines) + tuple(figura.axes[0].texts)
        if momento == "durante":
            assert primera._step() and primera._step()
            timer = primera.event_source
            with patch.object(timer, "stop", wraps=timer.stop) as detener:
                pulsar_boton_comparado(figura)
                detener.assert_called_once()
            assert figura._reproduccion["animacion"].event_source is not timer
        else:
            for _ in indices:
                assert primera._step()
            assert not primera._step()
            assert primera.event_source is None
            pulsar_boton_comparado(figura)
        anterior = primera
        for ciclo in range(2):
            actual = figura._reproduccion["animacion"]
            assert actual is not anterior
            # Reiniciar conserva los artistas, datos e índices originales;
            # únicamente cambia la instancia que controla el temporizador.
            assert tuple(figura.axes[0].lines) + tuple(figura.axes[0].texts) == artistas
            verificar_cuadro_comparado(figura, comparacion_animada, robot, 0)
            np.testing.assert_array_equal(list(actual.new_frame_seq()), indices)
            for indice in indices:
                assert actual._step()
                verificar_cuadro_comparado(figura, comparacion_animada, robot, indice)
            assert not actual._step()
            assert figura.axes[0].texts[0].get_text() == "t = 0.105 s"
            anterior = actual
            if ciclo == 0:
                pulsar_boton_comparado(figura)
        for campo, original in originales:
            np.testing.assert_array_equal(campo, original)
        assert all(r.simulacion.evaluaciones == 0 for r in comparacion_animada.values())
        print(f"Reinicio {momento}: dos repeticiones de tres robots, sin integración "
              "ni mutación; artistas originales conservados.")
    finally:
        actual = figura._reproduccion["animacion"]
        if actual.event_source is not None:
            actual.pause()
        plt.close(figura)


@pytest.mark.parametrize("diferencia", ["interior", "final", "longitud"])
def test_rechaza_grillas_distintas(comparacion_animada: dict, diferencia: str) -> None:
    """Exigir ValueError para tiempos interiores, horizonte o longitud distintos.

    Un único resultado cambia: 50 µs en una muestra interior, 1 ms en el
    final o eliminación del último tiempo. No debe interpolar automáticamente.
    """
    segundo = list(comparacion_animada.values())[1].simulacion
    # Conservar los demás registros permite detectar una comparación hecha
    # solo contra la primera simulación o contra el último tiempo.
    if diferencia == "interior":
        segundo.t[50] += 0.00005
    elif diferencia == "final":
        segundo.t[-1] += 0.001
    else:
        segundo.t = segundo.t[:-1]
    with pytest.raises(ValueError, match="misma grilla"):
        crear_animacion_comparada(comparacion_animada)


@pytest.mark.parametrize("periodo", [0.0, -0.01, np.nan, np.inf])
def test_rechaza_periodo_invalido(comparacion_animada: dict, periodo: float) -> None:
    """Exigir un período positivo y finito para seleccionar cuadros y timer."""
    # Rechazar antes de crear la figura evita reproductores incompletos.
    with pytest.raises(ValueError, match="positivo y finito"):
        crear_animacion_comparada(comparacion_animada, periodo=periodo)


def test_rechaza_comparacion_animada_vacia() -> None:
    """Exigir al menos un resultado para fijar el reloj de reproducción."""
    # Sin resultados no existen grilla ni estados para el primer fotograma.
    with pytest.raises(ValueError, match="al menos un resultado"):
        crear_animacion_comparada({})
