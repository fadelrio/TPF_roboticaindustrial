"""Validación física y de precisión del control continuo de la etapa 6."""

from unittest.mock import patch

import numpy as np
import pytest

from main import ESCENARIOS_CONTROL, comparar_continuo
from pendulo.control import ControladorPD
from pendulo.dinamica import Dinamica
from pendulo.modelo import crear_robot_actuado
from pendulo.parametros import ACTUADORES, Friccion, LIMITES_TORQUE
from pendulo.simulacion import medir_seguimiento, simular_seguimiento
from pendulo.trayectorias import TrayectoriaQuintica


@pytest.fixture(scope="module")
def dinamica_control() -> Dinamica:
    """Derivar una vez el modelo completo, con montaje y rotores aprobados."""
    # Todas las comparaciones reciben la misma planta y fricción nominal.
    return Dinamica(crear_robot_actuado())


@pytest.fixture(scope="module")
def comparaciones(dinamica_control: Dinamica) -> dict:
    """Simular siete recorridos nominales, cuatro recuperaciones e ida-vuelta.

    Usa PD y PD+G con ganancias nominales, integración RK45 a tolerancias
    acordadas y salida 1 ms. Las recuperaciones combinan signos de 5° en
    ambas juntas, en reposo inicial; cada referencia permanece 1 s al final.
    """
    resultados = {}
    controladores = [ControladorPD("PD"), ControladorPD("PD+G", gravedad=True)]
    for nombre in ("abajo_arriba", "arriba_abajo", "extremos", "extremos_opuestos",
                   "eje1", "eje2", "nulo_horizontal"):
        # Conservar los siete casos de etapa 6 evita duplicar los pares nuevos
        # que se verifican en la validación final de etapa 7.
        resultados[nombre] = comparar_continuo(dinamica_control, nombre, controladores)[nombre]
    target = np.array([np.pi / 2, 0])
    for signo1, signo2 in [(1, 1), (1, -1), (-1, 1), (-1, -1)]:
        nombre = f"recuperacion_{signo1}_{signo2}"
        resultados[nombre] = {}
        for controlador in controladores:
            trayectoria = TrayectoriaQuintica(target, target)
            q0 = target + np.deg2rad([5 * signo1, 5 * signo2])
            resultados[nombre][controlador.nombre] = simular_seguimiento(
                dinamica_control, trayectoria, controlador, q0=q0)
    # La ida ya calculada permite comprobar la continuidad física de la
    # vuelta sin volver a integrar una ida idéntica dentro de esta fixture.
    resultados["vuelta_continuada"] = {}
    caso = ESCENARIOS_CONTROL["arriba_abajo"]
    for controlador in controladores:
        ida = resultados["abajo_arriba"][controlador.nombre]
        resultados["vuelta_continuada"][controlador.nombre] = simular_seguimiento(
            dinamica_control, TrayectoriaQuintica(caso["qi"], caso["qf"]), controlador,
            q0=ida.simulacion.q[-1], qd0=ida.simulacion.qd[-1])
    return resultados


@pytest.mark.parametrize("escenario", [
    "abajo_arriba", "arriba_abajo", "extremos", "extremos_opuestos",
    "eje1", "eje2", "nulo_horizontal", "vuelta_continuada",
])
def test_precision_nominal_y_demanda(comparaciones: dict, escenario: str) -> None:
    """Exigir precisión y capacidades del PD+G nominal en ocho recorridos.

    Máximo ≤2° por eje sobre movimiento y permanencia; final ≤0,2° después
    de 1 s. Contrasta demanda ideal/pedido/aplicado con los límites, rpm
    reales con capacidades de ficha y potencia mecánica con 6/12 W.
    No limita artificialmente las velocidades reales a los 3 rad/s de referencia.
    """
    r = comparaciones[escenario]["PD+G"]
    m = medir_seguimiento(r)
    assert m["cumple_precision"]
    assert m["cumple_capacidad"]
    assert m["solicitud_sin_saturacion"]
    assert np.all(m["error_maximo_grados"] <= 2)
    assert np.all(m["error_final_grados"] <= 0.2)
    assert np.all(m["torque_referencia_maximo"] <= LIMITES_TORQUE)
    assert np.all(m["torque_solicitado_maximo"] <= LIMITES_TORQUE)
    assert np.all(m["torque_aplicado_maximo"] <= LIMITES_TORQUE)
    for eje, actuador in enumerate(ACTUADORES):
        # Usar estado real y magnitud de potencia cubre accionamiento y
        # frenado mecánico; la estimación del motor conserva eta máxima.
        assert m["rpm_maxima"][eje] <= min(actuador.velocidad_motor_nominal,
                                         actuador.velocidad_entrada_continua)
        assert m["potencia_maxima"][eje] <= actuador.potencia_reductor_continua
        assert m["torque_motor_estimado"][eje] <= actuador.torque_motor_nominal
        potencia_nominal = actuador.torque_motor_nominal * actuador.velocidad_motor_nominal * 2 * np.pi / 60
        assert m["potencia_motor_estimada"][eje] <= potencia_nominal
    print(f"{escenario} PD+G: T={r.trayectoria.duracion:.12g} s; "
          f"error max/final [°]={m['error_maximo_grados']}/{m['error_final_grados']}; "
          f"torque pedido/ideal [N·m]="
          f"{m['torque_solicitado_maximo']}/{m['torque_referencia_maximo']}; "
          f"vmax [rad/s]={m['velocidad_maxima']}; rpm={m['rpm_maxima']}; "
          f"|P|max [W]={m['potencia_maxima']}; sat [%]={m['saturacion_porcentaje']}")
    # Registrar también el PD puro permite comparar la precisión obtenida
    # con idéntica planta, referencia y ganancias en el informe de la etapa.
    pd = medir_seguimiento(comparaciones[escenario]["PD"])
    print(f"{escenario} PD: error max/final [°]="
          f"{pd['error_maximo_grados']}/{pd['error_final_grados']}")


@pytest.mark.parametrize("signos", [(1, 1), (1, -1), (-1, 1), (-1, -1)])
def test_recuperacion_invertido_separada_del_seguimiento(comparaciones: dict, signos: tuple) -> None:
    """Recuperar cuatro perturbaciones ±5° sin aplicarles el máximo de 2°.

    PD+G debe terminar dentro de 0,2° por eje y asentarse antes del final
    de 3 s, permaneciendo dentro de ese umbral en las muestras posteriores.
    La solicitud inicial puede saturar; el aplicado debe respetar los límites.
    """
    r = comparaciones[f"recuperacion_{signos[0]}_{signos[1]}"]["PD+G"]
    m = medir_seguimiento(r)
    np.testing.assert_allclose(np.rad2deg(np.abs(r.error[0])), [5, 5], rtol=0, atol=1e-12)
    assert not m["cumple_precision"]
    assert m["asentamiento"] is not None and m["asentamiento"] < r.simulacion.t[-1]
    asentado = r.simulacion.t >= m["asentamiento"]
    assert np.max(np.rad2deg(np.abs(r.error[asentado]))) <= 0.2
    assert np.all(m["error_final_grados"] <= 0.2)
    assert np.all(m["torque_aplicado_maximo"] <= LIMITES_TORQUE)
    assert np.any(m["saturacion_porcentaje"] > 0)
    assert not m["solicitud_sin_saturacion"]
    # Las ganancias nominales exigen un pedido inicial mayor que el torque
    # continuo: registrar esa saturación aporta evidencia de la recuperación.
    print(f"Recuperación {signos}: asentamiento={m['asentamiento']:.6g} s; "
          f"final [°]={m['error_final_grados']}; pedido/aplicado [N·m]="
          f"{m['torque_solicitado_maximo']}/{m['torque_aplicado_maximo']}; "
          f"sat [%]={m['saturacion_porcentaje']}")
    pd = medir_seguimiento(comparaciones[f"recuperacion_{signos[0]}_{signos[1]}"]["PD"])
    print(f"Recuperación {signos} PD: asentamiento={pd['asentamiento']} s; "
          f"final [°]={pd['error_final_grados']}")


def test_comparacion_pd_y_pd_gravedad(comparaciones: dict, dinamica_control: Dinamica) -> None:
    """Comparar ambos controladores sin imponer aceptación nominal al PD puro.

    En horizontal nulo, PD+G debe sostener el reposo a 1e-12 rad; PD debe
    desarrollar error gravitatorio y su equilibrio final satisfacer Kp·e=G(q)
    aproximadamente a 1e-4 N·m. Se exige menor error máximo PD+G en abajo–arriba.
    """
    pd = comparaciones["nulo_horizontal"]["PD"]
    compensado = comparaciones["nulo_horizontal"]["PD+G"]
    np.testing.assert_allclose(compensado.simulacion.q, 0, rtol=0, atol=1e-12)
    np.testing.assert_allclose(compensado.simulacion.qd, 0, rtol=0, atol=1e-12)
    assert np.all(np.abs(pd.error[-1]) > np.deg2rad(1))
    # El controlador puro conserva su fórmula; el torque para sostener la
    # posición se obtiene mediante error y no mediante una compensación oculta.
    equilibrio = pd.controlador.kp * pd.error[-1]
    gravedad_final = dinamica_control.G(pd.simulacion.q[-1])
    # En la última muestra la velocidad es muy pequeña: el término
    # proporcional debe compensar aproximadamente la gravedad real.
    np.testing.assert_allclose(equilibrio, gravedad_final, rtol=0, atol=1e-4)
    m_pd = medir_seguimiento(comparaciones["abajo_arriba"]["PD"])
    m_g = medir_seguimiento(comparaciones["abajo_arriba"]["PD+G"])
    assert np.all(m_g["error_maximo_grados"] < m_pd["error_maximo_grados"])
    print(f"Comparación horizontal PD final [°]={medir_seguimiento(pd)['error_final_grados']}; "
          f"PD+G final [°]={medir_seguimiento(compensado)['error_final_grados']}; "
          f"abajo-arriba max PD/PD+G [°]="
          f"{m_pd['error_maximo_grados']}/{m_g['error_maximo_grados']}")


def test_referencia_registros_continuidad_y_potencia(comparaciones: dict) -> None:
    """Contrastar referencias, registros y continuidad física de ida-vuelta.

    Para todos los resultados exige tiempos desde 0 hasta T+1, posición
    deseada final exacta y derivadas nulas durante la permanencia. En la
    vuelta, condiciones iniciales idénticas al final real anterior, sin reset.
    Contrasta máximos de potencia/rpm con cuentas directas sobre los registros.
    """
    for casos in comparaciones.values():
        for resultado in casos.values():
            r, tr = resultado.simulacion, resultado.trayectoria
            assert r.t[0] == 0 and r.t[-1] == tr.duracion + 1
            assert resultado.q_d.shape == resultado.qd_d.shape == resultado.qdd_d.shape == r.q.shape
            hold = r.t >= tr.duracion
            np.testing.assert_array_equal(resultado.q_d[hold], np.tile(tr.qf, (sum(hold), 1)))
            np.testing.assert_array_equal(resultado.qd_d[hold], np.zeros((sum(hold), 2)))
            np.testing.assert_array_equal(resultado.qdd_d[hold], np.zeros((sum(hold), 2)))
            esperado = resultado.controlador.kp * resultado.error + resultado.controlador.kd * (
                resultado.qd_d - r.qd)
            if resultado.controlador.gravedad:
                # La ley se contrastó unitariamente y aquí se verifica contra
                # la gravedad geométrica independiente del modelo ampliado.
                q1, q2 = r.q[:, 0], r.q[:, 1]
                esperado += np.column_stack([0.600372 * np.cos(q1) + 0.105948 * np.cos(q1 + q2),
                                             0.105948 * np.cos(q1 + q2)])
            np.testing.assert_allclose(r.torque_solicitado, esperado, rtol=0, atol=1e-12)
            np.testing.assert_array_equal(r.torque_aplicado, np.clip(
                r.torque_solicitado, -np.array(LIMITES_TORQUE), LIMITES_TORQUE))
            m = medir_seguimiento(resultado)
            np.testing.assert_array_equal(m["potencia_maxima"], np.abs(r.torque_aplicado * r.qd).max(axis=0))
            np.testing.assert_array_equal(m["velocidad_maxima"], np.abs(r.qd).max(axis=0))
    for nombre in ("PD", "PD+G"):
        ida = comparaciones["abajo_arriba"][nombre].simulacion
        vuelta = comparaciones["vuelta_continuada"][nombre].simulacion
        # Conserva tanto posición como velocidad residual, aunque sean pequeñas.
        np.testing.assert_array_equal(vuelta.q[0], ida.q[-1])
        np.testing.assert_array_equal(vuelta.qd[0], ida.qd[-1])


def test_control_evaluado_dentro_de_rk45(dinamica_control: Dinamica) -> None:
    """Verificar llamadas de control en RK45 además de los registros de salida.

    Intercepta calcular con un wrapper que conserva el resultado. El número
    de llamadas debe ser nfev más las muestras registradas, con referencia
    de movimiento nulo y una perturbación real de 5°.
    """
    controlador = ControladorPD("PD+G observado", gravedad=True)
    target = np.array([np.pi / 2, 0])
    with patch.object(controlador, "calcular", wraps=controlador.calcular) as evaluar:
        r = simular_seguimiento(dinamica_control, TrayectoriaQuintica(target, target),
                                controlador, q0=target + np.deg2rad([5, -5]))
    # El control se evalúa también en los pasos adaptativos del integrador,
    # no se mantiene entre las muestras de salida como un controlador digital.
    assert evaluar.call_count == r.simulacion.evaluaciones + len(r.simulacion.t)
    assert evaluar.call_count > len(r.simulacion.t)


def test_convergencia_control_continuo(comparaciones: dict, dinamica_control: Dinamica) -> None:
    """Repetir extremos opuestos PD+G con tolerancias cien veces más estrictas.

    Misma referencia, ganancias, planta, fricción y salida de 1 ms. Exige
    diferencias ≤1e-5 rad, ≤1e-4 rad/s y ≤1e-4 N·m en torque solicitado.
    La referencia estricta aporta convergencia, sin considerarse solución exacta.
    """
    nominal = comparaciones["extremos_opuestos"]["PD+G"]
    estricto = simular_seguimiento(dinamica_control, nominal.trayectoria,
                                   nominal.controlador, rtol=1e-9, atol=1e-11)
    a, b = nominal.simulacion, estricto.simulacion
    np.testing.assert_array_equal(a.t, b.t)
    dq = float(np.max(np.abs(a.q - b.q)))
    dv = float(np.max(np.abs(a.qd - b.qd)))
    dtau = float(np.max(np.abs(a.torque_solicitado - b.torque_solicitado)))
    assert dq <= 1e-5 and dv <= 1e-4 and dtau <= 1e-4
    # Verificar precisión también en la referencia confirma que no depende
    # de una tolerancia relajada que esconda el error de seguimiento.
    assert medir_seguimiento(estricto)["cumple_precision"]
    print(f"Convergencia extremos opuestos: Δq={dq:.12g} rad; Δqd={dv:.12g} rad/s; "
          f"Δtau={dtau:.12g} N·m; evaluaciones={a.evaluaciones}/{b.evaluaciones}")
