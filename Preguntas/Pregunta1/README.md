# Parcial Robótica — Gran Reto JetCobot

Repositorio del equipo para el Examen Parcial de Robótica 08079.

## Estructura

- `src/arm_broker`: broker reutilizado del RB-2.
- `src/arm_broker_interfaces`: acción, estado de cola y servicio `InterpretarOrden`.
- `src/interprete_ordenes`: nodo ROS 2 de la Pregunta 1, cliente LAYA, fallback por keywords y medidor.
- `evidencias/pregunta1`: conjunto de 50 frases y resultados del escenario en calma.
- `scripts/generar_figuras_p1.py`: genera las gráficas comparativas desde el CSV de resultados.

## Compilación

```bash
cd ~/ros2_ws
source /opt/ros/humble/setup.bash
colcon build
source install/setup.bash
```

## Ejecutar el intérprete

El servidor LAYA se configura mediante parámetro. No se guarda ninguna clave API en este repositorio.

```bash
ros2 run interprete_ordenes interprete --ros-args \
  -p laya_url:=http://IP_LAYA:PUERTO \
  -p timeout_laya_s:=2.0
```

## Medición de P1

```bash
python3 -m interprete_ordenes.medir_p1 \
  evidencias/pregunta1/frases_50.csv \
  evidencias/pregunta1/resultados_calma.csv \
  calma
```

## Figuras

```bash
python3 scripts/generar_figuras_p1.py evidencias/pregunta1/resultados_calma.csv
```

Pendiente para completar P1: repetir las mismas 50 frases en el escenario bajo carga y guardar el CSV/resumen correspondiente.
