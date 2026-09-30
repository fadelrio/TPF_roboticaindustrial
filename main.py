"""Punto de entrada inicial: diagnóstico del entorno de la etapa 1."""

from pendulo import verificar_entorno


def main() -> None:
    """Mostrar versiones y resultados del robot auxiliar, sin guardar archivos.

    Los resultados tienen unidades SI y corresponden al eslabón de prueba,
    no al modelo del doble péndulo. Los errores de dependencias o de Toolbox
    interrumpen la ejecución para que sean visibles durante el diagnóstico.
    """
    # La etapa inicial comprueba el entorno; los escenarios del péndulo se
    # incorporarán al punto de entrada durante sus etapas correspondientes.
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


if __name__ == "__main__":
    main()
