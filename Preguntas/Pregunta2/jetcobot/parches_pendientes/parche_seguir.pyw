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

# ADVERTENCIA: devuelve éxito aunque no se alcance la posición y activa
# continue_on_error; no ejecutar sobre el robot sin corrección y validación.
# Archivo conservado como referencia; no aplicado a robot.py ni a config.json.

import sys, json
r = open('robot.py', encoding='utf-8').read()
if 'PARCHE_SEGUIR' in r:
    print('robot.py: ya estaba parcheado')
else:
    r += '''

# PARCHE_SEGUIR: si motion.continue_on_error es true, un movimiento que no llega NO detiene el ciclo.
# Antes de rendirse reintenta en modo articular (mode=0), que a veces alcanza poses que la
# trayectoria recta no. Los limites de seguridad (mesa, alcance, z max) SIGUEN deteniendo.
_send_coords_original = MyCoBot280.send_coords


def _send_coords_seguir(self, coords, speed, mode=1, config=None):
    ok = _send_coords_original(self, coords, speed, mode, config)
    if ok or not (config or {}).get('motion', {}).get('continue_on_error', False):
        return ok
    ws = (config or {}).get('motion', {}).get('workspace', {})
    x, y, z = coords[0], coords[1], coords[2]
    if ((x * x + y * y) ** 0.5 > ws.get('reach_max_mm', 280) or z < ws.get('z_min_mm', 90)
            or z > ws.get('z_max_mm', 400)):
        return False  # limite de seguridad: no se sigue
    if mode == 1:
        logger.warning("No llego en linea recta: reintento en modo articular")
        if _send_coords_original(self, coords, speed, 0, config):
            return True
    logger.warning("No llego a la posicion, pero SIGO (continue_on_error=true)")
    return True


MyCoBot280.send_coords = _send_coords_seguir
'''
    open('robot.py', 'w', encoding='utf-8').write(r)
    print('robot.py: sigue aunque un movimiento no llegue (con reintento articular)')
c = json.load(open('config.json', encoding='utf-8'))
if c['motion'].get('continue_on_error') is not True:
    c['motion']['continue_on_error'] = True
    json.dump(c, open('config.json', 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
print('config.json: continue_on_error =', c['motion']['continue_on_error'])