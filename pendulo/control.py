"""Control PD articular y PD con compensación de gravedad para el 2R.

Cada instancia conserva su nombre y sus propias ganancias diagonales. El
resultado es torque solicitado; la planta aplica los límites de los actuadores.
"""

import numpy as np

from pendulo.dinamica import Dinamica


class ControladorPD:
    """Controlador continuo de dos ejes con compensación de gravedad opcional.

    ``kp`` y ``kd`` son vectores (2,) que representan las diagonales de Kp y
    Kd, en N·m/rad y N·m·s/rad. No incluye integral, anticipación de aceleración,
    saturación ni envoltura de ángulos. Las ganancias son independientes entre
    instancias, aunque sus entradas originales sean los mismos arrays.
    """

    def __init__(
        self, nombre: str, kp: tuple = (20.0, 5.0),
        kd: tuple = (1.3, 0.2), gravedad: bool = False,
    ) -> None:
        """Guardar nombre, ganancias y elección de compensar G(q).

        Acepta tuplas o arrays de dos componentes. Kp debe ser positiva y
        Kd no negativa, con valores finitos; una forma o valor inválido
        produce ValueError. Las ganancias se copian para evitar compartir
        memoria con los argumentos y con otras instancias.
        """
        # Copiar los vectores permite configurar cada comparación sin que
        # modificar una instancia altere los datos originales u otra instancia.
        self.nombre = nombre
        self.kp = np.array(kp, dtype=float, copy=True)
        self.kd = np.array(kd, dtype=float, copy=True)
        if self.kp.shape != (2,) or self.kd.shape != (2,):
            raise ValueError("kp y kd deben tener dos componentes, una por eje.")
        if not np.all(np.isfinite(self.kp)) or not np.all(np.isfinite(self.kd)):
            raise ValueError("Las ganancias deben ser finitas.")
        if np.any(self.kp <= 0) or np.any(self.kd < 0):
            raise ValueError("kp debe ser positiva y kd no negativa.")
        self.gravedad = gravedad

    def calcular(
        self, q: np.ndarray, qd: np.ndarray, q_d: np.ndarray,
        qd_d: np.ndarray, dinamica: Dinamica,
    ) -> np.ndarray:
        """Calcular torque solicitado (2,) en N·m desde estado y referencia.

        q y q_d se expresan en rad; qd y qd_d, en rad/s. Calcula
        Kp·(q_d−q)+Kd·(qd_d−qd). Si ``gravedad`` es True suma G(q),
        evaluada en la posición real. No modifica entradas, limita torque
        ni reduce el error a otro intervalo angular.
        """
        # Las conversiones admiten tuplas además de arrays; las operaciones
        # producen un nuevo vector y conservan cada diferencia angular literal.
        posicion = np.asarray(q, dtype=float)
        velocidad = np.asarray(qd, dtype=float)
        referencia = np.asarray(q_d, dtype=float)
        velocidad_referencia = np.asarray(qd_d, dtype=float)
        torque = (self.kp * (referencia - posicion)
                  + self.kd * (velocidad_referencia - velocidad))
        if self.gravedad:
            # Compensar el peso del estado actual sigue la fórmula aprobada;
            # el modelo de la planta conserva la responsabilidad de saturar.
            torque = torque + dinamica.G(posicion)
        return torque
