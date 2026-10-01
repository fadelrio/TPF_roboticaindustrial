"""Gráficos y animación 2D de resultados ya calculados, sin exportaciones."""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.text import Text
from matplotlib.widgets import Button

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
    """Crear animación 2D con botón para volver a reproducir los mismos datos.

    ``periodo`` está en s y vale 20 ms (50 fotogramas/s nominales) por defecto;
    se selecciona la primera muestra disponible para cada tiempo de reproducción
    y se incluye el final. Las longitudes están en m. La salida acordada de
    1 ms permite seleccionar cuadros cada 20 ms sin reintegrar. El temporizador
    gráfico depende del backend y no garantiza reproducción en tiempo real.
    Retorna la figura y la primera animación. La figura conserva el botón y
    la animación vigente en su registro privado ``_reproduccion``; pulsar el
    botón sustituye el reproductor y vuelve a t=0 sin integrar nuevamente.
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

    def nueva_animacion() -> FuncAnimation:
        """Crear un reproductor desde el primer índice sobre los artistas existentes."""
        # Cada FuncAnimation recibe una nueva secuencia de los mismos índices;
        # no cambia los estados, la grilla ni la geometría de los resultados.
        return FuncAnimation(figura, actualizar_animacion, frames=indices,
                             fargs=(resultado, linea, texto, longitudes),
                             interval=1000 * periodo, repeat=False, blit=False,
                             cache_frame_data=False)

    reproduccion = {"animacion": nueva_animacion()}

    def reiniciar(evento) -> None:
        """Detener el reproductor anterior y comenzar otra reproducción desde t=0.

        ``evento`` es el evento de ratón recibido por el botón de Matplotlib.
        Al terminar una reproducción, event_source puede ser None; en ese
        caso solo se crea el nuevo temporizador y se dibuja el estado inicial.
        """
        anterior = reproduccion["animacion"]
        # pause detiene el temporizador antes de sustituirlo. En el final
        # natural Matplotlib ya lo detuvo y eliminó su referencia.
        if anterior.event_source is not None:
            anterior.pause()
        reproduccion["animacion"] = nueva_animacion()
        actualizar_animacion(0, resultado, linea, texto, longitudes)
        # Dibujar ahora inicializa el nuevo reproductor antes de otro clic,
        # sin dejar su arranque pendiente de un redraw futuro.
        figura.canvas.draw()

    # Reservar una franja inferior antes de agregar el eje del botón evita
    # que tight_layout superponga el control con la etiqueta X del gráfico.
    figura.tight_layout(rect=(0.0, 0.13, 1.0, 1.0))
    eje_boton = figura.add_axes((0.20, 0.025, 0.60, 0.065))
    boton = Button(eje_boton, "Volver a reproducir")
    boton.on_clicked(reiniciar)
    reproduccion["boton"] = boton
    # Los widgets y los reproductores necesitan referencias persistentes para
    # recibir eventos después de que esta función haya retornado.
    figura._reproduccion = reproduccion
    return figura, reproduccion["animacion"]
