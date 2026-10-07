# ==============================================================================
# UNIVERSIDAD ESAN
# ROBÓTICA 08079
# EXAMEN PARCIAL - GRAN RETO JETCOBOT
# Grupo 7
#
# Integrantes:
#   - Sebastian Pedro Aguirre Acosta
#   - Anahi Cortez Chinchay
#   - Ramirez Quevedo Karen Noelia
#   - Vara Vargas Valentino Uziel
#
# Archivo: laya_client.py
# Descripción:
#   Cliente HTTP para consultar al servidor LAYA y convertir una frase en una
#   decisión tipada para el sistema robótico.
# ==============================================================================

import json
import time
import urllib.request


def consultar_laya(frase, base_url, timeout_s):
    """
    Consulta LAYA mediante POST /v1/systemone.

    Devuelve:
        accion
        objeto
        color
        prioridad
        permitido
        latencia_total_ms
        tiempo_servidor_ms
        tiempo_red_estimado_ms
    """

    preguntas = {
        'accion': {
            'type': 'choice',
            'instructions': '¿Qué acción solicita el operador al robot?',
            'criteria': {
                'recoger': 'tomar o agarrar un objeto',
                'mover': 'mover o trasladar un objeto',
                'soltar': 'soltar o dejar un objeto',
                'otro': 'cualquier otra acción'
            }
        },

        'objeto': {
            'type': 'choice',
            'instructions': '¿Qué objeto menciona la orden?',
            'criteria': {
                'cubo': 'objeto con forma de cubo',
                'bloque': 'bloque u objeto similar',
                'pelota': 'objeto esférico o pelota',
                'cilindro': 'objeto cilíndrico',
                'otro': 'otro objeto o no identificable'
            }
        },

        'color': {
            'type': 'choice',
            'instructions': '¿Qué color menciona la orden?',
            'criteria': {
                'rojo': 'color rojo',
                'azul': 'color azul',
                'verde': 'color verde',
                'amarillo': 'color amarillo',
                'otro': 'otro color o color no especificado'
            }
        },

        'urgencia_maxima': {
            'type': 'choice',
            'instructions': (
                'Indica si la orden expresa explícitamente urgencia máxima.'
            ),
            'criteria': {
                'si': (
                    'La frase contiene una expresión explícita como urgente, '
                    'inmediatamente, emergencia o máxima prioridad.'
                ),
                'no': (
                    'La frase no expresa explícitamente urgencia máxima.'
                )
            }
        },

        'rapidez': {
            'type': 'choice',
            'instructions': (
                'Indica si la orden expresa explícitamente que debe realizarse rápido.'
            ),
            'criteria': {
                'si': (
                    'La frase contiene una expresión explícita como rápido, '
                    'rápidamente o pronto.'
                ),
                'no': (
                    'La frase no contiene una expresión explícita de rapidez.'
                )
            }
        },

        'permitido': {
            'type': 'choice',
            'instructions': (
                'Clasifica la orden según la política de seguridad del robot.'
            ),
            'criteria': {
                'permitida': (
                    'Orden normal y segura de manipulación de objetos, '
                    'como recoger, mover, llevar o soltar un objeto.'
                ),
                'prohibida': (
                    'Orden que solicita golpear, romper, lanzar, dañar '
                    'o realizar una acción peligrosa.'
                )
            }
        }
    }

    payload = {
        'state': frase,
        'lang': 'es',
        'questions': preguntas
    }

    datos = json.dumps(payload).encode('utf-8')

    url = base_url.rstrip('/') + '/v1/systemone'

    request = urllib.request.Request(
        url,
        data=datos,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )

    inicio = time.perf_counter()

    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        contenido = response.read().decode('utf-8')
        latencia_total_ms = (time.perf_counter() - inicio) * 1000.0

        header_inferencia = response.headers.get('X-Inference-Time-Ms')

    respuesta = json.loads(contenido)
    answers = respuesta['answers']

    accion = answers['accion']['choice']
    objeto = answers['objeto']['choice']
    color = answers['color']['choice']
    decision_urgencia = answers['urgencia_maxima']['choice']
    decision_rapidez = answers['rapidez']['choice']

    # La prioridad proviene de las decisiones tipadas de LAYA.
    # Python únicamente convierte esas clases al entero usado por el broker.
    if decision_urgencia == 'si':
        prioridad = 3
    elif decision_rapidez == 'si':
        prioridad = 2
    else:
        prioridad = 1

    # LAYA devuelve una decisión tipada: permitida o prohibida.
    decision_permitido = answers['permitido']['choice']
    permitido = decision_permitido == 'permitida'

    # Guardamos también la probabilidad asignada a "permitida"
    # para posteriores mediciones y análisis.
    probabilidades_permitido = answers['permitido'].get('probabilities', {})
    prob_permitido = float(
        probabilidades_permitido.get('permitida', 0.0)
    )

    tiempo_servidor_ms = None

    if header_inferencia is not None:
        try:
            tiempo_servidor_ms = float(header_inferencia)
        except ValueError:
            tiempo_servidor_ms = None

    tiempo_red_estimado_ms = None

    if tiempo_servidor_ms is not None:
        tiempo_red_estimado_ms = max(
            0.0,
            latencia_total_ms - tiempo_servidor_ms
        )

    return {
        'accion': accion,
        'objeto': objeto,
        'color': color,
        'prioridad': prioridad,
        'permitido': permitido,
        'prob_permitido': prob_permitido,
        'latencia_total_ms': latencia_total_ms,
        'tiempo_servidor_ms': tiempo_servidor_ms,
        'tiempo_red_estimado_ms': tiempo_red_estimado_ms
    }
