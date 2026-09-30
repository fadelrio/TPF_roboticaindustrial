"""Verificaciones físicas, de referencias y cinemáticas de la etapa 2."""

import numpy as np
import pytest

from pendulo.modelo import crear_robot, posiciones_geometricas, posiciones_toolbox
from pendulo.parametros import BARRAS, GRAVEDAD


def test_propiedades_geometricas_y_transferencia_a_toolbox() -> None:
    """Contrastar cada barra con valores analíticos en SI y su carga en Toolbox.

    Se espera masa 0,108 kg, centro distal (-0,1,0,0) m y tensor central
    diag(4,5e-6; 3,609e-4; 3,636e-4) kg·m². La tolerancia absoluta es 1e-12
    en cada unidad. Verifica también el tensor trasladado al extremo por Steiner.
    """
    robot = crear_robot()
    for barra, eslabon in zip(BARRAS, robot.links):
        # Valores calculados independientemente a partir de las dimensiones
        # en SI, contrastados tanto con las propiedades como con el modelo.
        np.testing.assert_allclose(barra.masa, 0.108, rtol=0, atol=1e-12)
        np.testing.assert_allclose(barra.centro_masa, [-0.1, 0, 0], rtol=0, atol=1e-12)
        esperado = np.diag([4.5e-6, 3.609e-4, 3.636e-4])
        np.testing.assert_allclose(barra.inercia, esperado, rtol=0, atol=1e-12)
        np.testing.assert_allclose(eslabon.m, 0.108, rtol=0, atol=1e-12)
        np.testing.assert_allclose(eslabon.r, [-0.1, 0, 0], rtol=0, atol=1e-12)
        np.testing.assert_allclose(eslabon.I, esperado, rtol=0, atol=1e-12)

        # Este traslado sirve de comprobación; el modelo conserva I central
        # porque cargar el tensor distal duplicaría el efecto de la distancia.
        r = barra.centro_masa
        distal = barra.inercia + barra.masa * (r @ r * np.eye(3) - np.outer(r, r))
        np.testing.assert_allclose(
            distal, np.diag([4.5e-6, 1.4409e-3, 1.4436e-3]), rtol=0, atol=1e-12
        )


def test_convenciones_dh_y_ausencia_de_actuadores() -> None:
    """Verificar DH estándar, gravedad física y parámetros sin accionamiento.

    Confirma dos articulaciones revolutas, longitudes de 0,2 m, desplazamientos
    y torsiones nulos, base/herramienta identidad y efectos de actuadores nulos.
    """
    robot = crear_robot()
    assert robot.n == 2
    assert not robot.mdh
    np.testing.assert_array_equal(robot.gravity, GRAVEDAD)
    np.testing.assert_array_equal(robot.base.A, np.eye(4))
    np.testing.assert_array_equal(robot.tool.A, np.eye(4))
    for eslabon in robot.links:
        # La relación unitaria no añade transmisión: con Jm y fricción cero
        # solo quedan los cuerpos rígidos de las barras en esta etapa.
        assert eslabon.sigma == 0
        assert eslabon.a == 0.20
        assert eslabon.d == eslabon.alpha == eslabon.offset == 0.0
        assert eslabon.Jm == eslabon.B == 0.0
        assert eslabon.G == 1.0
        np.testing.assert_array_equal(eslabon.Tc, [0.0, 0.0])


@pytest.mark.parametrize(
    "q, esperadas",
    [
        ((0, 0), [[0, 0, 0], [0.2, 0, 0], [0.4, 0, 0]]),
        ((-np.pi / 2, 0), [[0, 0, 0], [0, -0.2, 0], [0, -0.4, 0]]),
        ((np.pi / 2, 0), [[0, 0, 0], [0, 0.2, 0], [0, 0.4, 0]]),
        ((0, np.pi), [[0, 0, 0], [0.2, 0, 0], [0, 0, 0]]),
        ((0, np.pi / 2), [[0, 0, 0], [0.2, 0, 0], [0.2, 0.2, 0]]),
        ((np.pi / 2, -np.pi / 2), [[0, 0, 0], [0, 0.2, 0], [0.2, 0.2, 0]]),
    ],
    ids=["horizontal", "colgante", "invertida", "plegada", "q2_positivo", "q2_relativo"],
)
def test_posiciones_conocidas(q: tuple, esperadas: list) -> None:
    """Contrastar geometría y Toolbox con posiciones conocidas, a 1e-12 m.

    Incluye los cuatro casos de cierre y dos casos que distinguen el signo
    de q2 y su carácter relativo. Las coordenadas esperadas son XYZ en metros.
    """
    # Los valores esperados son posiciones conocidas, sin reutilizar ninguna
    # de las dos implementaciones de la cinemática que se están verificando.
    np.testing.assert_allclose(posiciones_geometricas(q), esperadas, rtol=0, atol=1e-12)
    np.testing.assert_allclose(
        posiciones_toolbox(crear_robot(), q), esperadas, rtol=0, atol=1e-12
    )


def test_cinematica_y_centros_en_grilla_reproducible() -> None:
    """Contrastar 625 pares y centros globales en [-pi,pi]², a 1e-12 m.

    Usa 25 valores equiespaciados por eje, incluidos extremos. Verifica
    centros transformados desde DH contra los puntos medios geométricos y
    orientación del extremo contra una rotación q1+q2, a 1e-12 adimensional.
    """
    robot = crear_robot()
    max_posicion = max_centro = max_rotacion = 0.0
    for q1 in np.linspace(-np.pi, np.pi, 25):
        for q2 in np.linspace(-np.pi, np.pi, 25):
            q = np.array([q1, q2])
            geometria = posiciones_geometricas(q)
            toolbox = posiciones_toolbox(robot, q)
            np.testing.assert_allclose(toolbox, geometria, rtol=0, atol=1e-12)
            max_posicion = max(max_posicion, np.max(np.abs(toolbox - geometria)))

            # Transformar cada centro local contrasta la referencia distal
            # con la interpretación física de barra uniforme entre articulaciones.
            ternas = robot.fkine_all(q, old=False)
            for i, barra in enumerate(BARRAS):
                centro = ternas[i + 1].R @ barra.centro_masa + ternas[i + 1].t
                esperado = (geometria[i] + geometria[i + 1]) / 2.0
                np.testing.assert_allclose(centro, esperado, rtol=0, atol=1e-12)
                max_centro = max(max_centro, np.max(np.abs(centro - esperado)))

            # La orientación absoluta del segundo eslabón acumula ambos ángulos.
            c, s = np.cos(q1 + q2), np.sin(q1 + q2)
            rotacion = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
            np.testing.assert_allclose(ternas[2].R, rotacion, rtol=0, atol=1e-12)
            max_rotacion = max(max_rotacion, np.max(np.abs(ternas[2].R - rotacion)))
            np.testing.assert_allclose(robot.fkine(q).A, ternas[2].A, rtol=0, atol=1e-12)
    print(f"Grilla: posición={max_posicion:.17g} m; centro={max_centro:.17g} m; "
          f"rotación={max_rotacion:.17g}")


def test_angulos_y_estado_no_se_modifican() -> None:
    """Comprobar que evaluar fuera del rango de destinos no recorta ni altera q.

    Usa q=(2pi+0,3; -2pi-0,2) rad y verifica la rotación DH del primer
    eslabón con el ángulo original. El rango acordado es para destinos,
    no constituye un tope físico de la planta.
    """
    robot = crear_robot()
    q = np.array([2 * np.pi + 0.3, -2 * np.pi - 0.2])
    original = q.copy()
    estado = robot.q.copy()
    # Un recorte a [-pi,pi] produciría otra geometría en este caso. La
    # periodicidad de las rotaciones no implica modificar el array articular.
    np.testing.assert_allclose(
        posiciones_toolbox(robot, q), posiciones_geometricas(q), rtol=0, atol=1e-12
    )
    np.testing.assert_array_equal(q, original)
    np.testing.assert_array_equal(robot.q, estado)
    np.testing.assert_allclose(
        robot.links[0].A(q[0]).R[0, 0], np.cos(q[0]), rtol=0, atol=1e-12
    )
