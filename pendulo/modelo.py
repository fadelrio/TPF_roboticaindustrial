"""Modelo DH y cinemática del manipulador 2R en el plano XY vertical."""

import numpy as np
import roboticstoolbox as rtb

from .parametros import (ACTUADORES, BARRAS, GRAVEDAD, Actuador, Barra,
                        componentes_codo, componer_cuerpos)


def crear_robot(barras: tuple[Barra, Barra] = BARRAS) -> rtb.DHRobot:
    """Construir el 2R mediante DH estándar con las dos barras indicadas.

    Las longitudes, masas, centros de masa y tensores se expresan en SI.
    Ambos ejes giran alrededor de +Z; d=alpha=offset=0. La base y herramienta
    son identidad y la gravedad física apunta hacia −Y. No se incluyen
    actuadores, rotor, fricción, colisiones ni topes articulares.
    """
    # I es central y r se expresa en la terna distal: Toolbox aplica sus
    # traslaciones de referencia durante los cálculos dinámicos posteriores.
    eslabones = [
        rtb.RevoluteDH(
            a=barra.longitud,
            d=0.0,
            alpha=0.0,
            offset=0.0,
            m=barra.masa,
            r=barra.centro_masa,
            I=barra.inercia,
            Jm=0.0,
            G=1.0,
            B=0.0,
            Tc=[0.0, 0.0],
        )
        for barra in barras
    ]
    return rtb.DHRobot(eslabones, gravity=GRAVEDAD, name="Doble péndulo 2R: barras")


def crear_robot_actuado(
    barras: tuple[Barra, Barra] = BARRAS,
    actuadores: tuple[Actuador, Actuador] = ACTUADORES,
) -> rtb.DHRobot:
    """Construir el 2R con montaje transportado e inercia de los dos rotores.

    El motor y reductor del eje 1 quedan fijos a la base: no se suman a
    los cuerpos móviles. El conjunto del eje 2 y su fijación pertenecen al
    primer eslabón, centrados en el codo y detrás de la barra. Jm y G se
    cargan por separado para representar N²Jm una sola vez en la dinámica.
    La fricción suave articular se aplica fuera de Toolbox: aquí B=Tc=0.
    """
    robot = crear_robot(barras)
    conjunto = componer_cuerpos((barras[0], *componentes_codo(barras[0], actuadores[1])))
    primero = robot.links[0]
    # La distribución conjunta se entrega como centro y tensor central;
    # no incluir el segundo motor en el eslabón 2 ni el motor fijo de base.
    primero.m, primero.r, primero.I = conjunto.masa, conjunto.centro_masa, conjunto.inercia
    for eslabon, actuador in zip(robot.links, actuadores):
        eslabon.Jm, eslabon.G = actuador.inercia_rotor, actuador.relacion
    robot.name = "Doble péndulo 2R: actuado"
    return robot


def posiciones_toolbox(robot: rtb.DHRobot, q: np.ndarray) -> np.ndarray:
    """Retornar posiciones XYZ de base, codo y extremo como array (3, 3), en m.

    ``robot`` es uno de los modelos 2R del proyecto y ``q`` contiene los dos
    ángulos en radianes. Incluye explícitamente la terna base en fkine_all.
    No altera el estado almacenado del robot ni los ángulos recibidos.
    """
    # Los orígenes de las tres ternas DH coinciden con los puntos de interés.
    ternas = robot.fkine_all(np.asarray(q, dtype=float), old=False)
    return np.array([terna.t for terna in ternas])


def posiciones_geometricas(
    q: np.ndarray, longitudes: tuple[float, float] = (0.20, 0.20)
) -> np.ndarray:
    """Calcular base, codo y extremo por geometría plana, en metros.

    ``q`` contiene dos ángulos en radianes: q1 desde +X y q2 relativo al
    primer eslabón. ``longitudes`` contiene las dos longitudes en metros.
    Retorna un array (3, 3), con una fila XYZ por punto. No modifica ni
    envuelve los ángulos recibidos; supone entradas de las formas indicadas.
    """
    q1, q2 = np.asarray(q, dtype=float)
    l1, l2 = longitudes

    # La orientación absoluta del segundo eslabón es q1+q2. Ambos puntos
    # móviles permanecen en Z=0; la base se encuentra en el origen.
    codo = np.array([l1 * np.cos(q1), l1 * np.sin(q1), 0.0])
    extremo = codo + [l2 * np.cos(q1 + q2), l2 * np.sin(q1 + q2), 0.0]
    return np.array([np.zeros(3), codo, extremo])
