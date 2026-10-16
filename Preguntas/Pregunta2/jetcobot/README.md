# JetCobot — Núcleo de Pick & Place

```text
# ==============================================================================
# UNIVERSIDAD ESAN
# ROBÓTICA S-003
# EXAMEN PARCIAL - GRAN RETO JETCOBOT
# Grupo 7
#
# Integrantes:
#   - Sebastian Pedro Aguirre Acosta
#   - Anahi Cortez Chinchay
#   - Ramirez Quevedo Karen Noelia
#   - Vara Vargas Valentino Uziel
# ==============================================================================
```

## Estructura mínima

```text
jetcobot/
├── pick_place.py          # Orquestador del ciclo
├── robot.py               # Adaptador real y simulación
├── vision.py              # Captura de cámara y detección por colores
├── calibration.py         # Homografía y calibración
├── config_ejemplo.json    # Esquema de configuración (no calibración real)
├── .gitignore             # Exclusión de datos locales
└── README.md
```

### Dependencias verificadas

`pick_place.py` importa directamente:
- `robot.create_robot`, `robot.RobotAdapter`, `robot.SimRobot`
- `vision.CameraCapture`, `vision.ColorDetector`, `vision.capture_and_detect`
- `calibration.HomographyCalibrator`, `calibration.CalibrationUI`

Para ejecutar en software: Python 3, `numpy`, `opencv-python`. El adaptador de hardware también utiliza `pymycobot` al conectarse al robot real.

### Estado y configuración

El script **exige `config.json`** en el directorio de trabajo. La calibración se guarda en `calibracion.json` y depende de las mediciones específicas de la cámara, mesa y brazo. Ambos archivos están excluidos del repositorio. `config_ejemplo.json` es solo una plantilla de referencia; **no debe sobrescribir la configuración calibrada** de la Jetson.

Se comprobó la sintaxis de los cuatro módulos y las **41 pruebas automatizadas de la versión anterior** (antes de retirar el directorio histórico de pruebas). No se verificó un ciclo físico completo ni la integración final con LAYA.

### Prueba sin movimiento físico

```bash
python3 -m py_compile pick_place.py robot.py vision.py calibration.py
# Solo en carpeta aislada de simulación, sin sobrescribir la configuración real:
cp config_ejemplo.json config.json
python3 pick_place.py --simular --estado
```

Si ya existe `config.json`, **no ejecutar la instrucción `cp`**. El archivo de ejemplo no sustituye la calibración física.

### Parches pendientes

Se espera recibir `parche_altura_deposito.py` y `parche_seguir.py` (nombre exacto por confirmar). No figuran en el ZIP ni en el repositorio; por ello no están incluidos aquí. Los antiguos parches `parche_levante.py` y `parche_reenvio.py` se retiraron para evitar su reaplicación accidental. El programa de `pick_place.py` conserva su implementación anterior hasta que se verifique la nueva.

Los archivos de simulación ROS 2 y las herramientas auxiliares anteriores están en la rama de respaldo `respaldo-pregunta2-previo-limpieza-20261016`. Para ejecutar el intérprete ROS 2 y LAYA, consultar la Pregunta 1, que se mantiene separada.
