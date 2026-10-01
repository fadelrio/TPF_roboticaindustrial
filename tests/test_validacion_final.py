"""Validación final reproducible del 2R, con control continuo y digital.

Los resultados se conservan en la fixture de módulo y se reutilizan entre
comprobaciones. Las filas JSON se imprimen en consola para el informe, sin
exportar archivos ni modificar ganancias, componentes o condiciones iniciales.
"""

import json

import numpy as np
import pytest

from main import ESCENARIOS_CONTROL
from pendulo.control import ControladorPD
from pendulo.dinamica import Dinamica
from pendulo.modelo import crear_robot_actuado
from pendulo.parametros import Friccion, LIMITES_TORQUE
from pendulo.simulacion import medir_seguimiento, simular_seguimiento
from pendulo.trayectorias import TrayectoriaQuintica


# La lista explícita conserva los casos nominales aunque main agregue otros
# presets. La vuelta usa el estado real final de la ida correspondiente.
NOMINALES = (
    "abajo_arriba", "arriba_abajo", "extremos", "extremos_opuestos",
    "eje1", "eje2", "nulo_horizontal", "vuelta_continuada",
)
MODOS = ("continuo", "digital")
LEYES = ("PD", "PD+G")
SIGNOS = ((1, 1), (1, -1), (-1, 1), (-1, -1))
ESCALAS = (0.0, 0.5, 1.0, 2.0)
PERIODOS = (0.0005, 0.001, 0.005, 0.01, 0.02)
PARES = {
    "interior_a": {"qi": (-3 * np.pi / 4, np.pi / 5),
                   "qf": (np.pi / 6, -2 * np.pi / 3)},
    "interior_b": {"qi": (np.pi / 3, -np.pi / 2),
                   "qf": (-np.pi / 4, 3 * np.pi / 4)},
    "borde": {"qi": (np.pi - np.pi / 180, -np.pi + np.pi / 180),
              "qf": (-np.pi + np.pi / 180, np.pi - np.pi / 180)},
}


def clave_resultado(
    nombre: str, ley: str, modo: str, escala: float = 1.0, periodo: float = 0.001,
) -> tuple:
    """Identificar un caso por escenario, ley, modo, fricción y período.

    En continuo el período no existe y se representa por None. Este criterio
    permite reutilizar el nominal de 1 ms y la fricción nominal en los barridos.
    """
    # Canonizar únicamente el período evita integrar otra vez casos idénticos.
    return nombre, ley, modo, escala, periodo if modo == "digital" else None


def registrar_metricas(nombre: str, ley: str, modo: str, escala: float, resultado) -> None:
    """Imprimir una fila reproducible con errores y demandas físicas por eje.

    Errores en grados, torques en N·m, velocidad en rad/s, entrada en rpm
    y potencia mecánica en W. La fila conserva signos extremos de potencia,
    saturación y asentamiento, sin atribuir eficiencia real ni modelo térmico.
    """
    m = medir_seguimiento(resultado)
    # JSON convierte los arrays a listas sin redondear los resultados numéricos.
    fila = {
        "caso": nombre, "ley": ley, "modo": modo, "friccion": escala,
        "Ts_s": resultado.periodo, "T_s": resultado.trayectoria.duracion,
        "emax_deg": m["error_maximo_grados"].tolist(),
        "efinal_deg": m["error_final_grados"].tolist(),
        "tau_pedido_Nm": m["torque_solicitado_maximo"].tolist(),
        "tau_aplicado_Nm": m["torque_aplicado_maximo"].tolist(),
        "tau_ideal_Nm": m["torque_referencia_maximo"].tolist(),
        "vmax_rad_s": m["velocidad_maxima"].tolist(),
        "rpm": m["rpm_maxima"].tolist(),
        "Pabs_W": m["potencia_maxima"].tolist(),
        "Ppositiva_W": m["potencia_positiva_maxima"].tolist(),
        "Pnegativa_W": m["potencia_negativa_minima"].tolist(),
        "sat_pct": m["saturacion_porcentaje"].tolist(),
        "asentamiento_s": m["asentamiento"],
        "precision": m["cumple_precision"], "capacidad": m["cumple_capacidad"],
        "pedido_sin_sat": m["solicitud_sin_saturacion"],
        "nfev": resultado.simulacion.evaluaciones,
    }
    print("VALIDACION " + json.dumps(fila, ensure_ascii=False, separators=(",", ":")))


def ejecutar_caso(
    resultados: dict, dinamica: Dinamica, nombre: str, caso: dict,
    ley: str, modo: str, escala: float = 1.0, periodo: float = 0.001,
):
    """Integrar una combinación nueva o devolver la ya calculada en memoria.

    Cada controlador recibe sus ganancias nominales independientes. El caso
    puede indicar q0 y qd0 reales para recuperar el invertido o continuar una
    vuelta. Las demás entradas y la permanencia de 1 s permanecen iguales.
    """
    clave = clave_resultado(nombre, ley, modo, escala, periodo)
    if clave not in resultados:
        # Reutilizar el modelo derivado y guardar cada combinación evita que
        # las pruebas de precisión, sensibilidad y registros repitan integraciones.
        resultados[clave] = simular_seguimiento(
            dinamica, TrayectoriaQuintica(caso["qi"], caso["qf"]),
            ControladorPD(ley, gravedad=ley == "PD+G"),
            q0=caso.get("q0"), qd0=caso.get("qd0"), friccion=Friccion(escala=escala),
            modo=modo, periodo=periodo,
        )
        registrar_metricas(nombre, ley, modo, escala, resultados[clave])
    return resultados[clave]


@pytest.fixture(scope="module")
def dinamica_final() -> Dinamica:
    """Derivar una vez el modelo completo con montaje, rotores y gravedad."""
    # La única planta común permite atribuir las diferencias a control y fricción.
    return Dinamica(crear_robot_actuado())


@pytest.fixture(scope="module")
def validacion_final(dinamica_final: Dinamica) -> dict:
    """Calcular ochenta combinaciones reproducibles y conservarlas en memoria.

    Incluye ocho nominales, cuatro recuperaciones, tres pares nuevos,
    cuatro fricciones y cinco períodos. Nominales y recuperaciones comparan
    PD y PD+G en ambos modos; sensibilidades usan PD+G. Los barridos reutilizan
    las combinaciones nominales presentes en el mismo diccionario.
    """
    resultados = {}
    for modo in MODOS:
        for ley in LEYES:
            for nombre in NOMINALES[:-1]:
                ejecutar_caso(resultados, dinamica_final, nombre,
                              ESCENARIOS_CONTROL[nombre], ley, modo)
            ida = resultados[clave_resultado("abajo_arriba", ley, modo)]
            vuelta = dict(ESCENARIOS_CONTROL["arriba_abajo"])
            # Heredar ambas componentes del estado conserva la continuidad
            # física del mismo recorrido, incluidos los residuos del control.
            vuelta.update(q0=ida.simulacion.q[-1], qd0=ida.simulacion.qd[-1])
            ejecutar_caso(resultados, dinamica_final, "vuelta_continuada", vuelta, ley, modo)
            for signo1, signo2 in SIGNOS:
                target = np.array([np.pi / 2, 0.0])
                caso = {"qi": target, "qf": target,
                        "q0": target + np.deg2rad([5 * signo1, 5 * signo2])}
                nombre = f"recuperacion_{signo1}_{signo2}"
                ejecutar_caso(resultados, dinamica_final, nombre, caso, ley, modo)
            for nombre, caso in PARES.items():
                ejecutar_caso(resultados, dinamica_final, nombre, caso, ley, modo)
        for nombre in ("abajo_arriba", "extremos_opuestos"):
            for escala in ESCALAS:
                ejecutar_caso(resultados, dinamica_final, nombre,
                              ESCENARIOS_CONTROL[nombre], "PD+G", modo, escala)
    for periodo in PERIODOS:
        ejecutar_caso(resultados, dinamica_final, "extremos_opuestos",
                      ESCENARIOS_CONTROL["extremos_opuestos"], "PD+G", "digital", periodo=periodo)
        target = np.array([np.pi / 2, 0.0])
        caso = {"qi": target, "qf": target, "q0": target + np.deg2rad([5, 5])}
        ejecutar_caso(resultados, dinamica_final, "recuperacion_1_1", caso,
                      "PD+G", "digital", periodo=periodo)
    return resultados


@pytest.mark.parametrize("nombre", NOMINALES)
@pytest.mark.parametrize("modo", MODOS)
def test_aceptacion_nominal_final(validacion_final: dict, nombre: str, modo: str) -> None:
    """Exigir precisión y demanda de PD+G nominal en ocho recorridos por modo.

    Máximo ≤2° por eje, final ≤0,2° tras 1 s, capacidad de torque/rpm/potencia
    y ausencia de pedidos saturados. PD comparte referencia y tiempos, pero
    sirve para diagnóstico y no recibe estos criterios de aceptación.
    """
    compensado = validacion_final[clave_resultado(nombre, "PD+G", modo)]
    puro = validacion_final[clave_resultado(nombre, "PD", modo)]
    m = medir_seguimiento(compensado)
    assert m["cumple_precision"] and m["cumple_capacidad"]
    assert m["solicitud_sin_saturacion"]
    assert np.all(m["error_maximo_grados"] <= 2.0)
    assert np.all(m["error_final_grados"] <= 0.2)
    assert np.all(m["torque_solicitado_maximo"] <= LIMITES_TORQUE)
    assert np.all(m["torque_referencia_maximo"] <= LIMITES_TORQUE)
    # Igualar referencias y tiempos verifica una comparación justa sin
    # exigir que PD puro elimine el sesgo de gravedad que se quiere observar.
    np.testing.assert_array_equal(puro.simulacion.t, compensado.simulacion.t)
    np.testing.assert_array_equal(puro.q_d, compensado.q_d)
    np.testing.assert_array_equal(puro.qd_d, compensado.qd_d)
    if nombre == "vuelta_continuada":
        for ley, resultado in (("PD", puro), ("PD+G", compensado)):
            ida = validacion_final[clave_resultado("abajo_arriba", ley, modo)]
            np.testing.assert_array_equal(resultado.simulacion.q[0], ida.simulacion.q[-1])
            np.testing.assert_array_equal(resultado.simulacion.qd[0], ida.simulacion.qd[-1])


@pytest.mark.parametrize("signos", SIGNOS)
@pytest.mark.parametrize("modo", MODOS)
def test_recuperacion_final(validacion_final: dict, signos: tuple, modo: str) -> None:
    """Recuperar ±5° en ambas juntas sin aplicarles el máximo de seguimiento.

    Exige PD+G dentro de 0,2° antes del final de 3 s y durante el horizonte
    restante. La saturación inicial se registra y no se disfraza como una
    solicitud físicamente entregada; el PD puro se conserva como comparación.
    """
    nombre = f"recuperacion_{signos[0]}_{signos[1]}"
    resultado = validacion_final[clave_resultado(nombre, "PD+G", modo)]
    m = medir_seguimiento(resultado)
    # El error inicial de 5° es una perturbación real, no una referencia de
    # movimiento; su recuperación se evalúa con asentamiento independiente.
    np.testing.assert_allclose(np.abs(np.rad2deg(resultado.error[0])), [5, 5], atol=1e-12, rtol=0)
    assert not m["cumple_precision"] and not m["solicitud_sin_saturacion"]
    assert m["asentamiento"] is not None and m["asentamiento"] < resultado.simulacion.t[-1]
    posterior = resultado.simulacion.t >= m["asentamiento"]
    assert np.max(np.abs(np.rad2deg(resultado.error[posterior]))) <= 0.2
    assert np.all(m["torque_aplicado_maximo"] <= LIMITES_TORQUE)
    assert np.any(m["saturacion_porcentaje"] > 0)


@pytest.mark.parametrize("nombre", tuple(PARES))
@pytest.mark.parametrize("modo", MODOS)
def test_pares_reproducibles(validacion_final: dict, nombre: str, modo: str) -> None:
    """Aceptar tres pares deterministas interiores y cercanos al borde.

    PD+G debe satisfacer los mismos límites nominales sin envolver ángulos;
    ambas leyes usan posiciones, duración y reposo inicial idénticos. Los
    pares amplían la evidencia del rango sin afirmar que lo cubran exhaustivamente.
    """
    g = validacion_final[clave_resultado(nombre, "PD+G", modo)]
    pd = validacion_final[clave_resultado(nombre, "PD", modo)]
    m = medir_seguimiento(g)
    assert m["cumple_precision"] and m["cumple_capacidad"] and m["solicitud_sin_saturacion"]
    # Comprobar el desplazamiento literal reconoce el sentido aprobado de
    # los giros y evita sustituirlos por un camino angular abreviado.
    np.testing.assert_array_equal(g.q_d[0], PARES[nombre]["qi"])
    np.testing.assert_array_equal(g.q_d[-1], PARES[nombre]["qf"])
    np.testing.assert_array_equal(g.simulacion.q[0], pd.simulacion.q[0])
    np.testing.assert_array_equal(g.simulacion.qd[0], pd.simulacion.qd[0])
    np.testing.assert_array_equal(g.q_d, pd.q_d)


@pytest.mark.parametrize("nombre", ("abajo_arriba", "extremos_opuestos"))
@pytest.mark.parametrize("modo", MODOS)
def test_sensibilidad_friccion(validacion_final: dict, nombre: str, modo: str) -> None:
    """Comparar fricción nula, media, nominal y doble con condiciones comunes.

    Verifica disipación instantánea no negativa y cambio observable entre
    fricción nula y doble. Los errores, torques y capacidades de cada escala
    quedan impresos por la fixture; no exige aceptación nominal fuera de escala1.
    """
    casos = [validacion_final[clave_resultado(nombre, "PD+G", modo, escala)] for escala in ESCALAS]
    for escala, resultado in zip(ESCALAS, casos):
        r = resultado.simulacion
        # f·qd es potencia perdida por rozamiento, aun durante control activo;
        # el controlador puede aumentar E, pero el rozamiento nunca la aporta.
        perdida = np.sum(r.rozamiento * r.qd, axis=1)
        assert np.min(perdida) >= -1e-12
        assert np.all(np.isfinite(r.q)) and np.all(np.isfinite(r.qd))
        np.testing.assert_array_equal(resultado.q_d, casos[0].q_d)
        if escala == 0:
            np.testing.assert_array_equal(r.rozamiento, np.zeros_like(r.rozamiento))
    assert not np.allclose(casos[0].simulacion.q, casos[-1].simulacion.q, rtol=0, atol=1e-5)


@pytest.mark.parametrize("nombre", ("recuperacion_1_1", "extremos_opuestos"))
def test_sensibilidad_periodo(validacion_final: dict, nombre: str) -> None:
    """Diagnosticar cinco períodos entre 0,5 y 20 ms sin forzar aceptación.

    Mantiene ganancias, planta y condiciones iniciales. Los resultados deben
    ser finitos y conservar la referencia; los períodos mayores pueden causar
    oscilación o incumplimientos, que se informan como resultados físicos.
    """
    casos = [validacion_final[clave_resultado(nombre, "PD+G", "digital", periodo=ts)]
             for ts in PERIODOS]
    for ts, resultado in zip(PERIODOS, casos):
        r = resultado.simulacion
        # La comparación usa el estado completo observado; no reduce sus
        # ángulos ni velocidades cuando el control discreto empeora la respuesta.
        assert resultado.modo == "digital" and resultado.periodo == ts
        assert np.all(np.isfinite(r.q)) and np.all(np.isfinite(r.qd))
        assert np.all(np.isfinite(r.torque_solicitado))
        np.testing.assert_array_equal(resultado.q_d, casos[0].q_d)
        np.testing.assert_array_equal(r.q[0], casos[0].simulacion.q[0])
        np.testing.assert_array_equal(r.qd[0], casos[0].simulacion.qd[0])
        assert np.all(np.abs(r.torque_aplicado).max(axis=0) <= LIMITES_TORQUE)
    assert not np.allclose(casos[0].simulacion.q, casos[-1].simulacion.q, rtol=0, atol=1e-5)


def test_aproximacion_al_continuo(validacion_final: dict) -> None:
    """Contrastar digital de 0,5/1 ms con continuo en extremos opuestos.

    Compara estados en los mismos tiempos y exige menor diferencia de posición
    al reducir el período en este caso concreto. El digital de 1 ms debe quedar
    a ≤0,1° del continuo; no presupone monotonicidad global de todas las métricas.
    """
    continuo = validacion_final[clave_resultado("extremos_opuestos", "PD+G", "continuo")]
    diferencias = []
    for ts in (0.0005, 0.001):
        digital = validacion_final[clave_resultado("extremos_opuestos", "PD+G", "digital", periodo=ts)]
        np.testing.assert_array_equal(digital.simulacion.t, continuo.simulacion.t)
        # Los máximos usan estados reales y referencias idénticas, separando
        # error de integración de la aproximación causada por muestreo y retención.
        dq = float(np.max(np.abs(digital.simulacion.q - continuo.simulacion.q)))
        dv = float(np.max(np.abs(digital.simulacion.qd - continuo.simulacion.qd)))
        diferencias.append(dq)
        print(f"DIFERENCIA_CONTINUO Ts={ts:g} s; Δq={dq:.12g} rad; Δqd={dv:.12g} rad/s")
    assert diferencias[0] <= diferencias[1]
    assert diferencias[1] <= np.deg2rad(0.1)


def test_convergencia_integracion_digital(validacion_final: dict, dinamica_final: Dinamica) -> None:
    """Repetir extremos opuestos digital1ms con tolerancias cien veces menores.

    Misma referencia, ganancias, muestreo y fricción. Exige diferencias máximas
    ≤1e-5 rad, ≤1e-4 rad/s y ≤1e-4 N·m en pedidos; la integración más precisa
    sirve como contraste de convergencia y no como solución exacta.
    """
    nominal = validacion_final[clave_resultado("extremos_opuestos", "PD+G", "digital")]
    estricto = simular_seguimiento(
        dinamica_final, nominal.trayectoria, nominal.controlador,
        modo="digital", periodo=0.001, rtol=1e-9, atol=1e-11,
    )
    a, b = nominal.simulacion, estricto.simulacion
    np.testing.assert_array_equal(a.t, b.t)
    # Solo las tolerancias cambian: las diferencias corresponden al cálculo
    # numérico, no al período de control, al montaje ni al controlador.
    dq = float(np.max(np.abs(a.q - b.q)))
    dv = float(np.max(np.abs(a.qd - b.qd)))
    dtau = float(np.max(np.abs(a.torque_solicitado - b.torque_solicitado)))
    assert dq <= 1e-5 and dv <= 1e-4 and dtau <= 1e-4
    assert medir_seguimiento(estricto)["cumple_precision"]
    registrar_metricas("extremos_opuestos_integracion_estricta", "PD+G", "digital", 1.0, estricto)
    print(f"CONVERGENCIA_DIGITAL Δq={dq:.12g} rad; Δqd={dv:.12g} rad/s; "
          f"Δtau={dtau:.12g} N·m; nfev={a.evaluaciones}/{b.evaluaciones}")
