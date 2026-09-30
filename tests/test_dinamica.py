"""Contraste y propiedades estructurales de la dinámica propia de la etapa 3."""

import numpy as np
import pytest
import sympy as sp

from pendulo.dinamica import Dinamica
from pendulo.modelo import crear_robot, posiciones_geometricas
from pendulo.parametros import BARRAS, GRAVEDAD


@pytest.fixture(scope="module")
def modelo_dinamico() -> tuple:
    """Crear un robot y derivar su dinámica una vez para todas las pruebas.

    Retorna (dinámica propia, robot Toolbox) sin rotor ni fricción. Compartir
    la instancia evita repetir la derivación al evaluar distintos estados.
    """
    # Las dos rutas reciben exactamente los mismos parámetros mecánicos.
    robot = crear_robot()
    return Dinamica(robot), robot


def estados_reproducibles() -> list:
    """Generar 324 estados de contraste, sin azar, con unidades SI.

    Combina 9 valores equiespaciados en [-pi,pi] por eje con cuatro pares
    (velocidad, aceleración). Las velocidades llegan a ±3 rad/s y las
    aceleraciones a ±6 rad/s²; cada estado contiene tres arrays (2,).
    """
    perfiles = [((0, 0), (0, 0)), ((1.2, -0.7), (2, -1)),
                ((-2, 1.5), (-6, 4)), ((3, -3), (6, -6))]
    # Incluir reposo y ambos signos permite detectar errores de términos
    # gravitatorios, centrífugos, cruzados y de aceleración.
    return [(np.array([q1, q2]), np.array(v, dtype=float), np.array(a, dtype=float))
            for q1 in np.linspace(-np.pi, np.pi, 9)
            for q2 in np.linspace(-np.pi, np.pi, 9) for v, a in perfiles]


def potencial_geometrico(q: np.ndarray) -> float:
    """Calcular U en J desde las alturas de los puntos medios de las barras.

    Es una cuenta independiente de las expresiones simbólicas: emplea la
    geometría plana y U=−sum m·g·p. La referencia es Y=0 para ambos centros.
    """
    puntos = posiciones_geometricas(q)
    # Cada centro coincide con el punto medio de su segmento uniforme.
    centros = (puntos[:-1] + puntos[1:]) / 2.0
    return -sum(barra.masa * np.dot(GRAVEDAD, centro)
                for barra, centro in zip(BARRAS, centros))


def test_pseudoinercias_en_terna_distal(modelo_dinamico: tuple) -> None:
    """Verificar segundos y primeros momentos y masa de cada pseudoinercia.

    Para el prisma uniforme: Sxx=mL²/3=0,00144, Syy=3,6e-6 y Szz=9e-7
    kg·m², primer momento X=−0,0108 kg·m y masa 0,108 kg. Se admite
    diferencia absoluta 1e-12 en las unidades de cada bloque.
    """
    dinamica, _ = modelo_dinamico
    esperado = np.array([[0.00144, 0, 0, -0.0108], [0, 3.6e-6, 0, 0],
                         [0, 0, 9e-7, 0], [-0.0108, 0, 0, 0.108]])
    # Los momentos esperados proceden de integrar el prisma en coordenadas
    # DH distales, donde X abarca [-L,0], Y=[-a/2,a/2] y Z=[-e/2,e/2].
    for j in dinamica.pseudoinercias:
        np.testing.assert_allclose(np.array(j, dtype=float), esperado, rtol=0, atol=1e-12)


def test_identidades_simbolicas(modelo_dinamico: tuple) -> None:
    """Verificar simetría de M, antisimetría de Ṁ−2C y G=grad(U) exactas.

    Se simplifican los residuos con SymPy y se exige cero simbólico, sin
    tolerancia numérica. Comprueba las identidades para las expresiones
    derivadas, además del contraste numérico de los otros casos.
    """
    d, _ = modelo_dinamico
    # La combinación de Ṁ y la C de Christoffel tiene parte simétrica nula.
    n = d.M_punto_simbolica - 2 * d.C_simbolica
    assert (d.M_simbolica - d.M_simbolica.T).applyfunc(sp.trigsimp) == sp.zeros(2)
    assert (n + n.T).applyfunc(sp.trigsimp) == sp.zeros(2)
    gradiente = sp.Matrix([sp.diff(d.U_simbolica, q) for q in d.q_simbolica])
    assert (d.G_simbolica - gradiente).applyfunc(sp.trigsimp) == sp.zeros(2, 1)


def test_contraste_toolbox_en_estados_reproducibles(modelo_dinamico: tuple) -> None:
    """Comparar M, G, C·qd e inversa con Toolbox en 324 estados a 1e-12.

    La tolerancia absoluta se expresa en kg·m² para M y N·m para los tres
    torques; rtol=0. No se exige igualdad de las matrices C: se contrasta
    el vector de torque que representan para cada velocidad.
    """
    d, robot = modelo_dinamico
    maximos = dict.fromkeys(["M", "G", "Cqd", "inversa"], 0.0)
    for q, v, a in estados_reproducibles():
        # Toolbox constituye una ruta independiente mediante Newton-Euler;
        # la implementación propia usa trazas y derivadas de la matriz M.
        propios = [d.M(q), d.G(q), d.C(q, v) @ v, d.inversa(q, v, a)]
        referencias = [robot.inertia(q), robot.gravload(q),
                       robot.coriolis(q, v) @ v, robot.rne(q, v, a)]
        for nombre, propio, referencia in zip(maximos, propios, referencias):
            np.testing.assert_allclose(propio, referencia, rtol=0, atol=1e-12)
            maximos[nombre] = max(maximos[nombre], float(np.max(np.abs(propio - referencia))))
    print(f"Contraste 324 estados: {maximos}")


def test_m_positiva_en_grilla(modelo_dinamico: tuple) -> None:
    """Verificar simetría y autovalores positivos en 625 pares articulares.

    Grilla de 25 valores por eje en [-pi,pi], incluidos extremos. Se exige
    simetría a 1e-12 kg·m² y autovalor mínimo estrictamente mayor que cero;
    la grilla aporta evidencia numérica, no una prueba de todo el rango.
    """
    d, _ = modelo_dinamico
    minimo, simetria = np.inf, 0.0
    for q1 in np.linspace(-np.pi, np.pi, 25):
        for q2 in np.linspace(-np.pi, np.pi, 25):
            m = d.M([q1, q2])
            # eigvalsh utiliza la simetría, comprobada antes de interpretar
            # los autovalores como criterio de energía cinética positiva.
            np.testing.assert_allclose(m, m.T, rtol=0, atol=1e-12)
            simetria = max(simetria, float(np.max(np.abs(m - m.T))))
            autovalores = np.linalg.eigvalsh(m)
            assert np.min(autovalores) > 0
            minimo = min(minimo, float(np.min(autovalores)))
    print(f"M: asimetría={simetria:.17g} kg·m²; autovalor mínimo={minimo:.17g} kg·m²")


def test_m_punto_y_antisimetria_numericas(modelo_dinamico: tuple) -> None:
    """Contrastar Ṁ por diferencias centrales y antisimetría en 324 estados.

    Usa paso temporal h=1e-6 s, evaluando M(q±h·qd). Tolerancia 1e-10
    kg·m²/s para diferencias finitas y 1e-12 kg·m²/s para la parte simétrica
    de Ṁ−2C. Verifica también la potencia cuadrática nula a 1e-12 W.
    """
    d, _ = modelo_dinamico
    max_derivada = max_simetrica = max_potencia = 0.0
    h = 1e-6
    for q, v, _ in estados_reproducibles():
        # La derivada numérica es independiente de la diferenciación simbólica.
        numerica = (d.M(q + h * v) - d.M(q - h * v)) / (2 * h)
        mdot = d.M_punto(q, v)
        np.testing.assert_allclose(mdot, numerica, rtol=0, atol=1e-10)
        n = mdot - 2 * d.C(q, v)
        np.testing.assert_allclose(n + n.T, np.zeros((2, 2)), rtol=0, atol=1e-12)
        potencia = float(v @ n @ v)
        assert abs(potencia) <= 1e-12
        max_derivada = max(max_derivada, float(np.max(np.abs(mdot - numerica))))
        max_simetrica = max(max_simetrica, float(np.max(np.abs(n + n.T))))
        max_potencia = max(max_potencia, abs(potencia))
    print(f"Ṁ: diferencia={max_derivada:.17g} kg·m²/s; "
          f"parte simétrica={max_simetrica:.17g} kg·m²/s; potencia={max_potencia:.17g} W")


def test_gravedad_y_potencial_geometrico(modelo_dinamico: tuple) -> None:
    """Contrastar U geométrica y G por gradiente numérico en 81 posiciones.

    Usa nueve ángulos por eje en [-pi,pi], h=1e-6 rad y diferencias
    centrales del potencial geométrico. Exige diferencia en U ≤1e-12 J
    y en gradiente ≤1e-9 N·m; rtol=0.
    """
    d, _ = modelo_dinamico
    max_u = max_g = 0.0
    h = 1e-6
    for q1 in np.linspace(-np.pi, np.pi, 9):
        for q2 in np.linspace(-np.pi, np.pi, 9):
            q = np.array([q1, q2])
            geom = potencial_geometrico(q)
            np.testing.assert_allclose(d.potencial(q), geom, rtol=0, atol=1e-12)
            gradiente = np.zeros(2)
            # Diferenciar las alturas geométricas evita validar G solo contra
            # otra expresión derivada de las mismas transformaciones simbólicas.
            for eje in range(2):
                desplazamiento = np.zeros(2)
                desplazamiento[eje] = h
                gradiente[eje] = (potencial_geometrico(q + desplazamiento) -
                                 potencial_geometrico(q - desplazamiento)) / (2 * h)
            np.testing.assert_allclose(d.G(q), gradiente, rtol=0, atol=1e-9)
            max_u = max(max_u, abs(d.potencial(q) - geom))
            max_g = max(max_g, float(np.max(np.abs(d.G(q) - gradiente))))
    print(f"Potencial: diferencia={max_u:.17g} J; gradiente={max_g:.17g} N·m")


@pytest.mark.parametrize(
    "q, torque, potencial",
    [((0, 0), (0.423792, 0.105948), 0),
     ((-np.pi / 2, 0), (0, 0), -0.423792),
     ((np.pi / 2, 0), (0, 0), 0.423792),
     ((0, np.pi), (0.211896, -0.105948), 0),
     ((np.pi, 0), (-0.423792, -0.105948), 0)],
    ids=["horizontal", "colgante", "invertida", "plegada", "hacia_izquierda"],
)
def test_sosten_y_energia_conocidos(
    modelo_dinamico: tuple, q: tuple, torque: tuple, potencial: float
) -> None:
    """Verificar torque estático y potencial contra cuentas manuales conocidas.

    Sin movimiento, las cuentas usan los pesos y brazos horizontales de
    los centros de ambas barras. Tolerancias absolutas 1e-12 N·m y 1e-12 J.
    Colgante e invertida tienen torque cero, aunque distinto potencial.
    """
    d, robot = modelo_dinamico
    # En reposo, la dinámica inversa debe reducirse exactamente al término G;
    # los valores esperados no dependen de la implementación propia ni de RTB.
    np.testing.assert_allclose(d.G(q), torque, rtol=0, atol=1e-12)
    np.testing.assert_allclose(d.inversa(q, np.zeros(2), np.zeros(2)), torque,
                               rtol=0, atol=1e-12)
    np.testing.assert_allclose(robot.rne(q, np.zeros(2), np.zeros(2)), torque,
                               rtol=0, atol=1e-12)
    np.testing.assert_allclose(d.potencial(q), potencial, rtol=0, atol=1e-12)


def test_evaluacion_no_repite_derivacion(modelo_dinamico: tuple, monkeypatch) -> None:
    """Comprobar que evaluar términos numéricos no vuelve a diferenciar símbolos.

    Después de construir la instancia se intercepta Matrix.diff; cualquier
    llamada durante M, C, G, Ṁ, U o inversa produce un fallo explícito.
    """
    d, _ = modelo_dinamico

    def impedir_derivacion(*args, **kwargs) -> None:
        """Fallar si se intenta diferenciar durante una evaluación numérica."""
        # Este reemplazo convierte una derivación inadvertida en fallo visible.
        pytest.fail("Se intentó derivar durante una evaluación numérica")

    # La restauración automática al terminar la prueba no altera otras pruebas.
    monkeypatch.setattr(sp.MatrixBase, "diff", impedir_derivacion)
    q, v, a = np.array([0.4, -0.7]), np.array([1.2, -0.8]), np.array([2.0, -1.0])
    assert np.isfinite(d.M(q)).all()
    assert np.isfinite(d.C(q, v)).all()
    assert np.isfinite(d.G(q)).all()
    assert np.isfinite(d.M_punto(q, v)).all()
    assert np.isfinite(d.potencial(q))
    assert np.isfinite(d.inversa(q, v, a)).all()
