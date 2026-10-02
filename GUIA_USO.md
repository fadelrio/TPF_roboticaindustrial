# Guía de uso del doble péndulo 2R

Esta guía describe el programa implementado hasta la etapa 7. Para consultar
ecuaciones, fuentes, decisiones físicas e informes de pruebas, ver el
[README](README.md). Las trayectorias desde archivos JSON y los destinos XY
pertenecen a la siguiente entrega: todavía no son entradas del programa.

## Índice

- [Entorno y primera ejecución](#entorno-y-primera-ejecución)
- [Ejecución en PyCharm](#ejecución-en-pycharm)
- [Argumentos de consola](#argumentos-de-consola)
- [Escenarios disponibles](#escenarios-disponibles)
- [Ejemplos de ejecución](#ejemplos-de-ejecución)
- [Lectura de resultados y ventanas](#lectura-de-resultados-y-ventanas)
- [Uso desde Python](#uso-desde-python)
- [Referencia de funciones públicas](#referencia-de-funciones-públicas)
- [Resultados y métricas de Python](#resultados-y-métricas-de-python)
- [Supuestos y alcance](#supuestos-y-alcance)
- [Verificación de esta guía](#verificación-de-esta-guía)

## Entorno y primera ejecución

Los comandos siguientes se ejecutan desde la carpeta que contiene `main.py`,
`requirements.txt` y `pendulo/`. Las rutas y comandos corresponden a Linux.
Python 3.12 se instala por separado; `requirements.txt` fija las dependencias
del proyecto, incluida Robotics Toolbox 1.4.4.

Si todavía no existe el entorno:

~~~bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
~~~

Para comprobar el intérprete y consultar las opciones:

~~~bash
.venv/bin/python --version
.venv/bin/python main.py --help
~~~

Para ejecutar el caso predeterminado:

~~~bash
.venv/bin/python main.py
~~~

Ejecuta movimiento libre `oscilacion` durante 5 s, con modelo `actuado` y
fricción nominal. Primero realiza el diagnóstico del entorno, la cinemática
y la dinámica; después integra y abre los gráficos y la animación.
La derivación simbólica inicial forma parte de esa preparación.

Se puede activar el entorno para abreviar los comandos:

~~~bash
source .venv/bin/activate
python main.py --help
deactivate
~~~

Usar `.venv/bin/python` directamente permite identificar el intérprete incluso
si hay otro entorno activado. Para comprobar dependencias y ejecutar pruebas:

~~~bash
.venv/bin/python -m pip check
.venv/bin/python -m pytest -v
~~~

Los cálculos sin ventanas se ejecutan con `--sin-graficos`. Si hace falta elegir
explícitamente un backend sin pantalla:

~~~bash
MPLBACKEND=Agg .venv/bin/python main.py --caso colgante --sin-graficos
~~~

Para ventanas, el entorno necesita un backend gráfico y acceso al escritorio.
`TkAgg` fue verificado en las etapas anteriores:

~~~bash
MPLBACKEND=TkAgg .venv/bin/python main.py --caso oscilacion
~~~

Si aparece un aviso de caché de Matplotlib sin permisos de escritura, se puede
elegir una carpeta escribible para su configuración:

~~~bash
MPLBACKEND=Agg MPLCONFIGDIR=/tmp/tpf-matplotlib .venv/bin/python main.py --sin-graficos
~~~

Esa carpeta contiene configuración/caché de Matplotlib; el programa no exporta
resultados de simulación.

## Ejecución en PyCharm

Abrir la carpeta del proyecto. En las opciones del intérprete, agregar un
intérprete local existente y elegir el ejecutable de esta `.venv`. La
[documentación de JetBrains](https://www.jetbrains.com/help/pycharm/configuring-python-interpreter.html)
explica el procedimiento; en versiones recientes está en **Settings → Python →
Interpreter → Add Interpreter → Add Local Interpreter**, seleccionando el
Python existente. Los nombres de los menús pueden variar con la versión.

En esta ubicación del proyecto, el ejecutable es:

~~~text
/home/fadelrio/Ingenieria/Robotica Industrial/TPF/.venv/bin/python
~~~

Antes de seleccionarlo, comprobarlo desde una terminal:

~~~bash
"/home/fadelrio/Ingenieria/Robotica Industrial/TPF/.venv/bin/python" --version
~~~

Si ese comando informa que el archivo no existe, revisar la ubicación del
proyecto y el entorno. Un enlace de `.venv/bin/python` cuyo Python base fue
movido o eliminado también puede fallar así. Consultar el destino con
`readlink -f .venv/bin/python` desde la carpeta del proyecto y reconstruir el
entorno con Python 3.12 si su intérprete base dejó de estar disponible.

Si el ejecutable funciona en una **terminal del sistema** y falla en PyCharm,
comprobar si el IDE está instalado mediante Flatpak. Flatpak utiliza un
sistema de archivos de runtime; `/usr` dentro de la aplicación puede diferir
del `/usr` del sistema, como explica su
[documentación de permisos](https://docs.flatpak.org/en/latest/sandbox-permissions.html).
En el equipo verificado para esta guía, PyCharm 2026.2.2 está instalado por
Flatpak: la `.venv` apunta a `/usr/bin/python3.12` del sistema y el runtime
25.08 tiene Python 3.13, sin ese ejecutable 3.12. Reconstruir la misma
`.venv` externa no resuelve esa diferencia. Para usar este entorno, ejecutar
desde la terminal del sistema o configurar un PyCharm nativo con acceso al
Python 3.12 del sistema.

En la configuración de ejecución:

| Campo | Valor |
|---|---|
| Script | `main.py` de este proyecto |
| Intérprete | El ejecutable de `.venv` seleccionado |
| Directorio de trabajo | La carpeta que contiene `main.py` |
| Parámetros | Por ejemplo: `--control pd_gravedad --modo digital --periodo 0.001 --escenario abajo_arriba` |
| Variables de entorno | Opcional: `MPLBACKEND=TkAgg` para ventanas |

En el campo de parámetros se colocan solamente los argumentos, sin repetir el
ejecutable ni `main.py`. Si se ejecuta en la consola Python del IDE, configurar
también allí el intérprete y directorio del proyecto.

## Argumentos de consola

Formato general: `.venv/bin/python main.py [opciones]`. En valores numéricos de
consola y Python se utiliza punto decimal: `0.001`.

| Argumento | Valores admitidos | Predeterminado | Efecto |
|---|---|---|---|
| `-h`, `--help` | Sin valor | — | Muestra la ayuda y termina, sin integrar. |
| `--caso` | `colgante`, `invertido`, `oscilacion` | `oscilacion` | Condición inicial del movimiento libre. |
| `--modelo` | `barras`, `actuado` | `actuado` | Selecciona barras ideales o modelo con montaje e inercias de rotor. |
| `--friccion` | `0`, `0.5`, `1`, `2` | 1 en `actuado`; 0 en `barras` | Escala los parámetros B y Tc. |
| `--sin-graficos` | Sin valor | Desactivado | Integra e informa en consola; omite figuras y espera de ventanas. |
| `--control` | `libre`, `pd`, `pd_gravedad`, `comparar` | `libre` | Selecciona movimiento sin torque, PD, PD+G o ambas leyes. |
| `--escenario` | Los nombres de la tabla de escenarios controlados | `abajo_arriba` | Referencia del movimiento controlado. |
| `--modo` | `continuo`, `digital`, `comparar` | `continuo` | Modo de control; `comparar` ejecuta ambos. |
| `--periodo` | Número positivo y finito, en segundos | `0.001` | Período de actualización digital Ts. |
| `--barrido` | `ninguno`, `friccion`, `periodo` | `ninguno` | Ejecuta el caso elegido o compara las variantes predefinidas. |

### Combinaciones y prioridades

- `--control comparar` compara **PD y PD+G**. `--modo comparar` compara
  **continuo y digital**. Juntos producen cuatro resultados por tramo.
- `--caso` se utiliza con `--control libre`. Con control activo se utiliza
  `--escenario`; el argumento `--caso` no modifica esa simulación.
- `--escenario` no cambia un movimiento libre. Con `--control libre` deben
  mantenerse `--modo continuo` y `--barrido ninguno`; otras combinaciones
  terminan con un mensaje de error.
- `--barrido friccion` usa escalas 0, 0.5, 1 y 2, sustituyendo la selección de
  `--friccion` para las simulaciones del barrido. Conserva los modos elegidos
  y el período digital.
- `--barrido periodo` ejecuta un continuo y digitales de **0.5, 1, 5, 10 y
  20 ms**, con cada controlador elegido. Sustituye `--modo` y `--periodo`
  para el barrido y conserva el modelo y la fricción. El continuo se
  calcula una sola vez por controlador.
- `--periodo` se valida siempre como positivo y finito, aunque el modo sea
  continuo o el barrido seleccione otros períodos.
- `--sin-graficos` conserva los cálculos y métricas. No reduce la integración
  a una comprobación rápida.

El diagnóstico inicial de `main.py` informa las propiedades de las barras
antes de seleccionar el modelo de simulación. En un barrido de fricción,
también puede mostrar la escala inicial seleccionada; las etiquetas de cada
resultado indican la escala que se utilizó en esa integración.

### Qué se configura desde Python

Actualmente la consola no recibe ganancias, ángulos propios, duración elegida
del movimiento, velocidad inicial propia, permanencia final, tolerancias del
integrador, paso de salida ni período de animación. Las funciones de Python
permiten modificar varios de esos parámetros, como se detalla más adelante.
`TrayectoriaQuintica` calcula automáticamente su duración; tampoco admite
un tiempo o porcentaje de rapidez desde Python en esta versión.

## Escenarios disponibles

El modelo se mueve en XY vertical: `q1` se mide desde +X y `q2` es relativo al
primer eslabón. Los valores de las tablas controladas están en **grados** para
facilitar su lectura; las funciones de Python reciben **radianes**.

### Movimiento libre: argumento --caso

| Caso | q0 [rad] | qd0 [rad/s] | Duración [s] | Propósito |
|---|---|---|---|---|
| `colgante` | `(-π/2, 0)` | `(0, 0)` | 5 | Equilibrio inferior, con pequeñas diferencias numéricas posibles. |
| `invertido` | `(π/2 + π/180, 0)` | `(0, 0)` | 2 | Invertido perturbado 1° en el eje 1; observar inestabilidad. |
| `oscilacion` | `(-π/2 + 0.3, -0.2)` | `(0.4, -0.1)` | 5 | Movimiento libre desde una desviación y velocidad inicial explícitas. |

El torque aplicado es cero. El modelo y la fricción se eligen independientemente.

### Movimiento controlado: argumento --escenario

| Escenario | qi [°] | qf [°] | Particularidad |
|---|---|---|---|
| `abajo_arriba` | `(-90, 0)` | `(90, 0)` | Del colgante al invertido. |
| `arriba_abajo` | `(90, 0)` | `(-90, 0)` | Del invertido al colgante. |
| `extremos` | `(-180, -180)` | `(180, 180)` | Desplazamiento literal de 360° en ambos ejes. |
| `extremos_opuestos` | `(-180, 180)` | `(180, -180)` | Desplazamientos de 360° en sentidos opuestos. |
| `eje1` | `(-90, 60)` | `(90, 60)` | Cambia solo la referencia del eje 1. |
| `eje2` | `(0, -180)` | `(0, 180)` | Cambia solo la referencia del eje 2. |
| `nulo_horizontal` | `(0, 0)` | `(0, 0)` | Referencia constante horizontal. |
| `estabilizacion` | `(90, 0)` | `(90, 0)` | Estado real inicial `(95, 5)°`; recuperación desde +5° en ambos ejes. |
| `interior_a` | `(-135, 36)` | `(30, -120)` | Par reproducible interior al rango. |
| `interior_b` | `(60, -90)` | `(-45, 135)` | Otro par interior. |
| `borde` | `(179, -179)` | `(-179, 179)` | Destinos próximos a los límites, con diferencias literales de 358°. |
| `ida_vuelta` | `(-90, 0)` | `(90, 0)` y regreso | Dos resultados: `abajo_arriba` y `arriba_abajo`. |

La quintica sincroniza los ejes, comienza y termina con velocidad y aceleración
nulas y respeta 2 s mínimos, 3 rad/s de velocidad máxima de referencia y
6 rad/s² de aceleración máxima de referencia. La duración se calcula a partir
del mayor desplazamiento articular. Después mantiene el destino 1 s.

Las diferencias angulares son literales: de −180° a +180° se recorre una
vuelta completa. Un eje con referencia constante puede moverse ligeramente
por el error de control o el acoplamiento dinámico.

`ida_vuelta` conserva el estado real final, incluida la velocidad residual,
de cada combinación de controlador y modo para iniciar su regreso. Mantiene
1 s en cada destino. Cada tramo tiene tiempos desde cero y sus propias
figuras y métricas.

La duración también es 2 s cuando no hay desplazamiento; `nulo_horizontal` y
`estabilizacion` se simulan durante 3 s contando la permanencia final.

## Ejemplos de ejecución

### Equilibrio inferior ideal, sin ventanas

~~~bash
.venv/bin/python main.py --caso colgante --modelo barras --friccion 0 --sin-graficos
~~~

### Invertido libre perturbado

~~~bash
.venv/bin/python main.py --caso invertido --modelo barras --friccion 0
~~~

### Seguimiento PD con gravedad

~~~bash
.venv/bin/python main.py --control pd_gravedad --escenario abajo_arriba --sin-graficos
~~~

### PD sin gravedad

~~~bash
.venv/bin/python main.py --control pd --escenario abajo_arriba
~~~

### Ambas leyes y ambos modos

~~~bash
.venv/bin/python main.py --control comparar --modo comparar --periodo 0.001 --escenario interior_a --sin-graficos
~~~

Quitar `--sin-graficos` abre los gráficos y la animación simultánea.

### Recuperación con control digital de 1 ms

~~~bash
.venv/bin/python main.py --control pd_gravedad --modo digital --periodo 0.001 --escenario estabilizacion --sin-graficos
~~~

### Ida y vuelta con ambas leyes

~~~bash
.venv/bin/python main.py --control comparar --escenario ida_vuelta --sin-graficos
~~~

### Sensibilidad a fricción

~~~bash
.venv/bin/python main.py --control pd_gravedad --modo comparar --barrido friccion --escenario abajo_arriba --sin-graficos
~~~

Produce ocho resultados: cuatro escalas por dos modos.

### Sensibilidad al período digital

~~~bash
.venv/bin/python main.py --control pd_gravedad --barrido periodo --escenario estabilizacion --sin-graficos
~~~

Produce seis resultados: un continuo y cinco digitales. Los períodos mayores
pueden incumplir recuperación o seguimiento; se conservan sus resultados para
diagnóstico.

## Lectura de resultados y ventanas

### Consola

El robot auxiliar del diagnóstico de entorno tiene una barra de 1 m y 1 kg;
sirve para comprobar Toolbox y no es el doble péndulo del proyecto.
Las cabeceras de etapas identifican los diagnósticos y la simulación.

En movimiento libre se informan condiciones iniciales, duración, cantidad de
muestras, evaluaciones de la ecuación diferencial, estado final y energía.
`evaluaciones` no es la cantidad de pasos de RK45 ni de muestras guardadas.

En seguimiento se informan, por eje:

- Duración `T` del movimiento y tiempo final, que incluye la permanencia.
- Modo y, en digital, período y cantidad de actualizaciones.
- Error máximo absoluto y error final absoluto, en grados.
- Velocidad real final, en rad/s.
- Precisión nominal o recuperación, según el escenario.
- Máximos absolutos de torque solicitado, aplicado e ideal.
- Porcentaje de muestras saturadas y si todo el pedido observado entra
  en los límites.
- Velocidad real máxima, velocidad de entrada del motor/reductor y potencia.
- Estimaciones de torque/potencia de motor y evaluación de capacidad.

El error es `q_d − q`. El torque **solicitado** sale del controlador; el
**aplicado** está limitado a ±1.20 y ±0.31 N·m. El torque **ideal** es la
dinámica inversa de la referencia más su rozamiento. Se calcula para evaluar
demanda; el controlador PD o PD+G no utiliza ese torque como anticipación.

`cumple_precision` exige máximo ≤2° y final ≤0.2° por eje. La recuperación
desde 5° se interpreta por asentamiento dentro de ±0.2°, separadamente del
máximo nominal de seguimiento. El asentamiento considera error de posición;
la velocidad final se informa aparte.

`cumple_capacidad` compara la demanda ideal y lo aplicado con las capacidades
nominales consideradas. No significa que todas las solicitudes fueron
satisfechas: revisar además `solicitud_sin_saturacion` y los torques.
La potencia mecánica conserva el signo: `τ_aplicado·qd`. Valores negativos
indican frenado mecánico; no son una medición de energía eléctrica recuperada.
Las estimaciones del motor usan la eficiencia máxima de ficha del reductor.

En digital, los máximos de torque pedido/aplicado utilizan todas las
actualizaciones de control. Errores, velocidades, potencia y porcentaje de
saturación utilizan las muestras de salida. Ese porcentaje cuenta muestras,
no tiempo exacto saturado.

### Gráficos

El movimiento libre tiene cuatro paneles: ángulos [rad], velocidades [rad/s],
energías K/U/E [J] y variación `E−E(0)` [J].

El seguimiento tiene seis paneles: cada columna es una articulación y las
filas son posición [rad], error [°] y torque [N·m]. La referencia es negra
discontinua; cada combinación tiene un color. En torques, la línea continua
es el pedido y la discontinua es el aplicado. Las guías grises indican
límites; no recortan las curvas. En recuperación se muestran guías de ±0.2°.
Con tres o más resultados se utiliza una leyenda común fuera de los paneles.

### Animación y reproducción

La animación utiliza los estados ya calculados. Cada robot representa su
propio resultado y, en comparación, comparte el reloj e índice temporal.
El texto muestra tiempo físico de simulación.

La primera reproducción empieza al mostrar la figura y queda en el último
fotograma. **Volver a reproducir** reinicia desde t=0 durante el movimiento
o después del final, sin integrar ni cambiar los resultados originales.
Cerrar todas las ventanas permite terminar la ejecución normal de `main.py`.

| Tiempo o período | Predeterminado | Función |
|---|---|---|
| `periodo` de seguimiento / `--periodo` | 0.001 s | Actualización del control digital. |
| `paso_salida` | 0.001 s | Grilla de resultados y gráficos; último intervalo puede ser menor. |
| `periodo` de animación | 0.020 s | Selección de fotogramas y temporizador gráfico, 50 fps nominales. |

RK45 utiliza pasos internos adaptativos. El temporizador gráfico depende del
backend y del equipo; los 50 fps no garantizan reproducción en tiempo real.
Los fotogramas usan la primera muestra disponible desde cada tiempo objetivo,
incluyendo la última; no interpolan estados. Los gráficos digitales unen
muestras con líneas, mientras que la retención de torque entre actualizaciones
se aplica en la integración y queda registrada en las trazas de control.

## Uso desde Python

Ejecutar desde la carpeta del proyecto, con el mismo intérprete. Solo
`verificar_entorno` se reexporta en `pendulo`; las demás entradas se importan
desde sus submódulos.

### Modelo, referencia propia y seguimiento

Este ejemplo usa las ganancias nominales y ángulos expresados inicialmente en
grados. Puede pegarse en la consola Python del proyecto:

~~~python
import numpy as np

from pendulo.modelo import crear_robot_actuado
from pendulo.dinamica import Dinamica
from pendulo.parametros import Friccion
from pendulo.trayectorias import TrayectoriaQuintica
from pendulo.control import ControladorPD
from pendulo.simulacion import simular_seguimiento, medir_seguimiento

# Derivar una sola vez; cada integración reutiliza la misma dinámica.
robot = crear_robot_actuado()
dinamica = Dinamica(robot)
trayectoria = TrayectoriaQuintica(
    np.deg2rad([-90.0, 0.0]),
    np.deg2rad([90.0, 0.0]),
)
controlador = ControladorPD(
    "PD+G", kp=(20.0, 5.0), kd=(1.3, 0.2), gravedad=True,
)

# Declarar fricción y modo permite repetir las mismas condiciones.
resultado = simular_seguimiento(
    dinamica, trayectoria, controlador,
    friccion=Friccion(escala=1.0),
    modo="digital", periodo=0.001,
)
metricas = medir_seguimiento(resultado)
print(metricas["error_maximo_grados"])
print(resultado.simulacion.q[-1])
~~~

`q0` y `qd0` de `simular_seguimiento` permiten cambiar el estado real inicial
sin cambiar la referencia. Por ejemplo, la recuperación del invertido utiliza
referencia constante `(π/2,0)` y estado real `(95°,5°)` convertido a radianes.
Las ganancias de cada instancia son independientes. Las posiciones propias
de `TrayectoriaQuintica` deben estar entre −π y π.

### Mostrar los resultados calculados

Continuando el ejemplo anterior:

~~~python
import matplotlib.pyplot as plt
from pendulo.visualizacion import graficar_seguimientos, crear_animacion_comparada

# Conservar figuras y animación mientras se procesa la ventana.
resultados = {"PD+G digital": resultado}
figura_curvas = graficar_seguimientos(resultados, nombre="Referencia propia")
figura_animacion, animacion = crear_animacion_comparada(
    resultados, nombre="Referencia propia",
)
plt.show()
~~~

Las funciones gráficas retornan las figuras; quien las llama decide cuándo
mostrar con `plt.show()`. La figura de animación conserva el botón y la
animación vigente. El segundo elemento retornado es la primera animación;
después de pulsar el botón, la figura retiene el nuevo reproductor.

### Comparar instancias

Con la `dinamica` ya creada:

~~~python
from main import comparar_control

# Los nombres distintos identifican cada instancia en curvas y métricas.
controladores = [
    ControladorPD("PD nominal"),
    ControladorPD("PD+G nominal", gravedad=True),
]
comparaciones = comparar_control(
    dinamica, "abajo_arriba", controladores,
    friccion=Friccion(escala=1.0),
    modos=("continuo", "digital"), periodo=0.001,
)
resultados_ida = comparaciones["abajo_arriba"]
~~~

Para comparar otras ganancias se crean instancias con sus `kp` y `kd`
explícitos y nombres distintos. Para otro par inicial/final se utiliza
`TrayectoriaQuintica` y `simular_seguimiento` directamente; las funciones de
comparación de `main` reciben los nombres de los escenarios existentes.

La animación simultánea exige grillas de tiempo exactamente iguales. El
gráfico de seguimiento supone referencias comunes y dibuja solo la del
primer resultado. Comparar condiciones con tiempos o referencias diferentes
requiere preparar las figuras correspondientes por separado.

### Movimiento libre y configuración numérica

~~~python
from pendulo.simulacion import simular_libre

# El modelo se reutiliza; fricción cero se declara explícitamente.
libre = simular_libre(
    dinamica, q0=(-np.pi / 2, 0.0), qd0=(0.0, 0.0),
    duracion=5.0, friccion=Friccion(escala=0.0),
    paso_salida=0.001, rtol=1e-7, atol=1e-9,
)
~~~

En Python, `simular_libre` y `simular_planta` tienen fricción nula por defecto,
incluso si `dinamica` viene de un robot actuado. `simular_seguimiento` y las
comparaciones tienen fricción nominal por defecto. La consola elige la escala
según `--modelo`; conviene declararla explícitamente en los ejemplos propios.

## Referencia de funciones públicas

Las firmas siguientes enumeran todos los argumentos propios. Los vectores
articulares tienen dos componentes; sus unidades internas son SI.
Los métodos de apoyo y las estructuras mecánicas se incluyen para poder
consultar cuentas y resultados sin ejecutar el punto de entrada.

### Entorno y modelo

| Entrada | Argumentos | Retorno y uso |
|---|---|---|
| `pendulo.verificar_entorno()` | Ninguno | Diccionario con `versiones`, `posicion` (3,) [m], `inercia` (1,1) [kg·m²], `gravedad` y `torque_estatico` (1,) [N·m], calculados con el robot auxiliar. |
| `crear_robot(barras=BARRAS)` | Tupla de dos `Barra` | `DHRobot` de barras, sin actuadores, rotor ni fricción. |
| `crear_robot_actuado(barras=BARRAS, actuadores=ACTUADORES)` | Dos barras y dos actuadores | `DHRobot` con montaje transportado y rotor; la fricción se aplica fuera de Toolbox. |
| `posiciones_toolbox(robot, q)` | Robot y q (2,) [rad] | Array (3,3): XYZ de base, codo y extremo, en m. |
| `posiciones_geometricas(q, longitudes=(0.20,0.20))` | q [rad], dos longitudes [m] | El mismo formato de posiciones, mediante geometría plana. |

Estas cuatro funciones del modelo se importan desde `pendulo.modelo`.

### Parámetros y composición de cuerpos

Se importan desde `pendulo.parametros`.

| Entrada | Argumentos y valores predeterminados | Retorno o propiedades |
|---|---|---|
| `Barra` | `longitud=0.20`, `ancho=0.02`, `espesor=0.01` [m], `densidad=2700.0` [kg/m³] | Propiedades `masa` [kg], `centro_masa` (3,) [m] respecto de DH distal e `inercia` central (3,3) [kg·m²]. |
| `Cuerpo` | `masa` [kg], `centro_masa` (3,) [m], `inercia` central (3,3) [kg·m²] | Estructura de propiedades en una terna compartida, con los tres atributos recibidos. |
| `cilindro(masa, diametro, longitud, centro)` | Masa [kg], dimensiones [m], centro XYZ [m] | `Cuerpo` cilíndrico equivalente con eje Z y tensor central. |
| `componer_cuerpos(cuerpos)` | Tupla de `Barra` o `Cuerpo` en la misma terna | `Cuerpo` compuesto mediante centros ponderados y Steiner. |
| `componentes_codo(barra=BARRAS[0], actuador=ACTUADORES[1])` | Barra 1 y conjunto motor/reductor transportado | Tupla de tres `Cuerpo`: fijación, reductor y motor. |
| `Friccion` | `B=(0.02,0.005)` [N·m·s/rad], `Tc=(0.03,0.01)` [N·m], `epsilon=0.01` [rad/s], `escala=1.0` | Parámetros de `escala·(B·qd+Tc·tanh(qd/epsilon))`. |
| `friccion.torque(qd)` | qd (2,) [rad/s] | f(qd) (2,) [N·m], que la planta resta; no cambia qd. |

`Actuador` recibe los argumentos siguientes; solo `diametro` tiene un valor
predeterminado. Los dos candidatos ya configurados se encuentran en `ACTUADORES`.

| Argumento | Unidad o significado |
|---|---|
| `nombre` | Nombre del conjunto |
| `masa_motor`, `masa_reductor` | kg |
| `longitud_motor`, `longitud_reductor` | m |
| `etapas` | Cantidad de etapas del reductor |
| `relacion` | Reducción N, adimensional |
| `inercia_rotor` | kg·m², antes de reflejar por N² |
| `torque_motor_nominal` | N·m en el eje del motor |
| `torque_reductor_continuo` | N·m en la salida del reductor |
| `eficiencia_maxima` | Fracción adimensional |
| `velocidad_motor_nominal` | rpm |
| `velocidad_entrada_continua` | rpm de entrada del reductor |
| `potencia_reductor_continua` | W |
| `limite_torque` | N·m aplicado como límite nominal de salida |
| `diametro=0.022` | m |

Sus propiedades son `inercia_reflejada=N²Jm` [kg·m²] y
`torque_continuo_estimado=min(torque_reductor_continuo,
N·eficiencia_maxima·torque_motor_nominal)` [N·m].
Las estructuras `Barra`, `Actuador`, `Cuerpo` y `Friccion` son dataclasses
con campos congelados; no se reasignan sus atributos.

Las constantes son `BARRAS`, `ACTUADORES`, `GRAVEDAD=(0,-9.81,0)` [m/s²] y
`LIMITES_TORQUE=(1.20,0.31)` [N·m].

**Personalización del modelo:** pasar otras barras o actuadores a
`crear_robot_actuado` cambia sus propiedades mecánicas. El seguimiento sigue
usando `LIMITES_TORQUE` y las métricas siguen usando `ACTUADORES` globales;
esa llamada no propaga nuevas capacidades automáticamente. `simular_planta`
sí permite límites explícitos. Si se cambian longitudes, indicarlas también
en la cinemática geométrica y las animaciones.

### Dinámica

Se importa desde `pendulo.dinamica`. `Dinamica(robot)` deriva las expresiones
una vez y prepara sus evaluadores numéricos. Supone el modelo 2R DH estándar
del proyecto, con base/herramienta identidad y `d=alpha=offset=0`.
Si se modifica el robot después, crear otra instancia de `Dinamica`.

| Método | Argumentos | Retorno |
|---|---|---|
| `M(q)` | q (2,) [rad] | Matriz (2,2) [kg·m²], con inercia reflejada. |
| `C(q, qd)` | q [rad], qd [rad/s] | Matriz (2,2) [kg·m²/s]. |
| `G(q)` | q [rad] | Torque gravitatorio (2,) [N·m]. |
| `M_punto(q, qd)` | q [rad], qd [rad/s] | Derivada temporal de M (2,2) [kg·m²/s]. |
| `potencial(q)` | q [rad] | Energía potencial escalar [J], cero en altura Y=0. |
| `inversa(q, qd, qdd)` | q [rad], qd [rad/s], qdd [rad/s²] | Torque (2,) [N·m]: M·qdd+C·qd+G, sin fricción ni saturación. |

Para inspección simbólica están disponibles `q_simbolica`, `qd_simbolica`,
`M_cuerpos_simbolica`, `M_simbolica`, `C_simbolica`, `G_simbolica`,
`M_punto_simbolica` y `U_simbolica`. También se conservan `transformaciones`,
`pseudoinercias` e `inercias_reflejadas`.

La función pública `pseudoinercia(masa, centro, inercia)` recibe masa [kg],
centro (3,) [m] y tensor central (3,3) [kg·m²] en la misma terna. Retorna la
matriz homogénea SymPy (4,4), con segundos momentos, primeros momentos y masa.

### Trayectoria y control

| Entrada | Argumentos | Retorno o comportamiento |
|---|---|---|
| `TrayectoriaQuintica(qi, qf)`, desde `pendulo.trayectorias` | Dos vectores (2,) [rad], finitos, dentro de [−π,π] | Copia destinos y calcula `duracion` [s]. No recibe duración manual. |
| `trayectoria.evaluar(t)` | Tiempo [s] | Tupla de q_d, qd_d, qdd_d (2,), en rad, rad/s y rad/s². Antes de cero mantiene qi; desde duración mantiene qf, con derivadas nulas. |
| `ControladorPD(nombre, kp=(20.0,5.0), kd=(1.3,0.2), gravedad=False)`, desde `pendulo.control` | Nombre; diagonales kp [N·m/rad] y kd [N·m·s/rad]; compensación opcional | Instancia con ganancias copiadas. kp positiva, kd no negativa y ambas finitas. |
| `controlador.calcular(q, qd, q_d, qd_d, dinamica)` | Estado y referencia (2,) en rad y rad/s; dinámica | Torque solicitado (2,) [N·m]. Si `gravedad=True` suma G(q) del estado real. No satura. |

La duración se calcula con `d=max(abs(qf−qi))`:

\[
T=\max\left(2,\frac{(15/8)d}{3},
\sqrt{\frac{(10\sqrt{3}/3)d}{6}}\right).
\]

### Simulación

Se importa desde `pendulo.simulacion`. Firmas completas:

~~~python
simular_libre(dinamica, q0, qd0, duracion=5.0, paso_salida=0.001,
              rtol=1e-7, atol=1e-9, friccion=None)
simular_planta(dinamica, q0, qd0, duracion=5.0, paso_salida=0.001,
               rtol=1e-7, atol=1e-9, torque=None, friccion=None,
               limites=LIMITES_TORQUE)
simular_seguimiento(dinamica, trayectoria, controlador, q0=None, qd0=None,
                    permanencia=1.0, friccion=Friccion(), paso_salida=0.001,
                    rtol=1e-7, atol=1e-9, modo="continuo", periodo=0.001)
~~~

Estas firmas son una referencia de consulta; los ejemplos ejecutables incluyen
los imports y objetos necesarios.

| Argumento | Uso |
|---|---|
| `dinamica` | Instancia `Dinamica` ya derivada. |
| `q0`, `qd0` | Estado real inicial (2,) [rad] y [rad/s]. En seguimiento, `None` utiliza qi y velocidad cero. |
| `duracion` | Horizonte positivo [s], en libre/planta. |
| `paso_salida` | Separación positiva [s] de muestras guardadas. |
| `rtol`, `atol` | Tolerancia relativa y absoluta de RK45; el estado integrado contiene ángulos y velocidades. |
| `friccion` | Instancia `Friccion`. Libre/planta admiten `None` para rozamiento nulo; en seguimiento utilizar `Friccion(escala=0.0)` para anularlo. |
| `torque` | En planta, función `torque(t,q,qd)` que devuelve dos torques pedidos [N·m]; `None` solicita cero. |
| `limites` | En planta, dos límites simétricos [N·m]. |
| `trayectoria` | Referencia `TrayectoriaQuintica` para seguimiento. |
| `controlador` | Instancia `ControladorPD`. |
| `permanencia` | Tiempo final en reposo de la referencia [s], ≥1. El horizonte es T+permanencia. |
| `modo` | `"continuo"` o `"digital"` en seguimiento. |
| `periodo` | Ts [s] positivo y finito en modo digital; no afecta al continuo. |

`simular_libre` y `simular_planta` retornan `ResultadoSimulacion`;
`simular_seguimiento` retorna `ResultadoSeguimiento`. El callback de torque
debe conservar sus entradas y no tener efectos laterales: se llama durante
la integración y nuevamente para registrar la salida.
En digital se actualiza desde t=0, excluyendo el tiempo final; se mantiene
el torque entre muestras. La fricción sigue la velocidad instantánea.

Las funciones auxiliares públicas son:

| Función | Argumentos | Retorno |
|---|---|---|
| `grilla_tiempo(duracion, paso=0.001)` | Duración y paso positivos [s] | Array desde cero hasta el final inclusive; el último intervalo puede ser menor. |
| `limitar_torque(solicitado, limites=LIMITES_TORQUE)` | Torque (2,) y límites [N·m] | Nuevo array recortado entre ±límites, sin modificar la solicitud. |
| `medir_seguimiento(resultado)` | `ResultadoSeguimiento` | Diccionario descrito en la sección de métricas. |

### Comparaciones del punto de entrada

Se importan desde `main`; importar ese módulo no ejecuta su función `main()`.

~~~python
comparar_continuo(dinamica, escenario, controladores, friccion=Friccion())
comparar_control(dinamica, escenario, controladores, friccion=Friccion(),
                 modos=("continuo",), periodo=0.001)
comparar_variantes(dinamica, escenario, controladores, friccion, modos,
                   periodo, barrido="ninguno")
informar_seguimiento(resultado, recuperacion=False)
main()
~~~

`escenario` es un nombre de la tabla controlada; `controladores` es una lista
de instancias con nombres distintos. `modos` contiene `"continuo"` y/o
`"digital"`. Para un único modo usar una tupla como `("digital",)`,
no un string. `barrido` admite los mismos tres valores que la consola.
`comparar_continuo` reutiliza la comparación común en modo continuo.
Las tres comparaciones retornan `{tramo: {identificador: ResultadoSeguimiento}}`.
`informar_seguimiento` imprime métricas y retorna `None`; `recuperacion=True`
usa el resumen de recuperación. `main()` procesa los argumentos del proceso
y retorna `None` al finalizar.

En `comparar_variantes`, el barrido de fricción crea instancias `Friccion`
con parámetros nominales y las cuatro escalas; no conserva B/Tc/epsilon
personalizados del argumento `friccion`. El barrido de período sí conserva
la instancia recibida. Utilizar los valores de barrido documentados.

### Visualización

Se importa desde `pendulo.visualizacion`.

| Función | Argumentos y predeterminados | Retorno |
|---|---|---|
| `graficar_resultado` | `resultado`: `ResultadoSimulacion`; `nombre="Movimiento libre"` | `Figure` con cuatro paneles. |
| `graficar_seguimientos` | `resultados`: diccionario de seguimientos; `nombre="Control continuo"`; `limite_error=2.0` [°], positivo y finito | `Figure` con seis paneles. |
| `crear_animacion` | `resultado`: `ResultadoSimulacion`; `nombre="Movimiento libre"`; `longitudes=(0.20,0.20)` [m]; `periodo=0.020` [s] | Tupla `(Figure, FuncAnimation)`. |
| `crear_animacion_comparada` | `resultados`: diccionario de seguimientos con tiempos iguales; `nombre="Comparación"`; `longitudes=(0.20,0.20)` [m]; `periodo=0.020` [s] | Tupla `(Figure, FuncAnimation)`. |
| `actualizar_animacion` | `indice` de muestra; `resultado` libre/planta; artistas `linea` y `texto`; `longitudes` [m] | Tupla de artistas modificados; dibuja manualmente una muestra. |

Los diccionarios de comparación deben contener al menos un resultado. Los
colores siguen su orden de inserción; pueden repetirse si se supera el ciclo
de colores. Ninguna de estas funciones integra, muestra con `show` ni guarda
archivos automáticamente.

## Resultados y métricas de Python

### ResultadoSimulacion

Normalmente se obtiene del integrador. Su constructor recibe, en orden,
`t, q, qd, cinetica, potencial, evaluaciones, torque_solicitado,
torque_aplicado, rozamiento`, sin valores predeterminados.

| Campo | Forma | Unidad / significado |
|---|---|---|
| `t` | (n,) | s |
| `q`, `qd` | (n,2) | rad y rad/s |
| `cinetica`, `potencial` | (n,) | J |
| `energia` | (n,) | Propiedad calculada: K+U [J] |
| `evaluaciones` | Entero | Llamadas a la ecuación diferencial |
| `torque_solicitado`, `torque_aplicado`, `rozamiento` | (n,2) | N·m, en la grilla de salida |

### ResultadoSeguimiento

Su constructor recibe `simulacion, trayectoria, controlador, q_d, qd_d,
qdd_d, torque_referencia`. Los campos adicionales tienen los valores
predeterminados indicados abajo:

| Campo | Forma o tipo | Unidad / predeterminado |
|---|---|---|
| `simulacion` | `ResultadoSimulacion` | Estados y torques reales |
| `trayectoria`, `controlador` | Objetos usados | Referencia e instancia de control |
| `q_d`, `qd_d`, `qdd_d` | (n,2) | rad, rad/s, rad/s² |
| `torque_referencia` | (n,2) | Demanda ideal [N·m] |
| `error` | (n,2) | Propiedad q_d−q [rad] |
| `modo` | Texto | `"continuo"` |
| `periodo` | Número o `None` | Ts [s]; predeterminado `None` |
| `tiempos_control` | (n_control,) o `None` | s; predeterminado `None` |
| `torque_control_solicitado`, `torque_control_aplicado` | (n_control,2) o `None` | N·m; predeterminado `None` |

En resultados continuos el período y las trazas de control son `None`.
En digital, las trazas guardan cada actualización, incluso si el período
es menor que el paso de salida. El tiempo final no agrega una actualización.

### Diccionario de medir_seguimiento

Los valores por eje son arrays de dos componentes. Las tres comprobaciones
son booleanos; `asentamiento` es un tiempo escalar o `None`.

| Clave | Unidad y definición |
|---|---|
| `error_maximo_grados` | °; máximo absoluto observado por eje |
| `error_final_grados` | °; valor absoluto en la última muestra |
| `velocidad_final` | rad/s; velocidad con signo en la última muestra |
| `asentamiento` | s; primera muestra posterior al último error >0.2° en cualquiera de los ejes; 0 si nunca estuvo fuera, `None` si el final está fuera |
| `torque_solicitado_maximo` | N·m; máximo absoluto del pedido |
| `torque_aplicado_maximo` | N·m; máximo absoluto entregado |
| `torque_referencia_maximo` | N·m; máximo absoluto ideal |
| `saturacion_porcentaje` | % de muestras de salida con pedido fuera del límite |
| `velocidad_maxima` | rad/s; máximo absoluto real |
| `rpm_maxima` | rpm; velocidad real máxima multiplicada por N y convertida |
| `potencia_maxima` | W; máximo absoluto de τ_aplicado·qd |
| `potencia_positiva_maxima` | W; máximo positivo, o 0 |
| `potencia_negativa_minima` | W; mínimo negativo, o 0 |
| `torque_motor_estimado` | N·m; torque aplicado máximo dividido por N·ηmax |
| `potencia_motor_estimada` | W; potencia absoluta máxima dividida por ηmax |
| `solicitud_sin_saturacion` | Todo el pedido observado cabe en los límites de torque |
| `cumple_precision` | Ambos ejes cumplen máximo ≤2° y final ≤0.2° |
| `cumple_capacidad` | Demanda ideal dentro de torque límite y velocidad, potencia y torque de motor estimado dentro de las capacidades consideradas |

El asentamiento solo describe el horizonte y la resolución de salida
observados. Los máximos muestreados no demuestran el extremo entre muestras.

## Supuestos y alcance

El modelo es un 2R vertical con dos barras de aluminio uniforme de
200×20×10 mm y 108 g cada una, sin carga adicional. La gravedad apunta a −Y.
El modelo actuado incorpora el conjunto del segundo eje transportado en el
codo, fijación estimada de 20 g e inercias de rotor reflejadas por N².
El primer motor está fijo en la base.

La planta usa M, C, G y rozamiento suave B·qd+Tc·tanh(qd/epsilon).
Los parámetros de fricción son supuestos, no mediciones. Las pérdidas a
3 rad/s equivalen aproximadamente a 7.5–8% de los límites continuos nominales.
La compensación de gravedad utiliza el mismo modelo y un estado ideal medido.

La transmisión se supone rígida; se omiten juego, elasticidad, fricción
estática, dinámica eléctrica, temperatura, colisiones y topes. La planta
limita torque y conserva los estados integrados, incluso fuera del rango
de las referencias. No impone límites artificiales de velocidad.

Las capacidades se estiman con los candidatos Maxon documentados en el
README. Las eficiencias máximas se usan en las métricas de selección; no
modifican la entrega de torque de la planta.

Los criterios nominales corresponden a PD+G continuo y digital de 1 ms.
PD sin gravedad y las variaciones sirven para comparar y diagnosticar.
En las verificaciones anteriores, períodos de 10/20 ms incumplieron la
recuperación y 20 ms incumplió seguimiento extremo. Ejecutar un caso sin
excepciones no implica que cumpla precisión.

Las pruebas aportan evidencia para los casos simulados. No garantizan todos
los estados posibles ni la precisión de una construcción física.

## Verificación de esta guía

Esta sección registra las comprobaciones de la entrega documental. Los
ejemplos se ejecutan sin ventanas; la interacción gráfica se apoya en las
pruebas TkAgg anteriores del README, incluidas reproducción, botón y
animación simultánea. No se atribuye una nueva revisión de escritorio a
esta entrega.

Comprobado el **1 de octubre de 2026**, con Python 3.12.14 y las dependencias
fijadas del proyecto. Los ocho comandos válidos utilizaron el intérprete
`.venv/bin/python` y retornaron código 0. Se ejecutaron los ejemplos de
consola indicados en la tabla con `MPLBACKEND=Agg` y
`MPLCONFIGDIR=/tmp/tpf-guia-mpl`; las simulaciones usaron `--sin-graficos`.

| Prueba y propósito | Método y condiciones | Resultado esperado | Resultado obtenido | Estado | Análisis preliminar |
|---|---|---|---|---|---|
| Ayuda y argumentos | `main.py --help`; contrastar con las declaraciones del parser | Ayuda completa, sin integración | Código 0; coinciden los diez argumentos documentados, contando `-h/--help` como uno | Cumplida | Las opciones, valores predeterminados e interacciones se verificaron contra el código. |
| Equilibrio inferior libre | Ejemplo `colgante`, modelo `barras`, fricción 0; 5 s, RK45 con rtol=1e-7 y atol=1e-9 | Permanecer cerca de (−π/2,0), sin torque ni disipación física | 5001 muestras; q2 final≈2.284e-9 rad; qd final≈(1.395e-8,−4.319e-8) rad/s; variación máxima de E registrada 0 J | Cumplida | Las desviaciones pequeñas son numéricas; el cero de energía corresponde a este registro. |
| Seguimiento continuo | Ejemplo PD+G `abajo_arriba`, modelo actuado y fricción nominal | Máximo≤2° y final≤0.2° por eje; horizonte 3 s | Máximos≈(0.446448,0.159042)°; finales≈(0.000152,0.001434)°; precisión y capacidad verdaderas | Cumplida | Confirma el uso documentado de la referencia y permanencia final. |
| Comparar leyes y modos | Ejemplo `--control comparar --modo comparar`, `interior_a`, Ts=1 ms | Cuatro resultados; distinguir precisión de ejecución correcta | Cuatro resultados de 3 s; PD+G digital: máximos≈(0.383749,0.414541)° y finales≈(0.000177,0.001226)°; PD final eje 1≈1.504° en ambos modos | Uso cumplido; precisión PD incumplida | PD+G cumple; el error estacionario de PD queda visible y no se presenta como fallo del comando. |
| Recuperación digital | Ejemplo PD+G digital, `estabilizacion`, Ts=1 ms | Evaluar la recuperación de 5° por asentamiento, separadamente del máximo nominal | 3000 actualizaciones; asentamiento 0.176 s; finales≈(2.079e-7,8.593e-7)° | Cumplida | Confirma las unidades de Ts y el resumen de recuperación. |
| Barrido de fricción | Ejemplo PD+G, `abajo_arriba`, ambos modos; escalas 0/0.5/1/2 | Ocho resultados con condiciones comunes y etiquetas de escala | Ocho resultados de 3 s; todos cumplen precisión y capacidad; peor máximo observado≈0.649566°, peor error final≈0.010356° | Cumplida | Reproduce la sensibilidad sin alterar las ganancias. |
| Barrido de períodos | Ejemplo PD+G, `estabilizacion`; continuo y Ts=0.5/1/5/10/20 ms | Seis resultados; conservar incumplimientos de períodos grandes | Continuo y 0.5/1/5 ms asientan en 0.176 s; a 10 ms final≈(0.003457,0.356670)°; a 20 ms≈(1.239987,5.998702)° | Uso cumplido; recuperación a 10/20 ms incumplida | El barrido ejecuta y documenta todos los casos; completar la integración no garantiza recuperación. |
| Ida y vuelta | Ejemplo `--control comparar --escenario ida_vuelta` | Dos tramos con dos controladores, tiempos reiniciados y estado heredado | Cuatro resultados en total (dos por tramo), de 3 s cada uno; PD+G cumple en ambos; PD supera 2° durante la ida | Uso cumplido; máximo PD en ida incumplido | Se contrastó también la herencia del estado contra la implementación de la comparación. |
| Errores de argumentos | `main.py --periodo 0 --sin-graficos` y `main.py --modo digital --sin-graficos`, sin seleccionar controlador | Rechazo antes de integrar | Ambos retornan código 2, con mensajes sobre período positivo o selección de controlador | Cumplida | Confirma las restricciones descritas en la tabla de combinaciones. |
| Referencia pública y ejemplos Python | Contraste de firmas/defaults con los módulos; análisis AST de entradas públicas; compilar seis bloques y ejecutar los cuatro ejemplos completos en orden | Referencia completa y ejemplos utilizables con sus imports | 50 entradas públicas presentes, sin nombres omitidos; seis bloques compilados; cuatro ejemplos completos ejecutados; 3001 muestras digitales, 5001 libres y cuatro comparaciones | Cumplida | La comprobación de presencia se complementó con revisión de argumentos, unidades y retornos; no valida nuevos modelos físicos. |
| Figuras del ejemplo Python | Dibujar las figuras y animación del ejemplo con Agg, sin guardar archivos | Construcción y dibujo sin errores | Curvas y primer fotograma dibujados; `plt.show()` avisó que Agg no es interactivo, como corresponde | Cumplida para Agg | El botón y los temporizadores reales se apoyan en las verificaciones TkAgg anteriores, no en esta comprobación. |
| Intérprete del IDE | `readlink -f .venv/bin/python`, `flatpak info` e inspección del runtime instalado | Identificar el Python utilizado y una posible diferencia entre sistema e IDE | Base /usr/bin/python3.12; PyCharm Flatpak 2026.2.2 con runtime 25.08 que dispone de Python 3.13 y no del ejecutable 3.12 | Diagnóstico cumplido | Se documentó la diferencia de entornos; esta entrega no cambió la instalación ni configuró el IDE. |
| Dependencias | `.venv/bin/python -m pip check` | Requisitos instalados compatibles según metadatos | Código 0; `No broken requirements found.`; aviso de caché de pip no escribible | Cumplida | El aviso desactiva la caché y no impide la comprobación; no se reinstalaron dependencias. |

Los enlaces locales de la guía se comprobaron y los ejemplos se contrastaron
con el código existente. La entrega es documental: no se modificaron el
modelo, las ganancias, las dependencias ni las funciones del programa.
Las comprobaciones cubren el uso descrito y mantienen visibles las limitaciones
numéricas y los incumplimientos de ciertos controladores/períodos.
