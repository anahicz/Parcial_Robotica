# Pregunta 2 — JetCobot: Pick & Place

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

## Estado

Se mantiene **solo el núcleo necesario** para el programa independiente `pick_place.py` (visión, calibración y control del brazo). Esta carpeta no incluye un broker ROS 2 funcional conectado a LAYA y **no se afirma que el flujo físico esté completamente validado**.

## Archivos que permanecen

| Archivo | Uso |
| --- | --- |
| [`jetcobot/pick_place.py`](jetcobot/pick_place.py) | Programa principal: observación, detección, aproximación, agarre y depósito. |
| [`jetcobot/robot.py`](jetcobot/robot.py) | Adaptador del brazo JetCobot y simulador. |
| [`jetcobot/vision.py`](jetcobot/vision.py) | Captura y detección HSV de cubos de colores. |
| [`jetcobot/calibration.py`](jetcobot/calibration.py) | Homografía y conversión de píxeles a coordenadas. |
| [`jetcobot/config_ejemplo.json`](jetcobot/config_ejemplo.json) | Esquema de configuración de referencia, **no** calibración física verificada. |
| [`jetcobot/.gitignore`](jetcobot/.gitignore) | Excluye calibraciones, configuraciones locales y registros. |
| [`jetcobot/README.md`](jetcobot/README.md) | Dependencias, verificación y límites. |

La dependencia directa de `pick_place.py` se verificó: importa `robot`, `vision` y `calibration`; no importa los archivos históricos eliminados. No se incorporan módulos innecesarios para su ejecución autónoma.

## Parches recibidos, sin aplicar

Se incorporaron los archivos originales de trabajo, con firma del Grupo 7, en [`jetcobot/parches_pendientes/`](jetcobot/parches_pendientes/):

- `parche_altura_deposito.pyw`: necesita adaptar su búsqueda de texto antes de poder parchear el `pick_place.py` actual.
- `parche_seguir.pyw`: requiere corregir su lógica de control de errores; puede notificar falsamente que un movimiento terminó correctamente y activa `continue_on_error`.

**No se ejecutaron ni se aplicaron los parches**. El código operativo `pick_place.py`, `robot.py`, `vision.py` y `calibration.py` permanece sin modificaciones.

## Comprobación sin mover el brazo

Desde `Preguntas/Pregunta2/jetcobot`, en un entorno de Python con NumPy y OpenCV:

```bash
python3 -m py_compile pick_place.py robot.py vision.py calibration.py
```

Para una prueba **exclusivamente en simulación**, usar una copia de `config_ejemplo.json` como `config.json` dentro de un entorno de pruebas aislado y ejecutar:

```bash
python3 pick_place.py --simular --estado
```

**Nunca reemplazar** el `config.json` o `calibracion.json` ajustado en la Jetson por el archivo de ejemplo. El código real requiere ambos archivos locales, la cámara y el controlador del robot; no se distribuyen por GitHub.

La versión anterior del ZIP superó **41 pruebas automatizadas** antes de la limpieza. Esas pruebas y el código histórico siguen disponibles en la rama de respaldo `respaldo-pregunta2-previo-limpieza-20261016`. La limpieza no es una nueva validación física del JetCobot.

## Conservación del historial

La rama [`respaldo-pregunta2-previo-limpieza-20261016`](https://github.com/anahicz/Parcial_Robotica/tree/respaldo-pregunta2-previo-limpieza-20261016/Preguntas/Pregunta2) preserva el broker simulado, scripts, notebooks, tests y herramientas experimentales retirados de `main`. La **Pregunta 1** continúa en `Preguntas/Pregunta1`, con ROS 2, el intérprete de órdenes y LAYA, sin modificaciones por esta limpieza.
