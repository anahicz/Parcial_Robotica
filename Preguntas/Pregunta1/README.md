# Pregunta 1 — Servicio de interpretación de órdenes

Esta carpeta contiene todo lo necesario para la Pregunta 1 del Gran Reto JetCobot.

## Estructura

```text
Pregunta1/
├── src/
│   ├── arm_broker/
│   ├── arm_broker_interfaces/
│   └── interprete_ordenes/
├── evidencias/
│   ├── frases_50.csv
│   ├── resultados_calma.csv
│   └── resultados_calma_resumen.txt
├── scripts/
│   └── generar_figuras_p1.py
└── README.md
```

- `arm_broker`: broker reutilizado del RB-2.
- `arm_broker_interfaces`: incluye `MoveArm.action`, `QueueState.msg` e `InterpretarOrden.srv`.
- `interprete_ordenes`: nodo ROS 2 que expone `/interpretar_orden`, consulta LAYA y usa keywords como respaldo.
- `evidencias`: dataset y resultados medidos.
- `scripts`: generación de figuras comparativas.

## Compilación

Desde la raíz del repositorio:

```bash
source /opt/ros/humble/setup.bash
colcon build --base-paths Preguntas/Pregunta1/src
source install/setup.bash
```

## Ejecutar el intérprete

```bash
ros2 run interprete_ordenes interprete --ros-args \
  -p laya_url:=http://IP_LAYA:PUERTO \
  -p timeout_laya_s:=2.0
```

## Ejecutar la medición en calma

```bash
python3 -m interprete_ordenes.medir_p1 \
  Preguntas/Pregunta1/evidencias/frases_50.csv \
  Preguntas/Pregunta1/evidencias/resultados_calma.csv \
  calma
```

## Generar figuras

```bash
python3 Preguntas/Pregunta1/scripts/generar_figuras_p1.py \
  Preguntas/Pregunta1/evidencias/resultados_calma.csv
```

Pendiente: repetir las mismas 50 frases bajo carga para obtener la comparación
final entre los escenarios **calma** y **carga**.
