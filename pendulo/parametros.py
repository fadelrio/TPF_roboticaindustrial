"""Parámetros mecánicos en SI de las barras sin componentes de accionamiento."""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Barra:
    """Barra prismática maciza y uniforme, con dimensiones locales X, Y y Z.

    Las dimensiones se expresan en metros y la densidad en kg/m³. X sigue
    la longitud; Y es el ancho en el plano XY y Z el espesor perpendicular.
    Los valores nominales son 200×20×10 mm y 2700 kg/m³. El origen de la
    terna DH está en el extremo distal; sus ejes coinciden con los de la barra.
    """

    longitud: float = 0.20
    ancho: float = 0.02
    espesor: float = 0.01
    densidad: float = 2700.0

    @property
    def masa(self) -> float:
        """Calcular la masa en kg como densidad por volumen del prisma."""
        # Se conservan las dimensiones en SI para evitar conversiones internas.
        return self.densidad * self.longitud * self.ancho * self.espesor

    @property
    def centro_masa(self) -> np.ndarray:
        """Retornar el centro de masa (3,) en m respecto de la terna DH distal."""
        # El centro geométrico queda a media longitud hacia el extremo proximal.
        return np.array([-self.longitud / 2.0, 0.0, 0.0])

    @property
    def inercia(self) -> np.ndarray:
        """Retornar el tensor central (3, 3) en kg·m², en los ejes locales.

        El tensor corresponde al centro de masa, tal como requiere Toolbox,
        y no al origen DH. No incluye rotor, reductores ni fijaciones.
        """
        l, a, e = self.longitud, self.ancho, self.espesor
        # La simetría del prisma anula los productos de inercia en estos ejes.
        return self.masa / 12.0 * np.diag([a**2 + e**2, l**2 + e**2, l**2 + a**2])


# Dos cuerpos independientes con las mismas propiedades nominales. La tupla
# y las dimensiones inmutables evitan cambiar accidentalmente el caso nominal.
BARRAS = (Barra(), Barra())
GRAVEDAD = (0.0, -9.81, 0.0)
