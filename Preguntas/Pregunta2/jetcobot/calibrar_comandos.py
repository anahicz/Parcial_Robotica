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

"""Calibracion camara->robot con el ROBOT moviendose (no a mano). Corrige la caida del brazo lejos de la base.

Uso:  python3 calibrar_comandos.py            (3 rondas x 4 cubos = 12 puntos)
      python3 calibrar_comandos.py --rondas 2
En cada cubo el robot va encima solo; vos lo corregis con comandos hasta que la pinza quede CENTRADA:
  x+3 x-3 y+3 y-3  (mm)    ok = guardar este punto    s = saltar este cubo    q = salir sin guardar nada
Se guarda la posicion COMANDADA, asi la calibracion incluye el desfase de la pinza y la caida del brazo.
Al final el desfase (grasp_offset_mm) vuelve a [0, 0], porque ya queda dentro de la calibracion.
"""
import json, sys, tempfile
import numpy as np, cv2
from robot import create_robot
from calibration import HomographyCalibrator
from vision import CameraCapture, ColorDetector
from pick_place import PickPlace

SIM = '--simular' in sys.argv
RONDAS = int(sys.argv[sys.argv.index('--rondas') + 1]) if '--rondas' in sys.argv else 3
c = json.load(open('config.json', encoding='utf-8'))
VEL = 15
robot = create_robot(SIM, c)
robot.power_on()
cal_vieja = HomographyCalibrator(c)
z = c['motion']['workspace']['z_min_mm'] + 40          # 4 cm sobre la mesa: se ve bien si esta centrada
H_sim = np.array([[0.0, -0.21, 282.0], [-0.13, 0.0, 247.0], [0, 0, 1]])

def ir_obs():
    if not robot.send_angles(c['poses']['observation']['angles'], VEL, config=c):
        sys.exit('No pude ir a OBSERVACION. No se guardo nada.')

def foto():
    if SIM:
        import random
        d = {k: (random.randint(140, 440), random.randint(80, 320), 1) for k in ('rojo', 'azul', 'amarillo', 'verde')}
        return d, None
    cam = CameraCapture(device=0, width=c['camera']['width'], height=c['camera']['height'], fps=c['camera']['fps'])
    f = cam.capture(); cam.release()
    if f is None:
        sys.exit('No pude leer la camara. No se guardo nada.')
    det = ColorDetector(c)
    return det.detect_all_colors(f), det

def estimar(u, v):
    if SIM:
        p = H_sim @ np.array([u, v, 1.0]); return p[0] / p[2] + 8, p[1] / p[2] - 6   # simula un error a corregir
    if cal_vieja.H is not None:
        return cal_vieja.pixel_to_robot(u, v)
    return 200.0, 0.0

pix, rob = [], []
for ronda in range(1, RONDAS + 1):
    if ronda > 1:
        input(f'\n>>> RONDA {ronda}: mueve los 4 cubos a OTRAS posiciones (incluye CERCA y LEJOS de la base). Enter... ')
    ir_obs()
    det, detector = foto()
    print(f'Ronda {ronda}: cubos vistos', {k: v[:2] for k, v in det.items()})
    pp = PickPlace(c, robot, None, detector, cal_vieja, tempfile.mktemp(suffix='.csv'), False)
    for color, (u, v, _) in det.items():
        x, y = estimar(u, v)
        rz = pp._rz_para(color) if cal_vieja.H is not None else c['motion'].get('grasp_rz_deg', 0)
        def ir():
            robot.send_coords([x, y, z, 180, 0, rz], VEL, config=c)
            print(f'  pinza en ({x:.1f}, {y:.1f})')
        print(f'\n{color.upper()} (pixel {u},{v}): voy encima...')
        ir()
        while True:
            if SIM:
                p = H_sim @ np.array([u, v, 1.0]); tx, ty = p[0] / p[2], p[1] / p[2]
                cmd = 'ok' if abs(x - tx) < 1.5 and abs(y - ty) < 1.5 else (('x-' if x > tx else 'x+') + '2' if abs(x - tx) >= 1.5 else ('y-' if y > ty else 'y+') + '2')
                print('>', cmd)
            else:
                cmd = input('> ').strip().lower().replace(' ', '')
            if cmd == 'q':
                ir_obs(); sys.exit('Salgo sin guardar nada.')
            if cmd == 's':
                break
            if cmd == 'ok':
                pix.append([u, v]); rob.append([x, y]); print(f'  punto {len(pix)} guardado'); break
            if len(cmd) >= 3 and cmd[0] in 'xy' and cmd[1] in '+-':
                try:
                    mm = float(cmd[2:])
                except ValueError:
                    print('  no entendi'); continue
                if mm > 20:
                    print('  maximo 20 mm por paso'); continue
                if cmd[0] == 'x': x += mm if cmd[1] == '+' else -mm
                else: y += mm if cmd[1] == '+' else -mm
                ir()
            else:
                print('  comandos: x+3 x-3 y+3 y-3 ok s q')
    ir_obs()

if len(pix) < 6:
    sys.exit(f'Solo {len(pix)} puntos; necesito al menos 6. No se guardo nada.')
H, _ = cv2.findHomography(np.float32(pix), np.float32(rob), 0)
if H is None:
    sys.exit('No se pudo calcular. No se guardo nada.')
pred = cv2.perspectiveTransform(np.float32(pix).reshape(-1, 1, 2), H).reshape(-1, 2)
err = np.linalg.norm(pred - np.float32(rob), axis=1)
print('\nError por punto (mm):', ' '.join(f'{e:.1f}' for e in err))
print(f'Error medio {err.mean():.1f} mm, maximo {err.max():.1f} mm  (bueno: medio < 4 mm)')
cal = HomographyCalibrator(c)
cal.pixel_points, cal.robot_points = pix, rob
cal.H = H; cal.H_inv = np.linalg.inv(H)
cal.save()
c['motion']['grasp_offset_mm'] = [0.0, 0.0]
json.dump(c, open('config.json', 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
print('LISTO: calibracion.json guardado con', len(pix), 'puntos; grasp_offset_mm vuelve a [0, 0].')
