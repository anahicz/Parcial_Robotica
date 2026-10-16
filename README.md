# Parcial Robótica — Gran Reto JetCobot

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

Repositorio del equipo para el Examen Parcial de Robótica S-003, organizado por preguntas.

## Estado general

| Pregunta | Contenido | Estado documentado |
| --- | --- | --- |
| [Pregunta 1](Preguntas/Pregunta1/README.md) | ROS 2 Humble, intérprete `/interpretar_orden`, LAYA, clasificador local de respaldo y evidencias de 50 frases. | Conservada; pendiente medición bajo carga. |
| [Pregunta 2](Preguntas/Pregunta2/README.md) | Núcleo independiente de `pick_place.py` con `robot.py`, `vision.py`, `calibration.py`. | Limpieza de dependencias completada; integración ROS 2/LAYA y parches nuevos pendientes. |
| [Pregunta 3](Preguntas/Pregunta3/README.md) | Área reservada para la Pregunta 3. | Sin cambios. |

## Estructura principal

```text
Parcial_Robotica/
├── Preguntas/
│   ├── Pregunta1/
│   │   ├── src/
│   │   ├── evidencias/
│   │   ├── scripts/
│   │   └── README.md
│   ├── Pregunta2/
│   │   ├── jetcobot/
│   │   │   ├── pick_place.py
│   │   │   ├── robot.py
│   │   │   ├── vision.py
│   │   │   ├── calibration.py
│   │   │   ├── config_ejemplo.json
│   │   │   ├── .gitignore
│   │   │   └── README.md
│   │   └── README.md
│   └── Pregunta3/
│       └── README.md
└── .gitignore
```

## Importante

La Pregunta 2 se depuró para dejar solo lo usado directamente por el ejecutable `pick_place.py`, junto con documentación y plantilla de configuración. **Aún no están disponibles** los archivos pedidos `parche_altura_deposito.py` y `parche_seguir.py`. La implementación anterior completa está preservada en la [rama de respaldo](../../tree/respaldo-pregunta2-previo-limpieza-20261016). La Pregunta 1 no se ha modificado.

No publicar `config.json`, `calibracion.json`, credenciales ni logs locales. Los resultados de simulación no certifican movimiento físico.
