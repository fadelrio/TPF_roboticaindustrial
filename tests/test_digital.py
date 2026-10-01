"""Muestreo, retención y continuidad física del control digital de etapa 7."""

from unittest.mock import patch

import numpy as np
import pytest

import pendulo.simulacion as simulacion
from pendulo.control import ControladorPD
from pendulo.dinamica import Dinamica
from pendulo.modelo import crear_robot_actuado
from pendulo.parametros import Friccion, LIMITES_TORQUE
from pendulo.simulacion import grilla_tiempo, medir_seguimiento, simular_planta, simular_seguimiento
from pendulo.trayectorias import TrayectoriaQuintica


@pytest.fixture(scope="module")
def dinamica_digital() -> Dinamica:
    """Derivar una sola vez la planta completa con montaje y rotores nominales."""
    # El cambio digital afecta la evaluación de control, no la mecánica.
    return Dinamica(crear_robot_actuado())


def test_retencion_no_alineada_y_continuidad(dinamica_digital: Dinamica, monkeypatch) -> None:
    """Verificar control de 7,3 ms con salida de 1 ms y último tramo fraccionario.

    Tres segundos con referencia horizontal nula, q0=(0,04;−0,02) rad y
    qd0=(0;0,1) rad/s. Se esperan 411 actualizaciones, última en 2,993 s
    y tramo final de 7 ms. Cada RK45 debe comenzar en el extremo anterior
    exacto; pedidos y aplicaciones se mantienen entre muestras de control.
    """
    controlador = ControladorPD("digital observado", gravedad=True)
    trayectoria = TrayectoriaQuintica((0.0, 0.0), (0.0, 0.0))
    periodos = []
    resolver = simulacion.solve_ivp

    def observar_intervalo(funcion, intervalo, inicial, **opciones):
        """Registrar fronteras, estado inicial y final de cada integración."""
        # La cuenta física se conserva; el wrapper observa la continuidad.
        solucion = resolver(funcion, intervalo, inicial, **opciones)
        periodos.append((intervalo, inicial.copy(), solucion.y[:, -1].copy()))
        return solucion

    monkeypatch.setattr(simulacion, "solve_ivp", observar_intervalo)
    with patch.object(controlador, "calcular", wraps=controlador.calcular) as calcular:
        with patch.object(simulacion, "limitar_torque", wraps=simulacion.limitar_torque) as limitar:
            resultado = simular_seguimiento(
                dinamica_digital, trayectoria, controlador, q0=(0.04, -0.02), qd0=(0.0, 0.1),
                modo="digital", periodo=0.0073)
    r = resultado.simulacion
    esperado_control = np.arange(411) * 0.0073
    # Se excluye tf=3: la última muestra conserva el torque anterior.
    np.testing.assert_array_equal(resultado.tiempos_control, esperado_control)
    np.testing.assert_array_equal(r.t, grilla_tiempo(3.0))
    assert len(periodos) == calcular.call_count == limitar.call_count == 411
    assert resultado.modo == "digital" and resultado.periodo == 0.0073
    assert resultado.tiempos_control[-1] < r.t[-1]
    assert abs(periodos[-1][0][1] - periodos[-1][0][0] - 0.007) <= 1e-15
    for indice, (intervalo, inicial, final) in enumerate(periodos):
        assert intervalo[0] == esperado_control[indice]
        assert intervalo[1] == (esperado_control[indice + 1] if indice < 410 else 3.0)
        if indice:
            np.testing.assert_array_equal(inicial, periodos[indice - 1][2])
        llamada = calcular.call_args_list[indice].args
        np.testing.assert_array_equal(llamada[0], inicial[:2])
        np.testing.assert_array_equal(llamada[1], inicial[2:])
        esperado = controlador.kp * (llamada[2] - inicial[:2]) + controlador.kd * (
            llamada[3] - inicial[2:]) + dinamica_digital.G(inicial[:2])
        np.testing.assert_allclose(resultado.torque_control_solicitado[indice], esperado,
                                   rtol=0, atol=1e-12)
    np.testing.assert_array_equal(np.concatenate([r.q[-1], r.qd[-1]]), periodos[-1][2])
    indices = np.searchsorted(resultado.tiempos_control, r.t, side="right") - 1
    np.testing.assert_array_equal(r.torque_solicitado, resultado.torque_control_solicitado[indices])
    np.testing.assert_array_equal(r.torque_aplicado, resultado.torque_control_aplicado[indices])
    np.testing.assert_array_equal(resultado.torque_control_aplicado, np.clip(
        resultado.torque_control_solicitado, -np.array(LIMITES_TORQUE), LIMITES_TORQUE))
    np.testing.assert_array_equal(r.rozamiento, np.array([Friccion().torque(v) for v in r.qd]))
    assert np.any(np.ptp(r.rozamiento[:8], axis=0) > 1e-3)
    print(f"Digital Ts=7,3 ms: controles={calcular.call_count}; "
          f"último tk={resultado.tiempos_control[-1]:.12g} s; "
          f"último tramo={periodos[-1][0][1]-periodos[-1][0][0]:.12g} s; "
          f"muestras={len(r.t)}; nfev={r.evaluaciones}")


def test_frontera_por_derecha_sin_actualizar_final(dinamica_digital: Dinamica) -> None:
    """Exigir nueva solicitud en t=1,5 s y retenerla al finalizar en 3 s.

    Ts=1,5 s, salida=0,5 s y PD puro con perturbación inicial permiten
    observar dos solicitudes diferentes. Solo se mide en t=0 y t=1,5;
    la muestra de frontera y el extremo final conservan la segunda solicitud.
    """
    controlador = ControladorPD("fronteras")
    trayectoria = TrayectoriaQuintica((0.0, 0.0), (0.0, 0.0))
    with patch.object(controlador, "calcular", wraps=controlador.calcular) as calcular:
        resultado = simular_seguimiento(
            dinamica_digital, trayectoria, controlador, q0=(0.02, -0.01),
            modo="digital", periodo=1.5, paso_salida=0.5)
    r = resultado.simulacion
    # El tiempo final no es una muestra de control adicional aunque tf/Ts
    # sea entero. La ley se llama dos veces y no durante los pasos RK45.
    assert calcular.call_count == 2
    np.testing.assert_array_equal(resultado.tiempos_control, [0.0, 1.5])
    assert not np.array_equal(resultado.torque_control_solicitado[0], resultado.torque_control_solicitado[1])
    for indice, tiempo in enumerate(r.t):
        evento = 0 if tiempo < 1.5 else 1
        np.testing.assert_array_equal(r.torque_solicitado[indice], resultado.torque_control_solicitado[evento])
        np.testing.assert_array_equal(r.torque_aplicado[indice], resultado.torque_control_aplicado[evento])


def test_torque_constante_contra_planta_y_estados_sin_recorte(
    dinamica_digital: Dinamica,
) -> None:
    """Contrastar un solo intervalo con planta independiente de torque constante.

    Ts=4 s supera el horizonte de 3 s. Pedido (2;−1) N·m, aplicación
    saturada (1,2;−0,31), q0=(pi+0,2;−pi−0,1) rad y qd0=(3,5;−3,2)
    rad/s. La integración digital y simular_planta deben coincidir a
    1e-10 rad, 1e-9 rad/s, sin envolver ni recortar los estados iniciales.
    """
    pedido = np.array([2.0, -1.0])
    controlador = ControladorPD("constante observado")
    trayectoria = TrayectoriaQuintica((0.0, 0.0), (0.0, 0.0))
    q0, qd0 = np.array([np.pi + 0.2, -np.pi - 0.1]), np.array([3.5, -3.2])

    def torque_constante(t, q, qd) -> np.ndarray:
        """Solicitar (2;−1) N·m independientemente del tiempo y del estado."""
        # La planta conserva su saturación y ecuación; esta entrada simple
        # separa la integración del algoritmo de actualización de control.
        return pedido.copy()

    with patch.object(controlador, "calcular", return_value=pedido) as calcular:
        digital = simular_seguimiento(dinamica_digital, trayectoria, controlador,
                                       q0=q0, qd0=qd0, modo="digital", periodo=4.0)
    continuo = simular_planta(dinamica_digital, q0, qd0, duracion=3.0,
                              torque=torque_constante, friccion=Friccion())
    r = digital.simulacion
    assert calcular.call_count == 1
    np.testing.assert_array_equal(digital.tiempos_control, [0.0])
    np.testing.assert_array_equal(r.t, continuo.t)
    np.testing.assert_allclose(r.q, continuo.q, rtol=0, atol=1e-10)
    np.testing.assert_allclose(r.qd, continuo.qd, rtol=0, atol=1e-9)
    np.testing.assert_allclose(r.energia, continuo.energia, rtol=0, atol=1e-10)
    np.testing.assert_array_equal(r.q[0], q0)
    np.testing.assert_array_equal(r.qd[0], qd0)
    assert np.max(np.abs(r.q)) > np.pi and np.max(np.abs(r.qd)) > 3.0
    np.testing.assert_array_equal(r.torque_solicitado, np.tile(pedido, (len(r.t), 1)))
    np.testing.assert_array_equal(r.torque_aplicado, np.tile(LIMITES_TORQUE, (len(r.t), 1)) * [1, -1])
    print(f"Torque constante: Δq={np.max(np.abs(r.q-continuo.q)):.12g} rad; "
          f"Δqd={np.max(np.abs(r.qd-continuo.qd)):.12g} rad/s; "
          f"ΔE={np.max(np.abs(r.energia-continuo.energia)):.12g} J")


def test_control_mas_rapido_que_salida_y_pedidos_no_observados(
    dinamica_digital: Dinamica,
) -> None:
    """Conservar 6000 eventos de 0,5 ms con salida de 1 ms sin perder picos.

    Una secuencia artificial alterna pedidos cero y (2;−1) N·m, de modo
    que los picos entre salidas solo aparezcan en la traza de control. La
    métrica debe detectarlos y descartar solicitud_sin_saturacion, aunque
    los registros en t=0,1,2... ms permanezcan en cero. El último pedido
    también es cero para que el extremo no revele un pico entre muestras.
    """
    controlador = ControladorPD("secuencia de comprobación")
    trayectoria = TrayectoriaQuintica((0.0, 0.0), (0.0, 0.0))
    pedidos = np.tile([[0.0, 0.0], [2.0, -1.0]], (3000, 1))
    pedidos[-1] = 0.0
    with patch.object(controlador, "calcular", side_effect=list(pedidos)) as calcular:
        resultado = simular_seguimiento(dinamica_digital, trayectoria, controlador,
                                        modo="digital", periodo=0.0005)
    # Ts menor que la grilla crea intervalos sin muestras de salida; aun así
    # deben integrarse y mantener sus controles en la traza completa.
    assert calcular.call_count == 6000
    assert len(resultado.simulacion.t) == 3001
    np.testing.assert_array_equal(resultado.torque_control_solicitado, pedidos)
    np.testing.assert_array_equal(resultado.simulacion.torque_solicitado, 0.0)
    # El extremo retiene el último pedido y no se vuelve a actualizar.
    metricas = medir_seguimiento(resultado)
    np.testing.assert_array_equal(metricas["torque_solicitado_maximo"], [2.0, 1.0])
    np.testing.assert_array_equal(metricas["torque_aplicado_maximo"], LIMITES_TORQUE)
    assert not metricas["solicitud_sin_saturacion"]
    print(f"Ts=0,5 ms: eventos={calcular.call_count}; "
          f"muestras={len(resultado.simulacion.t)}; "
          f"pedido máximo={metricas['torque_solicitado_maximo']} N·m")
