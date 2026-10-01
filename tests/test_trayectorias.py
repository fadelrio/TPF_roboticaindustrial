"""Comprobaciones de referencias quinticas y límites articulares acordados."""

import numpy as np
import pytest

from pendulo.trayectorias import TrayectoriaQuintica


@pytest.mark.parametrize(
    "qi,qf,duracion_esperada",
    [
        ([0, 0], [1, -0.5], 2.0),
        ([-np.pi / 2, 0], [np.pi / 2, 0], 2.0),
        ([-np.pi, np.pi], [np.pi, -np.pi], 5 * np.pi / 4),
    ],
    ids=["corto", "abajo_arriba", "extremos_sin_envoltura"],
)
def test_extremos_reposo_y_duracion(qi: list, qf: list, duracion_esperada: float) -> None:
    """Verificar destinos y reposo antes/después de tres movimientos conocidos.

    Exige duración a 1e-14 s, posición exacta en los extremos y derivadas
    exactamente nulas. La permanencia incluye 1 s y no reinicia el movimiento.
    """
    trayectoria = TrayectoriaQuintica(qi, qf)
    assert abs(trayectoria.duracion - duracion_esperada) <= 1e-14
    for t, esperado in [(-1, qi), (0, qi), (trayectoria.duracion, qf),
                        (trayectoria.duracion + 1, qf), (100, qf)]:
        # Son destinos conocidos y no otra evaluación del mismo polinomio.
        q, qd, qdd = trayectoria.evaluar(t)
        np.testing.assert_array_equal(q, esperado)
        np.testing.assert_array_equal(qd, [0, 0])
        np.testing.assert_array_equal(qdd, [0, 0])
    if qi == [-np.pi, np.pi]:
        # Un giro envuelto recorrería cero; a mitad del giro real ambos
        # ejes pasan por cero con velocidades opuestas y máximas de 3 rad/s.
        q, qd, qdd = trayectoria.evaluar(trayectoria.duracion / 2)
        np.testing.assert_allclose(q, [0, 0], rtol=0, atol=1e-14)
        np.testing.assert_allclose(qd, [3, -3], rtol=0, atol=1e-14)
        np.testing.assert_allclose(qdd, [0, 0], rtol=0, atol=1e-14)
    print(f"Trayectoria {qi} → {qf}: duración={trayectoria.duracion:.12g} s")


def test_continuidad_y_derivadas_por_diferencias_finitas() -> None:
    """Contrastar derivadas en 19 instantes y continuidad de los extremos.

    Diferencias centrales con h=1e-5 s contrastan qd desde q a 1e-9 rad/s
    y qdd desde qd a 1e-9 rad/s². Los límites interiores a 1e-7 s de
    ambos extremos deben aproximar posición a 1e-12 rad, velocidad a
    1e-12 rad/s y aceleración a 1e-5 rad/s².
    """
    trayectoria = TrayectoriaQuintica([-2, 1], [2.5, -2])
    error_v = error_a = 0.0
    h = 1e-5
    for t in np.linspace(0.05, 0.95, 19) * trayectoria.duracion:
        _, v, a = trayectoria.evaluar(t)
        q_menos, v_menos, _ = trayectoria.evaluar(t - h)
        q_mas, v_mas, _ = trayectoria.evaluar(t + h)
        # Las diferencias centrales son un contraste independiente de las
        # fórmulas analíticas de derivación implementadas en evaluar.
        v_numerica = (q_mas - q_menos) / (2 * h)
        a_numerica = (v_mas - v_menos) / (2 * h)
        np.testing.assert_allclose(v, v_numerica, rtol=0, atol=1e-9)
        np.testing.assert_allclose(a, a_numerica, rtol=0, atol=1e-9)
        error_v = max(error_v, float(np.max(np.abs(v - v_numerica))))
        error_a = max(error_a, float(np.max(np.abs(a - a_numerica))))
    for t, esperado in [(1e-7, trayectoria.qi),
                        (trayectoria.duracion - 1e-7, trayectoria.qf)]:
        q, v, a = trayectoria.evaluar(t)
        np.testing.assert_allclose(q, esperado, rtol=0, atol=1e-12)
        np.testing.assert_allclose(v, [0, 0], rtol=0, atol=1e-12)
        np.testing.assert_allclose(a, [0, 0], rtol=0, atol=1e-5)
    print(f"Derivadas: máxima diferencia qd={error_v:.12g} rad/s; "
          f"qdd={error_a:.12g} rad/s²")


def test_maximos_analiticos_y_sincronizacion() -> None:
    """Verificar 102 amplitudes, máximos exactos y progreso común de los ejes.

    Recorre amplitudes de 0 a 2pi rad. Evalúa velocidad en T/2 y
    aceleración en T(3±sqrt(3))/6, además de una grilla de 501 tiempos.
    Exige límites de 3 rad/s y 6 rad/s² a 1e-12, concordancia con máximos
    analíticos a 1e-12 y duración mínima determinada por al menos un límite.
    """
    velocidad_maxima = aceleracion_maxima = 0.0
    # Incluir 3,2 rad verifica el punto de máxima aceleración global: allí
    # la restricción de velocidad comienza a superar la duración mínima.
    amplitudes = np.unique(np.append(np.linspace(0, 2 * np.pi, 101), 3.2))
    for amplitud in amplitudes:
        qi = np.array([-amplitud / 2, amplitud / 4])
        qf = -qi
        trayectoria = TrayectoriaQuintica(qi, qf)
        T = trayectoria.duracion
        desplazamiento = qf - qi
        _, velocidad_pico, _ = trayectoria.evaluar(T / 2)
        aceleraciones = [trayectoria.evaluar(T * s)[2]
                        for s in ((3 - np.sqrt(3)) / 6, (3 + np.sqrt(3)) / 6)]
        velocidad_esperada = 15 * np.abs(desplazamiento) / (8 * T)
        aceleracion_esperada = (10 * np.sqrt(3) * np.abs(desplazamiento) / (3 * T**2))
        np.testing.assert_allclose(np.abs(velocidad_pico), velocidad_esperada,
                                   rtol=0, atol=1e-12)
        for aceleracion in aceleraciones:
            np.testing.assert_allclose(np.abs(aceleracion), aceleracion_esperada,
                                       rtol=0, atol=1e-12)
        assert np.max(velocidad_esperada) <= 3 + 1e-12
        assert np.max(aceleracion_esperada) <= 6 + 1e-12
        # Si T supera 2 s, disminuirla violaría algún límite activo. Esto
        # verifica minimalidad sin repetir la fórmula usada en __init__.
        assert (T == 2 or abs(np.max(velocidad_esperada) - 3) <= 1e-12 or
                abs(np.max(aceleracion_esperada) - 6) <= 1e-12)
        for t in np.linspace(0, T, 501):
            q, v, a = trayectoria.evaluar(t)
            assert np.max(np.abs(v)) <= 3 + 1e-12
            assert np.max(np.abs(a)) <= 6 + 1e-12
            if amplitud > 0:
                # Desplazamientos de sentidos y amplitudes distintos deben
                # compartir el mismo progreso normalizado, sin terminar antes.
                progreso = (q - qi) / desplazamiento
                assert abs(progreso[0] - progreso[1]) <= 1e-12
                assert -1e-12 <= progreso[0] <= 1 + 1e-12
        velocidad_maxima = max(velocidad_maxima, float(np.max(velocidad_esperada)))
        aceleracion_maxima = max(aceleracion_maxima, float(np.max(aceleracion_esperada)))
    np.testing.assert_allclose(aceleracion_maxima, 8 * np.sqrt(3) / 3,
                               rtol=0, atol=1e-12)
    print(f"102 amplitudes: velocidad máxima={velocidad_maxima:.12g} rad/s; "
          f"aceleración máxima={aceleracion_maxima:.12g} rad/s²")


def test_movimientos_nulos_eje_fijo_y_arrays_independientes() -> None:
    """Verificar referencias nulas, un solo eje y ausencia de mutaciones.

    Para destinos iguales conserva posición exacta y derivadas cero durante
    y después de los 2 s mínimos. Un segundo movimiento deja fijo el eje 2.
    Cambiar entradas o resultados no debe alterar los destinos almacenados.
    """
    qi = np.array([0.7, -0.4])
    qf = qi.copy()
    nula = TrayectoriaQuintica(qi, qf)
    qi[:] = qf[:] = 0
    for t in [-1, 0, 0.7, 1, 2, 3]:
        # Las copias del constructor desacoplan destinos de sus arrays de entrada.
        q, v, a = nula.evaluar(t)
        np.testing.assert_array_equal(q, [0.7, -0.4])
        np.testing.assert_array_equal(v, [0, 0])
        np.testing.assert_array_equal(a, [0, 0])
        q[:] = v[:] = a[:] = 9
    assert nula.duracion == 2
    un_eje = TrayectoriaQuintica([-np.pi, 0.4], [np.pi, 0.4])
    for t in np.linspace(0, un_eje.duracion + 1, 21):
        q, v, a = un_eje.evaluar(t)
        assert q[1] == 0.4 and v[1] == a[1] == 0
    np.testing.assert_array_equal(nula.qi, [0.7, -0.4])
    np.testing.assert_array_equal(nula.qf, [0.7, -0.4])


@pytest.mark.parametrize(
    "qi,qf",
    [([0], [0, 0]), ([0, 0], [[0, 0]]), ([0, 0, 0], [0, 0]),
     ([np.pi + 1e-6, 0], [0, 0]), ([0, 0], [-np.pi - 1e-6, 0]),
     ([np.nan, 0], [0, 0]), ([0, 0], [np.inf, 0])],
)
def test_rechaza_referencias_fuera_del_formato_y_rango(qi: list, qf: list) -> None:
    """Exigir ValueError para tamaños/rangos inválidos y valores no finitos.

    El rechazo corresponde a los destinos de la trayectoria; no cambia ni
    recorta estados físicos, que pueden superar el rango durante la integración.
    """
    # Rechazar la entrada impide ocultar una referencia equivocada mediante
    # envoltura, recorte o conversiones de dimensiones que cambien su sentido.
    with pytest.raises(ValueError):
        TrayectoriaQuintica(qi, qf)
