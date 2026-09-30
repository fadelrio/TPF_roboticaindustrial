"""Dinámica propia del 2R: trazas con pseudoinercias y símbolos de Christoffel.

Las expresiones se derivan al construir una instancia y se evalúan con NumPy.
El modelo de esta etapa contiene solamente las barras, sin accionamiento ni
fricción. Las convenciones de posición y gravedad son las de ``crear_robot``.
"""

import numpy as np
import roboticstoolbox as rtb
import sympy as sp


def _racional(valor: float) -> sp.Rational:
    """Representar el valor numérico del modelo como decimal racional exacto.

    Conserva la representación decimal del float recibido, incluidos sus
    residuos de redondeo. Evita que el álgebra simbólica acumule nuevos
    redondeos; no atribuye mayor exactitud física a los parámetros.
    """
    # No aproximar a fracciones pequeñas: los datos usados deben conservarse.
    return sp.Rational(str(float(valor)))


def pseudoinercia(masa: float, centro: np.ndarray, inercia: np.ndarray) -> sp.Matrix:
    """Construir la pseudoinercia homogénea (4,4) en la terna del eslabón.

    ``masa`` está en kg; ``centro`` es un vector (3,) en m respecto de DH;
    ``inercia`` es el tensor central (3,3) en kg·m², en los mismos ejes.
    El bloque superior contiene segundos momentos en kg·m², los bloques
    laterales primeros momentos en kg·m y la esquina inferior la masa en kg.
    """
    m = _racional(masa)
    r = sp.Matrix([_racional(x) for x in centro])
    tensor = sp.Matrix([[_racional(x) for x in fila] for fila in inercia])

    # En el centro, S_G=tr(I_G)/2·Id−I_G. El término m·r·rᵀ traslada los
    # segundos momentos al origen DH; equivale a aplicar Steiner al tensor.
    segundos = sp.trace(tensor) / 2 * sp.eye(3) - tensor + m * r * r.T
    j = sp.zeros(4)
    j[:3, :3] = segundos
    j[:3, 3] = m * r
    j[3, :3] = m * r.T
    j[3, 3] = m
    return j


class Dinamica:
    """Derivación simbólica y evaluación numérica de un modelo 2R sin actuadores.

    Recibe el DH estándar construido por ``crear_robot``: base/herramienta
    identidad, d=alpha=offset=0 y dos articulaciones revolutas. Se crea una
    instancia por modelo, fuera de la integración. Las expresiones conservan
    los parámetros presentes al construirla; si estos cambian hay que crear
    otra instancia. Los arrays articulares de entrada son de forma (2,) en SI.
    """

    def __init__(self, robot: rtb.DHRobot) -> None:
        """Derivar M, C, G, Ṁ y potencial y preparar sus funciones numéricas.

        Lee longitudes, masas, centros, tensores y gravedad del robot, sin
        invocar sus rutinas dinámicas. ``q_simbolica`` y ``qd_simbolica``
        identifican las variables; las matrices simbólicas quedan disponibles
        para inspección y las funciones compiladas se usan en cada evaluación.
        """
        self.q_simbolica = sp.symbols("q1 q2", real=True)
        self.qd_simbolica = sp.symbols("v1 v2", real=True)
        q, v = self.q_simbolica, self.qd_simbolica
        transformaciones, pseudoinercias, centros, masas = [], [], [], []
        acumulada = sp.eye(4)
        for angulo, eslabon in zip(q, robot.links):
            l = _racional(eslabon.a)
            c, s = sp.cos(angulo), sp.sin(angulo)
            # A0_i se acumula desde la base; cada paso usa DH estándar del 2R.
            local = sp.Matrix([[c, -s, 0, l * c], [s, c, 0, l * s],
                               [0, 0, 1, 0], [0, 0, 0, 1]])
            acumulada = sp.trigsimp(acumulada * local)
            transformaciones.append(sp.ImmutableMatrix(acumulada))
            pseudoinercias.append(sp.ImmutableMatrix(
                pseudoinercia(eslabon.m, eslabon.r, eslabon.I)))
            centros.append(sp.Matrix([*[_racional(x) for x in eslabon.r], 1]))
            masas.append(_racional(eslabon.m))
        self.transformaciones = tuple(transformaciones)
        self.pseudoinercias = tuple(pseudoinercias)

        # La traza integra la energía cinética de cada cuerpo usando la
        # derivada de su transformación y su distribución de masa homogénea.
        derivadas = [[a.diff(angulo) for angulo in q] for a in transformaciones]
        m = sp.zeros(2)
        for s in range(2):
            for k in range(2):
                m[s, k] = sp.trigsimp(sum(
                    sp.trace(derivadas[i][s] * pseudoinercias[i] * derivadas[i][k].T)
                    for i in range(2)))
        self.M_simbolica = sp.ImmutableMatrix(m)

        # Christoffel fija una representación de C coherente con M. Las
        # derivadas de M también permiten calcular Ṁ sin diferencias finitas.
        dm = [m.diff(angulo) for angulo in q]
        c = sp.zeros(2)
        for s in range(2):
            for j in range(2):
                c[s, j] = sp.trigsimp(sum(
                    (dm[k][s, j] + dm[j][s, k] - dm[s][j, k]) * v[k] / 2
                    for k in range(2)))
        self.C_simbolica = sp.ImmutableMatrix(c)
        mdot = dm[0] * v[0] + dm[1] * v[1]
        self.M_punto_simbolica = sp.ImmutableMatrix(mdot)

        # La gravedad homogénea tiene última componente cero y cada centro
        # última componente uno. G se obtiene por la fórmula de la cursada;
        # el potencial se calcula por separado para contrastar su gradiente.
        gravedad = sp.Matrix([*[_racional(x) for x in robot.gravity], 0])
        g = sp.zeros(2, 1)
        for s in range(2):
            g[s] = sp.trigsimp(-sum(masas[i] *
                (gravedad.T * derivadas[i][s] * centros[i])[0] for i in range(2)))
        self.G_simbolica = sp.ImmutableMatrix(g)
        self.U_simbolica = sp.trigsimp(-sum(masas[i] *
            (gravedad.T * transformaciones[i] * centros[i])[0] for i in range(2)))

        # Lambdify genera evaluadores NumPy una sola vez. Ninguna llamada de
        # M, C o G durante la simulación ejecutará diferenciación simbólica.
        self._m = sp.lambdify(q, self.M_simbolica, modules="numpy")
        self._c = sp.lambdify((*q, *v), self.C_simbolica, modules="numpy")
        self._g = sp.lambdify(q, self.G_simbolica, modules="numpy")
        self._mdot = sp.lambdify((*q, *v), self.M_punto_simbolica, modules="numpy")
        self._u = sp.lambdify(q, self.U_simbolica, modules="numpy")

    def M(self, q: np.ndarray) -> np.ndarray:
        """Evaluar la matriz de inercia (2,2) en kg·m² para q (2,) en rad."""
        # Convertir a float mantiene una interfaz numérica sin objetos SymPy.
        return np.asarray(self._m(*q), dtype=float)

    def C(self, q: np.ndarray, qd: np.ndarray) -> np.ndarray:
        """Evaluar C (2,2) en kg·m²/s para q en rad y qd en rad/s."""
        # Desplegar ambos vectores sigue el orden de argumentos de lambdify.
        return np.asarray(self._c(*q, *qd), dtype=float)

    def G(self, q: np.ndarray) -> np.ndarray:
        """Evaluar el torque de gravedad (2,) en N·m para q (2,) en rad."""
        # La expresión simbólica es una columna; la interfaz articular es plana.
        return np.asarray(self._g(*q), dtype=float).reshape(2)

    def M_punto(self, q: np.ndarray, qd: np.ndarray) -> np.ndarray:
        """Evaluar Ṁ (2,2) en kg·m²/s usando q (rad) y qd (rad/s)."""
        # Es la derivada direccional sum_k (∂M/∂q_k)·qd_k, evaluada directamente.
        return np.asarray(self._mdot(*q, *qd), dtype=float)

    def potencial(self, q: np.ndarray) -> float:
        """Evaluar energía potencial en J, con referencia cero en altura Y=0."""
        # La referencia es U=−sum m·gᵀ·p_G, sin un desplazamiento constante.
        return float(self._u(*q))

    def inversa(self, q: np.ndarray, qd: np.ndarray, qdd: np.ndarray) -> np.ndarray:
        """Calcular torque (2,) en N·m: M(q)qdd+C(q,qd)qd+G(q).

        q, qd y qdd tienen dos componentes en rad, rad/s y rad/s².
        No añade fricción ni satura torque: esos efectos pertenecen a la etapa 5.
        """
        # Componer los tres términos conserva sus unidades y permite
        # contrastarlos por separado con la dinámica inversa de Toolbox.
        return self.M(q) @ qdd + self.C(q, qd) @ qd + self.G(q)
