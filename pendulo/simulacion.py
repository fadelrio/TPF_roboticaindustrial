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


def _derivada_planta(
    dinamica: Dinamica, estado: np.ndarray, aplicado: np.ndarray,
    perdida: np.ndarray,
) -> np.ndarray:
    """Evaluar [qd,qdd] con estado (4,) y torques (2,) en unidades SI.

    Resuelve M·qdd=τaplicado−C·qd−G−f. La integración continua y cada
    intervalo digital utilizan esta misma ecuación, sin modificar el estado.
    """
    q, v = estado[:2], estado[2:]
    # Resolver el sistema lineal evita formar una inversa explícita de M.
    aceleracion = np.linalg.solve(
        dinamica.M(q), aplicado - dinamica.C(q, v) @ v - dinamica.G(q) - perdida)
    return np.concatenate([v, aceleracion])


def _crear_resultado_planta(
    dinamica: Dinamica, tiempos: np.ndarray, estados: np.ndarray,
    evaluaciones: int, registros: np.ndarray,
) -> ResultadoSimulacion:
    """Construir estados, energías y torques sobre la misma grilla de salida.

    ``estados`` tiene forma (n,4), con q y qd en SI. ``registros`` tiene
    forma (n,3,2), con torque solicitado, aplicado y de rozamiento en N·m.
    Las energías se calculan una vez, después de integrar todo el recorrido.
    """
    q, v = estados[:, :2].copy(), estados[:, 2:].copy()
    # Esta ruta común evita recalcular energías y crear resultados parciales
    # miles de veces cuando el controlador actualiza cada milisegundo.
    cinetica = np.array([0.5 * vi @ dinamica.M(qi) @ vi for qi, vi in zip(q, v)])
    potencial = np.array([dinamica.potencial(qi) for qi in q])
    return ResultadoSimulacion(tiempos.copy(), q, v, cinetica, potencial, evaluaciones,
                              registros[:, 0], registros[:, 1], registros[:, 2])


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
        _, aplicado, perdida = torques(t, estado[:2], estado[2:])
        # La ecuación también se usa cuando el accionamiento mantiene torque.
        return _derivada_planta(dinamica, estado, aplicado, perdida)

    solucion = solve_ivp(derivada, (0.0, duracion), inicial, method="RK45",
                        t_eval=tiempos, rtol=rtol, atol=atol)
    if not solucion.success:
        raise RuntimeError(f"Falló la integración de la planta: {solucion.message}")
    estados = solucion.y.T
    # Registrar en los mismos tiempos no fija los pasos internos de RK45.
    registros = np.array([torques(ti, estado[:2], estado[2:])
                         for ti, estado in zip(solucion.t, estados)])
    return _crear_resultado_planta(dinamica, solucion.t, estados, solucion.nfev, registros)


def _simular_digital(
    dinamica: Dinamica, q0: np.ndarray, qd0: np.ndarray, duracion: float,
    solicitar: Callable[[float, np.ndarray, np.ndarray], np.ndarray],
    friccion: Friccion | None, periodo: float, paso_salida: float,
    rtol: float, atol: float,
) -> tuple[ResultadoSimulacion, np.ndarray, np.ndarray, np.ndarray]:
    """Integrar control muestreado con retención de torque entre t_k=k·Ts.

    Actualiza solicitud y saturación una vez al comenzar cada intervalo,
    incluyendo t=0 y excluyendo el tiempo final. RK45 se reinicia desde
    el estado real de la frontera, con rozamiento evaluado continuamente.
    La salida conserva una grilla independiente del muestreo de control.
    Retorna el resultado y las trazas de tiempos, solicitud y aplicación.
    """
    tiempos = grilla_tiempo(duracion, paso_salida)
    fronteras = grilla_tiempo(duracion, periodo)
    estado = np.concatenate([np.asarray(q0, dtype=float), np.asarray(qd0, dtype=float)])
    estados = np.empty((len(tiempos), 4))
    pedidos_salida = np.empty((len(tiempos), 2))
    aplicados_salida = np.empty((len(tiempos), 2))
    pedidos_control, aplicados_control = [], []
    evaluaciones = 0
    for indice, (inicio, final) in enumerate(zip(fronteras[:-1], fronteras[1:])):
        # Medir únicamente el estado real en t_k. Copiar el pedido evita
        # compartir una solicitud reutilizada por un controlador externo.
        pedido = np.asarray(solicitar(inicio, estado[:2], estado[2:]), dtype=float).copy()
        aplicado = limitar_torque(pedido)
        pedidos_control.append(pedido)
        aplicados_control.append(aplicado)

        def derivada(t: float, actual: np.ndarray) -> np.ndarray:
            """Evaluar la planta con torque retenido y fricción instantánea."""
            # El controlador no interviene aquí: la resistencia conserva la
            # velocidad actual de cada paso interno, no la última muestreada.
            perdida = np.zeros(2) if friccion is None else friccion.torque(actual[2:])
            return _derivada_planta(dinamica, actual, aplicado, perdida)

        solucion = solve_ivp(derivada, (inicio, final), estado, method="RK45",
                            dense_output=True, rtol=rtol, atol=atol)
        if not solucion.success:
            raise RuntimeError(f"Falló la integración digital: {solucion.message}")
        evaluaciones += solucion.nfev
        # La interpolación densa de RK45 recoge las muestras dentro de cada
        # intervalo sin exigir que Ts sea múltiplo del paso de salida.
        desde = np.searchsorted(tiempos, inicio, side="left")
        ultimo = indice == len(fronteras) - 2
        hasta = np.searchsorted(tiempos, final, side="right" if ultimo else "left")
        if hasta > desde:
            estados[desde:hasta] = solucion.sol(tiempos[desde:hasta]).T
            pedidos_salida[desde:hasta] = pedido
            aplicados_salida[desde:hasta] = aplicado
        # Conservar el extremo integrado antes de actualizar en la próxima
        # frontera. El tiempo final no provoca una nueva llamada de control.
        estado = solucion.y[:, -1].copy()
    estados[-1] = estado
    perdidas = np.array([np.zeros(2) if friccion is None else friccion.torque(v)
                        for v in estados[:, 2:]])
    registros = np.stack([pedidos_salida, aplicados_salida, perdidas], axis=1)
    resultado = _crear_resultado_planta(dinamica, tiempos, estados, evaluaciones, registros)
    return resultado, fronteras[:-1].copy(), np.array(pedidos_control), np.array(aplicados_control)


@dataclass
class ResultadoSeguimiento:
    """Movimiento controlado y referencias sobre la misma grilla temporal.

    ``simulacion`` conserva los estados, energías y torques de la planta.
    q_d, qd_d y qdd_d son arrays (n,2) en rad, rad/s y rad/s². El torque
    de referencia (n,2), en N·m, es la demanda ideal de esa trayectoria,
    incluyendo fricción; no se utiliza como anticipación en el controlador.
    ``modo`` distingue continuo y digital. ``periodo`` es Ts en s solo para
    digital; en continuo es None. Las trazas opcionales contienen los tiempos
    de actualización (n_control,) y torques pedido/aplicado (n_control,2),
    excluyendo el tiempo final, donde se conserva el último torque retenido.
    """

    simulacion: ResultadoSimulacion
    trayectoria: TrayectoriaQuintica
    controlador: ControladorPD
    q_d: np.ndarray
    qd_d: np.ndarray
    qdd_d: np.ndarray
    torque_referencia: np.ndarray
    modo: str = "continuo"
    periodo: float | None = None
    tiempos_control: np.ndarray | None = None
    torque_control_solicitado: np.ndarray | None = None
    torque_control_aplicado: np.ndarray | None = None

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
    modo: str = "continuo",
    periodo: float = 0.001,
) -> ResultadoSeguimiento:
    """Integrar control continuo o digital durante movimiento y permanencia.

    Por defecto parte de qi y reposo. q0/qd0 permiten una perturbación o
    continuar desde el estado real de un tramo anterior, en rad y rad/s.
    ``permanencia`` debe ser al menos 1 s. La planta conserva RK45, límites
    físicos y grilla de salida. En ``modo='continuo'`` el controlador se
    evalúa en cada llamada interna. En ``modo='digital'`` mide el estado y
    actualiza cada ``periodo`` s desde t=0, manteniendo torque hasta la
    próxima muestra. No actualiza al finalizar ni anticipa torque ideal.
    """
    if permanencia < 1.0:
        raise ValueError("La permanencia final debe ser de al menos 1 s")
    if modo not in ("continuo", "digital"):
        raise ValueError("El modo debe ser 'continuo' o 'digital'")
    if modo == "digital" and (not np.isfinite(periodo) or periodo <= 0):
        raise ValueError("El período digital debe ser positivo y finito")
    inicial = trayectoria.qi if q0 is None else q0
    velocidad = np.zeros(2) if qd0 is None else qd0

    def solicitar(t: float, q: np.ndarray, qd: np.ndarray) -> np.ndarray:
        """Evaluar el torque PD o PD+G con referencia del tiempo recibido."""
        deseada, velocidad_deseada, _ = trayectoria.evaluar(t)
        # La saturación permanece en simular_planta, común a toda instancia.
        return controlador.calcular(q, qd, deseada, velocidad_deseada, dinamica)

    duracion = trayectoria.duracion + permanencia
    tiempos_control = pedido_control = aplicado_control = None
    if modo == "continuo":
        # Conservar la misma ruta de integración mantiene las llamadas y
        # los resultados de los escenarios previamente verificados.
        simulacion = simular_planta(
            dinamica, inicial, velocidad, duracion=duracion,
            paso_salida=paso_salida, rtol=rtol, atol=atol, torque=solicitar, friccion=friccion)
    else:
        simulacion, tiempos_control, pedido_control, aplicado_control = _simular_digital(
            dinamica, inicial, velocidad, duracion, solicitar, friccion,
            periodo, paso_salida, rtol, atol)
    referencias = np.array([trayectoria.evaluar(t) for t in simulacion.t])
    q_d, qd_d, qdd_d = referencias[:, 0], referencias[:, 1], referencias[:, 2]
    # Evaluar la demanda ideal permite cotejar capacidad, además del torque
    # aplicado limitado. No altera la ley de control ni la integración.
    torque_referencia = np.array([
        dinamica.inversa(q, v, a) + friccion.torque(v)
        for q, v, a in zip(q_d, qd_d, qdd_d)])
    return ResultadoSeguimiento(simulacion, trayectoria, controlador,
                               q_d, qd_d, qdd_d, torque_referencia, modo=modo,
                               periodo=periodo if modo == "digital" else None,
                               tiempos_control=tiempos_control,
                               torque_control_solicitado=pedido_control,
                               torque_control_aplicado=aplicado_control)


def medir_seguimiento(resultado: ResultadoSeguimiento) -> dict:
    """Calcular errores, demanda y capacidad de selección por eje, sin exportar.

    Errores, velocidades y potencias pertenecen a la grilla del resultado.
    Errores en grados, torques en N·m, velocidad articular en rad/s, entrada
    de motor/reductor en rpm y potencia mecánica en W. Las estimaciones de motor usan eta
    máxima del reductor; no modelan consumo eléctrico, temperatura ni frenado.
    ``cumple_precision`` aplica 2° máximo y 0,2° final a seguimiento nominal;
    la recuperación con error inicial de 5° se evalúa por asentamiento aparte.
    ``cumple_capacidad`` contrasta la trayectoria ideal y lo entregado por
    la planta; ``solicitud_sin_saturacion`` informa aparte si todo el pedido
    observado cabe en los límites. No convierte una solicitud saturada en
    una demanda satisfecha. La potencia del motor se estima con eta máxima.
    En digital, los máximos pedido y aplicado incorporan todos los eventos
    de control, aun si Ts es menor al paso de salida. Los máximos de estado
    y potencia, y el porcentaje de saturación, utilizan la grilla de salida;
    el último cuenta muestras saturadas, no tiempo exacto.
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
    # La traza conserva pedidos entre dos muestras de salida que podrían
    # quedar sin representar cuando el controlador se actualiza más rápido.
    pedidos = r.torque_solicitado if resultado.torque_control_solicitado is None else (
        resultado.torque_control_solicitado)
    aplicaciones = r.torque_aplicado if resultado.torque_control_aplicado is None else (
        resultado.torque_control_aplicado)
    pedido = np.abs(pedidos).max(axis=0)
    aplicado = np.abs(aplicaciones).max(axis=0)
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
