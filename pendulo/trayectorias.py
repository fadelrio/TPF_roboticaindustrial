"""Referencias articulares de quinto orden, sincronizadas y en unidades SI."""

import numpy as np


class TrayectoriaQuintica:
    """Movimiento 2R entre posiciones en reposo, seguido de permanencia final.

    ``qi`` y ``qf`` son vectores (2,) en rad, dentro de [−pi, pi]. Ambos
    ejes comparten ``duracion`` en s, calculada para respetar al menos 2 s,
    velocidad máxima de 3 rad/s y aceleración máxima de 6 rad/s². Los
    ángulos conservan el desplazamiento indicado, sin buscar un giro corto
    ni envolverlos. La permanencia final no aumenta la duración del movimiento.
    """

    def __init__(self, qi: np.ndarray, qf: np.ndarray) -> None:
        """Copiar los destinos y fijar la duración mínima por límites analíticos.

        La ley normalizada tiene máximos |h'|=15/8 y
        |h''|=10sqrt(3)/3. Se usa el mayor desplazamiento de ambos ejes
        para que una misma duración respete sus límites individualmente.
        """
        self.qi = np.array(qi, dtype=float, copy=True)
        self.qf = np.array(qf, dtype=float, copy=True)
        for posicion in (self.qi, self.qf):
            # El rango corresponde a las posiciones de referencia; no impone
            # topes ni recortes al estado de la planta durante la simulación.
            if posicion.shape != (2,):
                raise ValueError("Las posiciones deben tener dos componentes.")
            if not np.all(np.isfinite(posicion)) or np.any(np.abs(posicion) > np.pi):
                raise ValueError("Las posiciones deben estar entre −pi y pi rad.")
        self._desplazamiento = self.qf - self.qi
        amplitud = float(np.max(np.abs(self._desplazamiento)))
        # Resolver los límites respecto de T evita ajustar la duración por
        # tanteos o depender de una grilla temporal para detectar los máximos.
        self.duracion = max(
            2.0,
            (15.0 / 8.0) * amplitud / 3.0,
            np.sqrt((10.0 * np.sqrt(3.0) / 3.0) * amplitud / 6.0),
        )

    def evaluar(self, t: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Retornar posición, velocidad y aceleración (2,) para t en segundos.

        Antes de t=0 se mantiene ``qi``; desde ``duracion`` se mantiene
        ``qf``, con derivadas nulas en ambos casos. Durante el movimiento
        se evalúan la ley de quinto orden y sus derivadas analíticas, en
        rad, rad/s y rad/s². Los arrays retornados son independientes.
        """
        if t <= 0:
            # Las copias permiten usar las referencias sin alterar destinos.
            return self.qi.copy(), np.zeros(2), np.zeros(2)
        if t >= self.duracion:
            return self.qf.copy(), np.zeros(2), np.zeros(2)
        s = t / self.duracion
        # La regla de la cadena introduce 1/T y 1/T² en las derivadas;
        # ambos ejes recorren el mismo progreso s con su propio desplazamiento.
        h = 10 * s**3 - 15 * s**4 + 6 * s**5
        hd = 30 * s**2 - 60 * s**3 + 30 * s**4
        hdd = 60 * s - 180 * s**2 + 120 * s**3
        return (
            self.qi + self._desplazamiento * h,
            self._desplazamiento * hd / self.duracion,
            self._desplazamiento * hdd / self.duracion**2,
        )
