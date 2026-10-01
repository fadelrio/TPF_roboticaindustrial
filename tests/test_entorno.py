"""Verificaciones analíticas y de ejecución correspondientes a la etapa 1."""

from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from pendulo import verificar_entorno


def test_robot_auxiliar_con_resultados_analiticos() -> None:
    """Contrastar FK, inercia, gravedad y RNE con una barra uniforme conocida.

    En q=0, el extremo es (1,0,0) m. La inercia sobre la articulación es
    1/12 + 1·0,5² = 1/3 kg·m² y el torque de sostén es 1·9,81·0,5 =
    4,905 N·m. La tolerancia absoluta es 1e-12 en las unidades respectivas.
    """
    resultado = verificar_entorno()

    # Los valores esperados provienen de geometría, Steiner y equilibrio
    # estático; no se obtienen llamando otra vez a la misma función de Toolbox.
    np.testing.assert_allclose(
        resultado["posicion"], [1.0, 0.0, 0.0], rtol=0, atol=1e-12
    )
    np.testing.assert_allclose(
        resultado["inercia"], [[1.0 / 3.0]], rtol=0, atol=1e-12
    )
    np.testing.assert_allclose(
        resultado["gravedad"], [4.905], rtol=0, atol=1e-12
    )
    np.testing.assert_allclose(
        resultado["torque_estatico"], [4.905], rtol=0, atol=1e-12
    )


@pytest.mark.parametrize(
    "argumentos, modelo, escala",
    [([], "actuado", 1.0), (["--modelo", "barras"], "barras", 0.0),
     (["--modelo", "actuado", "--friccion", "0.5"], "actuado", 0.5)],
)
def test_punto_de_entrada_desde_el_interprete_activo(
    argumentos: list, modelo: str, escala: float
) -> None:
    """Ejecutar main.py en otro proceso y verificar su salida y finalización.

    Se usa el mismo intérprete que ejecuta pytest para comprobar el entorno
    seleccionado, sin depender del Python por defecto del sistema.
    Comprueba el modelo actuado nominal, las barras ideales y la selección
    explícita de fricción media, con diagnóstico y salida sin ventanas.
    """
    raiz = Path(__file__).resolve().parents[1]

    # La ejecución independiente detecta errores de imports y del punto de
    # entrada que podrían quedar ocultos al invocar solo una función importada.
    proceso = subprocess.run(
        [sys.executable, "main.py", "--sin-graficos", *argumentos],
        cwd=raiz,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proceso.returncode == 0, proceso.stdout + proceso.stderr
    assert "Etapa 1 — Diagnóstico del entorno" in proceso.stdout
    assert "roboticstoolbox-python: 1.4.4" in proceso.stdout
    assert "Torque estático por RNE [N·m]" in proceso.stdout
    assert "Etapa 2 — Modelo mecánico y cinemática" in proceso.stdout
    assert "Etapa 3 — Dinámica propia y contraste" in proceso.stdout
    assert "Etapa 4 — Movimiento libre e integración" in proceso.stdout
    assert "Etapa 5 — Actuadores, montaje y rozamiento" in proceso.stdout
    assert f"Modelo seleccionado: {modelo}; escala de fricción: {escala}" in proceso.stdout
    if modelo == "actuado":
        # La masa emitida comprueba que el constructor ampliado se utilizó,
        # además de reconocer el texto de la opción seleccionada.
        assert "Eslabón 1: masa [kg]=0.252" in proceso.stdout
