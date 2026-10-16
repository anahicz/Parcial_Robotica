# JetCobot - Control Autónomo de Brazo Robótico

**Proyecto del equipo: Sistema completo de recogida y depósito de cubos de colores usando el brazo **myCoBot 280** en Jetson, con detección visual por HSV y mapeo de píxeles a coordenadas del robot mediante homografía.


> ## ▶ Uso desde Jupyter (recomendado en el JetCobot)
> 1. En Jupyter: **Upload** → `jetcobot.zip` a tu carpeta personal.
> 2. Abrí una terminal de Jupyter o una celda y ejecutá: `!unzip -o ~/jetcobot.zip -d ~`
> 3. Abrí `jetcobot/JetCobot_Jupyter.ipynb` y ejecutá las celdas **en orden** con Shift+Enter.
> 4. Primero con `SIMULAR = True`, después con `False`. Todo el flujo (mesa, calibración, un color, ciclo) está ahí.
>
> La calibración por consola (`--calibrar`) abre una ventana de OpenCV y **no funciona dentro de Jupyter**: usá el paso 5 del cuaderno.


---

## Tabla de Contenidos
1. [Requisitos](#requisitos)
2. [Instalación](#instalación)
3. [Estructura del Proyecto](#estructura-del-proyecto)
4. [Modos de Operación](#modos-de-operación)
5. [Calibración](#calibración)
6. [Ejecución](#ejecución)
7. [Troubleshooting](#troubleshooting)
8. [Integración ROS 2 (Pregunta 2)](#integración-ros-2-pregunta-2)
9. [Parámetros y Límites](#parámetros-y-límites)
10. [Advertencias de Seguridad](#advertencias-de-seguridad)

---

## Requisitos

### Hardware
- **Robot**: myCoBot 280 (Elephant Robotics / Yahboom)
- **Jetson**: nvidia Jetson (cualquier versión compatible con Ubuntu 20.04+)
- **Cámara USB**: 640x480, formato YUYV (e.g., `/dev/video0`)
- **Serial**: `/dev/ttyUSB0`, baud rate 1000000

### Software
- **Python** 3.8+
- **pymycobot**: SDK oficial del robot
- **OpenCV** (cv2): detección de colores
- **NumPy**: operaciones matemáticas
- **ROS 2 Humble** (opcional): para el broker

---

## Instalación

### 1. Crea un entorno virtual

```bash
cd /ruta/a/jetcobot
python3 -m venv venv
source venv/bin/activate
```

### 2. Instala dependencias

```bash
pip install pymycobot opencv-python numpy
```

### 3. Verifica la cámara

```bash
# Lista dispositivos de video
ls -la /dev/video*

# Si la cámara está en uso por otro proceso (ej. Jupyter):
# Ciérralo o desactívalo
sudo fuser -k /dev/video0   # Libera la cámara
```

### 4. Verifica la conexión serial

```bash
ls -la /dev/ttyUSB*
# Debería ver /dev/ttyUSB0 con baud 1000000
```

---

## Estructura del Proyecto

```
jetcobot/
├── config.json                 # Configuración (posiciones, HSV, límites)
├── calibracion.json            # Homografía (generada)
├── intentos.csv                # Log de intentos (generado)
├── pick_place.py               # Orquestador principal
├── robot.py                    # Adapter pymycobot + SimRobot
├── vision.py                   # Detección HSV de colores
├── calibration.py              # Calibración por homografía
├── cinematica.py               # Cinemática directa (FK) para myCoBot 280
├── broker_node.py              # Nodo ROS 2 con cola de prioridad (opcional)
├── cliente_orden.py            # CLI para enviar órdenes al broker
├── interprete_stub.py          # Intérprete de frases en español
├── tests/
│   ├── test_jetcobot.py        # Suite de unit tests
│   └── __init__.py
├── logs/                       # Logs de ejecución (generado)
├── debug_images/               # Imágenes de depuración (generado)
└── README.md                   # Este archivo
```

---

## Modos de Operación

### 1. **Simulación sin Hardware** (`--simular`)
Prueba la lógica sin robot real ni cámara.

```bash
python3 pick_place.py --simular --paso-a-paso
```

**Uso**: verificar flujo antes de calibrar.

### 2. **Detección Visual** (`--detectar`)
Solo captura y detecta colores, sin mover el robot.

```bash
python3 pick_place.py --detectar
```

**Salida**: muestra píxeles detectados de cada cubo.

### 3. **Calibración Interactiva** (`--calibrar`)
Mapea píxeles a coordenadas del robot.

```bash
python3 pick_place.py --calibrar
```

**Proceso**:
1. Coloca marcadores (tape de colores) en 4-6 puntos visibles en la mesa
2. Haz click en cada marcador en la imagen
3. Presiona `r` para liberar servos
4. Jog manual del gripper al punto físico
5. Presiona `p` para leer y guardar coordenadas
6. Repite 4-6 veces
7. Presiona `c` para computar homografía

**Resultado**: genera `calibracion.json` con matriz de transformación.

### 4. **Enseñanza de Posiciones** (`--ensenar NOMBRE`)
Registra una nueva posición (e.g., HOME personalizada, zona de espera).

```bash
python3 pick_place.py --ensenar mi_posicion
```

**Proceso**:
1. Presiona `r` para liberar servos
2. Jog manual a la posición deseada
3. Presiona `p` para guardar
4. Se guarda en `config.json` bajo `poses.mi_posicion`

### 5. **Recogida de Un Color** (`--color ROJO`)
Recoge solo un cubo específico (útil para testing de color individual).

```bash
python3 pick_place.py --color rojo --paso-a-paso --velocidad 15
```

**Parámetros**:
- `--color`: rojo / azul / amarillo / verde
- `--velocidad`: 10-50 (por defecto 20)
- `--paso-a-paso`: espera Enter entre movimientos

### 6. **Ciclo Completo**
Detección → recogida de los 4 cubos en orden → depósito.

```bash
# Simulado
python3 pick_place.py --simular

# Real (requiere calibración previa)
python3 pick_place.py --paso-a-paso
```

### 7. **Estado del Sistema** (`--estado`)
Muestra ángulos, coords y estado de calibración.

```bash
python3 pick_place.py --estado
```

---

## Calibración

### ¿Por Qué Calibración?
La cámara y el robot viven en **espacios distintos**:
- **Cámara**: píxeles (u, v) de 640×480
- **Robot**: milímetros cartesianos (x, y, z)

La **homografía** mapea píxeles a tabla (x, y) a una altura constante (z_grasp).

### Paso a Paso

1. **Libera el espacio de trabajo**. Coloca la mesa/bandeja en el rango visual del robot (OBSERVATION).

2. **Prepara marcadores**: coloca 4-6 marcas visibles en la mesa (tape de colores, post-it, etc.) a alturas similares.

3. **Inicia calibración**:
   ```bash
   python3 pick_place.py --calibrar
   ```

4. **En la ventana de imagen**:
   - Ves lo que ve la cámara en OBSERVATION.
   - Haz click en cada marcador (aparecerá círculo rojo).
   - Presiona `r` para liberar servos.
   - Jog **manual** del gripper exactamente sobre el marcador físico (sin tocar).
   - Presiona `p` para leer coords del robot.
   - Se guarda el par (píxel, coords_robot).

5. **Repite 4-6 puntos** distribuidos en el área de trabajo (esquinas, centro).

6. **Presiona `c`** para computar la homografía.

7. **Resultado**: 
   - Se crea `calibracion.json` con la matriz H.
   - Se reporta error de reproyección (idealmente < 10 píxeles).

### Ejemplo: Homografía Inversa
La calibración permite:
```
píxel (u, v) -> robot (x, y) a z_grasp
```
Esto se usa en pick_place para saber dónde alcanzar cada cubo.

---

## Ejecución

### Flujo recomendado de ejecución

#### Día 1: Verificación
```bash
# 1. Verifica que todo se compila
python3 -m pytest tests/ -v

# 2. Simulación pura
python3 pick_place.py --simular --paso-a-paso

# 3. Si funciona en simulación, calibra
python3 pick_place.py --calibrar
```

#### Día 2: Pruebas Reales
```bash
# 1. Detecta cubos
python3 pick_place.py --detectar

# 2. Prueba un color con baja velocidad
python3 pick_place.py --color rojo --paso-a-paso --velocidad 15

# 3. Si rojo funciona, prueba otro
python3 pick_place.py --color azul --paso-a-paso --velocidad 15

# 4. Si 2 colores funcionan, ciclo completo
python3 pick_place.py --paso-a-paso --velocidad 20
```

#### Día 3: Automático
```bash
# Velocidad normal, sin parar
python3 pick_place.py --velocidad 30
```

### Monitoreo

Durante ejecución, se generan:
- **Logs**: `logs/run_YYYYMMDD_HHMMSS.log` (DEBUG)
- **CSV**: `logs/run_YYYYMMDD_HHMMSS.csv` (movimientos comandados vs medidos)
- **Imágenes** (si `--debug`): `debug_images/frame_0001.jpg`, etc.

```bash
# Ver último log en tiempo real
tail -f logs/run_*.log

# Analizar CSV
python3 -c "import pandas as pd; df = pd.read_csv('logs/run_*.csv'); print(df)"
```

---

## Troubleshooting

### "Error: Cámara /dev/video0 no disponible"
**Causa**: Otro proceso (Jupyter, navegador) la tiene abierta.

**Solución**:
```bash
# Libera la cámara
sudo fuser -k /dev/video0

# O reinicia Jupyter
pkill -f jupyter
```

### "Error: SerialException en /dev/ttyUSB0"
**Causa**: El puerto serial está en uso o el robot no está encendido.

**Solución**:
```bash
# Verifica que exista
ls /dev/ttyUSB0

# Si no existe, reconecta el cable USB

# Si existe, verifica permisos
sudo usermod -a -G dialout $USER
# Luego logout/login

# Si aún falla, intenta con `strace`
strace -e open python3 pick_place.py 2>&1 | grep ttyUSB
```

### "Error: Ángulos fuera de límites"
**Causa**: Posición calculada está fuera del rango articular del robot.

**Solución**:
- Verifica que `config.json` tenga límites correctos para myCoBot 280.
- Revisa que los ángulos enseñados estén dentro de `[-165, 165]` para J1-J5 y `[-175, 175]` para J6.

### "Error: Pose mismatch (error > tolerancia)"
**Causa**: El robot no alcanzó la posición comandada (interferencia física, fatiga de servos, etc.).

**Acción**:
- El script se detiene automáticamente (STOP).
- Verifica obstáculos en el espacio de trabajo.
- Reinicia el robot (desenchufa/enchufa).
- Si persiste, los servos pueden necesitar calibración.

### "Detección inestable / cambia de un frame a otro"
**Causa**: Iluminación variable o HSV ranges mal ajustados.

**Soluciones**:
1. Mejora iluminación (luz diffusa, evita sombras).
2. Ajusta HSV ranges en `config.json` para cada color:
   ```bash
   python3 pick_place.py --detectar
   # Observa qué se detecta y qué no
   ```
3. Aumenta `stability_frames` en config (ej. 8 en lugar de 4).

### "Gripper no cierra / queda a mitad"
**Causa**: Servos débiles, objeto duro, o valor de cierre incorrecto.

**Soluciones**:
- Verifica `close_value` en `config.json` (debe ser 60-80).
- Prueba con mano: `python3 pick_place.py --ensenar prueba_gripper` y verifica manualmente.
- Si el servicio está débil, contacta con Yahboom.

---

## Integración ROS 2 (Pregunta 2)

El broker ROS 2 implementa una **cola de prioridad** con un **single worker** (patrón obligatorio).

### Arquitectura

```
[CLI / Sensores] -> [/pedir_agarre service] -> [BrokerQueue (heapq)] 
                                                        |
                                                    [Worker Thread]
                                                        |
                                                   [robot.send_angles]
                                                   [robot.send_coords]
                                                   [log intentos.csv]
```

### Instalación ROS 2

```bash
source /opt/ros/humble/setup.bash
pip install rclpy
```

### Uso del Broker

1. **Inicia el broker**:
   ```bash
   python3 broker_node.py
   ```

2. **En otro terminal, envía órdenes**:
   ```bash
   # CLI simple
   python3 cliente_orden.py --color rojo

   # Simula 4 usuarios enviando en paralelo
   python3 cliente_orden.py --paralelo 4

   # Desde frase en español
   python3 cliente_orden.py --frase "recoge el cubo rojo urgente"
   ```

3. **Monitorea la cola**:
   ```bash
   ros2 topic echo /cola_broker
   ```

4. **Revisa intentos**:
   ```bash
   cat intentos.csv
   ```

### Integración con Pregunta 1 (LAYA)

El flujo real es:
```
[Audio] -> [LAYA voz/texto] -> [interprete_stub.py] -> [cliente_orden.py] -> [broker]
```

Hoy `interprete_stub.py` hace keyword matching. En el curso usa **LAYA** (Pregunta 1) para voz.

**Para conectar LAYA**: reemplaza `InterpretadorOrdenes` con la salida del API de LAYA en `cliente_orden.py`.

---

## Parámetros y Límites

### Límites Articulares (myCoBot 280)

```json
{
  "J1": [-165, 165],
  "J2": [-165, 165],
  "J3": [-165, 165],
  "J4": [-165, 165],
  "J5": [-165, 165],
  "J6": [-175, 175]
}
```

**Nunca envíes ángulos fuera estos rangos**. El script verifica antes de enviar.

### Espacio de Trabajo Cartesiano

- **Radio**: ~300-400 mm desde la base
- **Altura**: 150-400 mm (aproximado)
- **Orientación**: rx, ry, rz en [-180, 180] grados

### Velocidades

- `default_speed`: 20 (recomendado para precisión)
- `lento`: 10 (debug)
- `rapido`: 50 (no usar en ciclo completo, solo transits largos)

### Tolerancias

```json
{
  "tolerance_joints_deg": 2.5,    // Error máximo en ángulos
  "tolerance_coords_mm": 5        // Error máximo en cartesianas
}
```

Si error > tolerancia, se reporta WARNING y se para.

### Alturas de Movimiento

```json
{
  "approach_height_mm": 80,       // mm SOBRE la mesa (se suma a z_min_mm)
  "grasp_height_mm": 20,          // mm SOBRE la mesa (se suma a z_min_mm); ~mitad del cubo
  "step_descent_mm": 10,          // Pasos de descenso (seguridad)
  "workspace": {
    "z_min_mm": 90,               // CRÍTICO: altura de la mesa (tabla), medida local
    "z_max_mm": 400               // Límite superior de altura
  }
}
```

**CRÍTICO**: Debes medir y configurar `z_min_mm` en tu table/mesa:

```bash
python3 pick_place.py --ensenar table_height
# Jog manualmente a la ALTURA DE LA MESA (punto más bajo sin colisionar)
# Lee z en el CSV: logs/run_*.csv
# Actualiza en config.json: motion.workspace.z_min_mm = (ese valor, ej. 95 si es mesa a 95mm)
```

El script **rechaza automáticamente** cualquier movimiento por debajo de `z_min_mm` para evitar colisiones.

---

## Advertencias de Seguridad

### ⚠ Antes de Cada Ejecución

1. **Mano sobre el botón de emergencia**: El robot se puede mover inesperadamente.
2. **Espacio libre**: Retira objetos, manos, cabello del área de trabajo.
3. **Cámara abierta**: Verifica que no esté bloqueada.
4. **Serial libre**: No hay otro proceso hablando con el robot.

### 🛑 Si el Robot Se Comporta Anormal

1. **STOP INMEDIATAMENTE**: Presiona Ctrl+C.
2. **Mano sobre parada de emergencia** (si existe).
3. **Desenchufa el USB** del robot.
4. **Revisa los logs** (`logs/run_*.log`) para el último comando.
5. **No reinicies** hasta identificar la causa.

### 📋 Checklist Pre-Ejecución

```bash
# 1. Tests pasan
python3 -m pytest tests/ -q

# 2. Cámara funciona
python3 pick_place.py --detectar

# 3. Calibración existe
test -f calibracion.json && echo "OK" || echo "FALTAN CALIBRAR"

# 4. Robot responde
python3 pick_place.py --estado

# 5. Área despejada (visual)
python3 pick_place.py --detectar | grep -q "rojo" && echo "Cubos visibles"
```

---

## Notas Técnicas

### Cinemática Directa (FK)

Implementada en `cinematica.py` con parámetros DH del myCoBot 280:
```
Link 1: d=131.9mm
Link 2: a=136mm
Link 3: a=108.5mm
Link 4: a=0 (articulación de rotación)
Link 5: d=55.5mm
Link 6: d=55.8mm (gripper)
```

Usada para:
- Calcular error de posición (FK vs `get_coords()`)
- Verificar consistencia cinemática

### Homografía y Calibración

La transformación píxel → robot es una **perspectiva 2D**:
```
[u, v, 1] · H = [x, y, 1]
```

`cv2.findHomography()` se ajusta usando 4+ puntos calibrados.

**Error de reproyección**: mide cuán bien H predice los puntos de entrenamiento.
- Ideal: < 5 píxeles
- Aceptable: < 15 píxeles
- Rechazar: > 20 píxeles

### Single Publisher Pattern

El broker implementa el patrón del curso:
- Un **único worker thread** toca el robot.
- Las solicitudes se **encolan** con prioridad.
- El worker las procesa secuencialmente.

Esto evita:
- Comandos simultáneos (ROM conflict)
- Inconsistencia de estado
- Deadlocks

---

## Referencias

- **Elephant Robotics**: https://wiki.elephantrobotics.com/docs/en/
- **pymycobot**: https://github.com/elephantrobotics/pymycobot
- **ROS 2 Humble**: https://docs.ros.org/en/humble/
- **OpenCV HSV**: https://docs.opencv.org/master/df/d9d/tutorial_py_colorspaces.html

---

## Licencia

Este proyecto es para **fines educativos**. 

---

## Contexto académico

Material académico del equipo para el proyecto de control robótico autónomo.

---

## FAQ

**P: ¿Cuánto tarda la calibración?**  
R: ~10 minutos (4-6 puntos, jog manual).

**P: ¿Puedo usar otro color que no esté en config.json?**  
R: No. Edita `config.json` y añade rango HSV. Usa `--detectar` para ver si se detecta.

**P: ¿Funciona sin cámara?**  
R: Sí, en simulación (`--simular`). Para el robot real, necesitas cámara + calibración.

**P: ¿Puedo cambiar posiciones de depósito?**  
R: Sí, enseña posiciones con `--ensenar zona_nueva` y actualiza `config.json`.

**P: ¿El robot usa MoveIt2?**  
R: No en esta versión. Usa directamente `pymycobot.send_coords()` (lineal) y `send_angles()` (articular). Si tienes MoveIt2 para myCoBot en Jetson, puedes adaptar `robot.py` para usar su planeador.

**P: ¿Qué pasa si pierdo `calibracion.json`?**  
R: Vuelve a calibrar: `python3 pick_place.py --calibrar`.

---

**Última actualización**: octubre 2026  
**Versión**: 1.0  
**Estado**: Integración parcial; pendientes las validaciones del flujo físico y de ROS 2/LAYA
