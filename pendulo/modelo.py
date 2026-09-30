"""Modelo DH y cinemática del manipulador 2R en el plano XY vertical."""

import numpy as np
import roboticstoolbox as rtb

from .parametros import BARRAS, GRAVEDAD, Barra


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


def posiciones_toolbox(robot: rtb.DHRobot, q: np.ndarray) -> np.ndarray:
    """Retornar posiciones XYZ de base, codo y extremo como array (3, 3), en m.

    ``robot`` es el 2R creado por ``crear_robot`` y ``q`` contiene los dos
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
