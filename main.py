"""Diagnóstico y escenarios de movimiento libre con gráficos y animación 2D."""

import argparse

import numpy as np
import matplotlib.pyplot as plt

from pendulo import verificar_entorno
from pendulo.dinamica import Dinamica
from pendulo.modelo import (crear_robot, crear_robot_actuado,
                            posiciones_geometricas, posiciones_toolbox)
from pendulo.parametros import ACTUADORES, BARRAS, Friccion
from pendulo.simulacion import simular_libre
from pendulo.visualizacion import crear_animacion, graficar_resultado


# Estos escenarios conservan las condiciones reproducibles de la etapa 4.
# No aplican torque; el modelo y la fricción se seleccionan por separado.
ESCENARIOS_LIBRES = {
    "colgante": {"q0": (-np.pi / 2, 0.0), "qd0": (0.0, 0.0), "duracion": 5.0},
    "invertido": {"q0": (np.pi / 2 + np.deg2rad(1), 0.0), "qd0": (0.0, 0.0), "duracion": 2.0},
    "oscilacion": {"q0": (-np.pi / 2 + 0.3, -0.2), "qd0": (0.4, -0.1), "duracion": 5.0},
}


def main() -> None:
    """Diagnosticar etapas previas, simular un caso y mostrar sus resultados.

    ``--caso`` elige colgante, invertido u oscilacion (por defecto). La opción
    ``--sin-graficos`` ejecuta las cuentas y el resumen en consola, sin crear
    figuras ni esperar ventanas. La ejecución normal muestra gráficos y
    animación desde los resultados en memoria, sin exportar archivos.
    ``--modelo actuado`` (por defecto) incluye montaje, rotores y fricción
    nominal; ``--modelo barras`` conserva el caso ideal de las etapas previas.
    ``--friccion`` permite elegir escala 0, 0.5, 1 o 2 explícitamente.
    """
    # Las opciones seleccionan escenarios concretos y permiten ejecutar el
    # mismo programa en el IDE o en verificaciones sin interfaz gráfica.
    parser = argparse.ArgumentParser(description="Simulación del doble péndulo 2R")
    parser.add_argument("--caso", choices=ESCENARIOS_LIBRES, default="oscilacion")
    parser.add_argument("--modelo", choices=["barras", "actuado"], default="actuado")
    parser.add_argument("--friccion", type=float, choices=[0.0, 0.5, 1.0, 2.0],
                        help="Escala: por defecto 1 en actuado y 0 en barras")
    parser.add_argument("--sin-graficos", action="store_true", help="Solo cuentas y consola")
    opciones = parser.parse_args()
    # Conservar el diagnóstico inicial permite comprobar el entorno usado.
    resultado = verificar_entorno()
    print("Etapa 1 — Diagnóstico del entorno")
    for nombre, instalada in resultado["versiones"].items():
        print(f"{nombre}: {instalada}")

    # Mostrar magnitudes explícitas permite contrastar la ejecución con las
    # cuentas analíticas documentadas en el README.
    print("Robot auxiliar: barra uniforme de 1 m y 1 kg, q=0 rad")
    print(f"Extremo [m]: {resultado['posicion']}")
    print(f"Inercia articular [kg·m²]: {resultado['inercia']}")
    print(f"Gravedad [N·m]: {resultado['gravedad']}")
    print(f"Torque estático por RNE [N·m]: {resultado['torque_estatico']}")

    # Las propiedades centrales de cada barra se muestran con su referencia.
    print("\nEtapa 2 — Modelo mecánico y cinemática")
    robot = crear_robot()
    for indice, barra in enumerate(BARRAS, start=1):
        print(f"Barra {indice}: masa [kg] = {barra.masa:.12g}")
        print(f"Centro de masa en terna DH [m]: {barra.centro_masa}")
        print(f"Tensor central [kg·m²]:\n{barra.inercia}")

    # Los cuatro casos permiten revisar signos, ángulo relativo y plegado.
    configuraciones = {
        "Horizontal": (0.0, 0.0),
        "Colgante": (-np.pi / 2.0, 0.0),
        "Invertida": (np.pi / 2.0, 0.0),
        "Plegada": (0.0, np.pi),
    }
    longitudes = tuple(barra.longitud for barra in BARRAS)
    for nombre, q in configuraciones.items():
        geometria = posiciones_geometricas(q, longitudes)
        toolbox = posiciones_toolbox(robot, q)
        diferencia = np.max(np.abs(toolbox - geometria))
        print(f"{nombre}: q [rad] = {q}")
        print(f"  Geometría, codo/extremo [m]:\n{geometria[1:]}")
        print(f"  Toolbox, codo/extremo [m]:\n{toolbox[1:]}")
        print(f"  Diferencia máxima [m]: {diferencia:.3e}")

    # Derivar una vez para este modelo; las llamadas siguientes solo evalúan
    # funciones numéricas compiladas desde las expresiones de SymPy.
    print("\nEtapa 3 — Dinámica propia y contraste")
    dinamica = Dinamica(robot)
    print(f"M simbólica [kg·m²], coeficientes redondeados:\n{dinamica.M_simbolica.evalf(8)}")
    print(f"C simbólica [kg·m²/s], coeficientes redondeados:\n{dinamica.C_simbolica.evalf(8)}")
    print(f"G simbólica [N·m], coeficientes redondeados:\n{dinamica.G_simbolica.evalf(8)}")
    for nombre, q in configuraciones.items():
        print(f"{nombre}: sostén propio [N·m] = {dinamica.G(q)}; "
              f"Toolbox [N·m] = {robot.gravload(q)}; U [J] = {dinamica.potencial(q):.9g}")

    # Un estado con ambas juntas en movimiento comprueba el término C·qd y
    # la inversa completa, sin exigir que las matrices C sean idénticas.
    q = np.array([0.4, -0.7])
    v = np.array([1.2, -0.8])
    a = np.array([2.0, -1.0])
    print(f"Estado de contraste: q [rad]={q}, qd [rad/s]={v}, qdd [rad/s²]={a}")
    print(f"M propia [kg·m²]:\n{dinamica.M(q)}")
    print(f"C·qd propio [N·m]: {dinamica.C(q, v) @ v}")
    print(f"G propio [N·m]: {dinamica.G(q)}")
    propio, referencia = dinamica.inversa(q, v, a), robot.rne(q, v, a)
    print(f"Torque inverso propio/Toolbox [N·m]: {propio} / {referencia}")
    print(f"Diferencia máxima de inversa [N·m]: {np.max(np.abs(propio - referencia)):.3e}")

    # Esta cabecera mantiene explícita la relación con la integración libre
    # de la etapa 4. El modelo ampliado se deriva solo si fue seleccionado.
    print("\nEtapa 4 — Movimiento libre e integración")
    print("\nEtapa 5 — Actuadores, montaje y rozamiento")
    if opciones.modelo == "actuado":
        robot = crear_robot_actuado()
        dinamica = Dinamica(robot)
        for indice, (eslabon, actuador) in enumerate(zip(robot.links, ACTUADORES), start=1):
            print(f"Eslabón {indice}: masa [kg]={eslabon.m:.12g}; "
                  f"centro DH [m]={eslabon.r}")
            print(f"Tensor central [kg·m²]:\n{eslabon.I}")
            print(f"Actuador: {actuador.nombre}; N≈{actuador.relacion:g}; "
                  f"N²Jm [kg·m²]={actuador.inercia_reflejada:.12g}; "
                  f"límite [N·m]={actuador.limite_torque}")
            # La selección se contrasta a la velocidad articular prevista,
            # sin atribuir al seguimiento una verificación que aún no existe.
            rpm = 3 * actuador.relacion * 60 / (2 * np.pi)
            print(f"A 3 rad/s: entrada [rpm]={rpm:.9g}; "
                  f"potencia al límite [W]={3 * actuador.limite_torque:.9g}")
        print(f"Gravedad máxima por eje [N·m]: {dinamica.G([0, 0])}")
        print(f"Contraste M con Toolbox en q=(0,0) [kg·m²]: "
              f"{np.max(np.abs(dinamica.M([0, 0]) - robot.inertia([0, 0]))):.3e}")
    escala = opciones.friccion
    if escala is None:
        escala = 1.0 if opciones.modelo == "actuado" else 0.0
    friccion = Friccion(escala=escala)
    print(f"Modelo seleccionado: {opciones.modelo}; escala de fricción: {escala}")
    print(f"Fricción a 3 rad/s por eje [N·m]: {friccion.torque([3, 3])}")

    # Las expresiones compiladas alimentan una única planta con registros
    # de torque y fricción, conservando los estados sin recortes artificiales.
    caso = ESCENARIOS_LIBRES[opciones.caso]
    libre = simular_libre(dinamica, **caso, friccion=friccion)
    print(f"Caso: {opciones.caso}; q0 [rad]={caso['q0']}; qd0 [rad/s]={caso['qd0']}")
    print(f"Duración [s]: {libre.t[-1]}; muestras: {len(libre.t)}; evaluaciones: {libre.evaluaciones}")
    print(f"q final [rad]: {libre.q[-1]}; qd final [rad/s]: {libre.qd[-1]}")
    print(f"E inicial/final [J]: {libre.energia[0]:.12g} / {libre.energia[-1]:.12g}")
    print(f"Variación máxima de E [J]: {np.max(np.abs(libre.energia - libre.energia[0])):.9g}")
    print(f"Máximo torque solicitado/aplicado [N·m]: "
          f"{np.max(np.abs(libre.torque_solicitado), axis=0)} / "
          f"{np.max(np.abs(libre.torque_aplicado), axis=0)}")
    print(f"Máximo rozamiento [N·m]: {np.max(np.abs(libre.rozamiento), axis=0)}")
    if not opciones.sin_graficos:
        # Mantener ambos objetos locales vivos durante show evita que la
        # animación sea recolectada antes de reproducirse.
        nombre = f"{opciones.caso} — {opciones.modelo}, fricción ×{escala:g}"
        figura_graficos = graficar_resultado(libre, nombre)
        figura_animacion, animacion = crear_animacion(libre, nombre, longitudes)
        plt.show()


if __name__ == "__main__":
    main()
