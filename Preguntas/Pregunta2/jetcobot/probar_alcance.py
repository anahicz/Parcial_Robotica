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

"""Prueba a qué alturas acepta ir el brazo sobre un punto de la mesa (SIN cubo en la pinza).

Uso:  python3 probar_alcance.py                 (por defecto: donde estaba el azul)
      python3 probar_alcance.py 241 -39 -49     (x y rz)
Se mueve sólo en el aire: primero a z=193 sobre el punto, después sube de a 10 mm.
"""
import sys, time, json
try:
    from pymycobot.mycobot280 import MyCobot280 as MC
except ImportError:
    from pymycobot.mycobot import MyCobot as MC

x, y, rz = (float(a) for a in sys.argv[1:4]) if len(sys.argv) >= 4 else (241.0, -38.8, -49.0)
port = json.load(open('config.json')).get('robot', {}).get('serial_port', '/dev/ttyUSB0')
mc = MC(port, 1000000)
time.sleep(0.5)

def ir(z, rot=(180, 0)):
    antes = mc.get_coords()
    mc.send_coords([x, y, z, rot[0], rot[1], rz], 15, 1)
    t = time.time(); movio = False
    while time.time() - t < 3:
        if mc.is_moving() == 1:
            movio = True; break
        time.sleep(0.05)
    while time.time() - t < 12 and mc.is_moving() == 1:
        time.sleep(0.1)
    time.sleep(0.5)
    ahora = mc.get_coords()
    dz = round(ahora[2] - z, 1) if ahora else None
    print(f'z={z:5.0f}  se movio={"SI" if movio else "NO"}  llego a z={ahora[2] if ahora else "?"}  (dz={dz})')
    return movio

print(f'Punto x={x} y={y} rz={rz}  (distancia a la base {(x*x+y*y)**0.5:.0f} mm)')
ir(193)
for z in (203, 213, 223, 233, 243):
    ir(z)
print('Listo. Copiame todo lo que salio arriba.')
