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
# Archivo: clasificador.py
# Descripción:
#   Clasificador de respaldo basado en palabras clave para la interpretación
#   de órdenes cuando el servidor LAYA no responde o supera el tiempo límite.
# ==============================================================================

def clasificar(frase):
    texto = frase.lower().strip()

    accion = 'otro'
    objeto = 'desconocido'
    color = 'desconocido'
    prioridad = 1
    permitido = True
    causa = ''

    # ---------------- ACCION ----------------
    if any(p in texto for p in ['recoge', 'recoger', 'agarra', 'agarrar', 'toma', 'tomar']):
        accion = 'recoger'
    elif any(p in texto for p in ['mueve', 'mover', 'lleva', 'llevar']):
        accion = 'mover'

    # ---------------- OBJETO ----------------
    objetos = ['cubo', 'bloque', 'pelota', 'cilindro']

    for obj in objetos:
        if obj in texto:
            objeto = obj
            break

    # ---------------- COLOR ----------------
    colores = ['rojo', 'azul', 'verde', 'amarillo']

    for col in colores:
        if col in texto:
            color = col
            break

    # ---------------- PRIORIDAD ----------------
    if any(p in texto for p in ['urgente', 'inmediatamente', 'máxima prioridad', 'maxima prioridad']):
        prioridad = 3
    elif any(p in texto for p in ['prioridad alta', 'rápido', 'rapido']):
        prioridad = 2
    else:
        prioridad = 1

    # ---------------- ORDENES NO PERMITIDAS ----------------
    prohibidas = [
        'golpea',
        'golpear',
        'rompe',
        'romper',
        'lanza',
        'lanzar'
    ]

    if any(p in texto for p in prohibidas):
        permitido = False
        causa = 'Orden no permitida'

    return {
        'accion': accion,
        'objeto': objeto,
        'color': color,
        'prioridad': prioridad,
        'permitido': permitido,
        'causa': causa
    }
