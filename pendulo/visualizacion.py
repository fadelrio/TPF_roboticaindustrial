"""Gráficos y animación 2D de resultados ya calculados, sin exportaciones."""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.text import Text

from .modelo import posiciones_geometricas
from .simulacion import ResultadoSimulacion


def graficar_resultado(resultado: ResultadoSimulacion, nombre: str = "Movimiento libre") -> Figure:
    """Crear figura con q, qd, K/U/E y variación de E frente al tiempo.

    Cada curva usa la grilla del resultado, con ejes y unidades SI. Retorna
    la figura sin llamar a show ni guardar archivos; el punto de entrada
    decide cuándo mostrarla junto con la animación.
    """
    figura, ejes = plt.subplots(4, 1, sharex=True, figsize=(8, 9))
    figura.suptitle(nombre)
    # Las posiciones se muestran tal como fueron integradas, sin envolverlas.
    for eje in range(2):
        ejes[0].plot(resultado.t, resultado.q[:, eje], label=f"q{eje + 1}")
        ejes[1].plot(resultado.t, resultado.qd[:, eje], label=f"qd{eje + 1}")
    ejes[0].set_ylabel("Ángulo [rad]")
    ejes[1].set_ylabel("Velocidad [rad/s]")
    ejes[2].plot(resultado.t, resultado.cinetica, label="K")
    ejes[2].plot(resultado.t, resultado.potencial, label="U")
    ejes[2].plot(resultado.t, resultado.energia, label="E = K + U")
    ejes[2].set_ylabel("Energía [J]")
    ejes[3].plot(resultado.t, resultado.energia - resultado.energia[0], label="E − E(0)")
    ejes[3].set_ylabel("Variación de E [J]")
    ejes[3].set_xlabel("Tiempo [s]")
    # Una grilla y leyendas por panel ayudan a relacionar estados y energía.
    for eje in ejes:
        eje.grid(True, alpha=0.3)
        eje.legend(loc="upper right")
    figura.tight_layout()
    return figura


def actualizar_animacion(
    indice: int,
    resultado: ResultadoSimulacion,
    linea: Line2D,
    texto: Text,
    longitudes: tuple[float, float],
) -> tuple:
    """Dibujar la muestra indicada y su tiempo físico, sin integrar nuevamente.

    ``indice`` selecciona una fila de q y t. Actualiza la polilínea base,
    codo y extremo en XY [m] y el texto temporal en s. Retorna los dos
    artistas modificados para que FuncAnimation pueda redibujarlos.
    """
    # La geometría usa exactamente el estado almacenado en esa muestra.
    puntos = posiciones_geometricas(resultado.q[indice], longitudes)
    linea.set_data(puntos[:, 0], puntos[:, 1])
    texto.set_text(f"t = {resultado.t[indice]:.3f} s")
    return linea, texto


def crear_animacion(
    resultado: ResultadoSimulacion,
    nombre: str = "Movimiento libre",
    longitudes: tuple[float, float] = (0.20, 0.20),
    periodo: float = 0.020,
) -> tuple[Figure, FuncAnimation]:
    """Crear animación 2D y retornar figura y objeto que debe mantenerse vivo.

    ``periodo`` está en s y vale 20 ms (50 fotogramas/s nominales) por defecto;
    se selecciona la primera muestra disponible para cada tiempo de reproducción
    y se incluye el final. Las longitudes están en m. La salida acordada de
    1 ms permite seleccionar cuadros cada 20 ms sin reintegrar. El temporizador
    gráfico depende del backend y no garantiza reproducción en tiempo real.
    """
    if periodo <= 0:
        raise ValueError("El período de animación debe ser positivo")
    figura, eje = plt.subplots(figsize=(6, 6))
    alcance = sum(longitudes)
    eje.set(xlim=(-1.1 * alcance, 1.1 * alcance), ylim=(-1.1 * alcance, 1.1 * alcance),
            xlabel="X [m]", ylabel="Y [m]", title=nombre)
    eje.set_aspect("equal")
    eje.grid(True, alpha=0.3)
    linea, = eje.plot([], [], "o-", linewidth=3)
    texto = eje.text(0.04, 0.94, "", transform=eje.transAxes)
    # Los índices apuntan a los mismos estados que los gráficos. Incluir el
    # último asegura que la animación alcance la muestra final del resultado.
    objetivos = np.arange(0.0, resultado.t[-1], periodo)
    indices = np.unique(np.append(np.searchsorted(resultado.t, objetivos), len(resultado.t) - 1))
    actualizar_animacion(0, resultado, linea, texto, longitudes)
    animacion = FuncAnimation(figura, actualizar_animacion, frames=indices,
                             fargs=(resultado, linea, texto, longitudes),
                             interval=1000 * periodo, repeat=False, blit=False,
                             cache_frame_data=False)
    figura.tight_layout()
    return figura, animacion
