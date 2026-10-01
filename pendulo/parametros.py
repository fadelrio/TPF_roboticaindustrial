"""Parámetros mecánicos, candidatos de accionamiento y rozamiento en SI."""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Barra:
    """Barra prismática maciza y uniforme, con dimensiones locales X, Y y Z.

    Las dimensiones se expresan en metros y la densidad en kg/m³. X sigue
    la longitud; Y es el ancho en el plano XY y Z el espesor perpendicular.
    Los valores nominales son 200×20×10 mm y 2700 kg/m³. El origen de la
    terna DH está en el extremo distal; sus ejes coinciden con los de la barra.
    """

    longitud: float = 0.20
    ancho: float = 0.02
    espesor: float = 0.01
    densidad: float = 2700.0

    @property
    def masa(self) -> float:
        """Calcular la masa en kg como densidad por volumen del prisma."""
        # Se conservan las dimensiones en SI para evitar conversiones internas.
        return self.densidad * self.longitud * self.ancho * self.espesor

    @property
    def centro_masa(self) -> np.ndarray:
        """Retornar el centro de masa (3,) en m respecto de la terna DH distal."""
        # El centro geométrico queda a media longitud hacia el extremo proximal.
        return np.array([-self.longitud / 2.0, 0.0, 0.0])

    @property
    def inercia(self) -> np.ndarray:
        """Retornar el tensor central (3, 3) en kg·m², en los ejes locales.

        El tensor corresponde al centro de masa, tal como requiere Toolbox,
        y no al origen DH. No incluye rotor, reductores ni fijaciones.
        """
        l, a, e = self.longitud, self.ancho, self.espesor
        # La simetría del prisma anula los productos de inercia en estos ejes.
        return self.masa / 12.0 * np.diag([a**2 + e**2, l**2 + e**2, l**2 + a**2])


# Dos cuerpos independientes con las mismas propiedades nominales. La tupla
# y las dimensiones inmutables evitan cambiar accidentalmente el caso nominal.
BARRAS = (Barra(), Barra())
GRAVEDAD = (0.0, -9.81, 0.0)


@dataclass(frozen=True)
class Actuador:
    """Datos de un motor de 18 V con reductor GPX 22 A estándar.

    Masas en kg, longitudes en m, inercia del rotor en kg·m², torques en
    N·m, velocidad de entrada en rpm y potencia en W. ``relacion`` es la
    reducción aproximada de catálogo y ``eficiencia_maxima`` es adimensional.
    La eficiencia máxima sirve para estimar capacidad, no es una medición
    en el punto de operación ni una eficiencia aplicada por la planta.
    """

    nombre: str
    masa_motor: float
    longitud_motor: float
    masa_reductor: float
    longitud_reductor: float
    etapas: int
    relacion: float
    inercia_rotor: float
    torque_motor_nominal: float
    torque_reductor_continuo: float
    eficiencia_maxima: float
    velocidad_motor_nominal: float
    velocidad_entrada_continua: float
    potencia_reductor_continua: float
    limite_torque: float
    diametro: float = 0.022

    @property
    def inercia_reflejada(self) -> float:
        """Calcular N²Jm en kg·m², referido al eje de salida del reductor."""
        # Se añade una sola vez a M; no se incorpora al tensor de la carcasa.
        return self.relacion**2 * self.inercia_rotor

    @property
    def torque_continuo_estimado(self) -> float:
        """Estimar torque de salida en N·m con la eficiencia máxima de ficha.

        Toma el menor entre el límite del reductor y N·ηmax·τmotor_nominal.
        Es una estimación de selección: no garantiza la eficiencia real,
        las condiciones térmicas ni el funcionamiento de un conjunto físico.
        """
        # Evitar atribuir al conjunto todo el torque multiplicado del motor
        # cuando el propio reductor tiene una capacidad inferior.
        return min(self.torque_reductor_continuo,
                   self.relacion * self.eficiencia_maxima * self.torque_motor_nominal)


# Fichas Maxon DCX 22 L/S (febrero 2025) y GPX 22 (marzo 2025).
# 1 g·cm² = 1e-7 kg·m². Las reducciones publicadas 62 y 26 son aproximadas.
# Se conservan los límites de salida aprobados de 1,20 y 0,31 N·m.
ACTUADORES = (
    Actuador(
        nombre="DCX 22 L + GPX 22 A",
        masa_motor=0.095, longitud_motor=0.0472,
        masa_reductor=0.067, longitud_reductor=0.0322,
        etapas=3, relacion=62.0, inercia_rotor=9.82e-7,
        torque_motor_nominal=0.0322, torque_reductor_continuo=1.20,
        eficiencia_maxima=0.74, velocidad_motor_nominal=10800.0,
        velocidad_entrada_continua=12000.0, potencia_reductor_continua=6.0,
        limite_torque=1.20,
    ),
    Actuador(
        nombre="DCX 22 S + GPX 22 A",
        masa_motor=0.066, longitud_motor=0.0342,
        masa_reductor=0.058, longitud_reductor=0.0264,
        etapas=2, relacion=26.0, inercia_rotor=5.22e-7,
        torque_motor_nominal=0.0149, torque_reductor_continuo=0.70,
        eficiencia_maxima=0.81, velocidad_motor_nominal=10800.0,
        velocidad_entrada_continua=10000.0, potencia_reductor_continua=12.0,
        limite_torque=0.31,
    ),
)
LIMITES_TORQUE = tuple(actuador.limite_torque for actuador in ACTUADORES)


@dataclass(frozen=True)
class Cuerpo:
    """Propiedades de un cuerpo rígido en una terna local compartida.

    ``masa`` está en kg; ``centro_masa`` es (3,) en m respecto del origen
    local; ``inercia`` es (3,3) en kg·m² referido a su propio centro, con
    ejes paralelos a la terna local. No incluye inercia reflejada del rotor.
    """

    masa: float
    centro_masa: np.ndarray
    inercia: np.ndarray


def cilindro(
    masa: float, diametro: float, longitud: float, centro: tuple[float, float, float]
) -> Cuerpo:
    """Calcular propiedades de un cilindro macizo uniforme con eje local Z.

    Masa en kg, diámetro/longitud y centro (3,) en m. La masa se especifica
    independientemente de la geometría: el cuerpo equivalente aproxima un
    componente completo, sin inferir su material ni su distribución real.
    Devuelve el tensor central en kg·m² y el centro en la terna compartida.
    """
    radio = diametro / 2
    # Ixx=Iyy=m(3R²+L²)/12 e Izz=mR²/2 para el cilindro de eje Z.
    transversal = masa * (3 * radio**2 + longitud**2) / 12
    tensor = np.diag([transversal, transversal, masa * radio**2 / 2])
    return Cuerpo(masa, np.array(centro, dtype=float), tensor)


def componer_cuerpos(cuerpos: tuple[Barra | Cuerpo, ...]) -> Cuerpo:
    """Componer masas, centros y tensores centrales de cuerpos en la misma terna.

    Las entradas comparten ejes locales y referencia de sus centros en m.
    Cada tensor es central en kg·m². El resultado contiene masa total en kg,
    centro ponderado y tensor en ese centro, trasladado mediante Steiner.
    """
    masa = sum(cuerpo.masa for cuerpo in cuerpos)
    centro = sum(cuerpo.masa * cuerpo.centro_masa for cuerpo in cuerpos) / masa
    tensor = np.zeros((3, 3))
    for cuerpo in cuerpos:
        desplazamiento = cuerpo.centro_masa - centro
        # Trasladar cada tensor al centro común, sin cargar en Toolbox
        # un tensor referido al origen DH y duplicar su propia traslación.
        tensor += cuerpo.inercia + cuerpo.masa * (
            np.dot(desplazamiento, desplazamiento) * np.eye(3) -
            np.outer(desplazamiento, desplazamiento))
    return Cuerpo(masa, centro, tensor)


def componentes_codo(
    barra: Barra = BARRAS[0], actuador: Actuador = ACTUADORES[1]
) -> tuple[Cuerpo, Cuerpo, Cuerpo]:
    """Construir fijación, reductor y motor transportados por el eslabón 1.

    Los tres cilindros son coaxiales con Z y tienen X=Y=0 en la terna DH
    del codo. Se apilan detrás de la cara Z negativa de la barra: fijación
    equivalente de 20 g, Ø22×5 mm supuestos; después reductor y motor con
    dimensiones de ficha. No constituye un diseño de soporte fabricable.
    """
    longitud_fijacion = 0.005
    cara_barra = -barra.espesor / 2
    cara_reductor = cara_barra - longitud_fijacion
    cara_motor = cara_reductor - actuador.longitud_reductor
    # La cadena axial sigue el conjunto comercial motor–reductor; se omiten
    # ejes salientes, cables y vaciados, conservando sus masas completas.
    fijacion = cilindro(0.020, 0.022, longitud_fijacion,
                       (0, 0, cara_barra - longitud_fijacion / 2))
    reductor = cilindro(actuador.masa_reductor, actuador.diametro,
                       actuador.longitud_reductor,
                       (0, 0, cara_reductor - actuador.longitud_reductor / 2))
    motor = cilindro(actuador.masa_motor, actuador.diametro, actuador.longitud_motor,
                     (0, 0, cara_motor - actuador.longitud_motor / 2))
    return fijacion, reductor, motor


@dataclass(frozen=True)
class Friccion:
    """Rozamiento articular supuesto B·qd+Tc·tanh(qd/epsilon).

    ``B`` se expresa en N·m·s/rad, ``Tc`` en N·m y ``epsilon`` en rad/s.
    ``escala`` multiplica B y Tc: 0, 0,5, 1 y 2 representan los casos
    nulo, medio, nominal y doble. Los parámetros no son mediciones ni datos
    de los motores. No se modelan fricción estática ni histéresis.
    """

    B: tuple[float, float] = (0.02, 0.005)
    Tc: tuple[float, float] = (0.03, 0.01)
    epsilon: float = 0.01
    escala: float = 1.0

    def torque(self, qd: np.ndarray) -> np.ndarray:
        """Retornar f(qd) en N·m para qd (2,) en rad/s, sin alterar la entrada.

        f tiene el mismo signo que la velocidad y se resta en la ecuación
        de aceleración. En reposo devuelve cero; la transición tanh es suave.
        """
        v = np.asarray(qd, dtype=float)
        # Los parámetros ya están referidos a la articulación: no multiplicar
        # de nuevo por N ni N² como haría una fricción definida en el motor.
        return self.escala * (np.asarray(self.B) * v +
                             np.asarray(self.Tc) * np.tanh(v / self.epsilon))
