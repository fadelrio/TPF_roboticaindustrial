"""Verificaciones de rotor, rozamiento y torque limitado de la etapa 5."""

import numpy as np
import pytest
from scipy.integrate import trapezoid

from pendulo.dinamica import Dinamica
from pendulo.modelo import crear_robot, crear_robot_actuado, posiciones_toolbox
from pendulo.parametros import (ACTUADORES, BARRAS, Friccion, GRAVEDAD,
                                LIMITES_TORQUE, componentes_codo)
from pendulo.simulacion import limitar_torque, simular_libre, simular_planta


@pytest.mark.parametrize("escala", [0.0, 0.5, 1.0, 2.0])
def test_friccion_suave_y_disipativa(escala: float) -> None:
    """Verificar rozamiento en 441 pares de velocidades, en ambos sentidos.

    Combina 21 velocidades por eje entre −3 y 3 rad/s, incluyendo valores
    próximos a epsilon y cero. Exige f(−v)=−f(v), f(0)=0 y v·f(v)≥0;
    contrasta los torques nominales a 3 rad/s con (0,09;0,025) N·m a 1e-14.
    """
    f = Friccion(escala=escala)
    valores = np.array([-3, -2, -1, -0.1, -0.03, -0.02, -0.01, -0.005,
                        -0.001, -1e-8, 0, 1e-8, 0.001, 0.005, 0.01, 0.02,
                        0.03, 0.1, 1, 2, 3])
    potencia_minima = np.inf
    for v1 in valores:
        for v2 in valores:
            v = np.array([v1, v2])
            # El signo resistente se interpreta al restar f en la planta.
            # La simetría impar también permite comprobar ambos sentidos.
            np.testing.assert_allclose(f.torque(-v), -f.torque(v), rtol=0, atol=1e-14)
            potencia = float(v @ f.torque(v))
            assert potencia >= 0
            potencia_minima = min(potencia_minima, potencia)
    np.testing.assert_array_equal(f.torque(np.zeros(2)), [0, 0])
    np.testing.assert_allclose(f.torque([3, 3]), escala * np.array([0.09, 0.025]),
                               rtol=0, atol=1e-14)
    # Cerca de cero, la pendiente analítica es B+Tc/epsilon: no hay salto
    # de Coulomb ni torque estático impuesto en reposo.
    h = 1e-8
    pendiente = (f.torque([h, h]) - f.torque([-h, -h])) / (2 * h)
    np.testing.assert_allclose(pendiente, escala * np.array([3.02, 1.005]),
                               rtol=0, atol=1e-10)
    print(f"Fricción escala {escala}: mínimo v·f={potencia_minima:.12g} W; "
          f"f(3,3)={f.torque([3, 3])} N·m; pendiente en cero={pendiente}")


def test_saturacion_simetrica_sin_mutaciones() -> None:
    """Verificar saturación de 25 solicitudes, sin modificar sus arrays.

    Incluye pedidos nulos, dentro del rango, exactamente en los límites y
    por encima en ambos signos. Exige igualdad con el recorte analítico,
    conservando la solicitud original, con límites (1,20;0,31) N·m.
    """
    for t1 in [-2, -1.2, 0, 1.2, 2]:
        for t2 in [-1, -0.31, 0, 0.31, 1]:
            pedido = np.array([t1, t2])
            original = pedido.copy()
            # Calcular cada eje con min/max ofrece una referencia independiente
            # del np.clip utilizado por la implementación.
            esperado = [max(-1.2, min(1.2, t1)), max(-0.31, min(0.31, t2))]
            np.testing.assert_array_equal(limitar_torque(pedido), esperado)
            np.testing.assert_array_equal(pedido, original)


@pytest.fixture(scope="module")
def modelo_con_rotores() -> Dinamica:
    """Derivar barras con los rotores aprobados, aislando N²Jm del montaje.

    Es un modelo auxiliar de diagnóstico, sin masa de carcasa transportada.
    Su propósito es distinguir la inercia reflejada de la composición rígida.
    """
    robot = crear_robot()
    # El rotor se carga en los campos Jm y G del robot, exactamente una vez.
    for link, actuador in zip(robot.links, ACTUADORES):
        link.Jm, link.G = actuador.inercia_rotor, actuador.relacion
    return Dinamica(robot)


@pytest.fixture(scope="module")
def modelo_ampliado() -> tuple:
    """Derivar una vez el modelo con cuerpos transportados y ambos rotores.

    Retorna dinámica propia y robot Toolbox con los mismos parámetros.
    La fricción no está en el robot: se contrasta como término separado.
    """
    robot = crear_robot_actuado()
    # Compartir la derivación mantiene las pruebas numéricas fuera de SymPy.
    return Dinamica(robot), robot


def test_montaje_masa_centro_tensor_y_cinematica(modelo_ampliado: tuple) -> None:
    """Contrastar propiedades del montaje con cuentas geométricas independientes.

    Masa 0,252 kg y centros cilíndricos en Z=(−0,0075;−0,0232;−0,0535) m.
    Se suman segundos momentos en el origen del codo y se traslada el total
    al centro común. Tolerancias 1e-12 kg, m y kg·m². La cinemática se
    compara con las barras originales en 81 configuraciones a 1e-12 m.
    """
    _, robot = modelo_ampliado
    originales = crear_robot()
    masas = np.array([0.020, 0.058, 0.066])
    longitudes = np.array([0.005, 0.0264, 0.0342])
    z = np.array([-0.0075, -0.0232, -0.0535])
    for cuerpo, masa, longitud, altura in zip(componentes_codo(), masas, longitudes, z):
        np.testing.assert_allclose(cuerpo.masa, masa, rtol=0, atol=1e-12)
        np.testing.assert_allclose(cuerpo.centro_masa, [0, 0, altura], rtol=0, atol=1e-12)
        esperado = np.diag([masa * (0.011**2 / 4 + longitud**2 / 12)] * 2 +
                           [masa * 0.011**2 / 2])
        np.testing.assert_allclose(cuerpo.inercia, esperado, rtol=0, atol=1e-12)

    centro = np.array([-0.108 * 0.1, 0, masas @ z]) / 0.252
    # Primero sumar las inercias respecto del origen común, con brazos X
    # de la barra y Z de los cilindros. Esta ruta evita recomponer por el
    # mismo algoritmo de traslaciones individuales al centro implementado.
    origen = np.diag([4.5e-6, 0.0014409, 0.0014436])
    transversal = np.sum(masas * (0.011**2 / 4 + longitudes**2 / 12 + z**2))
    origen += np.diag([transversal, transversal, np.sum(masas) * 0.011**2 / 2])
    esperado = origen - 0.252 * (centro @ centro * np.eye(3) - np.outer(centro, centro))
    link = robot.links[0]
    np.testing.assert_allclose(link.m, 0.252, rtol=0, atol=1e-12)
    np.testing.assert_allclose(link.r, centro, rtol=0, atol=1e-12)
    np.testing.assert_allclose(link.I, esperado, rtol=0, atol=1e-12)
    assert np.linalg.eigvalsh(link.I).min() > 0
    np.testing.assert_allclose(robot.links[1].m, BARRAS[1].masa, rtol=0, atol=1e-12)
    np.testing.assert_array_equal(robot.links[1].r, BARRAS[1].centro_masa)
    np.testing.assert_array_equal(robot.links[1].I, BARRAS[1].inercia)
    assert all(eslabon.B == 0 and np.all(eslabon.Tc == 0) for eslabon in robot.links)
    for q1 in np.linspace(-np.pi, np.pi, 9):
        for q2 in np.linspace(-np.pi, np.pi, 9):
            np.testing.assert_allclose(posiciones_toolbox(robot, [q1, q2]),
                                       posiciones_toolbox(originales, [q1, q2]),
                                       rtol=0, atol=1e-12)
    print(f"Montaje: masa={link.m:.15g} kg; centro DH={link.r} m; "
          f"tensor central [kg·m²]=\n{link.I}; "
          f"diferencia tensor={np.max(np.abs(link.I - esperado)):.12g} kg·m²")


def test_dinamica_ampliada_y_efectos_separados(modelo_ampliado: tuple) -> None:
    """Comparar M, G, Cqd e inversa ampliadas con Toolbox en 324 estados.

    Usa nueve ángulos por eje en [-pi,pi] y cuatro pares (qd,qdd), hasta
    ±3 rad/s y ±6 rad/s². Exige diferencias ≤1e-12 en unidades respectivas.
    Contrasta M con barras más diag(0,005768712;0) por montaje y N²Jm por
    rotor; G con pesos y C con la expresión manual previa sin modificaciones.
    """
    d, robot = modelo_ampliado
    perfiles = [([0, 0], [0, 0]), ([1.2, -0.7], [2, -1]),
                ([-2, 1.5], [-6, 4]), ([3, -3], [6, -6])]
    maximos = dict.fromkeys(["M", "G", "Cqd", "inversa"], 0.0)
    for q1 in np.linspace(-np.pi, np.pi, 9):
        for q2 in np.linspace(-np.pi, np.pi, 9):
            q = np.array([q1, q2])
            c, s = np.cos(q2), np.sin(q2)
            barras = np.array([[0.0072072 + 0.00432 * c, 0.0014436 + 0.00216 * c],
                               [0.0014436 + 0.00216 * c, 0.0014436]])
            # El conjunto del codo gira solo con q1. Su masa puntual aporta
            # mL1² y sus cilindros mR²/2; no aporta acoplamientos con q2.
            montaje = np.diag([0.144 * 0.2**2 + 0.144 * 0.011**2 / 2, 0])
            rotores = np.diag([0.003774808, 0.000352872])
            np.testing.assert_allclose(d.M(q), barras + montaje + rotores,
                                       rtol=0, atol=1e-12)
            gravedad = [0.600372 * np.cos(q1) + 0.105948 * np.cos(q1 + q2),
                        0.105948 * np.cos(q1 + q2)]
            np.testing.assert_allclose(d.G(q), gravedad, rtol=0, atol=1e-12)
            for velocidad, aceleracion in perfiles:
                v, a = np.array(velocidad, dtype=float), np.array(aceleracion, dtype=float)
                c_manual = 0.00216 * s * np.array([[-v[1], -(v[0] + v[1])], [v[0], 0]])
                np.testing.assert_allclose(d.C(q, v), c_manual, rtol=0, atol=1e-12)
                propios = [d.M(q), d.G(q), d.C(q, v) @ v, d.inversa(q, v, a)]
                referencias = [robot.inertia(q), robot.gravload(q),
                               robot.coriolis(q, v) @ v, robot.rne(q, v, a)]
                for nombre, propio, referencia in zip(maximos, propios, referencias):
                    np.testing.assert_allclose(propio, referencia, rtol=0, atol=1e-12)
                    maximos[nombre] = max(maximos[nombre],
                                         float(np.max(np.abs(propio - referencia))))
                # Toolbox no implementa tanh: la inversa completa de planta
                # se verifica sumando el mismo rozamiento suave por separado.
                perdida = Friccion().torque(v)
                np.testing.assert_allclose(d.inversa(q, v, a) + perdida,
                                           robot.rne(q, v, a) + perdida,
                                           rtol=0, atol=1e-12)
    print(f"Contraste ampliado 324 estados: {maximos}; "
          "incremento montaje M11=0.005768712 kg·m²; rotores=(0.003774808,0.000352872)")


def test_propiedades_estructurales_y_potencial_ampliado(modelo_ampliado: tuple) -> None:
    """Verificar M positiva y simétrica, antisimetría y energía gravitatoria.

    Grilla de 625 posiciones: autovalor mínimo positivo, simetría de M a
    1e-12 kg·m² y parte simétrica de Mdot−2C a 1e-12 kg·m²/s. Contrasta U
    con alturas geométricas y G con diferencias centrales h=1e-6 rad,
    admitiendo 1e-12 J y 1e-9 N·m respectivamente.
    """
    d, _ = modelo_ampliado

    def potencial_alturas(q: np.ndarray) -> float:
        """Evaluar U en J con centros de barras y 144 g a la altura del codo."""
        q1, q2 = q
        # Los desplazamientos axiales Z no cambian alturas Y ni potencial.
        altura1 = 0.1 * np.sin(q1)
        altura2 = 0.2 * np.sin(q1) + 0.1 * np.sin(q1 + q2)
        altura_codo = 0.2 * np.sin(q1)
        return -GRAVEDAD[1] * (0.108 * altura1 + 0.108 * altura2 + 0.144 * altura_codo)

    minimo = np.inf
    residuo_skew = diferencia_u = diferencia_g = 0.0
    v, h = np.array([1.2, -0.7]), 1e-6
    for q1 in np.linspace(-np.pi, np.pi, 25):
        for q2 in np.linspace(-np.pi, np.pi, 25):
            q = np.array([q1, q2])
            m = d.M(q)
            np.testing.assert_allclose(m, m.T, rtol=0, atol=1e-12)
            minimo = min(minimo, float(np.linalg.eigvalsh(m).min()))
            n = d.M_punto(q, v) - 2 * d.C(q, v)
            residuo_skew = max(residuo_skew, float(np.max(np.abs(n + n.T))))
            diferencia_u = max(diferencia_u, abs(d.potencial(q) - potencial_alturas(q)))
            gradiente = np.array([(potencial_alturas(q + h * eje) -
                                  potencial_alturas(q - h * eje)) / (2 * h)
                                 for eje in np.eye(2)])
            diferencia_g = max(diferencia_g, float(np.max(np.abs(d.G(q) - gradiente))))
    assert minimo > 0
    assert residuo_skew <= 1e-12
    assert diferencia_u <= 1e-12
    assert diferencia_g <= 1e-9
    np.testing.assert_allclose(d.G([0, 0]), [0.70632, 0.105948], rtol=0, atol=1e-12)
    np.testing.assert_allclose(d.G([-np.pi / 2, 0]), [0, 0], rtol=0, atol=1e-12)
    np.testing.assert_allclose(d.G([np.pi / 2, 0]), [0, 0], rtol=0, atol=1e-12)
    print(f"Ampliado: autovalor mínimo={minimo:.12g} kg·m²; "
          f"residuo antisimetría={residuo_skew:.12g} kg·m²/s; "
          f"ΔU={diferencia_u:.12g} J; ΔgradU={diferencia_g:.12g} N·m")


def test_torque_registrado_y_usado_por_la_planta(modelo_ampliado: tuple) -> None:
    """Comprobar el registro y efecto físico de una solicitud saturada.

    En el modelo completo, desde el colgante en reposo, integrar 0,05 s
    con pedido (2;−1) N·m y
    fricción nominal. Comparar con pedir directamente (1,20;−0,31) N·m.
    Las trayectorias deben coincidir a 1e-12 rad y rad/s y los registros
    deben conservar exactamente ambos pedidos y sus torques aplicados.
    Para el balance energético se repite con salida de 0,1 ms: el cambio
    rápido de tanh al iniciar el movimiento exige refinar la cuadratura.
    El residuo de trabajo y pérdidas debe ser menor que 1e-6 J.
    """
    def pedido_excesivo(t: float, q: np.ndarray, v: np.ndarray) -> np.ndarray:
        """Pedir torque constante (2;−1) N·m, sin alterar el estado recibido."""
        # El pedido excede ambos límites para comprobar la acción del recorte.
        return np.array([2.0, -1.0])

    def pedido_limite(t: float, q: np.ndarray, v: np.ndarray) -> np.ndarray:
        """Pedir el mismo torque ya saturado (1,20;−0,31) N·m."""
        # Esta ruta comprueba que la planta usa el aplicado y no el pedido.
        return np.array([1.20, -0.31])

    dinamica, _ = modelo_ampliado
    condiciones = dict(q0=[-np.pi / 2, 0], qd0=[0, 0], duracion=0.05,
                       friccion=Friccion())
    r = simular_planta(dinamica, torque=pedido_excesivo, **condiciones)
    referencia = simular_planta(dinamica, torque=pedido_limite, **condiciones)
    np.testing.assert_allclose(r.q, referencia.q, rtol=0, atol=1e-12)
    np.testing.assert_allclose(r.qd, referencia.qd, rtol=0, atol=1e-12)
    np.testing.assert_array_equal(r.torque_solicitado, np.tile([2, -1], (len(r.t), 1)))
    np.testing.assert_array_equal(r.torque_aplicado, np.tile([1.2, -0.31], (len(r.t), 1)))
    np.testing.assert_allclose(r.rozamiento, Friccion().torque(r.qd), rtol=0, atol=1e-14)
    # La potencia aplicada menos las pérdidas debe explicar la variación
    # energética; trapezoid trabaja sobre la salida, no los pasos de RK45.
    potencia = np.sum((r.torque_aplicado - r.rozamiento) * r.qd, axis=1)
    balance = float(r.energia[-1] - r.energia[0] - trapezoid(potencia, r.t))
    fino = simular_planta(dinamica, torque=pedido_excesivo,
                          paso_salida=0.0001, **condiciones)
    potencia_fina = np.sum((fino.torque_aplicado - fino.rozamiento) * fino.qd, axis=1)
    balance_fino = float(fino.energia[-1] - fino.energia[0] -
                        trapezoid(potencia_fina, fino.t))
    np.testing.assert_allclose(fino.q[::10], r.q, rtol=0, atol=1e-12)
    assert abs(balance_fino) < 1e-6
    assert abs(balance_fino) < abs(balance)
    print(f"Saturación: pedido={r.torque_solicitado[0]} N·m; "
          f"aplicado={r.torque_aplicado[0]} N·m; diferencia estados="
          f"{np.max(np.abs(r.q - referencia.q)):.12g} rad; "
          f"balance 1 ms/0,1 ms={balance:.12g}/{balance_fino:.12g} J")


@pytest.fixture(scope="module")
def movimientos_ampliados(modelo_ampliado: tuple) -> dict:
    """Integrar oscilación del modelo completo sin fricción y con nominal.

    Parte de q=(−pi/2+0,3;−0,2) rad y qd=(0,4;−0,1) rad/s durante 5 s.
    Repite el caso nominal con rtol=1e-9, atol=1e-11. Mantiene salida de
    1 ms y usa además salida de 0,1 ms para contrastar la cuadratura de pérdidas.
    """
    d, _ = modelo_ampliado
    condiciones = dict(q0=[-np.pi / 2 + 0.3, -0.2], qd0=[0.4, -0.1], duracion=5)
    # Separar cambio físico de fricción y cambio numérico de tolerancias.
    return {
        "nulo": simular_libre(d, **condiciones),
        "nominal": simular_libre(d, **condiciones, friccion=Friccion()),
        "estricto": simular_libre(d, **condiciones, friccion=Friccion(),
                                  rtol=1e-9, atol=1e-11),
        "salida_fina": simular_libre(d, **condiciones, friccion=Friccion(),
                                     paso_salida=0.0001),
    }


def test_disipacion_y_convergencia_ampliadas(movimientos_ampliados: dict) -> None:
    """Contrastar energía conservada, disipada y convergencia de la planta.

    Sin fricción, variación ≤1e-5 J. Con nominal, no admite incrementos por
    muestra mayores que 1e-9 J y exige caída neta positiva. El balance con
    integral de qd·f debe cerrar a 1e-6 J al refinar salida a 0,1 ms; la
    referencia estricta debe diferir ≤1e-4 rad y ≤1e-3 rad/s en la grilla común.
    """
    nulo, nominal = movimientos_ampliados["nulo"], movimientos_ampliados["nominal"]
    estricto, fino = movimientos_ampliados["estricto"], movimientos_ampliados["salida_fina"]
    conservacion = float(np.max(np.abs(nulo.energia - nulo.energia[0])))
    aumento = float(np.max(np.diff(nominal.energia)))
    perdida = float(nominal.energia[0] - nominal.energia[-1])
    # La identidad energética permite detectar un signo de rozamiento
    # incorrecto, además de observar que la oscilación se amortigua.
    disipacion = trapezoid(np.sum(nominal.qd * nominal.rozamiento, axis=1), nominal.t)
    disipacion_fina = trapezoid(np.sum(fino.qd * fino.rozamiento, axis=1), fino.t)
    residuo = float(perdida - disipacion)
    residuo_fino = float(fino.energia[0] - fino.energia[-1] - disipacion_fina)
    np.testing.assert_array_equal(nominal.t, estricto.t)
    delta_q = float(np.max(np.abs(nominal.q - estricto.q)))
    delta_v = float(np.max(np.abs(nominal.qd - estricto.qd)))
    assert conservacion <= 1e-5
    assert aumento <= 1e-9
    assert perdida > 0
    assert abs(residuo_fino) <= 1e-6
    assert abs(residuo_fino) < abs(residuo)
    assert delta_q <= 1e-4 and delta_v <= 1e-3
    np.testing.assert_array_equal(nominal.torque_solicitado, np.zeros_like(nominal.q))
    np.testing.assert_array_equal(nominal.torque_aplicado, np.zeros_like(nominal.q))
    print(f"Libre ampliado: E0={nominal.energia[0]:.15g} J; "
          f"Efinal={nominal.energia[-1]:.15g} J; ΔE sin f={conservacion:.12g} J; "
          f"aumento máximo nominal={aumento:.12g} J; caída={perdida:.12g} J; "
          f"integral pérdidas={disipacion:.12g} J; "
          f"balance 1/0,1 ms={residuo:.12g}/{residuo_fino:.12g} J; "
          f"Δq={delta_q:.12g} rad; Δqd={delta_v:.12g} rad/s; "
          f"evaluaciones nulo/nominal/estricto="
          f"{nulo.evaluaciones}/{nominal.evaluaciones}/{estricto.evaluaciones}; "
          f"qfinal={nominal.q[-1]}; qdfinal={nominal.qd[-1]}")


def test_inercia_reflejada_una_sola_vez(modelo_con_rotores: Dinamica) -> None:
    """Aislar el incremento N²Jm de M en 81 posiciones reproducibles.

    Sin carcasa añadida, restar la M analítica de las barras a la dinámica
    con rotor. Exigir diag(0,003774808;0,000352872) kg·m² a 1e-12 y
    contrastar la M total con Toolbox configurado con esos mismos rotores.
    """
    robot = crear_robot()
    for link, actuador in zip(robot.links, ACTUADORES):
        link.G, link.Jm = actuador.relacion, actuador.inercia_rotor
    esperado = np.diag([0.003774808, 0.000352872])
    diferencia = 0.0
    for q1 in np.linspace(-np.pi, np.pi, 9):
        for q2 in np.linspace(-np.pi, np.pi, 9):
            # La expresión manual de las barras se obtuvo en la etapa 3 y
            # permite detectar que el incremento se duplique u omita.
            c = np.cos(q2)
            barras = np.array([[0.0072072 + 0.00432 * c, 0.0014436 + 0.00216 * c],
                               [0.0014436 + 0.00216 * c, 0.0014436]])
            m = modelo_con_rotores.M([q1, q2])
            np.testing.assert_allclose(m - barras, esperado, rtol=0, atol=1e-12)
            referencia = robot.inertia([q1, q2])
            np.testing.assert_allclose(m, referencia, rtol=0, atol=1e-12)
            diferencia = max(diferencia, float(np.max(np.abs(m - referencia))))
    print(f"Rotor aislado: incremento={np.diag(esperado)} kg·m²; "
          f"diferencia Toolbox={diferencia:.12g} kg·m²")


def test_planta_no_recorta_estados(modelo_ampliado: tuple) -> None:
    """Verificar que el rango de destinos no actúe como tope de la planta.

    Parte de q=(pi−0,001;0) rad y qd=(4;−4) rad/s, sin torque ni fricción,
    durante 2 ms. Debe conservar la velocidad inicial y permitir q1>pi.
    Los 3 rad/s corresponden al diseño de referencias, no a un recorte físico.
    """
    d, _ = modelo_ampliado
    # Elegir movimiento hacia el extremo del rango detecta tanto recorte
    # angular como envoltura inadvertida, sin introducir topes ficticios.
    r = simular_libre(d, [np.pi - 0.001, 0], [4, -4], duracion=0.002)
    np.testing.assert_array_equal(r.qd[0], [4, -4])
    assert r.q[-1, 0] > np.pi
    assert np.max(np.abs(r.qd)) > 3
    print(f"Sin recortes: q1 final={r.q[-1, 0]:.12g} rad; "
          f"máxima velocidad={np.max(np.abs(r.qd)):.12g} rad/s")


def test_capacidad_estatica_y_a_velocidad_objetivo() -> None:
    """Contrastar capacidad inicial con pesos y velocidad prevista de 3 rad/s.

    Cuenta gravitatoria independiente: 108 g por barra y 144 g adicionales
    en el codo. Incluye motor2 66 g, reductor2 58 g y fijación 20 g. Comprueba
    sostén máximo frente al torque limitado, entrada a 3 rad/s frente a rpm
    nominales/límite, potencia de salida frente al límite de cada reductor y
    potencia mecánica del motor estimada con eta máxima frente a su punto nominal.
    Son estimaciones de selección, no una validación de seguimiento ni térmica.
    """
    gravedad = np.array([0.70632, 0.105948])
    np.testing.assert_allclose(gravedad, [9.81 * (0.108 * 0.1 + 0.108 * 0.3 +
                                                0.144 * 0.2), 9.81 * 0.108 * 0.1],
                               rtol=0, atol=1e-12)
    for eje, actuador in enumerate(ACTUADORES):
        # No usar torque de bloqueo ni potencia del encabezado del motor
        # como si fueran capacidades continuas del conjunto seleccionado.
        rpm = 3 * actuador.relacion * 60 / (2 * np.pi)
        potencia = actuador.limite_torque * 3
        torque_motor = actuador.limite_torque / (actuador.relacion * actuador.eficiencia_maxima)
        potencia_motor = potencia / actuador.eficiencia_maxima
        potencia_motor_nominal = (actuador.torque_motor_nominal *
                                 actuador.velocidad_motor_nominal * 2 * np.pi / 60)
        assert gravedad[eje] < LIMITES_TORQUE[eje]
        assert actuador.limite_torque <= actuador.torque_continuo_estimado
        assert rpm < min(actuador.velocidad_motor_nominal, actuador.velocidad_entrada_continua)
        assert potencia < actuador.potencia_reductor_continua
        assert torque_motor <= actuador.torque_motor_nominal
        assert potencia_motor < potencia_motor_nominal
        print(f"Eje {eje + 1}: Gmax={gravedad[eje]} N·m; "
              f"reserva={actuador.limite_torque - gravedad[eje]:.12g} N·m; "
              f"capacidad estimada={actuador.torque_continuo_estimado:.12g} N·m; "
              f"entrada a 3 rad/s={rpm:.12g} rpm; "
              f"potencia al límite={potencia:.12g}/{actuador.potencia_reductor_continua} W; "
              f"torque motor estimado={torque_motor:.12g} N·m; "
              f"potencia motor estimada/nominal="
              f"{potencia_motor:.12g}/{potencia_motor_nominal:.12g} W")
