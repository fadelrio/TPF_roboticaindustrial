# Simulación del doble péndulo 2R

## Estado

Están completadas las **etapas 1, 2 y 3: entorno, modelo mecánico, cinemática
y dinámica propia contrastada**. Las etapas
siguientes requieren autorización por separado. El robot auxiliar del diagnóstico
no es el modelo mecánico del proyecto.

## Ejecución

Se utiliza Python 3.12 y una `.venv` dentro de esta carpeta. Para reproducir el
entorno con las dependencias fijadas en `requirements.txt`:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
.venv/bin/python -m pytest -v
```

El punto de entrada muestra versiones, propiedades de las barras, posiciones de
cuatro configuraciones y contraste de la dinámica en consola. No exporta datos,
gráficos ni videos. En el IDE debe seleccionarse `.venv/bin/python` como intérprete.

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
ubicación escribible mediante `MPLCONFIGDIR`. Todavía no se verificaron ventanas,
gráficos ni animaciones; corresponden a etapas posteriores.

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
verificarán en la **etapa 4, pendiente de autorización**. Esta etapa aún no incluye
montaje, inercia de rotores ni fricción. No se modificaron las dependencias.

## Diseño aprobado para las siguientes etapas

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
  y aproximadamente `0.31 N·m`, pendientes de verificar demanda. Añadir `N²Jm`
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
visualización se crearán cuando tengan una implementación concreta. No se generan
módulos vacíos por adelantado. Control cartesiano, fuerzas, adaptación y material
de presentación quedan fuera de la primera versión.

## Fuentes

- Enunciado: [ENUNCIADO.md](ENUNCIADO.md).
- Referencias de la cursada: [REFERENCIAS.md](REFERENCIAS.md).
- [Robotics Toolbox en PyPI](https://pypi.org/project/roboticstoolbox-python/1.4.4/).
- [Motor DCX 22 L](https://www.maxongroup.com/medias/sys_master/root/9394602541086/Cataloge-Page-EN-114.pdf).
- [Motor DCX 22 S](https://www.maxongroup.com/medias/sys_master/root/9394602410014/Cataloge-Page-EN-112.pdf).
- [Reductores GPX 22](https://www.maxongroup.co.jp/medias/sys_master/root/9406757797918/Cataloge-Page-EN-390.pdf).
