"""Cuentas manuales y contratos de los controladores articulares de etapa 6."""

import numpy as np
import pytest

from pendulo.control import ControladorPD


class GravedadPrueba:
    """Sustituto de G que registra q para comprobar la compensación.

    Su ley afín permite distinguir posición real y deseada con una cuenta
    manual. No representa la gravedad física del robot; esta se verifica
    junto con la dinámica y con las simulaciones de seguimiento.
    """

    def __init__(self) -> None:
        """Inicializar el registro de posiciones recibidas por G."""
        # Copiar en G preservará el historial aunque cambien datos de entrada.
        self.posiciones = []

    def G(self, q: np.ndarray) -> np.ndarray:
        """Registrar q y retornar [0,2+q1, −0,1+2·q2] en N·m."""
        # El cálculo deliberadamente sencillo facilita contrastarlo a mano.
        self.posiciones.append(np.array(q, dtype=float, copy=True))
        return np.array([0.2 + q[0], -0.1 + 2.0 * q[1]])


@pytest.mark.parametrize("gravedad", [False, True], ids=["PD", "PD_con_gravedad"])
def test_torques_con_errores_distintos_y_gravedad_real(gravedad: bool) -> None:
    """Contrastar torques de ambos ejes con cuentas manuales a 1e-12 N·m.

    Posiciones reales (0,25;−0,5), deseadas (0,4;−0,2) rad, velocidades
    reales (0,3;−0,8) y deseadas (0,1;0,5) rad/s, Kp=(12;3) y Kd=(2;0,4).
    PD debe producir (1,4;1,42) N·m. La compensación añade (0,45;−1,1),
    evaluada en q real, dando (1,85;0,32) N·m.
    """
    controlador = ControladorPD("comparacion", kp=(12.0, 3.0), kd=(2.0, 0.4),
                               gravedad=gravedad)
    dinamica = GravedadPrueba()
    q = np.array([0.25, -0.5])
    # Valores y signos diferentes por eje detectan mezcla de ganancias,
    # inversión de errores y uso de la posición deseada al compensar gravedad.
    torque = controlador.calcular(q, (0.3, -0.8), (0.4, -0.2), (0.1, 0.5), dinamica)
    esperado = (1.85, 0.32) if gravedad else (1.4, 1.42)
    np.testing.assert_allclose(torque, esperado, rtol=0, atol=1e-12)
    assert torque.shape == (2,)
    if gravedad:
        assert len(dinamica.posiciones) == 1
        np.testing.assert_array_equal(dinamica.posiciones[0], q)
    else:
        assert not dinamica.posiciones


def test_instancias_con_ganancias_y_nombres_independientes() -> None:
    """Comprobar independencia al reutilizar arrays de ganancias originales.

    Se cambia el primer controlador y luego las entradas originales; el
    segundo debe conservar (20;5), (1,3;0,2) y su nombre, sin memoria común.
    """
    kp, kd = np.array([20.0, 5.0]), np.array([1.3, 0.2])
    primero = ControladorPD("primero", kp, kd)
    segundo = ControladorPD("segundo", kp, kd, gravedad=True)
    # Los cambios de configuración deben afectar solamente a su instancia.
    primero.kp[0], primero.kd[1], primero.nombre = 10.0, 0.8, "ajustado"
    np.testing.assert_array_equal(kp, [20.0, 5.0])
    np.testing.assert_array_equal(kd, [1.3, 0.2])
    kp[:], kd[:] = 1.0, 0.0
    np.testing.assert_array_equal(segundo.kp, [20.0, 5.0])
    np.testing.assert_array_equal(segundo.kd, [1.3, 0.2])
    np.testing.assert_array_equal(primero.kp, [10.0, 5.0])
    np.testing.assert_array_equal(primero.kd, [1.3, 0.8])
    assert primero.nombre == "ajustado" and segundo.nombre == "segundo"
    assert not np.shares_memory(primero.kp, segundo.kp)
    assert not np.shares_memory(primero.kd, segundo.kd)


def test_no_envuelve_angulos_ni_satura_torque() -> None:
    """Exigir error literal de −2π y +2π, incluso con torques fuera de límites.

    Desde (π;−π) hasta (−π;π), en reposo y con ganancias nominales, se
    esperan (−40π;10π) N·m. El controlador no elige el recorrido angular
    más corto ni recorta al torque físico de la planta.
    """
    controlador = ControladorPD("extremos")
    # El resultado grande es intencional: registrar y limitar torque es
    # responsabilidad de la simulación, no de la ley de control solicitada.
    torque = controlador.calcular((np.pi, -np.pi), (0.0, 0.0),
                                  (-np.pi, np.pi), (0.0, 0.0), GravedadPrueba())
    np.testing.assert_allclose(torque, [-40.0 * np.pi, 10.0 * np.pi],
                               rtol=0, atol=1e-12)


def test_calcular_conserva_entradas_y_devuelve_vector_independiente() -> None:
    """Comprobar que calcular con gravedad conserva cuatro arrays de entrada.

    Se modifica después el torque retornado y se vuelve a exigir igualdad
    exacta de las entradas y ganancias. No debe compartir memoria con ellas.
    """
    controlador = ControladorPD("sin_mutacion", gravedad=True)
    entradas = [np.array(v) for v in [(0.4, -0.7), (0.8, -0.6),
                                     (-0.2, 0.9), (0.2, -0.5)]]
    originales = [valor.copy() for valor in entradas]
    torque = controlador.calcular(*entradas, GravedadPrueba())
    # Una referencia conservada por el resultado no debe permitir modificar
    # los estados, referencias ni parámetros del controlador.
    for valor, original in zip(entradas, originales):
        np.testing.assert_array_equal(valor, original)
        assert not np.shares_memory(torque, valor)
    assert not np.shares_memory(torque, controlador.kp)
    assert not np.shares_memory(torque, controlador.kd)
    torque[:] = 100.0
    for valor, original in zip(entradas, originales):
        np.testing.assert_array_equal(valor, original)
    np.testing.assert_array_equal(controlador.kp, [20.0, 5.0])
    np.testing.assert_array_equal(controlador.kd, [1.3, 0.2])


@pytest.mark.parametrize(
    "kp, kd",
    [((20.0,), (1.3, 0.2)), ((20.0, 5.0), ((1.3, 0.2),)),
     ((0.0, 5.0), (1.3, 0.2)), ((20.0, -5.0), (1.3, 0.2)),
     ((20.0, 5.0), (1.3, -0.2)), ((np.nan, 5.0), (1.3, 0.2)),
     ((20.0, 5.0), (np.inf, 0.2))],
    ids=["kp_incompleta", "kd_matriz", "kp_cero", "kp_negativa", "kd_negativa",
         "kp_no_finita", "kd_no_finita"],
)
def test_rechaza_ganancias_incompatibles(kp: tuple, kd: tuple) -> None:
    """Exigir ValueError para formas inválidas o ganancias fuera del contrato.

    La interfaz representa dos diagonales finitas, con Kp>0 y Kd>=0.
    No se admiten matrices, vectores incompletos, NaN o infinito.
    """
    # Rechazar aquí evita errores de broadcasting o parámetros sin sentido
    # durante evaluaciones sucesivas dentro del integrador.
    with pytest.raises(ValueError):
        ControladorPD("invalido", kp=kp, kd=kd)


def test_admite_amortiguacion_nula() -> None:
    """Admitir Kd nula y conservar torque proporcional (20;5) N·m.

    Con error de posición unitario y error de velocidad no nulo, Kd=(0;0)
    debe producir exactamente el término proporcional en ambos ejes.
    """
    controlador = ControladorPD("proporcional", kd=(0.0, 0.0))
    # Kd>=0 permite desactivar amortiguación explícitamente en una instancia.
    torque = controlador.calcular((0.0, 0.0), (3.0, -2.0),
                                  (1.0, 1.0), (0.0, 0.0), GravedadPrueba())
    np.testing.assert_array_equal(torque, [20.0, 5.0])
