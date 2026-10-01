# Simulación del doble péndulo 2R

## Estado

Están completadas las **etapas 1 a 7: entorno, modelo mecánico, cinemática,
dinámica propia, integración, gráficos, animación, actuadores, rozamiento,
trayectorias, control continuo y digital, comparación y animación simultánea**.
La primera versión acordada queda implementada.
El robot auxiliar del diagnóstico
no es el modelo mecánico del proyecto.

## Ejecución

Se utiliza Python 3.12 y una `.venv` dentro de esta carpeta. Para reproducir el
entorno con las dependencias fijadas en `requirements.txt`:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
.venv/bin/python main.py --caso invertido
.venv/bin/python main.py --modelo barras
.venv/bin/python main.py --modelo actuado --friccion 0
.venv/bin/python main.py --modelo actuado --friccion 0.5 --sin-graficos
.venv/bin/python main.py --caso colgante --sin-graficos
.venv/bin/python main.py --control comparar --escenario abajo_arriba
.venv/bin/python main.py --control comparar --escenario ida_vuelta
.venv/bin/python main.py --control pd_gravedad --escenario estabilizacion
.venv/bin/python main.py --control comparar --escenario extremos_opuestos --sin-graficos
.venv/bin/python main.py --control comparar --modo comparar --escenario abajo_arriba
.venv/bin/python main.py --control pd_gravedad --modo digital --periodo 0.001 --escenario interior_a
.venv/bin/python main.py --control pd_gravedad --modo comparar --barrido friccion --escenario extremos_opuestos
.venv/bin/python main.py --control pd_gravedad --barrido periodo --escenario estabilizacion --sin-graficos
.venv/bin/python -m pytest -v
```

El punto de entrada muestra versiones, propiedades de las barras, posiciones de
cuatro configuraciones y contraste de la dinámica en consola. Después simula
el escenario elegido y muestra gráficos y animación en ventanas; por defecto
ejecuta `oscilacion` con **montaje, rotores y fricción nominal**. `--modelo barras`
recupera las barras ideales de las etapas anteriores. `--friccion` elige escala
0, 0.5, 1 o 2; si se omite, vale 1 en actuado y 0 en barras.
`--sin-graficos` omite las figuras y la espera de ventanas.
No exporta datos, gráficos ni videos. En el IDE debe seleccionarse
`.venv/bin/python` como intérprete. Para terminar la ejecución gráfica, cerrar
todas las ventanas.

`--control` permite `libre` (por defecto), `pd`, `pd_gravedad` o `comparar`.
En control continuo, `--escenario` selecciona `abajo_arriba`, `arriba_abajo`,
`extremos`, `extremos_opuestos`, `eje1`, `eje2`, `nulo_horizontal`,
`estabilizacion`, `ida_vuelta`, `interior_a`, `interior_b` o `borde`.
`--modo` permite `continuo` (por defecto), `digital` o `comparar`; el último
compara ambos modos con idénticas condiciones. `--periodo` está en segundos y
vale `0.001` por defecto. Los gráficos y la animación simultánea muestran todas
las instancias calculadas, con nombres y colores comunes.
La ida-vuelta conserva el estado físico propio de cada combinación entre tramos
y crea una figura de comparación y una animación por tramo.

`--barrido friccion` compara escalas 0, 0.5, 1 y 2 usando los modos seleccionados.
`--barrido periodo` compara un continuo y digitales de 0.5, 1, 5, 10 y 20 ms,
independientemente de `--modo`, con la fricción elegida. No repite el continuo
por cada período. Los barridos requieren seleccionar un controlador con
`--control`; el modo libre sigue disponible por defecto.

La ventana de animación incluye **«Volver a reproducir»**. Se puede pulsar
durante el movimiento o al terminar para reiniciar desde t=0, usando los
resultados calculados, sin volver a ejecutar el programa.

Si Matplotlib selecciona `Agg`, solo dispone de renderizado sin ventanas. Se
verificó también `TkAgg` en el escritorio; puede elegirse explícitamente con
`MPLBACKEND=TkAgg .venv/bin/python main.py --caso oscilacion`, siempre que el
entorno tenga Tk y acceso a la pantalla.

## Comprobación de la etapa 1

Se utiliza una barra auxiliar uniforme de **1 m y 1 kg**, horizontal en `q=0 rad`,
con gravedad `(0,-9.81,0) m/s²`, sin rotor ni fricción. En DH estándar su centro
de masa es `(-0.5,0,0) m` respecto de la terna del extremo.

Los resultados esperados se calculan independientemente:

- Extremo: `(1,0,0) m` por geometría.
- Inercia articular: `1/12 + 1·0.5² = 1/3 kg·m²`, por Steiner.
- Torque gravitatorio de sostén: `1·9.81·0.5 = 4.905 N·m`.
- Dinámica inversa sin velocidad ni aceleración: el mismo torque de sostén.

Las pruebas contrastan esos valores con tolerancia absoluta `1e-12` en las unidades
respectivas y ejecutan `main.py` en otro proceso usando el intérprete activo.

### Resultados obtenidos

Entorno verificado con Python **3.12.14** en Linux. Versiones importadas:
Robotics Toolbox **1.4.4**, NumPy **2.5.3**, SciPy **1.18.1**, SymPy **1.14.0**,
Matplotlib **3.11.2** y pytest **9.1.1**. `requirements.txt` fija también las
dependencias transitivas instaladas; Python se instala por separado.

| Prueba y propósito | Método y condiciones | Resultado esperado | Resultado obtenido | Estado | Análisis preliminar |
|---|---|---|---|---|---|
| Importación y versiones: comprobar disponibilidad | `main.py` importa los seis módulos con el intérprete de `.venv` y consulta sus versiones | Importaciones sin excepciones; Toolbox 1.4.4 y Python 3.12 | Seis importaciones correctas; versiones indicadas arriba | Cumplida | Las bibliotecas cargan en este entorno; no verifica todas sus funcionalidades. |
| Cinemática: comprobar operación de Toolbox | FK del robot auxiliar descrito arriba, q=0 rad | Extremo (1,0,0) m; tolerancia absoluta 1e-12 m | (1,0,0) m; diferencia máxima 0 m | Cumplida | Coincide con la geometría auxiliar. |
| Inercia: comprobar operación dinámica | `inertia(q)` en el mismo robot | 1/3 kg·m²; tolerancia absoluta 1e-12 kg·m² | 0.3333333333333333 kg·m²; diferencia numérica 0 frente al valor esperado representado en punto flotante | Cumplida | Coincide con Steiner para esta barra. |
| Gravedad: comprobar signo y torque de sostén | `gravload(q)` con gravedad física hacia −Y | +4.905 N·m; tolerancia absoluta 1e-12 N·m | +4.905 N·m; diferencia 0 N·m | Cumplida | El torque positivo contrarresta la caída de la barra horizontal. |
| Dinámica inversa: comprobar RNE | `rne(q, q̇, q̈)` con q=q̇=q̈=0 | +4.905 N·m; tolerancia absoluta 1e-12 N·m | +4.905 N·m; diferencia 0 N·m | Cumplida | Coincide con el equilibrio estático esperado. |
| Punto de entrada: comprobar ejecución independiente | Ejecutar `main.py` desde `.venv`, directamente y como subproceso de pytest | Código de salida 0 y diagnóstico completo | Código 0 y salida con versiones, posición, inercia y torques en ambas ejecuciones | Cumplida | El proyecto puede ejecutarse desde el intérprete acordado. |
| Consistencia de dependencias | `.venv/bin/python -m pip check` | Sin requisitos incompatibles o faltantes | `No broken requirements found.`; código 0 | Cumplida | Los metadatos de las dependencias instaladas son consistentes. |

`pytest -v` ejecutó **dos pruebas**, ambas aprobadas: una agrupa las cuatro
comparaciones analíticas y otra verifica el punto de entrada en un proceso
independiente. Las diferencias cero corresponden a las representaciones numéricas
de este caso, no constituyen una garantía general de exactitud.

La restricción de escritura en la configuración del usuario hace que Matplotlib
use una caché temporal en `/tmp`, con un aviso al importar. Esto no impidió las
comprobaciones. Si se ejecuta bajo la misma restricción, se puede indicar una
ubicación escribible mediante `MPLCONFIGDIR`. Las verificaciones de ventanas,
gráficos y animaciones se documentan en la etapa 4.

El entorno permitió continuar con el modelo mecánico de la etapa 2. La
instalación actual y sus imports están verificados; aún no se
repitió la instalación completa desde cero usando el archivo de versiones fijadas.
Las pruebas de esta etapa no validan la mecánica ni la dinámica del doble péndulo.

## Modelo mecánico y cinemática: etapa 2

`pendulo/parametros.py` define las barras mediante una estructura simple e
inmutable `Barra`, con dimensiones y densidad en SI. Sus propiedades calculan
masa, centro de masa y tensor central. `pendulo/modelo.py` construye el robot
de Toolbox y entrega las posiciones de base, codo y extremo, como un array
`(3,3)` con filas XYZ en metros. También incluye la cinemática geométrica
independiente utilizada para contrastar los resultados.

### Propiedades y referencias

La orientación de la sección fue confirmada: longitud `L=0.20 m` sobre X local,
ancho `a=0.02 m` sobre Y local y espesor `e=0.01 m` sobre Z local. La densidad
supuestamente uniforme es `ρ=2700 kg/m³`. Cada barra tiene:

\[
m=\rho Lae=0.108\ \mathrm{kg},\qquad
{}^i r_G=(-L/2,0,0)=(-0.10,0,0)\ \mathrm{m}.
\]

La terna DH de cada eslabón está en su extremo **distal** y X apunta desde su
articulación proximal hacia ese extremo. Por eso el centro local tiene X negativa;
desde la articulación proximal está a `+0.10 m`. El tensor referido al centro
de masa, con ejes paralelos a la terna DH, es:

\[
I_G=\frac{m}{12}\operatorname{diag}(a^2+e^2,L^2+e^2,L^2+a^2)
=\operatorname{diag}(4.5\times10^{-6},3.609\times10^{-4},3.636\times10^{-4})
\ \mathrm{kg\,m^2}.
\]

Los productos de inercia son cero por simetría. Para comprobar la referencia,
Steiner al extremo da `diag(4.5e-6,1.4409e-3,1.4436e-3) kg·m²`. Este tensor
trasladado se usa únicamente en la verificación: Toolbox recibe **el tensor
central** y el centro de masa local, evitando duplicar la traslación.

### DH y geometría

Las dos articulaciones son revolutas, positivas alrededor de +Z (antihorarias
vistas desde +Z). La base coincide con el mundo y la herramienta con la terna
del extremo; ambas transformaciones son identidad. Se usa DH estándar:

| Eslabón | θ [rad] | d [m] | a [m] | α [rad] |
|---|---|---|---|---|
| 1 | q1 | 0 | 0.20 | 0 |
| 2 | q2 | 0 | 0.20 | 0 |

\[
{}^{i-1}A_i=
\begin{bmatrix}
\cos q_i&-\sin q_i&0&L_i\cos q_i\\
\sin q_i&\cos q_i&0&L_i\sin q_i\\
0&0&1&0\\
0&0&0&1
\end{bmatrix}.
\]

Las posiciones independientes son
`codo=(L1 cos(q1), L1 sin(q1), 0)` y
`extremo=codo+(L2 cos(q1+q2), L2 sin(q1+q2), 0)`.
La orientación absoluta del segundo eslabón es `q1+q2`, mientras que q2 es
relativo al primero. La gravedad física es `(0,-9.81,0) m/s²`.

El modelo actual contiene solo las barras. Se fijan explícitamente rotor,
fricción viscosa y Coulomb a cero y relación de transmisión a uno. No se añaden
topes: `[-π,π]` es el rango previsto de destinos, y las evaluaciones no recortan
ángulos ni modifican el estado del robot. El plegado es admisible en este modelo
sin colisiones, aunque represente superposición de cuerpos en una construcción.

### Configuraciones verificadas

La base es `(0,0,0) m` y Z=0 en todos los casos. Las coordenadas de esta tabla
son los valores geométricos exactos; las evaluaciones numéricas de seno/coseno
dejan residuos de hasta `2.4493e-17 m` en componentes que deben ser cero.
Toolbox y la geometría calculada coincidieron numéricamente en los cuatro casos.

| Configuración | q [rad] | Codo esperado y obtenido [m] | Extremo esperado y obtenido [m] |
|---|---|---|---|
| Horizontal | (0,0) | (0.20,0,0) | (0.40,0,0) |
| Colgante | (−π/2,0) | (0,−0.20,0) | (0,−0.40,0) |
| Invertida | (π/2,0) | (0,0.20,0) | (0,0.40,0) |
| Plegada | (0,π) | (0.20,0,0) | (0,0,0) |

### Informe de verificaciones

Método reproducible: `.venv/bin/python main.py` y
`.venv/bin/python -m pytest -v -s`. La grilla usa
`np.linspace(-np.pi,np.pi,25)` en cada eje, incluidos ambos extremos, sin azar.
Las comparaciones numéricas usan `rtol=0` y `atol=1e-12` en cada unidad.

| Prueba y propósito | Método y condiciones | Resultado esperado | Resultado obtenido | Estado | Análisis preliminar |
|---|---|---|---|---|---|
| Masa: comprobar volumen y SI | Ambas barras; ρLae y valores cargados en Toolbox | 0.108 kg por barra | 0.10800000000000001 kg; diferencia 1.3877787807814457e-17 kg | Cumplida | Masa calculada con densidad supuesta; no es una medición. |
| Centro: comprobar referencia local | Ambas barras y valores cargados en Toolbox | (−0.10,0,0) m en terna distal | Mismo vector; diferencia 0 m | Cumplida | El signo negativo responde al origen DH distal. |
| Inercia central: comprobar orientación de sección | Ambas barras; fórmula del prisma frente a valores analíticos y Toolbox | Diagonal indicada arriba; productos cero | Diagonal indicada arriba; diferencia máxima 1.6263032587282567e-19 kg·m² | Cumplida | El tensor está referido al centro de masa y usa la sección confirmada. |
| Steiner: comprobar referencia del tensor | Traslado al extremo usando m y r | diag(4.5e-6,1.4409e-3,1.4436e-3) kg·m² | Valores esperados; diferencia máxima 4.336808689942018e-19 kg·m² | Cumplida | Se conserva el tensor central en el modelo para evitar doble traslado. |
| DH y unidades: comprobar construcción | Dos juntas, base/herramienta identidad, d=α=offset=0, a=0.20 m y gravedad hacia −Y | DH estándar con parámetros acordados y actuadores/fricción nulos | Todos los parámetros coinciden | Cumplida | La etapa 2 modela únicamente las barras. |
| Cuatro posiciones: comprobar signos y plegado | Configuraciones de la tabla anterior; contraste de ambas rutas con coordenadas conocidas | Posiciones de la tabla a 1e-12 m | Error frente a valores exactos ≤2.4493e-17 m; diferencia entre rutas 0 m | Cumplida | Horizontal, colgante e invertida usan la misma convención; plegado sin colisiones. |
| Signo y carácter relativo de q2 | q=(0,π/2) y (π/2,−π/2) | Extremo (0.20,0.20,0) m en ambos casos | Coincide dentro de 1e-12 m | Cumplida | Distingue q2 relativo de un ángulo absoluto. |
| Cinemática en el rango | 625 pares de la grilla; base, codo y extremo por DH y geometría | Coincidencia a 1e-12 m | Diferencia máxima 1.2490009027033011e-16 m | Cumplida | Evidencia numérica reproducible dentro del rango, sin afirmar cubrir todos sus puntos. |
| Centros globales: comprobar transformación DH | Misma grilla; Rr+t frente al punto medio de cada barra | Coincidencia a 1e-12 m | Diferencia máxima 8.3266726846886741e-17 m | Cumplida | Confirma la referencia distal y la ubicación física de ambos centros. |
| Orientación final: comprobar suma de ángulos | Misma grilla; rotación DH frente a Rz(q1+q2) y comparación fkine/fkine_all | Diferencias ≤1e-12, adimensionales | Máxima diferencia de rotación 5.4252674220423293e-16; fkine y fkine_all coinciden | Cumplida | La composición de giros corresponde al 2R vertical acordado. |
| Ausencia de recorte y mutaciones | q=(2π+0.3,−2π−0.2); comparación de rutas y arrays antes/después | Geometría original, q y estado del robot sin cambios | Comparación aprobada a 1e-12 m; arrays sin cambios | Cumplida | El rango de destinos no se aplica como tope de la planta. |
| Regresión del entorno y ejecución | Dos pruebas de etapa 1 y ejecución ampliada de main.py | Diagnóstico anterior conservado; salida 0 | Ambas pruebas aprobadas; main.py finaliza con código 0 | Cumplida | Las incorporaciones no rompieron el diagnóstico inicial. |

En total se ejecutaron **12 casos de prueba**, de los cuales 10 corresponden a
esta etapa y 2 a la anterior. Los errores geométricos observados son compatibles
con el redondeo en punto flotante y están muy por debajo de la tolerancia.
Estas verificaciones corresponden al modelo mecánico y la cinemática; el
contraste de M, C y G se documenta en la sección siguiente. No se modificaron
las dependencias.

## Dinámica propia y contraste: etapa 3

`pendulo/dinamica.py` implementa `Dinamica(robot)` para el modelo 2R de barras.
Lee los parámetros del robot construido en la etapa 2, pero no llama a sus
operaciones dinámicas para obtener las expresiones propias. Las transformaciones,
pseudoinercias, M, C, G, Ṁ y potencial simbólicos quedan disponibles para revisar.
La construcción deriva una vez y prepara evaluadores NumPy con `lambdify`;
se utiliza la misma instancia para todas las evaluaciones de ese modelo.

Los parámetros se convierten de su representación decimal a racionales de
SymPy, conservando incluso los residuos de los floats del modelo. Esto permite
comprobar identidades algebraicas sin introducir redondeos simbólicos sucesivos;
no convierte supuestos físicos en valores exactos. Los métodos `M`, `C`, `G`,
`M_punto`, `potencial` e `inversa` retornan arrays o escalares numéricos en SI.
Si se cambia un parámetro del robot, debe construirse otra instancia de dinámica.

### Ecuaciones implementadas

Sea `I_G` el tensor central, `r` el centro en la terna DH distal y `m` la masa.
La pseudoinercia usa los segundos momentos respecto de esa terna:

\[
S=\tfrac12\operatorname{tr}(I_G)\,I_3-I_G+mrr^T,\qquad
J=\begin{bmatrix}S&mr\\mr^T&m\end{bmatrix}.
\]

El bloque superior de J se expresa en kg·m², los primeros momentos en kg·m
y la esquina inferior en kg. Para ambas barras, los valores nominales son:

\[
J=\begin{bmatrix}
0.00144&0&0&-0.0108\\
0&0.0000036&0&0\\
0&0&0.0000009&0\\
-0.0108&0&0&0.108
\end{bmatrix}.
\]

Se acumulan `A0_i` a partir del DH y se aplican las ecuaciones de la cursada:

\[
M_{sk}=\sum_{i=1}^{2}\operatorname{tr}
\left[\frac{\partial A_0^i}{\partial q_s}J_i
\left(\frac{\partial A_0^i}{\partial q_k}\right)^T\right],
\]
\[
C_{sj}=\sum_{k=1}^{2}\frac12\left[
\frac{\partial M_{sj}}{\partial q_k}
+\frac{\partial M_{sk}}{\partial q_j}
-\frac{\partial M_{jk}}{\partial q_s}\right]\dot q_k.
\]

Para hacer compatibles las dimensiones homogéneas, se definen
`g_h=(0,-9.81,0,0)` y `r_G_h=(r_x,r_y,r_z,1)`. Entonces:

\[
G_s=-\sum_{i=1}^{2}m_i g_h^T
\frac{\partial A_0^i}{\partial q_s}r_{G,h}^i,\qquad
U=-\sum_{i=1}^{2}m_i g_h^T A_0^i r_{G,h}^i.
\]

G se obtiene directamente con la primera fórmula y luego se verifica
`G=grad(U)`. Se calcula también `Ṁ=sum_k (∂M/∂q_k) q̇_k`. Las fórmulas de M,
C y G copiadas en el planteo resultaron coherentes con este contraste, usando
las referencias y los vectores homogéneos definidos aquí.

Para los parámetros nominales, los coeficientes redondeados a las cifras
mostradas dan:

\[
M=\begin{bmatrix}
0.0072072+0.00432\cos q_2&0.0014436+0.00216\cos q_2\\
0.0014436+0.00216\cos q_2&0.0014436
\end{bmatrix}\ \mathrm{kg\,m^2},
\]
\[
C=0.00216\sin q_2\begin{bmatrix}
-\dot q_2&-(\dot q_1+\dot q_2)\\\dot q_1&0
\end{bmatrix},
\qquad
G=\begin{bmatrix}
0.317844\cos q_1+0.105948\cos(q_1+q_2)\\
0.105948\cos(q_1+q_2)
\end{bmatrix}\ \mathrm{N\,m}.
\]

C tiene unidades kg·m²/s y `C q̇` tiene unidades N·m. La energía potencial es
`U=0.317844 sin(q1)+0.105948 sin(q1+q2)` J, con referencia cero cuando Y=0.
La dinámica inversa es `τ=M q̈+C q̇+G`, sin actuadores ni fricción en esta etapa.

### Condiciones reproducibles

Ejecutar `.venv/bin/python -m pytest -v -s` muestra las diferencias medidas.
El contraste usa nueve ángulos equiespaciados en `[-π,π]` por eje, con estos
cuatro perfiles de velocidad/aceleración para cada par: **324 estados**.

| q̇ [rad/s] | q̈ [rad/s²] |
|---|---|
| (0,0) | (0,0) |
| (1.2,−0.7) | (2,−1) |
| (−2,1.5) | (−6,4) |
| (3,−3) | (6,−6) |

El chequeo de positividad usa 25 ángulos por eje, **625 pares**. Los extremos
están incluidos en ambas grillas y no se usa azar. Las tolerancias son absolutas
(`rtol=0`): 1e-12 para comparaciones directas, 1e-10 kg·m²/s para diferencias
finitas de Ṁ y 1e-9 N·m para el gradiente numérico del potencial.

### Informe de verificaciones

| Prueba y propósito | Método y condiciones | Resultado esperado | Resultado obtenido | Estado | Análisis preliminar |
|---|---|---|---|---|---|
| Pseudoinercia: comprobar referencia DH | Ambas barras; J frente a integrales de un prisma con X en [−L,0] y sección centrada | Matriz nominal indicada arriba, diferencia ≤1e-12 en unidades de cada bloque | Ambas matrices coinciden dentro de la tolerancia | Cumplida | Los momentos incluyen correctamente la traslación del centro al origen distal. |
| M: contrastar inercia con Toolbox | 324 estados; trazas frente a `robot.inertia(q)` | Diferencia ≤1e-12 kg·m² | Máxima 1.734723475976807e-18 kg·m² | Cumplida | Las dos formulaciones representan la misma inercia de las barras en los casos probados. |
| G: contrastar gravedad con Toolbox | 324 estados; fórmula homogénea frente a `robot.gravload(q)` | Diferencia ≤1e-12 N·m | Máxima 1.6653345369377348e-16 N·m | Cumplida | Confirma signo y referencias del torque gravitatorio. |
| Cq̇: contrastar torque por velocidad | 324 estados; Christoffel frente a `robot.coriolis(q,qd) @ qd` | Diferencia ≤1e-12 N·m, sin exigir matrices C idénticas | Máxima 1.3877787807814457e-17 N·m | Cumplida | Coinciden los torques centrífugos y de Coriolis. |
| Inversa: contrastar torque completo | 324 estados; Mq̈+Cq̇+G frente a `robot.rne(q,qd,qdd)` | Diferencia ≤1e-12 N·m | Máxima 1.6653345369377348e-16 N·m | Cumplida | Incluye reposo, ambos signos y términos de aceleración. |
| Simetría de M: comprobar energía cinética | Residuo simbólico M−Mᵀ y grilla de 625 pares | Cero simbólico; residuo numérico ≤1e-12 kg·m² | Cero simbólico y máximo numérico 0 kg·m² | Cumplida | M es coherente con una forma cuadrática de energía. |
| Positividad de M: comprobar masas efectivas | Autovalores con `eigvalsh` en 625 pares | Todos estrictamente positivos | Menor observado 0.00028816834384900558 kg·m² | Cumplida | No hubo singularidad dinámica en la grilla; no demuestra todo estado posible. |
| Ṁ: contrastar derivada direccional | 324 estados; derivada simbólica frente a [M(q+hq̇)−M(q−hq̇)]/(2h), h=1e-6 s | Diferencia ≤1e-10 kg·m²/s | Máxima 8.7786028446501518e-13 kg·m²/s | Cumplida | La derivada numérica respalda la simbólica dentro del error de diferencias finitas. |
| Ṁ−2C: comprobar antisimetría | Parte simétrica simbólica y 324 estados numéricos | Cero simbólico y residuo ≤1e-12 kg·m²/s | Cero simbólico; máximo numérico 8.6736173798840355e-19 kg·m²/s | Cumplida | Se cumple la identidad estructural de la C elegida. |
| Potencia de la matriz antisimétrica | q̇ᵀ(Ṁ−2C)q̇ en 324 estados | Magnitud ≤1e-12 W | Máxima 1.7347234759768071e-18 W | Cumplida | No introduce potencia neta, dentro del redondeo numérico. |
| G=grad(U): comprobar identidad simbólica | Diferencia entre G por fórmula y derivadas de U | Vector cero simbólico | Cero en ambas componentes | Cumplida | El signo del potencial y el de los torques son coherentes. |
| Potencial: contrastar alturas geométricas | 81 posiciones; U simbólica frente a centros como puntos medios, sin usar A simbólicas | Diferencia ≤1e-12 J | Máxima 1.1102230246251565e-16 J | Cumplida | Verifica U con una cuenta geométrica independiente. |
| Gradiente numérico: contrastar torque | Mismas 81 posiciones; diferencias centrales del potencial geométrico, h=1e-6 rad | Diferencia con G ≤1e-9 N·m | Máxima 8.9530605151821874e-11 N·m | Cumplida | Diferencia compatible con truncamiento y redondeo al diferenciar numéricamente. |
| Sostén y potencial conocidos | Cinco configuraciones de la tabla siguiente; G, inversa propia y RNE en reposo | Torques manuales a 1e-12 N·m y potencial a 1e-12 J | Todas las comparaciones cumplen; valores indicados abajo | Cumplida | Las configuraciones verticales requieren torque cero, pero tienen distinto potencial. |
| Derivar una vez: comprobar evaluación | Interceptar `MatrixBase.diff` después de construir; evaluar M, C, G, Ṁ, U e inversa | Ninguna nueva diferenciación y resultados finitos | Sin llamadas de diferenciación; todos los resultados finitos | Cumplida | Las evaluaciones usan las funciones NumPy preparadas. |
| Regresión y entrada | Suite completa y `main.py` desde `.venv` | Pruebas previas preservadas; ejecución sin error | 24 casos aprobados (12 nuevos y 12 previos); salida 0 | Cumplida | La etapa 3 conserva el funcionamiento anterior. |

Los torques de sostén calculados manualmente y observados son:

| Configuración | q [rad] | τ esperado [N·m] | τ obtenido [N·m], redondeado | U esperado/obtenido [J], redondeado |
|---|---|---|---|---|
| Horizontal | (0,0) | (0.423792,0.105948) | (0.423792,0.105948) | 0 / 0 |
| Colgante | (−π/2,0) | (0,0) | (2.59498e-17,6.48744e-18) | −0.423792 / −0.423792 |
| Invertida | (π/2,0) | (0,0) | (2.59498e-17,6.48744e-18) | +0.423792 / +0.423792 |
| Plegada | (0,π) | (0.211896,−0.105948) | (0.211896,−0.105948) | 0 / 1.29749e-17 |
| Hacia izquierda | (π,0) | (−0.423792,−0.105948) | (−0.423792,−0.105948) | 0 / 5.18996e-17 |

Por ejemplo, en horizontal los brazos de los centros son 0.10 y 0.30 m para
el eje 1 y 0.10 m para el eje 2: `τ1=0.108·9.81·(0.10+0.30)` y
`τ2=0.108·9.81·0.10`. En el estado no estático mostrado por `main.py`,
`q=(0.4,−0.7)` rad, `q̇=(1.2,−0.8)` rad/s y `q̈=(2,−1)` rad/s², ambas
rutas dan aproximadamente `(0.41011555,0.10395993)` N·m; la diferencia
numérica observada en ese estado fue 0 N·m.

La evidencia respalda la dinámica propia del modelo actual, tanto por contraste
con Newton-Euler de Toolbox como por identidades simbólicas y cuentas
independientes de equilibrio y energía. No se detectaron discrepancias que
requieran cambiar el diseño. Los errores de diferencias finitas son mayores
que los del contraste directo, pero cumplen sus tolerancias específicas.
La integración, conservación de energía durante movimiento y animación se
documentan en la etapa 4. La dinámica de esta etapa aún no incluye montaje,
inercia de rotores ni fricción. No se modificaron las dependencias.

## Movimiento libre, integración y visualización: etapa 4

`pendulo/simulacion.py` integra el modelo sin torque ni fricción, usando la
instancia de dinámica ya derivada. Con estado `x=(q1,q2,qd1,qd2)`:

\[
\dot x=\begin{bmatrix}\dot q\\
M(q)^{-1}\big[-C(q,\dot q)\dot q-G(q)\big]\end{bmatrix}.
\]

En el código se resuelve el sistema con `np.linalg.solve`, sin formar M inversa.
Se usa `solve_ivp`, método RK45, `rtol=1e-7`, `atol=1e-9` y `t_eval` con salida
cada 1 ms. RK45 conserva sus pasos internos adaptativos: la grilla de salida
no obliga a integrar a paso fijo. Se incluye la muestra final; si la duración
no es múltiplo de 1 ms, el último intervalo de salida es más corto.

`ResultadoSimulacion` conserva tiempos, q, qd, energías cinética y potencial y
cantidad de evaluaciones de la ecuación diferencial. No se aplican topes ni
envoltura de ángulos. En cada muestra se calcula:

\[
K=\tfrac12\dot q^T M(q)\dot q,\qquad E=K+U.
\]

Como no hay trabajo externo ni fricción, la solución continua debe conservar E.
La variación numérica `E(t)−E(0)` permite evaluar la integración, sin confundirla
con pérdidas físicas. Las energías se calculan en la misma grilla que los estados.

### Escenarios y condiciones reproducibles

Los tres casos se definen en `main.py`; se puede elegir cualquiera con `--caso`:

| Caso | q0 [rad] | qd0 [rad/s] | Duración [s] | Muestras |
|---|---|---|---|---|
| colgante | (−π/2,0) | (0,0) | 5 | 5001 |
| invertido | (π/2+π/180,0) | (0,0) | 2 | 2001 |
| oscilacion | (−π/2+0.3,−0.2) | (0.4,−0.1) | 5 | 5001 |

La perturbación del invertido es explícitamente **1° en q1**, con q2 y
velocidades iniciales nulos. No se usa ruido para iniciar el movimiento.
El caso de oscilación tiene desviaciones y velocidades pequeñas alrededor del
colgante. La convergencia repite invertido y oscilación con `rtol=1e-9` y
`atol=1e-11`, manteniendo planta, estado inicial, duración y grilla de salida.

Reproducción de los informes:

```bash
.venv/bin/python -m pytest tests/test_simulacion.py tests/test_visualizacion.py -v -s
.venv/bin/python main.py --caso invertido --sin-graficos
.venv/bin/python -m pytest -v -s
```

Los criterios de esta etapa son verificaciones numéricas: posición del colgante
dentro de 1e-7 rad y velocidad dentro de 1e-6 rad/s; conservación de E dentro
de 1e-5 J; diferencias nominal/estricta dentro de 1e-4 rad y 1e-3 rad/s;
y menor variación de energía con tolerancias estrictas. No son especificaciones
de seguimiento de un controlador.

### Resultados de energía y convergencia

Las diferencias de estado son máximos por componente sobre todas las muestras,
sin envolver ángulos. Las variaciones de energía son `max(abs(E−E(0)))`.

| Caso | E inicial [J] | Variación de E nominal [J] | Variación de E estricta [J] | Diferencia q [rad] | Diferencia qd [rad/s] | Evaluaciones nominal/estricta |
|---|---|---|---|---|---|---|
| invertido | +0.42372745442571741 | 1.1994816722094015e-6 | 2.1532620297914917e-8 | 1.290201413262082e-5 | 2.9285636298226336e-4 | 2318 / 4988 |
| oscilacion | −0.408286589095539 | 8.6059217530021215e-9 | 8.5373985658776519e-11 | 1.0396894883218932e-6 | 1.621961817033224e-5 | 4082 / 9266 |

El colgante tiene E inicial `−0.42379200000000006 J` y variación de E observada
de 0 J a la resolución de los floats. Su desviación máxima fue
`3.5371651189042709e-9 rad` y su velocidad máxima `5.6230911325590502e-8 rad/s`.
No se sustituyó el torque gravitatorio por cero: los residuos de `cos(−π/2)`
y la tolerancia absoluta del integrador producen una evolución diminuta.
La energía no resuelve esa variación de estado, cuyo efecto es de segundo orden.

El invertido perturbado alcanza un alejamiento máximo de q1 respecto de π/2
de `7.7943627366525021 rad`. Al terminar los 2 s, q es aproximadamente
`(9.36515906,9.43315930) rad`. La salida incluye vueltas completas: el rango de
destinos `[-π,π]` no se impone como límite físico. La caída y las rotaciones
son compatibles con la transformación de potencial en energía cinética;
la deriva energética pequeña y decreciente al ajustar tolerancias es numérica.

### Gráficos y animación

`pendulo/visualizacion.py` crea cuatro paneles: q, qd, K/U/E y E−E(0).
Las ocho curvas usan los tiempos y valores originales. La animación 2D
representa base, codo y extremo en XY, con escala igual en ambos ejes y
tiempo físico rotulado. Las longitudes se toman del modelo en `main.py`.

La reproducción solicita un fotograma cada 20 ms, **50 fotogramas/s nominales**,
seleccionando la primera muestra disponible para cada tiempo objetivo e
incluyendo siempre la muestra final. Con salida de 1 ms y duración múltiplo de
20 ms, se usa una de cada 20 muestras. Si queda un tramo final más corto, se
incluye su extremo en el siguiente cuadro. El temporizador del backend puede
retrasarse; no garantiza sincronización exacta con el reloj del sistema.
La animación no reintegra ni cambia los resultados y no se repite automáticamente.
Para verla nuevamente, pulsar **«Volver a reproducir»** debajo del gráfico.
La primera reproducción empieza automáticamente; cada reinicio vuelve a t=0
y se detiene en el último fotograma.

Se verificaron el renderizado de la figura completa y un fotograma del invertido
en t=1 s, usando imágenes en memoria. No se guardaron gráficos ni videos.
También se abrieron y cerraron ventanas `TkAgg` en una prueba breve: para una
simulación de 0.105 s, el temporizador real alcanzó el rótulo `t = 0.105 s`.
Esto confirma el avance interactivo en este escritorio, sin medir su precisión
temporal ni garantizar el mismo backend en otro equipo.

### Informe de verificaciones

| Prueba y propósito | Método y condiciones | Resultado esperado | Resultado obtenido | Estado | Análisis preliminar |
|---|---|---|---|---|---|
| Colgante: comprobar equilibrio | Estado exacto colgante en reposo, 5 s, tolerancias nominales | Desviación ≤1e-7 rad; velocidad ≤1e-6 rad/s | Máximos 3.5371651189042709e-9 rad y 5.6230911325590502e-8 rad/s | Cumplida | Permanece cerca del equilibrio sin corregir artificialmente el estado. |
| Invertido: comprobar inestabilidad | Desviación inicial de q1 de 1°, q2=0, reposo, 2 s | Alejamiento de q1 >10° del invertido | Máximo 7.7943627366525021 rad | Cumplida | La perturbación explícita inicia un alejamiento físico importante. |
| Ausencia de topes ficticios | Mismo caso invertido; revisar q sobre todo el recorrido | Se conserva la evolución aunque salga de [-π,π] | q final ≈(9.36515906,9.43315930) rad y recorrido fuera del rango | Cumplida | Los ángulos de la planta no fueron recortados ni envueltos. |
| Conservación de energía: invertido | 2 s, torque y fricción nulos; calcular K+U por muestra | Variación máxima ≤1e-5 J | Nominal 1.1994816722094015e-6 J; estricta 2.1532620297914917e-8 J | Cumplida | La deriva disminuye con mayor precisión; no representa pérdidas físicas. |
| Conservación de energía: oscilación | 5 s, torque y fricción nulos; calcular K+U por muestra | Variación máxima ≤1e-5 J | Nominal 8.6059217530021215e-9 J; estricta 8.5373985658776519e-11 J | Cumplida | La energía mecánica permanece constante dentro del error numérico observado. |
| Convergencia: invertido | Misma salida de 1 ms, rtol/atol cien veces menores | Diferencias ≤1e-4 rad y ≤1e-3 rad/s, menor deriva de E | 1.290201413262082e-5 rad; 2.9285636298226336e-4 rad/s; deriva menor | Cumplida | La referencia más precisa respalda el recorrido en este horizonte de 2 s. |
| Convergencia: oscilación | Misma salida de 1 ms, rtol/atol cien veces menores | Diferencias ≤1e-4 rad y ≤1e-3 rad/s, menor deriva de E | 1.0396894883218932e-6 rad; 1.621961817033224e-5 rad/s; deriva menor | Cumplida | Coincidencia consistente con las tolerancias de integración. |
| Tiempos y estados | Tres escenarios; extremos, formas, valores finitos y condiciones iniciales | 5001/2001/5001 muestras; paso 1 ms a 1e-15 s; estado inicial exacto | Todas las comprobaciones cumplen; energías y estados comparten la grilla | Cumplida | Los resultados tienen correspondencia temporal explícita. |
| Duración no múltiplo de paso | Duración 2.5 ms y paso 1 ms | t=(0,0.001,0.002,0.0025) s | Vector exactamente coincidente | Cumplida | Se conserva la duración final con último intervalo corto. |
| Curvas: comprobar correspondencia | Ocho curvas de un caso de 0.105 s frente a arrays originales | Abscisas y ordenadas idénticas, lienzo renderizable | Igualdad exacta de datos; render Agg completo | Cumplida | Los gráficos muestran el resultado calculado sin otro remuestreo. |
| Fotogramas y tiempo | Caso de 0.105 s; avanzar los cuadros de FuncAnimation en Agg y comparar con DH | Índices 0,20,40,60,80,100,105; geometría a 1e-12 m; rótulo correcto y finalización | Secuencia esperada; todas las comparaciones cumplen; rótulo final 0.105 s; timer configurado a 20 ms | Cumplida | Los fotogramas usan los mismos estados que las curvas y llegan al final. |
| Inspección visual | Render en memoria de oscilación 5 s y cuadro invertido t=1 s | Ejes/unidades/leyendas legibles; geometría y tiempo reconocibles | Figuras revisadas sin recortes de texto ni exportaciones | Cumplida | Se ve la oscilación, el intercambio K/U y la deriva numérica por separado. |
| Ventanas y temporizador real | TkAgg; mostrar gráficos y animación de 0.105 s, procesar eventos durante 1 s y cerrar ventanas | Ventanas creadas y animación llega al final | Backend TkAgg; rótulo final `t = 0.105 s`; código de salida 0 | Cumplida | Funciona en este escritorio; no verifica reproducción con precisión de reloj. |
| Entrada y regresión | Suite completa y main.py con --sin-graficos | Etapas previas preservadas, salida sin error | 32 casos aprobados (8 nuevos y 24 previos); main.py finaliza con código 0 | Cumplida | La integración y visualización no rompieron las verificaciones anteriores. |

La etapa aporta evidencia de que la integración reproduce equilibrios y
movimiento libre de la planta acordada. Las rotaciones del invertido no son
producto de un recorte ni una perturbación numérica inadvertida. La conservación
de energía y el contraste con tolerancias estrictas respaldan los recorridos
en los horizontes examinados; la referencia estricta tampoco es una solución
exacta y no se extrapola esta convergencia a tiempos arbitrarios.
No se modificaron RK45, las tolerancias nominales ni las dependencias.
Las verificaciones de esta etapa se realizaron con barras sin actuadores,
fricción ni control. Ese modelo se conserva mediante `--modelo barras`;
el modelo ampliado y sus resultados se describen en la etapa 5.

### Reproducción manual añadida a la etapa 4

El botón detiene el temporizador anterior, si todavía existe, y crea una nueva
`FuncAnimation` sobre los mismos artistas, resultados e índices. Dibuja la muestra
inicial e inicia el nuevo reproductor. El retorno de `crear_animacion` sigue
siendo `(figura, animacion)`; la animación retornada es la primera. La figura
conserva el botón y el reproductor vigente en su registro privado
`_reproduccion`, para mantener las referencias después de retornar la función.
El botón permanece disponible al finalizar y puede usarse sucesivamente.

Verificaciones reproducibles con
`.venv/bin/python -m pytest tests/test_visualizacion.py -v`:

| Prueba y propósito | Método y condiciones | Resultado esperado | Resultado obtenido | Estado | Análisis preliminar |
|---|---|---|---|---|---|
| Reinicio durante reproducción | Recorrido de 0.105 s; avanzar dos fotogramas y emitir press/release sobre el botón | Detener timer anterior, crear otro y mostrar t=0 | Una llamada a stop; timer distinto; tiempo 0.000 s y geometría inicial correcta | Cumplida | No queda el reproductor anterior avanzando en paralelo. |
| Reinicio después del final | Completar la secuencia hasta que Matplotlib elimina event_source; pulsar el botón | Nuevo reproductor operativo desde t=0 | Reinicio correcto con el timer anterior ya ausente | Cumplida | No depende de reutilizar un temporizador terminado. |
| Dos repeticiones consecutivas | Después de cada condición anterior, completar dos ciclos reiniciados | Índices 0,20,40,60,80,100,105; geometría DH a 1e-12 m; tiempos correctos y finalización | Todas las comparaciones cumplen; cada ciclo termina en 0.105 s | Cumplida | El botón sigue funcionando después de cada reproducción. |
| Ausencia de reintegración y mutaciones | Interceptar solve_ivp para que cualquier llamada falle; comparar t,q,qd,K,U y evaluaciones antes/después | Ninguna llamada al integrador; arrays y contador idénticos | Sin llamadas; igualdad exacta en todos los campos comprobados | Cumplida | Las repeticiones solo redibujan resultados en memoria. |
| Presentación del botón | Render inicial en Agg, inspeccionado como imagen en memoria | Texto legible, control debajo del gráfico y ejes sin superposición | Botón y gráfico legibles, sin exportaciones | Cumplida | La franja inferior permite operar sin tapar la geometría ni los ejes. |
| Ventana y temporizador real | TkAgg, recorrido de 0.505 s; pulsar con movimiento visible y repetir dos veces después del final | Reinicio inmediato a t=0 y llegada al final en cada ciclo | Primer clic en t=0.020 s; reinicios a 0.000 s; ambos ciclos posteriores terminan en 0.505 s | Cumplida | Se comprobó el widget en una ventana real, sin exigir precisión de reloj al timer. |
| Regresión | Suite completa con las dos condiciones nuevas parametrizadas | Verificaciones previas preservadas | 34 casos aprobados, incluidos los 32 previos | Cumplida | La reproducción manual conserva las comprobaciones del modelo y de la integración. |

La mejora permite revisar el movimiento varias veces en la misma ventana.
No cambió las condiciones de simulación, la selección de fotogramas ni la
repetición automática desactivada. No se añadieron dependencias.

## Actuadores, montaje y rozamiento: etapa 5

### Parámetros verificados y alcance

Se consultaron las fichas primarias de los motores con **escobillas de grafito,
bobinado de 18 V**, y del reductor **GPX 22 A estándar**. Las fichas de motores
son de febrero de 2025 y la de reductores de marzo de 2025; indican datos
provisionales sujetos a cambios. Las relaciones de catálogo son aproximadas:
se conserva `N=62` y `N=26`, sin atribuirles la precisión de una relación exacta
de engranajes. `pendulo/parametros.py` conserva los datos en SI.

| Magnitud | Eje 1: DCX 22 L + GPX 22 A | Eje 2: DCX 22 S + GPX 22 A |
|---|---:|---:|
| Masa del motor / reductor [kg] | 0.095 / 0.067 | 0.066 / 0.058 |
| Diámetro / longitud del motor equivalente [m] | 0.022 / 0.0472 | 0.022 / 0.0342 |
| Etapas / longitud del reductor [m] | 3 / 0.0322 | 2 / 0.0264 |
| Inercia del rotor Jm [kg·m²] | 9.82e-7 | 5.22e-7 |
| Inercia reflejada N²Jm [kg·m²] | 0.003774808 | 0.000352872 |
| Torque nominal del motor [N·m] | 0.0322 | 0.0149 |
| Torque continuo del reductor [N·m] | 1.20 | 0.70 |
| Eficiencia máxima del reductor | 0.74 | 0.81 |
| Velocidad nominal del motor [rpm] | 10800 | 10800 |
| Velocidad continua máxima de entrada al reductor [rpm] | 12000 | 10000 |
| Potencia continua transmisible del reductor [W] | 6 | 12 |
| Límite de torque aplicado por la planta [N·m] | 1.20 | 0.31 |

Los tamaños describen cilindros equivalentes; las longitudes del motor son las
dimensiones máximas indicadas del cuerpo. La longitud efectiva del reductor
depende de su configuración y del motor asociado, como advierte su ficha.
No se consideran ejes salientes, cables, vaciados ni geometría interna real.

La estimación de torque continuo es
`min(τreductor, N·ηmax·τmotor_nominal)`: resulta `1.20 N·m` y `0.313794 N·m`.
Se conservan los límites aprobados `1.20` y `0.31 N·m`. Esta estimación usa la
**eficiencia máxima**, que no representa necesariamente la eficiencia a baja
velocidad o en sostén. No garantiza la capacidad térmica de una construcción.
La planta entrega torque ideal limitado, sin dinámica eléctrica ni térmica;
no multiplica nuevamente por la eficiencia ni aplica una fricción de Toolbox.

### Montaje coaxial y composición de cuerpos

Se confirmó la opción más cercana al conjunto comercial: motor y reductor del
eje 2 **coaxiales con Z, detrás de la barra y unidos a ella por una fijación**.
Es una distribución equivalente para dinámica, inspirada en el conjunto de las
fichas; no es un plano de montaje ni una geometría exacta del producto ensamblado.
Los tres centros tienen X=Y=0 respecto de la terna DH del codo. La cara posterior
de la barra está en Z=−5 mm; la fijación la sigue y después se apilan reductor y
motor hacia Z negativo:

| Cuerpo transportado | Masa [kg] | Diámetro × longitud [m] | Intervalo Z [m] | Centro en terna del codo [m] |
|---|---:|---|---|---|
| Fijación equivalente | 0.020 | 0.022 × 0.005, supuesto | [−0.010,−0.005] | (0,0,−0.0075) |
| Reductor del eje 2 | 0.058 | 0.022 × 0.0264 | [−0.0364,−0.010] | (0,0,−0.0232) |
| Motor del eje 2 | 0.066 | 0.022 × 0.0342 | [−0.0706,−0.0364] | (0,0,−0.0535) |

Cada cuerpo usa su masa total de ficha o estimada y la distribución de un cilindro
macizo uniforme. La fijación de 20 g es un equivalente de soporte y tornillería:
su cilindro no define material, densidad ni una pieza que se pueda fabricar.
Se omiten solapes del ensamblaje, ejes salientes, cables y detalles internos.
La masa del motor incluye su rotor como masa transportada; N²Jm representa
por separado su rotación relativa aproximada, sin añadir otra masa ni volver
a insertar la inercia reflejada en el tensor rígido.

`cilindro` calcula el tensor central de eje Z,
`Ixx=Iyy=m(3R²+L²)/12`, `Izz=mR²/2`. `componer_cuerpos` suma masas, calcula
`rG=sum(mi·ri)/sum(mi)` y aplica Steiner de cada centro al centro conjunto.
`crear_robot_actuado` entrega a Toolbox ese **tensor central**, no el tensor
trasladado al origen DH. El conjunto del codo pertenece al eslabón 1. El
motor/reductor del eje 1 permanece fijo a la base: no modifica masa, centro,
tensor ni potencial de los cuerpos móviles, aunque se conserva su rotor reflejado.

El primer eslabón pasa de `0.108` a **`0.252 kg`** y de `rG=(−0.1,0,0)` a
**`rG=(−0.0428571428571,0,−0.0199468253968) m`**, respecto de su terna DH distal.
Su tensor central pasa del prisma original a:

\[
I_{G,1}=\begin{bmatrix}
0.000139686034127&0&0.000215425714286\\
0&0.001113228891270&0\\
0.000215425714286&0&0.000989454857143
\end{bmatrix}\ \mathrm{kg\,m^2}.
\]

El término XZ aparece por la distribución de centros en X y Z; no se descarta
del tensor de Toolbox ni de la pseudoinercia. El segundo eslabón mantiene su
masa `0.108 kg`, centro y tensor de barra. La masa móvil total es `0.360 kg`.
Los desplazamientos axiales Z afectan el tensor completo, pero no las alturas
Y, la cinemática XY ni el momento alrededor de Z de este modelo plano.

### Inercia reflejada y planta

`Dinamica` lee `Jm` y `G` de los eslabones de Toolbox y añade una sola vez
`diag(G²Jm)` a la matriz derivada por trazas. `M_cuerpos_simbolica` permite
inspeccionar la contribución rígida anterior a esa suma. El término es constante:
no cambia C, G ni el potencial. Se omiten los acoplamientos adicionales del rotor
tal como se acordó. El modelo de barras de las etapas previas conserva Jm=0.

El montaje añade `diag(0.005768712,0) kg·m²` a M: `0.144·0.20²` por transportar
la masa del conjunto en el codo y `0.144·0.011²/2` por los cilindros alrededor
de Z. Los rotores añaden `diag(0.003774808,0.000352872) kg·m²`. El incremento
total respecto de las barras es `diag(0.009543520,0.000352872) kg·m²`.
Las expresiones ampliadas, redondeando residuos de punto flotante, son:

\[
M=\begin{bmatrix}
0.01675072+0.00432\cos q_2&0.0014436+0.00216\cos q_2\\
0.0014436+0.00216\cos q_2&0.001796472
\end{bmatrix},
\]

\[
G=\begin{bmatrix}
0.600372\cos q_1+0.105948\cos(q_1+q_2)\\
0.105948\cos(q_1+q_2)
\end{bmatrix},\quad
U=0.600372\sin q_1+0.105948\sin(q_1+q_2).
\]

M está en kg·m², G en N·m y U en J. C conserva la expresión de la etapa 3:
el incremento de M es constante, y los cuerpos del codo giran únicamente con
q1. La gravedad máxima por eje es `(0.70632,0.105948) N·m`, alcanzada con
ambas barras horizontales en q=(0,0). El peso transportado añade `0.282528 N·m`
al máximo del eje 1; el eje 2 permanece igual.

`Friccion.torque(qd)` evalúa, en unidades articulares:

\[
f(\dot q)=B\dot q+T_c\tanh(\dot q/\varepsilon),\quad
B=(0.02,0.005),\quad T_c=(0.03,0.01),\quad\varepsilon=0.01.
\]

B está en N·m·s/rad, Tc en N·m y epsilon en rad/s. A 3 rad/s resulta
`f=(0.09,0.025) N·m`, equivalente al `7.5%` y `8.0645%` de los límites
iniciales. Son **supuestos**, no parámetros identificados ni tomados de fichas.
La escala multiplica B y Tc: 0, 0.5, 1 y 2 representan rozamiento nulo, medio,
nominal y doble. La función es impar, suave y nula en reposo; no incluye fricción
estática, juego, elasticidad ni histéresis.

`simular_planta` recibe una función pura `torque(t,q,qd)` y resuelve
`M·qdd=τaplicado−C·qd−G−f`, con saturación simétrica por eje. La función de
torque se evalúa durante RK45 y nuevamente en la salida para registrar los
torques de cada muestra; no debe modificar entradas ni tener efectos laterales.
Los registros `torque_solicitado`, `torque_aplicado` y `rozamiento` tienen forma
`(n,2)` en N·m y comparten tiempos con los estados y las energías. No son el
historial de pasos internos del integrador. `simular_libre` reutiliza la misma
planta sin torque externo, con rozamiento opcional y nulo por defecto.

### Verificaciones y resultados de cierre

Las pruebas de etapa 5 se reproducen con
`.venv/bin/python -m pytest tests/test_actuacion.py -v -s`; la suite completa con
`.venv/bin/python -m pytest -v -s`. Pasaron **49 casos**: las verificaciones previas,
13 de actuación y dos selecciones adicionales del punto de entrada. Se verificó
que todas las funciones propias tengan docstring y que el diff no presente errores
de whitespace. La revisión gráfica se realizó en memoria y también con TkAgg.

| Prueba y propósito | Método y condiciones | Resultado esperado | Resultado obtenido | Estado | Análisis preliminar |
|---|---|---|---|---|---|
| Regresión dinámica y libre | Pruebas de etapas 3 y 4 con barras sin rotor ni rozamiento | Conservar sus tolerancias y resultados físicos | 18 casos aprobados | Cumplida | La extensión mantiene el movimiento ideal previo. |
| Inercia reflejada sin duplicación | Modelo auxiliar con barras y rotores, sin masa de carcasa; 81 posiciones en [-π,π]² | Incremento diag(0.003774808,0.000352872) kg·m²; contraste con Toolbox ≤1e-12 kg·m² | Incremento esperado; diferencia máxima 1.735e-18 kg·m² | Cumplida | Aísla el efecto de los rotores de la composición de cuerpos. |
| Montaje: masa, centro y tensor | Cilindros y barra en la terna del codo; sumar inercias en el origen y trasladar el total al centro conjunto, como ruta independiente | Masa 0.252 kg, centro y tensor indicados arriba; diferencias ≤1e-12 en las unidades respectivas; tensor positivo | Valores esperados; diferencia máxima de tensor 6.505e-19 kg·m²; autovalor mínimo 8.81935e-5 kg·m² | Cumplida | La composición conserva la referencia central y el producto XZ; el eslabón 2 mantiene sus propiedades originales. |
| Cinemática del montaje | Comparar modelos actuado y de barras en 81 configuraciones en [-π,π]² | Posiciones de base, codo y extremo iguales a 1e-12 m | Coinciden en todas las configuraciones | Cumplida | Cambiar distribución de masa no cambia DH ni la geometría plana. |
| Incrementos físicos separados | Restar la M analítica de barras a la ampliada en 81 posiciones; contrastar C con su expresión previa | Montaje diag(0.005768712,0), rotor diag(0.003774808,0.000352872) kg·m²; C idéntica a 1e-12 kg·m²/s | Todas las diferencias cumplen | Cumplida | Se distinguen masa transportada, momento cilíndrico y rotación del rotor, sin repetir N²Jm. |
| Contraste dinámico ampliado | 324 estados: 9 ángulos por eje y 4 pares qd/qdd hasta ±3 rad/s y ±6 rad/s²; RNE de Toolbox con B=Tc=0 | Diferencias ≤1e-12 kg·m² para M y ≤1e-12 N·m para G, Cqd e inversa | Máximos: M 3.469e-18 kg·m²; G 1.110e-16 N·m; Cqd 1.388e-17 N·m; inversa 2.220e-16 N·m | Cumplida | Las rutas coinciden numéricamente con las mismas aproximaciones. Toolbox no implementa la fricción tanh: se añade aparte al contraste de inversa de planta. |
| M y Christoffel ampliadas | Grilla de 625 posiciones, qd=(1.2,−0.7) rad/s | M simétrica a 1e-12 kg·m² y positiva; parte simétrica de Mdot−2C ≤1e-12 kg·m²/s | Autovalor mínimo 0.00114476263798 kg·m²; residuo de antisimetría 8.674e-19 kg·m²/s | Cumplida | Los rotores aumentan la inercia diagonal sin introducir términos de velocidad adicionales. La grilla no demuestra todos los estados. |
| Potencial y gravedad ampliados | 625 posiciones; alturas independientes de barras y masa de codo; diferencias centrales h=1e-6 rad | U coincide a 1e-12 J; G coincide con gradiente a 1e-9 N·m; sostén nulo colgante e invertido a 1e-12 N·m | ΔU máximo 2.220e-16 J; ΔgradU máximo 1.344e-10 N·m; torques conocidos cumplen | Cumplida | El montaje aumenta el peso sobre el eje 1 y conserva el signo de gravedad. |
| Rozamiento y sentido resistente | 441 pares de velocidades entre −3 y 3 rad/s por escala 0/0.5/1/2, incluyendo cero y transición tanh | f impar a 1e-14 N·m; f(0)=0; qd·f≥0 W; pendiente en cero a 1e-10 N·m·s/rad | Potencia mínima 0 W; nominal f(3,3)=(0.09,0.025) N·m y pendiente (3.02,1.005) N·m·s/rad | Cumplida | Verifica una resistencia suave y disipativa en los estados muestreados. |
| Saturación sin alterar solicitudes | 25 combinaciones dentro, sobre y fuera de ambos límites | Recorte exacto a ±(1.20,0.31) N·m; entradas idénticas | Todas coinciden con min/max por eje; arrays originales intactos | Cumplida | Solo se limita el torque. |
| Efecto físico y registro de saturación | Modelo completo; colgante en reposo, 0.05 s, rozamiento nominal; pedir (2,−1) y (1.20,−0.31) N·m | Estados iguales a 1e-12 rad y rad/s; registros pedidos/aplicados exactos | Diferencia 0 rad y 0 rad/s; pedido (2,−1), aplicado (1.20,−0.31) N·m | Cumplida | La planta recibe el torque aplicado y conserva el pedido para diagnóstico. |
| Trabajo y pérdidas en arranque | Caso anterior; integrar potencia neta por trapecios con salida 1 ms y repetir a 0.1 ms, mismas tolerancias RK45 | Residuo menor al refinar la cuadratura; fino ≤1e-6 J; estados comunes a 1e-12 rad | Residuos 1.42083e-5 y 1.48926e-7 J, respectivamente; estados coincidentes | Cumplida | La transición de tanh al arrancar exige salida más fina para integrar trabajo; no fue necesario cambiar la planta ni RK45. |
| Conservación sin rozamiento | Modelo completo; oscilación de 5 s desde q=(−π/2+0.3,−0.2) rad, qd=(0.4,−0.1) rad/s; tolerancias nominales, salida 1 ms | Variación de energía ≤1e-5 J | Máxima variación 8.862e-9 J; 2174 evaluaciones de planta | Cumplida | La inercia reflejada se incluye también en la energía cinética. |
| Disipación sin control | Mismo caso con fricción nominal; todos los pedidos/aplicados cero | Energía decreciente, incremento entre muestras ≤1e-9 J, pérdida neta positiva | E0=−0.677430650735218 J, Efinal=−0.706257966381397 J; caída 0.0288273156462 J; máximo incremento −6.644e-9 J; 8864 evaluaciones | Cumplida | El movimiento se amortigua por pérdidas físicas del modelo, sin torque de control ni recortes de estado. |
| Balance de pérdidas libre | Integrar qd·f por trapecios; repetir salida de 1 ms a 0.1 ms, mismas tolerancias | Integral compatible con caída energética; residuo fino ≤1e-6 J y menor que nominal | Integral nominal 0.0288273947065 J; residuos −7.906e-8 J y −7.099e-10 J | Cumplida | La disipación local explica el cambio de energía de la planta ampliada. |
| Convergencia con fricción | Misma oscilación y grilla; repetir con rtol=1e-9 y atol=1e-11 | Diferencias ≤1e-4 rad y ≤1e-3 rad/s | Δq máximo 3.594e-9 rad; Δqd máximo 4.685e-8 rad/s; 14462 evaluaciones estrictas | Cumplida | No fue necesario cambiar integrador, tolerancias nominales ni regularización. La referencia estricta no es solución exacta. |
| Ausencia de recortes de estado | q0=(π−0.001,0) rad, qd0=(4,−4) rad/s; libre sin fricción, 2 ms | Velocidad inicial conservada y q1 final mayor que π | q1 final=3.14866398632 rad; velocidad máxima 4.07132539831 rad/s | Cumplida | El rango de destinos y los 3 rad/s de referencias no se convierten en topes de planta. |
| Reserva estática | Máximo analítico por pesos y contraste del G ampliado en horizontal | Demanda inferior a (1.20,0.31) N·m | Gmax=(0.70632,0.105948) N·m; reserva=(0.49368,0.204052) N·m | Cumplida para el modelo | El sostén cabe en los límites iniciales; la eficiencia real y la construcción permanecen fuera de esta comprobación. |
| Velocidad y potencia de selección | Salida prevista 3 rad/s, torque en cada límite; cotejo con fichas | Entrada menor a nominal del motor y máxima continua del reductor; potencia de salida menor a transmisible | Entrada=(1776.17,744.845) rpm; potencia=(3.60,0.93) W frente a (6,12) W | Cumplida como estimación | No evalúa aún demanda de seguimiento, eficiencia real ni calentamiento. |
| Torque y potencia mecánica de motores | τmotor=τlímite/(N·ηmax), Pmotor=Psalida/ηmax; punto nominal calculado con torque/rpm de ficha | Torque motor menor al nominal y potencia mecánica menor a la del punto nominal | Torque=(0.0261552,0.0147198) N·m frente a (0.0322,0.0149); potencia estimada=(4.86486,1.14815) W frente a (36.4173,16.8515) W | Cumplida como estimación | Emplea eficiencia máxima; la potencia nominal no define por sí sola una envolvente ni garantiza el funcionamiento a cualquier velocidad. |
| Gráficos y fotograma ampliado | Oscilación nominal 5 s; render de cuatro paneles y animación en t=1 s, en memoria; geometría frente a Toolbox a 1e-12 m | Ejes, unidades y botón legibles; geometría y tiempo coincidentes | Figuras inspeccionadas sin recortes; t=1.000 s y geometría correctos | Cumplida | Se reconoce la amortiguación y la pérdida energética sin exportaciones. |
| Ventanas ampliadas y reproducción | TkAgg; recorrido de 0.105 s con fricción nominal; reiniciar al comenzar y completar dos ciclos posteriores | Temporizador real llega al final; reinicios a t=0; geometrías extremas a 1e-12 m; resultados intactos | Ambos ciclos terminan en t=0.105 s; igualdad exacta de estados, energías y los tres registros de torque | Cumplida | El montaje ampliado funciona con la visualización y el botón existentes. |
| Punto de entrada y regresión completa | Ejecutar main.py sin gráficos: actuado nominal por defecto, barras ideales y actuado con fricción media; suite completa | Código 0, modelo y fricción seleccionados correctamente, verificaciones previas conservadas | Tres procesos correctos; 49 casos aprobados | Cumplida | El caso ideal sigue disponible y el uso normal incluye la etapa 5. |

### Análisis conjunto y continuidad

La etapa verifica la composición mecánica, los términos dinámicos, la fricción
disipativa y la entrada de torque limitado. El montaje agrega peso y una inercia
constante al eje 1; ambos rotores aumentan su diagonal correspondiente. C permanece
igual porque la distribución añadida depende solo de q1 y su inercia articular
es constante. La cinemática, el rango sin topes y la reproducción en memoria
se conservan.

Los candidatos mantienen los límites aprobados. La reserva sobre el máximo de
gravedad es `0.49368 N·m` en el eje 1 y `0.204052 N·m` en el eje 2: capacidades
de aproximadamente 1.70 y 2.93 veces la demanda estática. A 3 rad/s, las
velocidades y potencias de selección quedan por debajo de los valores de ficha
indicados. El eje 1 queda limitado por el reductor; el eje 2 por la estimación
de torque del motor multiplicada por N y la eficiencia máxima del reductor.
En este último, `0.313794 N·m` supera al límite `0.31 N·m` apenas alrededor
de un 1.2%: no es una reserva comprobada frente a pérdidas reales de transmisión.

La eficiencia de ficha es máxima y la distribución de masa es equivalente.
La fijación es una estimación, no un diseño estructural. No se verifica
calentamiento, precisión constructiva, juego ni electrónica; tampoco se aplica
un recorte de velocidad o potencia que altere la planta. Las pruebas aportan
evidencia numérica para este modelo y estos horizontes, no una certificación
de los componentes físicos ni de todos los estados posibles.

La etapa 5 quedó completada con la reserva estática indicada. El contraste de
demanda durante seguimiento, recuperación y precisión se documenta a continuación.
Se conservan los mismos componentes, ganancias aprobadas y límites físicos.

## Trayectorias y control continuo: etapa 6

### Referencias y organización

`pendulo/trayectorias.py` contiene `TrayectoriaQuintica(qi,qf)`. Copia dos
vectores articulares de forma `(2,)` en rad dentro de `[-π,π]`, conserva el
desplazamiento literal y sincroniza ambos ejes con una duración común. Para
`0<t<T`, con `s=t/T` y `Δq=qf−qi`:

\[
q_d=q_i+\Delta q(10s^3-15s^4+6s^5),
\]
\[
\dot q_d=\frac{\Delta q}{T}(30s^2-60s^3+30s^4),\qquad
\ddot q_d=\frac{\Delta q}{T^2}(60s-180s^2+120s^3).
\]

Antes del inicio se mantiene qi; desde T se mantiene qf. Posición en los
extremos y derivadas nulas se asignan explícitamente. `evaluar(t)` entrega
`(q_d,qd_d,qdd_d)` en rad, rad/s y rad/s², sin modificar los destinos.

Para `d=max(abs(Δq))`, la duración mínima se obtiene de los máximos analíticos
`max(h')=15/8` y `max(abs(h''))=10√3/3`:

\[
T=\max\left(2,\frac{(15/8)d}{3},
\sqrt{\frac{(10\sqrt3/3)d}{6}}\right)\ \mathrm{s}.
\]

La velocidad alcanza su máximo en `s=1/2`; la aceleración en
`s=(3±√3)/6`. Un desplazamiento de π rad dura 2 s; uno de 2π rad dura
`5π/4=3.92699081699 s`. El movimiento nulo mantiene los 2 s mínimos.
Con estos límites, la aceleración máxima sobre amplitudes entre 0 y 2π
es `8√3/3=4.61880215352 rad/s²`, en d=3.2 rad; el límite de 6 rad/s²
no llega a determinar T en este rango. La fórmula conserva las tres condiciones.

`pendulo/control.py` contiene `ControladorPD(nombre,kp,kd,gravedad)`.
Cada instancia copia sus ganancias, representadas como diagonales `(2,)`:
`kp=(20,5) N·m/rad`, `kd=(1.3,0.2) N·m·s/rad`. La ley solicitada es

\[
\tau_{PD}=K_p(q_d-q)+K_d(\dot q_d-\dot q),\qquad
\tau_{PD+G}=\tau_{PD}+G(q).
\]

G se evalúa en el estado **real**, sin anticipación de aceleración ni integral.
La saturación permanece en la planta, común a todas las instancias. Los errores
no se envuelven y los estados no se recortan.

`simular_seguimiento` reutiliza `simular_planta`: evalúa el controlador dentro
de RK45, con `rtol=1e-7`, `atol=1e-9` y salida común cada 1 ms. Esta grilla
es de **registro**, no de actualización digital. Simula T más una permanencia
final de al menos 1 s. Permite q0/qd0 distintos de la referencia para recuperación
o continuidad entre tramos. `ResultadoSeguimiento` conserva la simulación, la
trayectoria, el controlador y referencias sobre sus mismos tiempos. Registra
además `torque_referencia=M(q_d)qdd_d+C(q_d,qd_d)qd_d+G(q_d)+f(qd_d)`:
es demanda ideal para diagnóstico y no se suministra al controlador.

`medir_seguimiento` calcula máximos sobre las muestras registradas: error máximo
y final en grados, velocidades finales, torque pedido/aplicado/ideal, porcentaje
de muestras saturadas, velocidad real, rpm de entrada y potencia mecánica
`P=τaplicado·qd`. Conserva máximos positivos y mínimos negativos para distinguir
accionamiento y frenado, sin atribuir regeneración eléctrica. Estima torque y
potencia de motor con η máxima, como en etapa 5.

`cumple_precision` exige máximo ≤2° por eje y final ≤0.2°;
`cumple_capacidad` compara la trayectoria ideal y el torque efectivamente
entregado con capacidades de selección, rpm y potencias. Un pedido saturado
puede recuperar la posición aunque no se entregue entero: el indicador separado
`solicitud_sin_saturacion` permite reconocerlo. El seguimiento nominal exige
también que la solicitud completa quepa en los límites.

`graficar_seguimientos` crea seis paneles: columnas por articulación y filas
de posición real/deseada, error en grados y torque pedido/aplicado. Usa un color
por controlador, referencia negra común y guías de ±2° (±0.2° en recuperación)
y ±los límites de torque. Usa resultados calculados sin reintegrar ni exportar.
La animación existente usa esos estados y conserva «Volver a reproducir».

### Escenarios y resultados nominales

Todos los resultados siguientes usan el **modelo actuado, fricción nominal,
ganancias comunes aprobadas y 1 s de permanencia**. Cada movimiento aislado
parte de qi en reposo. La vuelta continuada parte de q/qd reales al terminar
la ida. La derivación dinámica se reutiliza para las comparaciones.

| Escenario | qi → qf [rad] | T [s] |
|---|---|---:|
| abajo_arriba | (−π/2,0) → (π/2,0) | 2 |
| arriba_abajo | (π/2,0) → (−π/2,0) | 2 |
| extremos | (−π,−π) → (π,π) | 3.92699081699 |
| extremos_opuestos | (−π,π) → (π,−π) | 3.92699081699 |
| eje1 | (−π/2,π/3) → (π/2,π/3) | 2 |
| eje2 | (0,−π) → (0,π) | 3.92699081699 |
| nulo_horizontal | (0,0) → (0,0) | 2 |
| vuelta_continuada | referencia arriba_abajo, estado inicial real de abajo_arriba | 2 |

Los errores son magnitudes por eje `(e1,e2)`, incluyen movimiento y permanencia,
y se calculan sin envolver ángulos. Los valores de las tablas están redondeados;
las pruebas utilizan los resultados completos.

| Escenario | PD máximo [°] | PD final [°] | PD+G máximo [°] | PD+G final [°] | Precisión PD / PD+G |
|---|---|---|---|---|---|
| abajo_arriba | (2.264081,1.145396) | (0.000101,0.000715) | (0.446448,0.159042) | (0.000152,0.001434) | Incumplida / Cumplida |
| arriba_abajo | (1.757812,1.145694) | (0.000145,0.001515) | (0.446448,0.159042) | (0.000152,0.001434) | Cumplida / Cumplida |
| extremos | (2.264191,1.500329) | (1.415429,1.215319) | (0.443520,0.389128) | (0.000471,0.001251) | Incumplida / Cumplida |
| extremos_opuestos | (2.262084,1.212922) | (1.415453,1.212922) | (0.343191,0.452205) | (0.000447,0.001145) | Incumplida / Cumplida |
| eje1 | (2.164522,1.360111) | (0.274544,1.065663) | (0.420049,0.202815) | (0.000066,0.000840) | Incumplida / Cumplida |
| eje2 | (1.991827,1.495613) | (1.415937,1.212867) | (0.043816,0.297567) | (0.000016,0.001199) | Incumplida / Cumplida |
| nulo_horizontal | (2.021903,1.212142) | (2.021903,1.212141) | (0,0) | (0,0) | Incumplida / Cumplida |
| vuelta_continuada | (1.757812,1.145694) | (0.000145,0.001515) | (0.446447,0.159042) | (0.000152,0.001434) | Cumplida / Cumplida |

El PD puro se evalúa como comparación, sin exigirle la aceptación del PD+G.
En horizontal desarrolla el error necesario para sostener el peso: `Kp·e≈G(q)`.
PD+G conserva exactamente el horizontal nulo en esta integración con medición
y modelo ideales. Mover un solo eje de referencia deja una desviación pequeña
en el otro eje real por acoplamiento; el controlador la corrige.

### Demanda y capacidad de los actuadores

Se contrasta la **demanda ideal y la solicitud**, además del torque aplicado
limitado. En los ocho movimientos PD+G no hubo muestras saturadas y el pedido
coincide con lo aplicado. Potencias y rpm usan velocidades reales.

| Escenario PD+G | Pedido máximo [N·m] | Ideal máximo [N·m] | Velocidad real máxima [rad/s] | Máximo abs(P) [W] |
|---|---|---|---|---|
| abajo_arriba | (0.800254,0.112339) | (0.800067,0.106929) | (2.956660,0.009554) | (2.361386,0.000772) |
| arriba_abajo | (0.622518,0.100886) | (0.622646,0.106929) | (2.956660,0.009554) | (1.835872,0.000737) |
| extremos | (0.800121,0.131154) | (0.799728,0.131173) | (3.011797,2.991821) | (2.408741,0.392355) |
| extremos_opuestos | (0.797695,0.105948) | (0.797480,0.105967) | (3.005270,2.987370) | (2.396783,0.275659) |
| eje1 | (0.763162,0.120601) | (0.762666,0.124300) | (2.955412,0.008788) | (2.235313,0.000605) |
| eje2 | (0.714157,0.130989) | (0.708799,0.130964) | (0.002748,3.001004) | (0.001902,0.393093) |
| nulo_horizontal | (0.706320,0.105948) | (0.706320,0.105948) | (0,0) | (0,0) |
| vuelta_continuada | (0.622518,0.100885) | (0.622646,0.106929) | (2.956660,0.009554) | (1.835872,0.000737) |

Los máximos conjuntos de pedido son `(0.800254,0.131154) N·m`, frente a
`(1.20,0.31) N·m`: reserva aproximada `(0.399746,0.178846) N·m` en estos
recorridos. La demanda ideal máxima también cabe: `(0.800067,0.131173) N·m`.
Entrada real máxima `(1783.154,745.094) rpm`, frente a límites de selección
`(10800,10000) rpm`. Potencia de salida máxima absoluta
`(2.408741,0.393093) W`, frente a `(6,12) W` de transmisión.

Con η máxima, el torque máximo estimado de motor es aproximadamente
`(0.017443,0.006228) N·m`, frente a `(0.0322,0.0149) N·m`; su potencia
mecánica estimada máxima es `(3.2551,0.4853) W`, frente a
`(36.4173,16.8515) W` del punto nominal. Son contrastes de selección,
no una envolvente real de funcionamiento ni un modelo de pérdidas en frenado.

La velocidad de la **referencia** respeta 3 rad/s. El estado real llega a
`3.011797 rad/s` en el eje 1 y `3.001004 rad/s` en el eje 2, por la respuesta
del control, y conserva esos valores sin recorte. Cabe en las capacidades
físicas usadas en la selección. No se cambió T para ocultar esas diferencias.

### Recuperación del invertido

Referencia nula en `(π/2,0)`, q0 con las cuatro combinaciones de ±5°,
qd0=(0,0), horizonte 3 s, salida de 1 ms. Se mide el primer instante después
del último error superior a 0.2° en cualquier eje; luego ambos permanecen
dentro de ese umbral en las muestras restantes. La resolución es 1 ms y
la afirmación se limita al horizonte observado. Los 5° iniciales no se
comparan contra el criterio máximo de 2° del seguimiento.

| Perturbación [°] | Asentamiento PD / PD+G [s] | Final PD+G [°] | Pedido máximo PD+G [N·m] | Muestras saturadas PD+G [%] |
|---|---|---|---|---|
| (+5,+5) | 0.188 / 0.176 | (2.111e-7,8.768e-7) | (1.816053,0.454730) | (0.399867,0.299900) |
| (+5,−5) | 0.218 / 0.218 | (2.587e-7,1.444e-6) | (1.797655,0.436332) | (0.133289,0.066644) |
| (−5,+5) | 0.218 / 0.218 | (2.587e-7,1.444e-6) | (1.797655,0.436332) | (0.133289,0.066644) |
| (−5,−5) | 0.188 / 0.176 | (2.111e-7,8.768e-7) | (1.816053,0.454730) | (0.399867,0.299900) |

La recuperación se cumple con ambos controladores. La solicitud inicial
supera los límites y el aplicado queda en `(1.20,0.31) N·m` como máximos
absolutos, sin recurrir a torque intermitente ni recorte de estados. El porcentaje
es de **muestras**, no una medición exacta de duración de saturación. La planta
entrega un torque menor que el pedido en esas muestras: se informa explícitamente.

### Informe de verificaciones

Reproducción de las verificaciones de etapa 6 y de la suite completa:

```bash
.venv/bin/python -m pytest tests/test_trayectorias.py tests/test_control.py tests/test_seguimiento.py tests/test_graficos_control.py tests/test_cli_control.py -v -s
.venv/bin/python -m pytest -v -s
```

La suite completa aprobó **98 casos** en 53.81 s: 49 nuevos y los 49 previos.
La revisión de los 21 archivos Python comprobó docstrings y comentarios internos
en las 123 funciones/métodos propios. El diff pasó la revisión de whitespace.

| Prueba y propósito | Método y condiciones | Resultado esperado | Resultado obtenido | Estado | Análisis preliminar |
|---|---|---|---|---|---|
| Extremos, reposo y T | Tres trayectorias cortas/π/2π; tiempos antes, en extremos y después de T | Destinos exactos, derivadas cero y T conocido a 1e-14 s | Destinos/derivadas exactos; T=2,2,3.92699081699 s | Cumplida | El giro entre −π y π recorre 2π literalmente. |
| Derivadas y continuidad | 19 tiempos de qi=(−2,1), qf=(2.5,−2); diferencias centrales h=1e-5 s; interiores a 1e-7 s de extremos | Derivadas a 1e-9 en SI; continuidad q/v/a a 1e-12/1e-12/1e-5 en SI | Diferencias máximas 5.0591e-10 rad/s y 4.6551e-10 rad/s²; extremos cumplen | Cumplida | Contraste numérico independiente de las derivadas analíticas. |
| Límites, sincronización y minimalidad | 102 amplitudes hasta 2π, incluyendo 3.2 rad; 501 tiempos por amplitud y picos analíticos | T≥2 s, vmax≤3, amax≤6; progreso común; límite activo si T>2 | vmax=3 rad/s, amax=4.61880215352 rad/s²; concordancia a 1e-12 | Cumplida | La aceleración no es la restricción activa para los límites aprobados. |
| Movimiento nulo y eje fijo | Destinos iguales y giro de un solo eje; modificar copias de entradas y salidas | Posición fija y derivadas cero exactas; destinos intactos | Todas las igualdades se cumplen | Cumplida | La referencia nula no impide que PD puro derive físicamente por gravedad. |
| Formato y rango de referencias | Siete entradas con forma/rango/valores inválidos | ValueError sin envolver ni recortar destinos | Siete rechazos explícitos | Cumplida | El control de referencias no impone topes sobre el estado real. |
| Leyes de control y G real | Estado y ganancias conocidos; gravedad auxiliar distinta de la deseada | PD=(1.4,1.42), PD+G=(1.85,0.32) N·m a 1e-12; entradas intactas | Valores esperados; usa q real para G | Cumplida | La ley implementada coincide con las ecuaciones aprobadas. |
| Instancias y ganancias | Dos controladores desde arrays compartidos; modificación independiente; entradas de ganancias inválidas | Nombres/configuraciones independientes; Kp positiva y Kd no negativa; errores literales | Copias independientes, siete rechazos y Kd=0 admitida; error de 2π sin envolver | Cumplida | Permite comparaciones sin compartir ganancias accidentalmente. |
| Seguimiento nominal y demanda | Ocho recorridos de las tablas; PD y PD+G con condiciones idénticas | PD+G máximo≤2°, final≤0.2°, pedido e ideal dentro de límites y capacidad de rpm/potencia | Máximo conjunto (0.446448,0.452205)°, final conjunto (0.000471,0.001434)°; tablas de demanda; sin saturación nominal | Cumplida | PD+G cumple en los casos observados; PD puro tiene incumplimientos diagnósticos indicados. |
| Recuperación de 5° | Cuatro perturbaciones con ambos ejes en reposo; referencia invertida nula | Final≤0.2° y permanencia dentro del umbral tras asentarse; aplicado dentro de límites | PD+G asienta en 0.176–0.218 s; final≤1.444e-6°; saturación explícita | Cumplida | No se aplica el máximo de seguimiento al error inicial de recuperación. |
| Sesgo del PD puro y sostén con G | Horizontal nulo durante 3 s; contraste Kp·e frente a G(qfinal) | PD desarrolla sesgo; equilibrio a 1e-4 N·m; PD+G q/qd nulos a 1e-12 en SI | PD final (2.021903,1.212141)°; equilibrio dentro de tolerancia; PD+G permanece nulo | Cumplida | La compensación de gravedad elimina el sesgo en este modelo ideal. |
| Referencias, registros y continuidad | Todas las simulaciones; evaluar fórmula de torque y geometría de G independientes; conservar final real en vuelta | Referencia/estado misma grilla, t final=T+1; hold exacto; pedido a 1e-12 N·m, clipping exacto; continuidad q/qd exacta | Todas las condiciones se cumplen | Cumplida | No hay reinicio artificial en el regreso ni compensación oculta. |
| Control dentro de RK45 | Interceptar calcular sin alterar su resultado en recuperación (+5,−5)° | Llamadas=nfev+muestras de registro, más que muestras de salida | Igualdad cumplida | Cumplida | La salida de 1 ms no implementa retención de control digital. |
| Convergencia del control | Extremos opuestos PD+G, repetir con rtol=1e-9/atol=1e-11 y misma salida | Δq≤1e-5 rad, Δqd≤1e-4 rad/s, Δτpedido≤1e-4 N·m; conservar aceptación | Δq=1.6482e-9 rad, Δqd=3.1943e-7 rad/s, Δτ=9.2882e-8 N·m; 6842/15590 evaluaciones | Cumplida | Diferencias muy menores que los errores físicos de seguimiento; referencia estricta no es solución exacta. |
| Datos y renderizado de gráficos | Resultados sintéticos con tiempos/señales conocidos; seis paneles en Agg; bloquear integrador, show y exportaciones | Curvas exactas, errores en grados a 1e-12, colores comunes, referencia única, guías y datos intactos | Cinco casos gráficos cumplen; figuras renderizadas sin integración ni mutaciones | Cumplida | Los gráficos representan la salida, incluyendo solicitudes fuera de límites. |
| Ejecución y coordinación ida-vuelta | Subproceso con --control comparar --escenario ida_vuelta --sin-graficos; coordinación con resultados auxiliares distintos | Código 0, dos tramos y ambos controles; PD+G aceptado; herencia de q/qd reales | Código 0; cuatro informes, ambos PD+G aceptados; herencia exacta; llamadas de gráficos/exportación bloqueadas sin invocaciones | Cumplida | La coordinación conserva condiciones comunes y el estado real propio de cada instancia. |
| Inspección gráfica | Extremos opuestos y recuperación nominal; render de seis paneles en memoria | Etiquetas, guías y leyendas legibles; distinguir errores y saturación | Figuras inspeccionadas sin recortes ni superposición de etiquetas; saturación visible | Cumplida | Los datos permanecen en memoria; no se exportan figuras ni videos. |
| Ventanas y animación controlada | TkAgg; abajo–arriba PD+G de 3 s; pulsación real del botón durante/después; fotogramas en 0,1.5,3 s frente a Toolbox | Ventanas operativas; geometría a 1e-12 m y tiempo exacto; timer llega al final; reinicios a t=0; sin reintegración/mutaciones | Seis paneles y animación abiertos; timer termina en 3.000 s; reinicios y geometrías correctos; arrays intactos | Cumplida | La animación y su botón funcionan también con los estados controlados. |
| Regresión y documentación | Suite completa, revisión de docstrings/comentarios y diff | Preservar etapas previas; funciones propias documentadas; diff limpio | 98 casos aprobados; 123 funciones/métodos documentados en 21 archivos; diff limpio | Cumplida | Las incorporaciones conservan las verificaciones anteriores. |

### Análisis conjunto y continuidad

Las quinticas y las ganancias aprobadas permiten cumplir la precisión nominal
del PD+G continuo en los recorridos indicados, con la fricción y actuadores
de etapa 5. No fue necesario modificar ganancias, duración mínima, límites,
montaje ni candidatos. El sesgo del PD puro coincide con la ausencia de
compensación de gravedad; no se cambió su ley para hacerlo cumplir.

La recuperación tolera pedidos iniciales superiores al torque disponible
mediante la saturación física acordada. La demanda nominal cabe con reserva
en los límites de torque, rpm y potencia de selección. Las velocidades reales
ligeramente superiores a la referencia se conservan y se distinguen del límite
de diseño de la trayectoria.

Los errores y las reservas son evidencia numérica sobre estos casos y tiempos,
no garantías para todos los estados ni precisión de una construcción real.
Se mantienen fricción supuesta, eficiencia máxima, medición ideal y ausencia
de electrónica, juego, elasticidad y efectos térmicos. Las estimaciones de motor
en frenado no validan pérdidas ni regeneración. El control digital de 1 ms,
la sensibilidad a otros períodos y fricciones, más pares reproducibles y la
animación simultánea se documentan en la etapa 7 siguiente.
La etapa 6 queda completada con los resultados y limitaciones anteriores.

## Control digital y comparación completa: etapa 7

### Muestreo, integración y trazabilidad

`simular_seguimiento(..., modo='digital', periodo=0.001)` usa el mismo
modelo, trayectoria, ganancias, límites y fricción que el continuo. En
`t_k=k·Ts`, desde t=0, mide q/qd reales, evalúa la referencia y calcula el
pedido PD o PD+G una sola vez. Satura ese pedido y mantiene ambos torques
constantes hasta la siguiente actualización. Entre muestras integra

\[
M(q)\ddot q=\tau_{aplicado,k}-C(q,\dot q)\dot q-G(q)-f(\dot q)
\]

con RK45 a `rtol=1e-7`, `atol=1e-9`. La fricción responde continuamente
a la velocidad real, incluso con torque retenido. Cada intervalo empieza
desde el estado final real del anterior; RK45 termina exactamente en la
frontera antes de actualizar el controlador. Esto evita atravesar el salto
de torque usando una sola integración con un controlador dependiente de sus
llamadas internas. No añade retraso de cómputo, ruido ni cuantización de sensores.

El último intervalo se acorta si el horizonte no es múltiplo de Ts. No
actualiza en el tiempo final, porque no queda otro intervalo que accionar;
su registro conserva el último torque retenido. Los registros son por la
derecha en las fronteras anteriores. La salida sigue cada 1 ms, independiente
de Ts: la interpolación densa de RK45 evalúa las muestras dentro de cada
intervalo, sin interpolar los saltos de torque. Los intervalos sin muestras
de salida se integran igualmente y conservan su actualización de control.

`ResultadoSeguimiento` agrega `modo`, `periodo` y las trazas opcionales
`tiempos_control`, `torque_control_solicitado`, `torque_control_aplicado`.
Las trazas digitales registran todos los eventos, en s y N·m; el continuo
conserva None en esos campos. Los máximos de torque pedido/aplicado y la
estimación de torque de motor usan **todos los eventos digitales**, incluso
cuando Ts es menor al paso de salida. Error, velocidad, rpm, potencia y
porcentaje de muestras saturadas se calculan en la grilla de resultados.
Esos máximos no demuestran el extremo exacto entre muestras; el porcentaje
no se presenta como duración exacta de saturación.

La referencia almacenada mantiene qd/qdd analíticas en la grilla común,
también entre actualizaciones digitales. Se utiliza para comparar el estado
con la trayectoria prevista; el controlador digital sólo la evalúa en t_k.
La planta no recorta velocidades ni envuelve ángulos.

### Comparaciones y reproducción simultánea

`comparar_control` ejecuta las instancias elegidas en uno o ambos modos,
con condiciones comunes; `comparar_continuo` conserva la entrada anterior.
`comparar_variantes` reúne un caso normal o los barridos de fricción/período.
Los resultados se identifican por controlador, modo y variante. Cada
combinación de ida-vuelta hereda su propio q/qd final, sin compartir estados
con otras combinaciones ni reiniciar el regreso artificialmente.

Cada `ControladorPD` conserva nombre y ganancias independientes; varias
instancias pueden incorporarse a la lista de controladores de `main.py`.
La comparación nominal usa las dos leyes y ganancias aprobadas. Reutilizar
una misma ley entre modos no comparte una evolución interna: el controlador
no almacena estado ni modifica ganancias al calcular torque.

`crear_animacion_comparada` dibuja una polilínea por resultado sobre los
mismos ejes XY. Exige grillas temporales exactamente iguales, usa un único
índice y reloj y conserva colores/identificadores de los gráficos. Rechaza
grillas incompatibles en vez de aparentar simultaneidad mediante remuestreo.
Incluye el último fotograma y mantiene allí la imagen. «Volver a reproducir»
detiene el temporizador anterior y crea otra reproducción sobre los mismos
datos y artistas; la figura retiene el botón y la animación vigente.
Retorna `(figura, primera_animacion)`, como la animación simple existente.

Los gráficos con tres o más resultados usan una leyenda común fuera de los
seis paneles, para conservar visibles picos y errores. La reproducción usa
resultados ya calculados y su temporizador gráfico no garantiza velocidad
real de ejecución. No se exportan datos, imágenes ni videos automáticamente.

### Condiciones y resultados nominales

Se repiten los ocho recorridos de etapa 6, las cuatro perturbaciones de ±5°
y tres pares nuevos, con **ambas leyes y ambos modos**, mismo modelo actuado,
fricción nominal, ganancias originales y permanencia de 1 s. La fixture
reutiliza resultados entre comprobaciones y barridos: calcula 80 combinaciones
distintas y agrega una integración digital estricta. No hay azar.

| Par nuevo | qi → qf [rad] | T [s] |
|---|---|---:|
| interior_a | (−3π/4,π/5) → (π/6,−2π/3) | 2 |
| interior_b | (π/3,−π/2) → (−π/4,3π/4) | 2.45436926062 |
| borde | (π−π/180,−π+π/180) → (−π+π/180,π−π/180) | 3.90517420134 |

Magnitudes por eje `(e1,e2)`; las tablas redondean, las comprobaciones usan
los valores completos. PD+G cumple máximo ≤2° y final ≤0.2° en los once
recorridos **por modo**. Los resultados continuos originales están en etapa 6.

| Recorrido | PD digital máximo [°] | PD digital final [°] | PD+G digital máximo [°] | PD+G digital final [°] |
|---|---|---|---|---|
| abajo_arriba | (2.264104,1.145624) | (0.000098,0.000712) | (0.448111,0.159840) | (0.000149,0.001425) |
| arriba_abajo | (1.757825,1.145921) | (0.000141,0.001500) | (0.444789,0.158421) | (0.000148,0.001420) |
| extremos | (2.264247,1.500364) | (1.415433,1.215308) | (0.446124,0.386311) | (0.000467,0.001240) |
| extremos_opuestos | (2.262092,1.212932) | (1.415456,1.212932) | (0.345379,0.452250) | (0.000443,0.001135) |
| eje1 | (2.164526,1.360309) | (0.274543,1.065663) | (0.421516,0.202318) | (0.000064,0.000837) |
| eje2 | (1.991932,1.495621) | (1.415936,1.212877) | (0.044182,0.298975) | (0.000016,0.001188) |
| nulo_horizontal | (2.021903,1.212143) | (2.021903,1.212141) | (0,0) | (0,0) |
| vuelta_continuada | (1.757825,1.145921) | (0.000141,0.001500) | (0.444789,0.158420) | (0.000148,0.001420) |
| interior_a | (1.720530,0.496701) | (1.504022,0.032330) | (0.383749,0.414541) | (0.000177,0.001226) |
| interior_b | (1.814054,1.471826) | (1.196657,0.027183) | (0.199328,0.309767) | (0.000429,0.001175) |
| borde | (1.746660,1.658600) | (1.415332,1.215203) | (0.341338,0.451815) | (0.000442,0.001135) |

PD puro conserva sesgo por gravedad y cumple ambos umbrales sólo en
arriba_abajo y vuelta_continuada; se informa como comparación. En los pares
nuevos, PD+G continuo obtuvo máximos/finales: interior_a
`(0.382374,0.414639)/(0.000178,0.001235)°`, interior_b
`(0.199927,0.310350)/(0.000432,0.001184)°` y borde
`(0.343519,0.451856)/(0.000446,0.001145)°`.

| Máximo conjunto PD+G sobre once recorridos | Continuo | Digital 1 ms | Criterio o capacidad |
|---|---|---|---|
| Error máximo [°] | (0.446448,0.452205) | (0.448111,0.452250) | ≤(2,2) |
| Error final [°] | (0.000471,0.001434) | (0.000467,0.001425) | ≤(0.2,0.2) después de 1 s |
| Torque pedido/aplicado máximo [N·m] | (0.800254,0.145570) | (0.800264,0.145568) | (1.20,0.31); sin saturación nominal |
| Torque ideal máximo [N·m] | (0.800067,0.145471) | (0.800067,0.145471) | (1.20,0.31) |
| Velocidad real máxima [rad/s] | (3.011797,3.001004) | (3.012024,3.001098) | Contraste con rpm, sin recorte a la referencia |
| Entrada máxima [rpm] | (1783.154,745.094) | (1783.288,745.118) | (10800,10000) |
| Máximo abs(P) [W] | (2.408741,0.416219) | (2.408936,0.416265) | (6,12) de transmisión |

La reserva de torque digital en esos casos es aproximadamente
`(0.399736,0.164432) N·m`. Las estimaciones de motor con η máxima también
cumplen: torque aproximadamente `(0.017443,0.006912) N·m`, frente a
`(0.0322,0.0149) N·m`; potencia aproximadamente `(3.2553,0.5139) W`, frente
a `(36.4173,16.8515) W` del punto nominal. Se conservan las limitaciones
de selección de etapa 5, incluyendo eficiencia real y calentamiento desconocidos.

En recuperación de ±5°, PD+G digital asienta en 0.176 s para signos iguales
y 0.217 s para opuestos; el continuo, en 0.176 y 0.218 s. El error final
digital es ≤`(2.537e-7,1.410e-6)°`. El pedido inicial máximo
`(1.816053,0.454730) N·m` supera los límites; aplicado máximo
`(1.20,0.31) N·m`. Las muestras saturadas digitales son
`(0.399867,0.299900)%` para signos iguales y `(0.133289,0.066644)%`
para opuestos. Los 5° iniciales se evalúan por recuperación, no como
incumplimiento del máximo de seguimiento.

### Sensibilidad al período y al rozamiento

PD+G, fricción nominal, mismas condiciones de extremos_opuestos o
recuperación (+5,+5). Sólo cambia Ts; no se ajustan ganancias.

| Ts [ms] | Extremos opuestos: máximo [°] | Extremos opuestos: final [°] | Seguimiento | Recuperación: final [°] | Asentamiento [s] |
|---:|---|---|---|---|---|
| 0.5 | (0.344293,0.452221) | (0.000445,0.001140) | Cumple | (2.095e-7,8.679e-7) | 0.176 |
| 1 | (0.345379,0.452250) | (0.000443,0.001135) | Cumple nominal | (2.079e-7,8.593e-7) | 0.176 |
| 5 | (0.353527,0.452951) | (0.000429,0.001100) | Cumple en este caso | (1.972e-7,7.993e-7) | 0.176 |
| 10 | (0.362363,0.455018) | (0.000414,0.001060) | Cumple en este caso | (0.003457,0.356670) | No alcanza el umbral en 3 s |
| 20 | (2.009767,4.019261) | (0.000982,0.001536) | Incumple el máximo | (1.239987,5.998702) | No alcanza el umbral en 3 s |

En extremos_opuestos a 20 ms, pedidos máximos `(3.132317,1.189986) N·m`,
muestras saturadas `(17.04545,28.81494)%` y potencia absoluta máxima
`(5.458502,2.262572) W`. Aunque el error final sea pequeño, no cumple el
máximo de 2°. En recuperación a 10 ms el eje 2 termina fuera de 0.2°;
a 20 ms alcanza 7.520595° máximos y saturaciones cercanas al 80% de
las muestras. Son incumplimientos diagnósticos de períodos mayores, no
resultados nominales aceptados ni razones para cambiar silenciosamente las ganancias.

Los barridos de fricción usan PD+G en abajo_arriba y extremos_opuestos,
ambos modos; sólo escalan B y Tc por 0, 0.5, 1 y 2. Las **16 combinaciones**
observadas cumplen precisión, capacidad y pedido sin saturación. Máximos de
error por eje, en grados:

| Caso y modo | Nula | Media | Nominal | Doble |
|---|---|---|---|---|
| abajo_arriba continuo | (0.271492,0.188320) | (0.355390,0.176564) | (0.446448,0.159042) | (0.647739,0.127254) |
| abajo_arriba digital 1 ms | (0.272783,0.189092) | (0.356878,0.177389) | (0.448111,0.159840) | (0.649566,0.127976) |
| extremos_opuestos continuo | (0.110117,0.179148) | (0.224936,0.315490) | (0.343191,0.452205) | (0.585305,0.726607) |
| extremos_opuestos digital 1 ms | (0.112124,0.179188) | (0.227104,0.315533) | (0.345379,0.452250) | (0.587410,0.726655) |

Con fricción doble, error final abajo_arriba continuo/digital
`(0.004097,0.010341)/(0.004090,0.010356)°`, y extremos_opuestos
`(0.007933,0.017573)/(0.007902,0.017519)°`. La potencia perdida
`qd·f` es no negativa en todas las muestras. No se supone monotonía
del error: el eje 2 en abajo_arriba reduce su máximo al aumentar fricción.
Son resultados de estos casos con fricción supuesta, sin validación experimental.

### Informe de verificaciones y aceptación final

Reproducción de las nuevas comprobaciones y de la suite completa:

```bash
.venv/bin/python -m pytest tests/test_digital.py tests/test_validacion_final.py tests/test_animacion_comparada.py tests/test_cli_digital.py tests/test_graficos_control.py -v -s
.venv/bin/python -m pytest -v -s
```

La suite completa aprobó **159 casos en 205.58 s**: 61 nuevos y los 98
previos. La validación física final reutiliza 80 resultados y emite sus
métricas en consola (filas `VALIDACION`), además de un contraste estricto.
Las funciones/métodos propios tienen docstrings y comentarios internos en español.

| Prueba y propósito | Método y condiciones | Resultado esperado | Resultado obtenido | Estado | Análisis preliminar |
|---|---|---|---|---|---|
| Actualización digital y retención | Ts=7.3 ms, horizonte 3 s, salida 1 ms; interceptar controlador y entradas a cada solve_ivp | Una llamada por intervalo, fronteras exactas, q/qd continuos, última fracción, pedido/aplicado mantenidos | 411 actualizaciones, último t_k=2.993 s e intervalo final 7 ms; 3001 salidas; fronteras/retención exactas | Cumplida | Ts y salida no necesitan ser múltiplos; no se recalcula control dentro de RK45. |
| Planta común y ausencia de recortes | Modelo actuado, Ts=4 s y horizonte 3 s; pedir (2,−1) N·m; q0=(π+0.2,−π−0.1) rad, qd0=(3.5,−3.2) rad/s; comparar con planta de torque constante | q/qd/E coincidentes a 1e-10 rad/1e-9 rad/s/1e-10 J; aplicado=(1.20,−0.31) N·m; estados iniciales intactos | Δq=0 rad, Δqd=6.94e-18 rad/s, ΔE=0 J; estados sin envolver/recortar | Cumplida | Aísla integración y saturación de la variación de control; el rango limita destinos, no el estado físico. |
| Control más rápido que la salida | Ts=0.5 ms y salida 1 ms, incluyendo pedidos entre salidas | No perder intervalos ni picos de torque; actualizar 6000 veces | 6000 eventos/3001 salidas; trazas y métricas detectan pedidos/aplicaciones ausentes de la grilla | Cumplida | Los máximos de torque usan todos los eventos; estados y potencia conservan resolución de salida. |
| Frontera derecha y exclusión de actualización final | Ts=1.5 s durante 3 s, salida cada 0.5 s; PD con perturbación inicial | Dos actualizaciones en 0/1.5 s; frontera usa segundo pedido; final conserva última aplicación | Dos llamadas y registros de frontera/final exactos | Cumplida | No se fabrica una actualización sin intervalo posterior. |
| Seguimiento nominal en ambos modos | Ocho recorridos originales y tres pares nuevos; PD y PD+G, mismo modelo/ganancias/fricción; hold 1 s | PD+G máximo≤2°, final≤0.2°, pedido e ideal dentro de torque y capacidad de rpm/potencia | Once recorridos por modo cumplen; máximos y demandas de las tablas; ninguna saturación nominal | Cumplida | PD puro conserva incumplimientos de comparación; no se le impone la aceptación nominal. |
| Recuperación digital y continua | Cuatro signos de ±5° en las juntas, qd0=0, referencia invertida nula, 3 s | Asentamiento en ±0.2° antes del final, permanencia posterior y torque aplicado dentro de límites | Digital asienta en 0.176/0.217 s; continuo 0.176/0.218 s; final digital≤1.410e-6°; saturación informada | Cumplida | La desviación inicial se evalúa por recuperación. |
| Continuidad de ida-vuelta por combinación | Ambos modos/leyes, heredar final real; coordinación auxiliar con cuatro historias diferentes | Misma referencia, q/qd iniciales de regreso exactamente iguales a su propia ida | Igualdad exacta en las integraciones y en ocho llamadas auxiliares; ganancias/planta/fricción intactas | Cumplida | No hay reset artificial ni cruce de estados entre resultados. |
| Aproximación digital al continuo | Extremos_opuestos PD+G, Ts=0.5/1 ms frente a continuo, misma grilla | Menor diferencia de q al reducir Ts en este caso; digital 1 ms a ≤0.1° del continuo | 0.5 ms: Δq=1.9870e-5 rad, Δqd=6.7828e-5 rad/s; 1 ms: 3.9459e-5 rad y 1.3732e-4 rad/s | Cumplida | La diferencia corresponde al muestreo/retención; no se extrapola monotonía global. |
| Convergencia de integración digital | Extremos_opuestos de 1 ms, repetir rtol=1e-9/atol=1e-11, mismas condiciones | Δq≤1e-5 rad, Δqd≤1e-4 rad/s, Δτpedido≤1e-4 N·m; mantener precisión | Δq=1.5065e-11 rad, Δqd=1.2040e-9 rad/s, Δτ=2.0414e-10 N·m; 40250/57272 evaluaciones | Cumplida | Error numérico muy menor que las diferencias entre modos; contraste estricto no es solución exacta. |
| Sensibilidad a Ts | Cinco períodos en extremos_opuestos y recuperación (+5,+5), ganancias fijas | Registrar evolución finita y mismo caso; diagnosticar capacidad/errores sin imponer éxito a Ts mayores | Seguimiento falla a 20 ms; recuperación falla a 10/20 ms, con valores de la tabla | Diagnóstico cumplido; especificaciones incumplidas en esos casos | Los períodos grandes deterioran el control; se conserva 1 ms nominal. |
| Sensibilidad a fricción | Dos recorridos, dos modos, cuatro escalas; sólo cambia fricción | Resistencias disipativas y resultados comparables; reportar sensibilidad | 16 combinaciones dentro de umbrales/capacidad; qd·f≥0; error final máximo observado 0.017573° | Cumplida en los casos observados | Los coeficientes siguen siendo supuestos; no se afirma monotonía de todos los errores. |
| Gráficos y leyenda común | Curvas auxiliares conocidas, dos/tres instancias, render Agg; caja de leyenda frente a paneles | Datos/colores/estilos correctos; leyenda externa no interseca paneles ni sale de figura | Seis casos gráficos aprobados; figuras reales de cuatro resultados inspeccionadas con curvas visibles | Cumplida | Las leyendas no ocultan los picos al comparar modos. |
| Geometría, índices y reloj simultáneo | Tres robots auxiliares, tiempos hasta 105 ms, períodos gráficos 20/30/150 ms; contraste Toolbox | Geometría≤1e-12 m, tiempo común exacto, incluir final | Índices 0/20/40/60/80/100/105; 0/30/60/90/105; 0/105 respectivamente; geometrías y reloj correctos | Cumplida | Cada robot utiliza su propio estado para el mismo índice físico. |
| Botón y datos originales | Clic durante/después, dos ciclos; bloquear integrador y comparar arrays originales | Detener timer anterior, crear nuevo, conservar artistas/datos; comienzo y final correctos | Dos repeticiones correctas; arrays iguales y cero llamadas al integrador | Cumplida | Animación simple y comparada usan el mismo mecanismo de reproducción. |
| Ventanas y animación real | TkAgg; abajo_arriba, cuatro resultados (dos leyes×dos modos), 3 s; cuadros en 0/1.5/3 s y dos ciclos reales | Geometría≤1e-12 m, reloj común, reinicios, fin en 3 s; sin reintegración ni mutaciones | Ambos ciclos llegan a 3.000 s; clic durante y después funciona; estados/torques/referencias intactos | Cumplida | La verificación usa temporizador real, además de los tests sin ventana. |
| CLI, nombres y barridos | Subprocesos: comparación interior_a y digital horizontal con Ts=7.3 ms; coordinación auxiliar de barridos | Código 0, cuatro informes únicos; retención en todas las salidas; variantes completas, continuo una sola vez; sin gráficos/exportación al pedirlo | Cuatro informes correctos; PD+G aceptado; 411 eventos del caso horizontal; barridos de 4 escalas y 5 períodos más continuo, ordenados | Cumplida | La entrada permite reproducir nominales y diagnósticos sin editar el modelo. |
| Regresión y documentación | Suite completa, inspección de docstrings/comentarios y git diff --check | Conservar etapas previas; fuentes documentadas y diff limpio | 159 casos aprobados; 166 funciones/métodos documentados en 25 archivos; diff limpio | Cumplida | No se modificaron dependencias ni parámetros físicos durante la etapa. |

### Análisis conjunto y alcance de la primera versión

El seguimiento PD+G continuo y digital de 1 ms cumple las especificaciones
nominales en los once recorridos comprobados, incluyendo regreso físico y
pares interiores/cercanos a los extremos. Recupera las perturbaciones iniciales
de 5° y la demanda de selección cabe en los actuadores aprobados. Las
referencias empiezan y terminan en reposo; el estado real y sus velocidades
residuales se registran, sin imponer artificialmente reposo o posición final.

Los períodos grandes pueden producir oscilaciones y saturación aun con las
mismas ganancias: a 10/20 ms falla la recuperación y a 20 ms falla el máximo
del recorrido extremo. El período aprobado de 1 ms conserva margen en los
casos verificados. La fricción cambia el error y la demanda, pero las escalas
ensayadas siguen dentro de criterios en esos dos recorridos. No se cambiaron
ganancias ni componentes para esconder los incumplimientos de sensibilidad.

La primera versión acordada queda implementada. Las pruebas aportan evidencia
numérica para los casos y horizontes indicados: no demuestran todo el rango
ni garantizan comportamiento de una construcción real. Persisten distribución
de masa equivalente, fricción supuesta, transmisión rígida, medición ideal,
eficiencia máxima de selección y ausencia de electrónica, retrasos adicionales,
cuantización, juego, elasticidad, fricción estática y modelo térmico. No se
certifica regeneración eléctrica ni calentamiento. Control cartesiano, fuerzas,
adaptación y material de presentación siguen fuera del alcance acordado.

## Diseño aprobado del proyecto

- Dos articulaciones actuadas en el plano XY vertical; q1 se mide desde +X y q2
  respecto del primer eslabón. Invertido: `(π/2,0)`. Rango de destinos: `[-π,π]`,
  sin envolver ángulos ni modelar colisiones o topes.
- Dos barras de aluminio de `200×20×10 mm`; densidad supuesta `2700 kg/m³`, masa
  calculada `108 g` cada una, sin carga útil.
- Modelo construido con Robotics Toolbox. Derivación propia de M, C y G con
  SymPy mediante transformaciones homogéneas y pseudoinercias, contrastada con
  Toolbox. La derivación se realiza una vez por modelo.
- Motor del eje 1 fijo a la base. Motor y reductor del eje 2 transportados en el
  codo por el eslabón 1. Cuerpos cilíndricos equivalentes y fijación supuesta de
  `20 g`; composición de inercias y centros de masa por Steiner.
- Candidatos de 18 V: DCX 22 L + GPX 22 estándar ≈62:1 para el eje 1 y DCX 22 S
  + GPX 22 estándar ≈26:1 para el eje 2. Límites continuos iniciales: `1.20 N·m`
  y aproximadamente `0.31 N·m`, contrastados en seguimiento continuo. Añadir `N²Jm`
  a la diagonal de M sin duplicar el efecto.
- Fricción articular `B·q̇ + Tc·tanh(q̇/ε)`, con `B=(0.02,0.005) N·m·s/rad`,
  `Tc=(0.03,0.01) N·m` y `ε=0.01 rad/s`. Son supuestos de pérdidas moderadas:
  alrededor del 7.5–8% del torque continuo a `3 rad/s`, no valores identificados.
  Comparar fricción nula, media, nominal y doble.
- Transmisión rígida, sin juego, elasticidad, fricción estática, dinámica eléctrica
  ni modelo térmico. Medición ideal de posición y velocidad.
- Referencias articulares de quinto orden entre reposos, sincronizadas: duración
  mínima `2 s`, velocidad máxima `3 rad/s`, aceleración máxima `6 rad/s²`,
  permanencia final de al menos `1 s`.
- PD y PD con compensación de gravedad, con error de velocidad deseada menos
  real. Ganancias iniciales: `Kp=diag(20,5)` y `Kd=diag(1.3,0.2)` en unidades SI.
  Varias instancias independientes; saturación común y registro de torques pedidos
  y aplicados, sin recortar estados.
- Control continuo y digital, inicialmente con período digital `1 ms` configurable.
  Integración RK45 con `rtol=1e-7`, `atol=1e-9` y resultados cada `1 ms`.
- Gráficos y animaciones 2D con Matplotlib, incluyendo comparación simultánea.
  Resultados en memoria; exportación únicamente a pedido.
- Aceptación nominal para PD con gravedad continuo y digital de `1 ms`: error
  máximo `2°` por eje, final `0.2°` tras `1 s` de permanencia y capacidad suficiente
  de torque, velocidad y potencia. La recuperación desde desviaciones de `5°`
  se evalúa separadamente del error máximo de seguimiento.

## Ruta por etapas

| Etapa | Entrega y verificaciones principales |
|---|---|
| 1 | Entorno y estructura: imports/versiones, robot auxiliar, FK y dinámica analíticas, punto de entrada. |
| 2 | Mecánica y DH: masas, centros de masa, tensores, posiciones horizontal/colgante/invertida/plegada y contraste geométrico. |
| 3 | M, C y G propias: contraste con Toolbox, simetría/positividad, antisimetría de Ṁ−2C, potencial y torque de sostén. |
| 4 | Movimiento libre: equilibrios, perturbación del invertido, energía, convergencia y animación básica. |
| 5 | Actuadores/fricción: montaje, inercia reflejada, contraste ampliado, disipación, capacidades y saturación. |
| 6 | Quinticas y control continuo: extremos/límites, estabilización, abajo–arriba, recorridos extremos, un eje y comparación PD/PD+G. |
| 7 | Digital y comparación: muestreo, múltiples instancias, pares reproducibles, sensibilidad, métricas y animación simultánea. |

Cada cierre informa **prueba y propósito, condiciones/método, resultado esperado,
resultado obtenido con unidades y tolerancias, estado y análisis preliminar**.
Si una comprobación necesaria falla, se resuelve dentro de la etapa. Cambiar diseño,
ganancias o componentes requiere confirmación; no se avanza automáticamente.

Tras completar y verificar con éxito cada etapa, se hará commit y push del
proyecto y se actualizará y publicará su referencia como submódulo en el
repositorio padre. Los commits incluirán únicamente los cambios de la etapa.

Los módulos de parámetros, modelo, dinámica, trayectorias, control, simulación y
visualización contienen implementaciones concretas. No se generan módulos vacíos
por adelantado. Control cartesiano, fuerzas, adaptación y material
de presentación quedan fuera de la primera versión.

## Fuentes

- Enunciado: [ENUNCIADO.md](ENUNCIADO.md).
- Referencias de la cursada: [REFERENCIAS.md](REFERENCIAS.md).
- [Robotics Toolbox en PyPI](https://pypi.org/project/roboticstoolbox-python/1.4.4/).
- [Motor DCX 22 L](https://www.maxongroup.com/medias/sys_master/root/9394602541086/Cataloge-Page-EN-114.pdf).
- [Motor DCX 22 S](https://www.maxongroup.com/medias/sys_master/root/9394602410014/Cataloge-Page-EN-112.pdf).
- [Reductores GPX 22](https://www.maxongroup.co.jp/medias/sys_master/root/9406757797918/Cataloge-Page-EN-390.pdf).
