"""Pruebas físicas y de convergencia del movimiento libre en la etapa 4."""

import numpy as np
import pytest

from main import ESCENARIOS_LIBRES
from pendulo.dinamica import Dinamica
from pendulo.modelo import crear_robot
from pendulo.simulacion import grilla_tiempo, simular_libre


@pytest.fixture(scope="module")
def movimientos_libres() -> dict:
    """Integrar los tres escenarios nominales y dos referencias más estrictas.

    Se deriva una instancia del modelo. Los tres casos usan rtol=1e-7,
    atol=1e-9 y salida de 1 ms; invertido y oscilación se repiten con
    rtol=1e-9 y atol=1e-11, conservando condiciones y grilla.
    """
    d = Dinamica(crear_robot())
    resultados = {}
    # Cada comparación conserva la misma planta y estado inicial; solo
    # cambia la precisión solicitada al integrador adaptativo.
    for nombre, caso in ESCENARIOS_LIBRES.items():
        resultados[nombre] = simular_libre(d, **caso)
        if nombre != "colgante":
            resultados[nombre + "_estricto"] = simular_libre(d, **caso, rtol=1e-9, atol=1e-11)
    return resultados


def test_equilibrio_colgante(movimientos_libres: dict) -> None:
    """Mantener el colgante exacto durante 5 s dentro de tolerancias numéricas.

    Parte de q=(−pi/2,0), qd=(0,0). Se admite desviación de posición
    ≤1e-7 rad y velocidad ≤1e-6 rad/s; no se fuerza G a cero ni se recorta
    el estado para corregir los residuos de cos(−pi/2) en punto flotante.
    """
    r = movimientos_libres["colgante"]
    # El equilibrio continuo es exacto, pero la evaluación numérica conserva
    # el pequeño residuo trigonométrico y la tolerancia absoluta de RK45.
    posicion = float(np.max(np.abs(r.q - [-np.pi / 2, 0])))
    velocidad = float(np.max(np.abs(r.qd)))
    assert posicion <= 1e-7
    assert velocidad <= 1e-6
    print(f"Colgante: desviación={posicion:.17g} rad; velocidad={velocidad:.17g} rad/s")


def test_alejamiento_invertido_perturbado(movimientos_libres: dict) -> None:
    """Observar alejamiento desde 1° de perturbación de q1 durante 2 s.

    Parte de q=(pi/2+pi/180,0) y reposo. Exige que q1 se aleje más de
    10° del invertido y que el recorrido incluya ángulos fuera de [-pi,pi],
    comprobando también que el movimiento libre no aplica topes ficticios.
    """
    r = movimientos_libres["invertido"]
    # La perturbación es explícita, no depende de ruido o del residuo numérico
    # para iniciar la caída. El máximo permite observar el recorrido completo.
    alejamiento = float(np.max(np.abs(r.q[:, 0] - np.pi / 2)))
    assert np.isclose(r.q[0, 0] - np.pi / 2, np.deg2rad(1))
    assert alejamiento > np.deg2rad(10)
    assert np.max(np.abs(r.q)) > np.pi
    print(f"Invertido: máximo alejamiento de q1={alejamiento:.17g} rad; q final={r.q[-1]}")


@pytest.mark.parametrize("nombre", ["invertido", "oscilacion"])
def test_conservacion_y_convergencia(movimientos_libres: dict, nombre: str) -> None:
    """Contrastar energía y recorrido nominales con integración más estricta.

    Duraciones: 2 s invertido, 5 s oscilación. Sin torque ni fricción se
    exige variación de E ≤1e-5 J, diferencias nominal/estricta ≤1e-4 rad
    y ≤1e-3 rad/s, y menor variación energética en la referencia estricta.
    """
    nominal, estricto = movimientos_libres[nombre], movimientos_libres[nombre + "_estricto"]
    # Usar los mismos tiempos evita confundir interpolación entre grillas con
    # diferencias de integración. La referencia estricta no es solución exacta.
    np.testing.assert_array_equal(nominal.t, estricto.t)
    energia = float(np.max(np.abs(nominal.energia - nominal.energia[0])))
    energia_estricta = float(np.max(np.abs(estricto.energia - estricto.energia[0])))
    posicion = float(np.max(np.abs(nominal.q - estricto.q)))
    velocidad = float(np.max(np.abs(nominal.qd - estricto.qd)))
    assert energia <= 1e-5
    assert energia_estricta < energia
    assert posicion <= 1e-4
    assert velocidad <= 1e-3
    assert np.min(nominal.cinetica) >= 0
    print(f"{nombre}: E0={nominal.energia[0]:.17g} J; ΔE={energia:.17g} J; "
          f"ΔE estricta={energia_estricta:.17g} J; Δq={posicion:.17g} rad; "
          f"Δqd={velocidad:.17g} rad/s; evaluaciones={nominal.evaluaciones}/{estricto.evaluaciones}")


def test_grilla_estados_y_condiciones_iniciales(movimientos_libres: dict) -> None:
    """Verificar muestras cada 1 ms, extremos, formas y valores finitos.

    Cada escenario debe incluir exactamente el estado inicial y finalizar
    en su duración: 5001 muestras para 5 s y 2001 para 2 s.
    """
    for nombre, caso in ESCENARIOS_LIBRES.items():
        r = movimientos_libres[nombre]
        # Todos los campos comparten una sola grilla; esa correspondencia es
        # necesaria para interpretar juntos gráficos, energía y animaciones.
        assert len(r.t) == int(caso["duracion"] / 0.001) + 1
        assert r.t[0] == 0 and r.t[-1] == caso["duracion"]
        np.testing.assert_allclose(np.diff(r.t), 0.001, rtol=0, atol=1e-15)
        assert r.q.shape == r.qd.shape == (len(r.t), 2)
        assert r.cinetica.shape == r.potencial.shape == (len(r.t),)
        np.testing.assert_array_equal(r.q[0], caso["q0"])
        np.testing.assert_array_equal(r.qd[0], caso["qd0"])
        assert np.isfinite(r.q).all() and np.isfinite(r.qd).all()
        assert np.isfinite(r.energia).all()


def test_grilla_con_ultimo_intervalo_corto() -> None:
    """Incluir duración 2,5 ms sin sobrepasarla al usar salida de 1 ms."""
    # El último intervalo de 0,5 ms conserva el destino temporal exacto.
    np.testing.assert_array_equal(grilla_tiempo(0.0025), [0.0, 0.001, 0.002, 0.0025])
