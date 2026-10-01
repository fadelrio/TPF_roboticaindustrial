"""Diagnóstico, movimiento libre y comparación del control continuo del 2R."""

import argparse

import numpy as np
import matplotlib.pyplot as plt

from pendulo import verificar_entorno
from pendulo.control import ControladorPD
from pendulo.dinamica import Dinamica
from pendulo.modelo import (crear_robot, crear_robot_actuado,
                            posiciones_geometricas, posiciones_toolbox)
from pendulo.parametros import ACTUADORES, BARRAS, Friccion
from pendulo.simulacion import medir_seguimiento, simular_libre, simular_seguimiento
from pendulo.trayectorias import TrayectoriaQuintica
from pendulo.visualizacion import crear_animacion, graficar_resultado, graficar_seguimientos


# Estos escenarios conservan las condiciones reproducibles de la etapa 4.
# No aplican torque; el modelo y la fricción se seleccionan por separado.
ESCENARIOS_LIBRES = {
    "colgante": {"q0": (-np.pi / 2, 0.0), "qd0": (0.0, 0.0), "duracion": 5.0},
    "invertido": {"q0": (np.pi / 2 + np.deg2rad(1), 0.0), "qd0": (0.0, 0.0), "duracion": 2.0},
    "oscilacion": {"q0": (-np.pi / 2 + 0.3, -0.2), "qd0": (0.4, -0.1), "duracion": 5.0},
}

# Cada referencia usa posiciones iniciales y finales literales, sin giros
# abreviados. La perturbación cambia solo el estado real de recuperación.
ESCENARIOS_CONTROL = {
    "abajo_arriba": {"qi": (-np.pi / 2, 0), "qf": (np.pi / 2, 0)},
    "arriba_abajo": {"qi": (np.pi / 2, 0), "qf": (-np.pi / 2, 0)},
    "extremos": {"qi": (-np.pi, -np.pi), "qf": (np.pi, np.pi)},
    "extremos_opuestos": {"qi": (-np.pi, np.pi), "qf": (np.pi, -np.pi)},
    "eje1": {"qi": (-np.pi / 2, np.pi / 3), "qf": (np.pi / 2, np.pi / 3)},
    "eje2": {"qi": (0, -np.pi), "qf": (0, np.pi)},
    "nulo_horizontal": {"qi": (0, 0), "qf": (0, 0)},
    "estabilizacion": {"qi": (np.pi / 2, 0), "qf": (np.pi / 2, 0),
                       "q0": (np.pi / 2 + np.deg2rad(5), np.deg2rad(5))},
}


def comparar_continuo(
    dinamica: Dinamica, escenario: str, controladores: list[ControladorPD],
    friccion: Friccion = Friccion(),
) -> dict:
    """Simular un escenario con las instancias indicadas y condiciones comunes.

    Retorna {tramo: {nombre: ResultadoSeguimiento}}, con datos en memoria.
    ``ida_vuelta`` ejecuta abajo–arriba y regreso para cada instancia,
    heredando q y qd reales finales de la ida y manteniendo 1 s en cada destino.
    Los tiempos de cada resultado se expresan desde el inicio de su tramo.
    """
    resultados = {}
    nombres = [controlador.nombre for controlador in controladores]
    if len(nombres) != len(set(nombres)):
        raise ValueError("Los controladores de una comparación deben tener nombres distintos")
    for controlador in controladores:
        tramos = ["abajo_arriba", "arriba_abajo"] if escenario == "ida_vuelta" else [escenario]
        anterior = None
        for tramo in tramos:
            caso = ESCENARIOS_CONTROL[tramo]
            trayectoria = TrayectoriaQuintica(caso["qi"], caso["qf"])
            q0, qd0 = caso.get("q0"), None
            if anterior is not None:
                # Continuar desde el estado obtenido conserva el error residual
                # y la velocidad física, sin reiniciar artificialmente la planta.
                q0, qd0 = anterior.simulacion.q[-1], anterior.simulacion.qd[-1]
            anterior = simular_seguimiento(dinamica, trayectoria, controlador,
                                          q0=q0, qd0=qd0, friccion=friccion)
            resultados.setdefault(tramo, {})[controlador.nombre] = anterior
    return resultados


def informar_seguimiento(resultado, recuperacion: bool = False) -> None:
    """Mostrar errores y demanda por eje con unidades, sin exportar archivos.

    Distingue recuperación de la aceptación de seguimiento nominal: 5°
    iniciales no se comparan contra el máximo de 2°. En recuperación informa
    asentamiento dentro de 0,2° y error final durante el horizonte observado.
    """
    # Las métricas reutilizan la grilla registrada; distinguir recuperación
    # evita calificar sus 5° iniciales como un fallo de seguimiento nominal.
    m = medir_seguimiento(resultado)
    print(f"Controlador: {resultado.controlador.nombre}; "
          f"T [s]={resultado.trayectoria.duracion:.12g}; "
          f"final [s]={resultado.simulacion.t[-1]:.12g}")
    print(f"Error máximo/final por eje [°]: {m['error_maximo_grados']} / {m['error_final_grados']}")
    print(f"Velocidad final [rad/s]: {m['velocidad_final']}")
    if recuperacion:
        print(f"Recuperación desde 5°: asentamiento en ±0.2° [s]={m['asentamiento']}")
        print(f"Recuperación cumplida: {m['asentamiento'] is not None}")
    else:
        print(f"Precisión nominal (máximo 2°, final 0.2°): {m['cumple_precision']}")
    print(f"Torque máximo pedido/aplicado/ideal [N·m]: "
          f"{m['torque_solicitado_maximo']} / {m['torque_aplicado_maximo']} / "
          f"{m['torque_referencia_maximo']}")
    print(f"Muestras saturadas por eje [%]: {m['saturacion_porcentaje']}")
    print(f"Todo el pedido observado cabe en los límites: {m['solicitud_sin_saturacion']}")
    print(f"Velocidad real máxima [rad/s]: {m['velocidad_maxima']}; entrada [rpm]: {m['rpm_maxima']}")
    print(f"Potencia mecánica máxima absoluta [W]: {m['potencia_maxima']}; "
          f"máximo positivo/mínimo negativo [W]: "
          f"{m['potencia_positiva_maxima']} / {m['potencia_negativa_minima']}")
    print(f"Torque/potencia de motor estimados con ηmax [N·m]/[W]: "
          f"{m['torque_motor_estimado']} / {m['potencia_motor_estimada']}")
    print(f"Capacidad para referencia ideal y torque entregado en el modelo: {m['cumple_capacidad']}")


def main() -> None:
    """Diagnosticar etapas previas, simular un caso y mostrar sus resultados.

    ``--caso`` elige colgante, invertido u oscilacion (por defecto). La opción
    ``--sin-graficos`` ejecuta las cuentas y el resumen en consola, sin crear
    figuras ni esperar ventanas. La ejecución normal muestra gráficos y
    animación desde los resultados en memoria, sin exportar archivos.
    ``--modelo actuado`` (por defecto) incluye montaje, rotores y fricción
    nominal; ``--modelo barras`` conserva el caso ideal de las etapas previas.
    ``--friccion`` permite elegir escala 0, 0.5, 1 o 2 explícitamente.
    ``--control`` selecciona libre, PD, PD con gravedad o comparación;
    ``--escenario`` elige una referencia controlada o una ida y vuelta.
    """
    # Las opciones seleccionan escenarios concretos y permiten ejecutar el
    # mismo programa en el IDE o en verificaciones sin interfaz gráfica.
    parser = argparse.ArgumentParser(description="Simulación del doble péndulo 2R")
    parser.add_argument("--caso", choices=ESCENARIOS_LIBRES, default="oscilacion")
    parser.add_argument("--modelo", choices=["barras", "actuado"], default="actuado")
    parser.add_argument("--friccion", type=float, choices=[0.0, 0.5, 1.0, 2.0],
                        help="Escala: por defecto 1 en actuado y 0 en barras")
    parser.add_argument("--sin-graficos", action="store_true", help="Solo cuentas y consola")
    parser.add_argument("--control", choices=["libre", "pd", "pd_gravedad", "comparar"],
                        default="libre")
    parser.add_argument("--escenario", choices=[*ESCENARIOS_CONTROL, "ida_vuelta"],
                        default="abajo_arriba")
    opciones = parser.parse_args()
    # Conservar el diagnóstico inicial permite comprobar el entorno usado.
    resultado = verificar_entorno()
    print("Etapa 1 — Diagnóstico del entorno")
    for nombre, instalada in resultado["versiones"].items():
        print(f"{nombre}: {instalada}")

    # Mostrar magnitudes explícitas permite contrastar la ejecución con las
    # cuentas analíticas documentadas en el README.
    print("Robot auxiliar: barra uniforme de 1 m y 1 kg, q=0 rad")
    print(f"Extremo [m]: {resultado['posicion']}")
    print(f"Inercia articular [kg·m²]: {resultado['inercia']}")
    print(f"Gravedad [N·m]: {resultado['gravedad']}")
    print(f"Torque estático por RNE [N·m]: {resultado['torque_estatico']}")

    # Las propiedades centrales de cada barra se muestran con su referencia.
    print("\nEtapa 2 — Modelo mecánico y cinemática")
    robot = crear_robot()
    for indice, barra in enumerate(BARRAS, start=1):
        print(f"Barra {indice}: masa [kg] = {barra.masa:.12g}")
        print(f"Centro de masa en terna DH [m]: {barra.centro_masa}")
        print(f"Tensor central [kg·m²]:\n{barra.inercia}")

    # Los cuatro casos permiten revisar signos, ángulo relativo y plegado.
    configuraciones = {
        "Horizontal": (0.0, 0.0),
        "Colgante": (-np.pi / 2.0, 0.0),
        "Invertida": (np.pi / 2.0, 0.0),
        "Plegada": (0.0, np.pi),
    }
    longitudes = tuple(barra.longitud for barra in BARRAS)
    for nombre, q in configuraciones.items():
        geometria = posiciones_geometricas(q, longitudes)
        toolbox = posiciones_toolbox(robot, q)
        diferencia = np.max(np.abs(toolbox - geometria))
        print(f"{nombre}: q [rad] = {q}")
        print(f"  Geometría, codo/extremo [m]:\n{geometria[1:]}")
        print(f"  Toolbox, codo/extremo [m]:\n{toolbox[1:]}")
        print(f"  Diferencia máxima [m]: {diferencia:.3e}")

    # Derivar una vez para este modelo; las llamadas siguientes solo evalúan
    # funciones numéricas compiladas desde las expresiones de SymPy.
    print("\nEtapa 3 — Dinámica propia y contraste")
    dinamica = Dinamica(robot)
    print(f"M simbólica [kg·m²], coeficientes redondeados:\n{dinamica.M_simbolica.evalf(8)}")
    print(f"C simbólica [kg·m²/s], coeficientes redondeados:\n{dinamica.C_simbolica.evalf(8)}")
    print(f"G simbólica [N·m], coeficientes redondeados:\n{dinamica.G_simbolica.evalf(8)}")
    for nombre, q in configuraciones.items():
        print(f"{nombre}: sostén propio [N·m] = {dinamica.G(q)}; "
              f"Toolbox [N·m] = {robot.gravload(q)}; U [J] = {dinamica.potencial(q):.9g}")

    # Un estado con ambas juntas en movimiento comprueba el término C·qd y
    # la inversa completa, sin exigir que las matrices C sean idénticas.
    q = np.array([0.4, -0.7])
    v = np.array([1.2, -0.8])
    a = np.array([2.0, -1.0])
    print(f"Estado de contraste: q [rad]={q}, qd [rad/s]={v}, qdd [rad/s²]={a}")
    print(f"M propia [kg·m²]:\n{dinamica.M(q)}")
    print(f"C·qd propio [N·m]: {dinamica.C(q, v) @ v}")
    print(f"G propio [N·m]: {dinamica.G(q)}")
    propio, referencia = dinamica.inversa(q, v, a), robot.rne(q, v, a)
    print(f"Torque inverso propio/Toolbox [N·m]: {propio} / {referencia}")
    print(f"Diferencia máxima de inversa [N·m]: {np.max(np.abs(propio - referencia)):.3e}")

    # Esta cabecera mantiene explícita la relación con la integración libre
    # de la etapa 4. El modelo ampliado se deriva solo si fue seleccionado.
    print("\nEtapa 4 — Movimiento libre e integración")
    print("\nEtapa 5 — Actuadores, montaje y rozamiento")
    if opciones.modelo == "actuado":
        robot = crear_robot_actuado()
        dinamica = Dinamica(robot)
        for indice, (eslabon, actuador) in enumerate(zip(robot.links, ACTUADORES), start=1):
            print(f"Eslabón {indice}: masa [kg]={eslabon.m:.12g}; "
                  f"centro DH [m]={eslabon.r}")
            print(f"Tensor central [kg·m²]:\n{eslabon.I}")
            print(f"Actuador: {actuador.nombre}; N≈{actuador.relacion:g}; "
                  f"N²Jm [kg·m²]={actuador.inercia_reflejada:.12g}; "
                  f"límite [N·m]={actuador.limite_torque}")
            # Este contraste de selección conserva la referencia de etapa 5;
            # las velocidades y potencias reales se informan en seguimiento.
            rpm = 3 * actuador.relacion * 60 / (2 * np.pi)
            print(f"A 3 rad/s: entrada [rpm]={rpm:.9g}; "
                  f"potencia al límite [W]={3 * actuador.limite_torque:.9g}")
        print(f"Gravedad máxima por eje [N·m]: {dinamica.G([0, 0])}")
        print(f"Contraste M con Toolbox en q=(0,0) [kg·m²]: "
              f"{np.max(np.abs(dinamica.M([0, 0]) - robot.inertia([0, 0]))):.3e}")
    escala = opciones.friccion
    if escala is None:
        escala = 1.0 if opciones.modelo == "actuado" else 0.0
    friccion = Friccion(escala=escala)
    print(f"Modelo seleccionado: {opciones.modelo}; escala de fricción: {escala}")
    print(f"Fricción a 3 rad/s por eje [N·m]: {friccion.torque([3, 3])}")

    if opciones.control != "libre":
        print("\nEtapa 6 — Trayectorias y control continuo")
        controladores = []
        if opciones.control in ("pd", "comparar"):
            controladores.append(ControladorPD("PD"))
        if opciones.control in ("pd_gravedad", "comparar"):
            controladores.append(ControladorPD("PD+G", gravedad=True))
        comparaciones = comparar_continuo(dinamica, opciones.escenario, controladores, friccion)
        figuras, animaciones = [], []
        for tramo, resultados in comparaciones.items():
            print(f"\nEscenario: {tramo}")
            recuperacion = tramo == "estabilizacion"
            for resultado_control in resultados.values():
                informar_seguimiento(resultado_control, recuperacion)
            if not opciones.sin_graficos:
                # La comparación usa resultados calculados. En esta etapa se
                # reproduce una instancia; la animación simultánea queda en 7.
                figuras.append(graficar_seguimientos(
                    resultados, tramo, limite_error=0.2 if recuperacion else 2.0))
                elegido = resultados.get("PD+G", next(iter(resultados.values())))
                figura, animacion = crear_animacion(
                    elegido.simulacion, f"{tramo} — {elegido.controlador.nombre}", longitudes)
                figuras.append(figura)
                animaciones.append(animacion)
        if not opciones.sin_graficos:
            plt.show()
        return

    # Las expresiones compiladas alimentan una única planta con registros
    # de torque y fricción, conservando los estados sin recortes artificiales.
    caso = ESCENARIOS_LIBRES[opciones.caso]
    libre = simular_libre(dinamica, **caso, friccion=friccion)
    print(f"Caso: {opciones.caso}; q0 [rad]={caso['q0']}; qd0 [rad/s]={caso['qd0']}")
    print(f"Duración [s]: {libre.t[-1]}; muestras: {len(libre.t)}; evaluaciones: {libre.evaluaciones}")
    print(f"q final [rad]: {libre.q[-1]}; qd final [rad/s]: {libre.qd[-1]}")
    print(f"E inicial/final [J]: {libre.energia[0]:.12g} / {libre.energia[-1]:.12g}")
    print(f"Variación máxima de E [J]: {np.max(np.abs(libre.energia - libre.energia[0])):.9g}")
    print(f"Máximo torque solicitado/aplicado [N·m]: "
          f"{np.max(np.abs(libre.torque_solicitado), axis=0)} / "
          f"{np.max(np.abs(libre.torque_aplicado), axis=0)}")
    print(f"Máximo rozamiento [N·m]: {np.max(np.abs(libre.rozamiento), axis=0)}")
    if not opciones.sin_graficos:
        # Mantener ambos objetos locales vivos durante show evita que la
        # animación sea recolectada antes de reproducirse.
        nombre = f"{opciones.caso} — {opciones.modelo}, fricción ×{escala:g}"
        figura_graficos = graficar_resultado(libre, nombre)
        figura_animacion, animacion = crear_animacion(libre, nombre, longitudes)
        plt.show()


if __name__ == "__main__":
    main()
