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

"""Mide el desfase entre donde apunta la camara y donde queda la pinza. Se hace UNA vez.

Uso:  python3 medir_offset.py rojo
El brazo va 8 cm sobre el cubo (alineado con su giro) y se queda. Vos lo corregis con comandos:
  x+3  x-3  y+3  y-3   (milimetros; x = hacia adelante, lejos de la base; y = hacia la izquierda del robot)
  ok   guarda el desfase       q   sale sin guardar
"""
import json, sys, tempfile
from robot import create_robot
from calibration import HomographyCalibrator
from vision import CameraCapture, ColorDetector
from pick_place import PickPlace

color = sys.argv[1] if len(sys.argv) > 1 else 'rojo'
SIM = '--simular' in sys.argv
c = json.load(open('config.json', encoding='utf-8'))
vel = 15
robot = create_robot(SIM, c)
robot.power_on()
cal = HomographyCalibrator(c)
if cal.H is None:
    sys.exit('Falta calibracion')
for pose in ('home', 'observation'):
    if not robot.send_angles(c['poses'][pose]['angles'], vel, config=c):
        sys.exit(f'Fallo yendo a {pose}; me detengo')
det = None
if SIM:
    d = {color: (426, 298, 1)}
else:
    cam = CameraCapture(device=0, width=c['camera']['width'], height=c['camera']['height'], fps=c['camera']['fps'])
    f = cam.capture(); cam.release()
    det = ColorDetector(c)
    d = det.detect_all_colors(f) if f is not None else {}
if color not in d:
    sys.exit(f'{color} no detectado: {list(d)}')
u, v, _ = d[color]
x0, y0 = cal.pixel_to_robot(u, v)          # donde la camara dice que esta el cubo (SIN desfase)
pp = PickPlace(c, robot, None, det, cal, tempfile.mktemp(suffix='.csv'), False)
rz = pp._rz_para(color)
z = c['motion']['workspace']['z_min_mm'] + c['motion']['approach_height_mm']
x, y = x0, y0
def ir():
    ok = robot.send_coords([x, y, z, 180, 0, rz], vel, config=c)
    print(f'  pinza en ({x:.1f}, {y:.1f}) z={z:.1f} rz={rz:.1f}  desfase actual ({x - x0:+.1f}, {y - y0:+.1f})' + ('' if ok else '  [fuera de tolerancia, mira donde quedo]'))
print(f'{color}: la camara lo ve en ({x0:.1f}, {y0:.1f}). Voy encima SIN desfase...')
ir()
print('Corregi hasta que la pinza quede CENTRADA sobre el cubo. Comandos: x+3 x-3 y+3 y-3 ok q')
while True:
    cmd = input('> ').strip().lower().replace(' ', '')
    if cmd == 'q':
        sys.exit('Salgo sin guardar')
    if cmd == 'ok':
        break
    if len(cmd) >= 3 and cmd[0] in 'xy' and cmd[1] in '+-':
        try:
            mm = float(cmd[2:])
        except ValueError:
            print('  no entendi'); continue
        if mm > 20:
            print('  maximo 20 mm por paso'); continue
        if cmd[0] == 'x': x += mm if cmd[1] == '+' else -mm
        else: y += mm if cmd[1] == '+' else -mm
        if abs(x - x0) > 40 or abs(y - y0) > 40:
            print('  desfase mayor a 4 cm: revisa la calibracion antes de seguir'); x, y = min(max(x, x0 - 40), x0 + 40), min(max(y, y0 - 40), y0 + 40)
        ir()
    else:
        print('  comandos: x+3 x-3 y+3 y-3 ok q')
c['motion']['grasp_offset_mm'] = [round(x - x0, 1), round(y - y0, 1)]
c['motion']['grasp_offset_ref_rz'] = round(rz, 1)
json.dump(c, open('config.json', 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
print(f"Guardado: grasp_offset_mm = {c['motion']['grasp_offset_mm']} con giro de referencia {c['motion']['grasp_offset_ref_rz']}")
