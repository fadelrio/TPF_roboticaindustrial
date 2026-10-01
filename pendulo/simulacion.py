"""Integración de la planta 2R y resultados en memoria, con unidades SI."""

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp

from .dinamica import Dinamica
from .parametros import LIMITES_TORQUE, Friccion


@dataclass
class ResultadoSimulacion:
    """Resultados muestreados de una integración, sin exportación de archivos.

    ``t`` tiene forma (n,) en s; ``q`` y ``qd`` forma (n,2), en rad y rad/s.
    ``cinetica`` y ``potencial`` son arrays (n,) en J. ``evaluaciones`` cuenta
    llamadas a la ecuación diferencial, no pasos ni muestras de salida.
    Los torques solicitado, aplicado y de rozamiento tienen forma (n,2)
    en N·m y corresponden a la misma grilla de salida que los estados.
    """

    t: np.ndarray
    q: np.ndarray
    qd: np.ndarray
    cinetica: np.ndarray
    potencial: np.ndarray
    evaluaciones: int
    torque_solicitado: np.ndarray
    torque_aplicado: np.ndarray
    rozamiento: np.ndarray

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
    friccion: Friccion | None = None,
) -> ResultadoSimulacion:
    """Integrar el 2R sin torque externo, con rozamiento opcional.

    ``dinamica`` ya está derivada; ``q0`` y ``qd0`` tienen forma (2,) en rad
    y rad/s. Usa solve_ivp/RK45 con tolerancias indicadas y salida cada 1 ms
    por defecto. No recorta estados ni envuelve ángulos. Si el integrador no
    alcanza el final correctamente, propaga un RuntimeError con su diagnóstico.
    ``friccion=None`` conserva el movimiento ideal de la etapa 4; una instancia
    de Friccion permite estudiar disipación sin introducir un controlador.
    """
    # Reutilizar una sola ecuación de planta evita mantener dos integradores
    # distintos para el movimiento libre y las entradas de torque.
    return simular_planta(dinamica, q0, qd0, duracion=duracion,
                          paso_salida=paso_salida, rtol=rtol, atol=atol,
                          friccion=friccion)


def limitar_torque(
    solicitado: np.ndarray, limites: tuple[float, float] = LIMITES_TORQUE
) -> np.ndarray:
    """Saturar torque (2,) en N·m entre ±los límites de cada articulación.

    Devuelve un array nuevo sin modificar la solicitud. Solo limita el torque:
    no modifica posición, velocidad ni aceleración del estado de la planta.
    """
    # Un límite simétrico representa el accionamiento ideal aprobado para
    # ambos sentidos, sin recurrir a capacidad intermitente ni dinámica eléctrica.
    return np.clip(np.asarray(solicitado, dtype=float), -np.asarray(limites), limites)


def simular_planta(
    dinamica: Dinamica,
    q0: np.ndarray,
    qd0: np.ndarray,
    duracion: float = 5.0,
    paso_salida: float = 0.001,
    rtol: float = 1e-7,
    atol: float = 1e-9,
    torque: Callable[[float, np.ndarray, np.ndarray], np.ndarray] | None = None,
    friccion: Friccion | None = None,
    limites: tuple[float, float] = LIMITES_TORQUE,
) -> ResultadoSimulacion:
    """Integrar M·qdd=τaplicado−C·qd−G−f mediante solve_ivp/RK45.

    Las entradas articulares tienen dos componentes en SI. ``torque(t,q,qd)``
    devuelve la solicitud en N·m; debe ser una función sin efectos laterales
    ni modificaciones de sus entradas. Se evalúa dentro de la integración
    y en la grilla de salida para registrar ambos torques. ``None`` pide cero.
    ``friccion=None`` indica rozamiento nulo. Se conservan las tolerancias y
    grilla acordadas; no se envuelven ángulos ni se recortan estados.
    """
    tiempos = grilla_tiempo(duracion, paso_salida)
    inicial = np.concatenate([np.asarray(q0, dtype=float), np.asarray(qd0, dtype=float)])

    def torques(t: float, q: np.ndarray, v: np.ndarray) -> tuple:
        """Evaluar solicitud, saturación y rozamiento, todos (2,) en N·m."""
        # f conserva el signo de v: se resta como resistencia en la planta.
        pedido = np.zeros(2) if torque is None else np.asarray(torque(t, q, v), dtype=float)
        aplicado = limitar_torque(pedido, limites)
        perdida = np.zeros(2) if friccion is None else friccion.torque(v)
        return pedido, aplicado, perdida

    def derivada(t: float, estado: np.ndarray) -> np.ndarray:
        """Evaluar [qd,qdd] para estado [q1,q2,qd1,qd2], con tiempo en s.

        Resuelve el sistema lineal de la planta usando el torque saturado,
        los torques conservativos y el rozamiento articular suave.
        """
        q, v = estado[:2], estado[2:]
        _, aplicado, perdida = torques(t, q, v)
        # Resolver el sistema lineal evita formar una inversa explícita de M.
        aceleracion = np.linalg.solve(
            dinamica.M(q), aplicado - dinamica.C(q, v) @ v - dinamica.G(q) - perdida)
        return np.concatenate([v, aceleracion])

    solucion = solve_ivp(derivada, (0.0, duracion), inicial, method="RK45",
                        t_eval=tiempos, rtol=rtol, atol=atol)
    if not solucion.success:
        raise RuntimeError(f"Falló la integración de la planta: {solucion.message}")
    q, v = solucion.y[:2].T.copy(), solucion.y[2:].T.copy()

    # Las energías corresponden a las mismas muestras usadas por gráficos y
    # animación, no a otro recorrido ni a los pasos internos del integrador.
    cinetica = np.array([0.5 * vi @ dinamica.M(qi) @ vi for qi, vi in zip(q, v)])
    potencial = np.array([dinamica.potencial(qi) for qi in q])
    registros = np.array([torques(ti, qi, vi) for ti, qi, vi in zip(solucion.t, q, v)])
    return ResultadoSimulacion(solucion.t.copy(), q, v, cinetica, potencial, solucion.nfev,
                              registros[:, 0], registros[:, 1], registros[:, 2])
