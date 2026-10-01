"""Integración de la planta 2R y resultados en memoria, con unidades SI."""

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_ivp

from .control import ControladorPD
from .dinamica import Dinamica
from .parametros import ACTUADORES, LIMITES_TORQUE, Friccion
from .trayectorias import TrayectoriaQuintica


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


@dataclass
class ResultadoSeguimiento:
    """Movimiento controlado y referencias sobre la misma grilla temporal.

    ``simulacion`` conserva los estados, energías y torques de la planta.
    q_d, qd_d y qdd_d son arrays (n,2) en rad, rad/s y rad/s². El torque
    de referencia (n,2), en N·m, es la demanda ideal de esa trayectoria,
    incluyendo fricción; no se utiliza como anticipación en el controlador.
    """

    simulacion: ResultadoSimulacion
    trayectoria: TrayectoriaQuintica
    controlador: ControladorPD
    q_d: np.ndarray
    qd_d: np.ndarray
    qdd_d: np.ndarray
    torque_referencia: np.ndarray

    @property
    def error(self) -> np.ndarray:
        """Retornar error articular deseado menos real (n,2) en rad."""
        # Usar los mismos tiempos evita introducir remuestreo en las métricas.
        return self.q_d - self.simulacion.q


def simular_seguimiento(
    dinamica: Dinamica,
    trayectoria: TrayectoriaQuintica,
    controlador: ControladorPD,
    q0: np.ndarray | None = None,
    qd0: np.ndarray | None = None,
    permanencia: float = 1.0,
    friccion: Friccion = Friccion(),
    paso_salida: float = 0.001,
    rtol: float = 1e-7,
    atol: float = 1e-9,
) -> ResultadoSeguimiento:
    """Integrar control continuo durante la quintica y la permanencia final.

    Por defecto parte de qi y reposo. q0/qd0 permiten una perturbación o
    continuar desde el estado real de un tramo anterior, en rad y rad/s.
    ``permanencia`` debe ser al menos 1 s. La planta conserva RK45, límites
    físicos y grilla de salida; el controlador se evalúa en cada llamada
    interna, sin muestreo digital ni anticipación del torque de referencia.
    """
    if permanencia < 1.0:
        raise ValueError("La permanencia final debe ser de al menos 1 s")
    inicial = trayectoria.qi if q0 is None else q0
    velocidad = np.zeros(2) if qd0 is None else qd0

    def solicitar(t: float, q: np.ndarray, qd: np.ndarray) -> np.ndarray:
        """Evaluar el torque PD o PD+G solicitado en el tiempo real de RK45."""
        deseada, velocidad_deseada, _ = trayectoria.evaluar(t)
        # La saturación permanece en simular_planta, común a toda instancia.
        return controlador.calcular(q, qd, deseada, velocidad_deseada, dinamica)

    simulacion = simular_planta(
        dinamica, inicial, velocidad, duracion=trayectoria.duracion + permanencia,
        paso_salida=paso_salida, rtol=rtol, atol=atol, torque=solicitar, friccion=friccion)
    referencias = np.array([trayectoria.evaluar(t) for t in simulacion.t])
    q_d, qd_d, qdd_d = referencias[:, 0], referencias[:, 1], referencias[:, 2]
    # Evaluar la demanda ideal permite cotejar capacidad, además del torque
    # aplicado limitado. No altera la ley de control ni la integración.
    torque_referencia = np.array([
        dinamica.inversa(q, v, a) + friccion.torque(v)
        for q, v, a in zip(q_d, qd_d, qdd_d)])
    return ResultadoSeguimiento(simulacion, trayectoria, controlador,
                               q_d, qd_d, qdd_d, torque_referencia)


def medir_seguimiento(resultado: ResultadoSeguimiento) -> dict:
    """Calcular errores, demanda y capacidad de selección por eje, sin exportar.

    Los máximos pertenecen a la grilla del resultado. Errores en grados,
    torques en N·m, velocidad articular en rad/s, entrada de motor/reductor
    en rpm y potencia mecánica en W. Las estimaciones de motor usan eta
    máxima del reductor; no modelan consumo eléctrico, temperatura ni frenado.
    ``cumple_precision`` aplica 2° máximo y 0,2° final a seguimiento nominal;
    la recuperación con error inicial de 5° se evalúa por asentamiento aparte.
    ``cumple_capacidad`` contrasta la trayectoria ideal y lo entregado por
    la planta; ``solicitud_sin_saturacion`` informa aparte si todo el pedido
    observado cabe en los límites. No convierte una solicitud saturada en
    una demanda satisfecha. La potencia del motor se estima con eta máxima.
    """
    r = resultado.simulacion
    error = np.rad2deg(np.abs(resultado.error))
    maximo, final = error.max(axis=0), error[-1]
    relaciones = np.array([a.relacion for a in ACTUADORES])
    eficiencias = np.array([a.eficiencia_maxima for a in ACTUADORES])
    limites_rpm = np.array([min(a.velocidad_motor_nominal, a.velocidad_entrada_continua)
                           for a in ACTUADORES])
    limites_potencia = np.array([a.potencia_reductor_continua for a in ACTUADORES])
    limites_motor = np.array([a.torque_motor_nominal for a in ACTUADORES])
    potencias_nominales_motor = np.array([
        a.torque_motor_nominal * a.velocidad_motor_nominal * 2 * np.pi / 60
        for a in ACTUADORES])
    velocidad = np.abs(r.qd).max(axis=0)
    rpm = velocidad * relaciones * 60 / (2 * np.pi)
    pedido = np.abs(r.torque_solicitado).max(axis=0)
    aplicado = np.abs(r.torque_aplicado).max(axis=0)
    ideal = np.abs(resultado.torque_referencia).max(axis=0)
    # Mantener signo de P distingue accionamiento y frenado. La comparación
    # de capacidad usa magnitud, sin atribuir recuperación de energía eléctrica.
    potencia = r.torque_aplicado * r.qd
    potencia_max = np.abs(potencia).max(axis=0)
    torque_motor = aplicado / (relaciones * eficiencias)
    # Asentamiento: primer tiempo después del último error mayor que 0,2°.
    # Su resolución es la de salida y solo certifica el horizonte observado.
    fuera = np.flatnonzero(np.any(error > 0.2, axis=1))
    asentamiento = 0.0 if len(fuera) == 0 else (
        float(r.t[fuera[-1] + 1]) if fuera[-1] < len(r.t) - 1 else None)
    return {
        "error_maximo_grados": maximo,
        "error_final_grados": final,
        "velocidad_final": r.qd[-1].copy(),
        "asentamiento": asentamiento,
        "torque_solicitado_maximo": pedido,
        "torque_aplicado_maximo": aplicado,
        "torque_referencia_maximo": ideal,
        "saturacion_porcentaje": 100 * np.mean(
            np.abs(r.torque_solicitado) > np.asarray(LIMITES_TORQUE), axis=0),
        "velocidad_maxima": velocidad,
        "rpm_maxima": rpm,
        "potencia_maxima": potencia_max,
        "potencia_positiva_maxima": np.maximum(0, potencia.max(axis=0)),
        "potencia_negativa_minima": np.minimum(0, potencia.min(axis=0)),
        "torque_motor_estimado": torque_motor,
        "potencia_motor_estimada": potencia_max / eficiencias,
        "solicitud_sin_saturacion": bool(np.all(pedido <= np.asarray(LIMITES_TORQUE))),
        "cumple_precision": bool(np.all(maximo <= 2) and np.all(final <= 0.2)),
        "cumple_capacidad": bool(
            np.all(ideal <= np.asarray(LIMITES_TORQUE)) and
            np.all(rpm <= limites_rpm) and np.all(potencia_max <= limites_potencia) and
            np.all(torque_motor <= limites_motor) and
            np.all(potencia_max / eficiencias <= potencias_nominales_motor)),
    }
