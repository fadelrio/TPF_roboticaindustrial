"""Diagnóstico de dependencias mediante un robot auxiliar de resultado conocido.

El eslabón auxiliar de 1 m y 1 kg solo comprueba la instalación de Toolbox;
no representa las dimensiones ni las masas del doble péndulo del proyecto.
"""

from importlib import import_module
from importlib.metadata import version
import platform

import numpy as np
import roboticstoolbox as rtb


def verificar_entorno() -> dict:
    """Importar dependencias y calcular operaciones de un robot auxiliar.

    Retorna un diccionario con ``versiones`` y cuatro arrays: ``posicion``
    (3,), en m; ``inercia`` (1, 1), en kg·m²; ``gravedad`` y
    ``torque_estatico`` (1,), en N·m. La articulación se evalúa en q=0 rad,
    sin velocidad ni aceleración. Las comprobaciones analíticas se encuentran
    en las pruebas de la etapa 1.

    Propaga los errores de importación o cálculo para que una instalación
    incompleta no se presente como una comprobación satisfactoria.
    """
    # Importar cada módulo comprueba su carga real, no solo su presencia en pip.
    dependencias = {
        "roboticstoolbox-python": "roboticstoolbox",
        "numpy": "numpy",
        "scipy": "scipy",
        "sympy": "sympy",
        "matplotlib": "matplotlib",
        "pytest": "pytest",
    }
    versiones = {"Python": platform.python_version()}
    for distribucion, modulo in dependencias.items():
        import_module(modulo)
        versiones[distribucion] = version(distribucion)

    # En DH estándar el origen del eslabón está en el extremo: su centro de
    # masa está a -0,5 m. Izz=1/12 kg·m² corresponde a una barra uniforme.
    robot = rtb.DHRobot(
        [
            rtb.RevoluteDH(
                a=1.0,
                m=1.0,
                r=[-0.5, 0.0, 0.0],
                I=[0.0, 1.0 / 12.0, 1.0 / 12.0],
                Jm=0.0,
                B=0.0,
                Tc=[0.0, 0.0],
                G=1.0,
            )
        ],
        gravity=[0.0, -9.81, 0.0],
        name="Prueba del entorno: barra de 1 m",
    )
    q = np.zeros(1)

    # Separar gravedad y dinámica inversa permite verificar ambas rutas de
    # cálculo: sin movimiento, el torque de sostén debe coincidir con G(q).
    return {
        "versiones": versiones,
        "posicion": np.asarray(robot.fkine(q).t),
        "inercia": np.asarray(robot.inertia(q)),
        "gravedad": np.asarray(robot.gravload(q)),
        "torque_estatico": np.asarray(robot.rne(q, q, q)),
    }
