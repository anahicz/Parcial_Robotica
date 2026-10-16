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
| [Pregunta 1](Preguntas/Pregunta1/README.md) | ROS 2 Humble, servicio `/interpretar_orden`, LAYA con clasificador local de respaldo, broker reutilizado, 50 frases y resultados en calma. | Implementación y evidencias parciales; pendiente medición bajo carga. |
| [Pregunta 2](Preguntas/Pregunta2/README.md) | Base de cliente de visión, broker de simulación y trabajo adicional de JetCobot con visión, homografía y pick-and-place por colores. | Integración parcial; pruebas de software no equivalen a validación física ni conexión final con LAYA. |
| [Pregunta 3](Preguntas/Pregunta3/README.md) | Área reservada para los entregables de la Pregunta 3. | Sin entregables adicionales confirmados. |

## Organización

```text
Parcial_Robotica/
├── Preguntas/
│   ├── Pregunta1/
│   │   ├── src/              # Paquetes ROS 2 e interfaces
│   │   ├── evidencias/       # CSV y resultados
│   │   ├── scripts/
│   │   └── README.md
│   ├── Pregunta2/
│   │   ├── src/              # ROS 2 P2 y broker simulado existente
│   │   ├── scripts/
│   │   ├── jetcobot/         # Fuentes adicionales incorporadas desde el ZIP
│   │   └── README.md
│   └── Pregunta3/
│       └── README.md
└── .gitignore
```

## Importante

La **Pregunta 1 se conserva sin modificaciones**. Las dos implementaciones de la Pregunta 2 (ROS 2 preexistente y módulo autónomo del ZIP) no son intercambiables y todavía necesitan integración. No publicar archivos locales `config.json`, `calibracion.json`, credenciales ni registros temporales de ejecución.

Para requisitos, pasos de prueba y limitaciones, consultar el README individual de cada pregunta.
