"""Gráficos y animación 2D de resultados ya calculados, sin exportaciones."""

from collections.abc import Callable
from functools import partial

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.text import Text
from matplotlib.widgets import Button

from .modelo import posiciones_geometricas
from .parametros import LIMITES_TORQUE
from .simulacion import ResultadoSeguimiento, ResultadoSimulacion


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


def graficar_seguimientos(
    resultados: dict[str, ResultadoSeguimiento],
    nombre: str = "Control continuo",
    limite_error: float = 2.0,
) -> Figure:
    """Crear comparación 3×2 de posiciones, errores y torques ya calculados.

    Cada columna corresponde a una articulación. Las filas muestran q real
    y deseada en rad, error deseado menos real en grados y torque solicitado
    y aplicado en N·m. Usa los tiempos originales de cada resultado, sin
    remuestreo. Los resultados deben corresponder a una referencia común,
    dibujada una sola vez desde el primero. ``limite_error`` se expresa en
    grados: 2 para seguimiento nominal o 0,2 para observar recuperación.
    Con tres o más resultados usa una leyenda común fuera de los paneles
    para conservar visibles las curvas durante comparaciones y barridos.
    Devuelve una figura sin mostrarla, exportarla ni reintegrar los estados.
    """
    if not resultados:
        raise ValueError("La comparación debe incluir al menos un resultado.")
    if not np.isfinite(limite_error) or limite_error <= 0:
        raise ValueError("El límite de error debe ser positivo y finito.")
    muchos = len(resultados) >= 3
    figura, ejes = plt.subplots(3, 2, sharex=True, figsize=(14, 9) if muchos else (11, 9))
    figura.suptitle(nombre)
    primero = next(iter(resultados.values()))
    colores = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    for articulacion in range(2):
        # Una referencia negra común evita repetir curvas idénticas y permite
        # distinguir los resultados reales de cada instancia del controlador.
        ejes[0, articulacion].plot(
            primero.simulacion.t, primero.q_d[:, articulacion],
            color="black", linestyle="--", label="Referencia")
        ejes[0, articulacion].set_title(f"Articulación {articulacion + 1}")
        ejes[0, articulacion].set_ylabel("Ángulo [rad]")
        ejes[1, articulacion].set_ylabel("Error [°]")
        ejes[2, articulacion].set_ylabel("Torque [N·m]")
        ejes[2, articulacion].set_xlabel("Tiempo [s]")
        # Las guías horizontales representan criterios y límites físicos;
        # no recortan señales que excedan esas magnitudes.
        ejes[1, articulacion].axhline(
            limite_error, color="gray", linestyle=":", label=f"±{limite_error:g}°")
        ejes[1, articulacion].axhline(-limite_error, color="gray", linestyle=":")
        ejes[2, articulacion].axhline(
            LIMITES_TORQUE[articulacion], color="gray", linestyle=":", label="Límite físico")
        ejes[2, articulacion].axhline(
            -LIMITES_TORQUE[articulacion], color="gray", linestyle=":")
    for indice, (identificador, resultado) in enumerate(resultados.items()):
        r = resultado.simulacion
        color = colores[indice % len(colores)]
        error_grados = np.rad2deg(resultado.error)
        for articulacion in range(2):
            # El mismo color sigue al controlador en estados, error y ambos
            # torques. La línea discontinua identifica el torque aplicado.
            ejes[0, articulacion].plot(
                r.t, r.q[:, articulacion], color=color, label=identificador)
            ejes[1, articulacion].plot(
                r.t, error_grados[:, articulacion], color=color, label=identificador)
            ejes[2, articulacion].plot(
                r.t, r.torque_solicitado[:, articulacion], color=color,
                label=f"{identificador}: solicitado")
            ejes[2, articulacion].plot(
                r.t, r.torque_aplicado[:, articulacion], color=color, linestyle="--",
                label=f"{identificador}: aplicado")
    # Mostrar unidades, grilla y leyendas en cada panel mantiene legibles las
    # comparaciones aun cuando las señales de dos controladores se aproximen.
    for eje in ejes.flat:
        eje.grid(True, alpha=0.3)
        if not muchos:
            eje.legend(loc="best")
    if muchos:
        # Separar identificadores y estilos evita repetir ocho o más entradas
        # de torque dentro de cada panel, tapando los picos de las señales.
        leyenda = [Line2D([], [], color=colores[i % len(colores)], label=nombre)
                   for i, nombre in enumerate(resultados)]
        leyenda.extend([
            Line2D([], [], color="black", linestyle="--", label="Referencia articular"),
            Line2D([], [], color="black", linestyle="-", label="Torque solicitado"),
            Line2D([], [], color="black", linestyle="--", label="Torque aplicado"),
            Line2D([], [], color="gray", linestyle=":", label="Guías de límites"),
        ])
        figura.legend(handles=leyenda, loc="upper right", fontsize=9,
                      bbox_to_anchor=(0.99, 0.94))
        figura.tight_layout(rect=(0.0, 0.0, 0.76, 0.97))
    else:
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
    actualizar = partial(actualizar_animacion, resultado=resultado, linea=linea,
                         texto=texto, longitudes=longitudes)
    actualizar(0)
    return figura, _agregar_reproductor(figura, actualizar, indices, periodo)


def crear_animacion_comparada(
    resultados: dict[str, ResultadoSeguimiento],
    nombre: str = "Comparación",
    longitudes: tuple[float, float] = (0.20, 0.20),
    periodo: float = 0.020,
) -> tuple[Figure, FuncAnimation]:
    """Animar simultáneamente resultados con grilla temporal exactamente común.

    Cada identificador del diccionario tiene una polilínea XY de base, codo
    y extremo, con el mismo color usado por ``graficar_seguimientos``. Todos
    dibujan el mismo índice bajo un reloj común. No remuestrea ni integra;
    rechaza grillas distintas, incluso si comparten el último tiempo.
    ``longitudes`` está en m y ``periodo`` en s. Incluye el último fotograma
    y mantiene allí la imagen. El botón reinicia desde t=0 usando los datos
    en memoria, durante o después de la reproducción. Retorna la figura y
    primera animación; ``figura._reproduccion`` conserva botón y vigente.
    """
    if not resultados:
        raise ValueError("La comparación debe incluir al menos un resultado.")
    if not np.isfinite(periodo) or periodo <= 0:
        raise ValueError("El período de animación debe ser positivo y finito.")
    primero = next(iter(resultados.values())).simulacion
    for resultado in resultados.values():
        # Una igualdad exacta impide dibujar como simultáneos estados que
        # corresponden a tiempos físicos distintos, sin interpolación oculta.
        if not np.array_equal(resultado.simulacion.t, primero.t):
            raise ValueError("Las animaciones comparadas requieren la misma grilla de tiempos.")
    figura, eje = plt.subplots(figsize=(6, 6))
    alcance = sum(longitudes)
    eje.set(xlim=(-1.1 * alcance, 1.1 * alcance), ylim=(-1.1 * alcance, 1.1 * alcance),
            xlabel="X [m]", ylabel="Y [m]", title=nombre)
    eje.set_aspect("equal")
    eje.grid(True, alpha=0.3)
    colores = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    lineas = []
    for indice, identificador in enumerate(resultados):
        # Mantener el orden del diccionario conserva la identidad visual
        # de cada instancia entre gráficos y reproducción simultánea.
        linea, = eje.plot([], [], "o-", linewidth=2,
                          color=colores[indice % len(colores)], label=identificador)
        lineas.append(linea)
    eje.legend(loc="upper right")
    texto = eje.text(0.04, 0.94, "", transform=eje.transAxes)
    objetivos = np.arange(0.0, primero.t[-1], periodo)
    indices = np.unique(np.append(np.searchsorted(primero.t, objetivos), len(primero.t) - 1))

    def actualizar(indice: int) -> tuple:
        """Dibujar todos los robots en la misma muestra y actualizar un reloj.

        Cada polilínea usa q[indice] de su propio resultado; los tiempos
        son idénticos por contrato. Retorna los artistas actualizados.
        """
        for linea, resultado in zip(lineas, resultados.values()):
            # La cinemática únicamente transforma los ángulos ya calculados;
            # no se vuelve a resolver la dinámica al avanzar o reiniciar.
            puntos = posiciones_geometricas(resultado.simulacion.q[indice], longitudes)
            linea.set_data(puntos[:, 0], puntos[:, 1])
        texto.set_text(f"t = {primero.t[indice]:.3f} s")
        return (*lineas, texto)

    actualizar(0)
    return figura, _agregar_reproductor(figura, actualizar, indices, periodo)


def _agregar_reproductor(
    figura: Figure, actualizar: Callable[[int], tuple], indices: np.ndarray, periodo: float,
) -> FuncAnimation:
    """Conectar el temporizador y botón a artistas existentes de una figura.

    ``actualizar(indice)`` dibuja los datos originales y retorna sus artistas.
    ``indices`` selecciona las muestras y ``periodo`` está en s. La figura
    retiene botón y animación vigente; retorna la primera para conservar
    las interfaces de animación simple y comparada.
    """

    def nueva_animacion() -> FuncAnimation:
        """Crear un reproductor desde el primer índice sobre los artistas existentes."""
        # Cada FuncAnimation recibe una nueva secuencia de los mismos índices;
        # no cambia los estados, la grilla ni la geometría de los resultados.
        return FuncAnimation(figura, actualizar, frames=indices,
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
        actualizar(0)
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
    return reproduccion["animacion"]
