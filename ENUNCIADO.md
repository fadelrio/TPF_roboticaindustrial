# Trabajo Pr´actico

### Coloquio 2025

## Planteo del problema

Se propone realizar el dise˜no, selecci´on de componentes y simulaci´on de un doble p´endulo invertido. A partir de un conjunto de especificaciones a definir por vos, se deber´an abordar las siguientes tareas:

Definir las longitudes (cinem´atica) de los eslabones.

#### Calcular sus par´ametros din´amicos.

Seleccionar los actuadores (motores y reductores), especificando su mon- taje.

Incorporar al modelo din´amico los efectos correspondientes de los actuadores.

Implementar en la simulaci´on un generador de trayectorias con perfil de velocidad trapezoidal o de orden superior, en el espacio joint y/o carte- siano.

Incorporar un controlador adecuado para estabilizar el sistema y seguir las trayectorias.

Como validaci´on del trabajo, se deber´an presentar simulaciones que demues- tren el cumplimiento de las especificaciones propuestas. Se sugiere incluir ani- maciones para enriquecer la presentaci´on. Para cumplir con los objetivos de la evaluaci´on, es indispensable aplicar los m´etodos vistos en clase y utilizar herramientas como roboticstoolbox-python.

## Puntos adicionales

Para quienes deseen profundizar y seguir investigando, proponemos los siguientes ejercicios opcionales:

Control de fuerzas: partiendo del controlador de posici´on desarrollado, implementar un controlador de fuerzas que permita realizar un movimiento en l´ınea recta mientras se mantiene el contacto.

Control adaptativo: implementar un estimador on-line de las masas de los eslabones y utilizar dichas estimaciones para corregir el modelo empleado en el control. De este modo, se pueden simular —aunque de manera muy rudimentaria— los efectos producidos por variaciones en las masas (por ejemplo, al tomar un objeto).

Ante cualquier consulta, no duden en escribir.

## Presentaci´on

El trabajo se presenta de forma oral en la fecha de examen correspondien- te. Se dispondr´a de 20 minutos para la exposici´on y 20 minutos para preguntas. Durante la presentaci´on, es indispensable mostrar el software en fun- cionamiento.
