"""Integración del movimiento libre y resultados en memoria, con unidades SI."""

from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp

from .dinamica import Dinamica


@dataclass
class ResultadoSimulacion:
    """Resultados muestreados de una integración, sin exportación de archivos.

    ``t`` tiene forma (n,) en s; ``q`` y ``qd`` forma (n,2), en rad y rad/s.
    ``cinetica`` y ``potencial`` son arrays (n,) en J. ``evaluaciones`` cuenta
    llamadas a la ecuación diferencial, no pasos ni muestras de salida.
    """

    t: np.ndarray
    q: np.ndarray
    qd: np.ndarray
    cinetica: np.ndarray
    potencial: np.ndarray
    evaluaciones: int

    @property
    def energia(self) -> np.ndarray:
        """Retornar energía mecánica total (n,) en J como K+U."""
        # Calcular la suma evita almacenar una tercera copia de las energías.
        return self.cinetica + self.potencial


def grilla_tiempo(duracion: float, paso: float = 0.001) -> np.ndarray:
    """Crear tiempos (n,) en s desde cero hasta duración, incluidos extremos.

    ``duracion`` y ``paso`` deben ser positivos. Las muestras están separadas
    por ``paso``, salvo el último intervalo, que puede ser menor cuando la
    duración no es múltiplo del paso. No fija los pasos internos de RK45.
    """
    if duracion <= 0 or paso <= 0:
        raise ValueError("La duración y el paso de salida deben ser positivos")
    # Incluir el final por separado evita sobrepasar t_span por redondeo.
    tiempos = np.arange(0.0, duracion, paso)
    return np.append(tiempos[tiempos < duracion], duracion)


def simular_libre(
    dinamica: Dinamica,
    q0: np.ndarray,
    qd0: np.ndarray,
    duracion: float = 5.0,
    paso_salida: float = 0.001,
    rtol: float = 1e-7,
    atol: float = 1e-9,
) -> ResultadoSimulacion:
    """Integrar el 2R sin torque ni fricción y calcular energías por muestra.

    ``dinamica`` ya está derivada; ``q0`` y ``qd0`` tienen forma (2,) en rad
    y rad/s. Usa solve_ivp/RK45 con tolerancias indicadas y salida cada 1 ms
    por defecto. No recorta estados ni envuelve ángulos. Si el integrador no
    alcanza el final correctamente, propaga un RuntimeError con su diagnóstico.
    """
    tiempos = grilla_tiempo(duracion, paso_salida)
    inicial = np.concatenate([np.asarray(q0, dtype=float), np.asarray(qd0, dtype=float)])

    def derivada(t: float, estado: np.ndarray) -> np.ndarray:
        """Evaluar [qd,qdd] para estado [q1,q2,qd1,qd2], con tiempo en s.

        En movimiento libre qdd=solve(M,−Cqd−G). El tiempo forma parte de
        la interfaz de solve_ivp aunque esta planta sea autónoma.
        """
        q, v = estado[:2], estado[2:]
        # Resolver el sistema lineal evita formar una inversa explícita de M.
        aceleracion = np.linalg.solve(dinamica.M(q), -dinamica.C(q, v) @ v - dinamica.G(q))
        return np.concatenate([v, aceleracion])

    solucion = solve_ivp(derivada, (0.0, duracion), inicial, method="RK45",
                        t_eval=tiempos, rtol=rtol, atol=atol)
    if not solucion.success:
        raise RuntimeError(f"Falló la integración libre: {solucion.message}")
    q, v = solucion.y[:2].T.copy(), solucion.y[2:].T.copy()

    # Las energías corresponden a las mismas muestras usadas por gráficos y
    # animación, no a otro recorrido ni a los pasos internos del integrador.
    cinetica = np.array([0.5 * vi @ dinamica.M(qi) @ vi for qi, vi in zip(q, v)])
    potencial = np.array([dinamica.potencial(qi) for qi in q])
    return ResultadoSimulacion(solucion.t.copy(), q, v, cinetica, potencial, solucion.nfev)
