"""Lleva la pinza a 8 cm SOBRE un cubo, ALINEADA con el giro del cubo, y se QUEDA ahi (no baja ni agarra).

Uso:  python3 probar_aproximacion.py rojo          (giro automatico: base + giro del cubo)
      python3 probar_aproximacion.py rojo -30      (fuerza un rz manual, para comparar)
Mira si la pinza queda centrada y con los dedos paralelos a las caras del cubo.
"""
import json, sys, tempfile
from robot import create_robot
from calibration import HomographyCalibrator
from vision import CameraCapture, ColorDetector
from pick_place import PickPlace

color = sys.argv[1] if len(sys.argv) > 1 else 'rojo'
manual = next((float(a) for a in sys.argv[2:] if a.lstrip('-').replace('.', '', 1).isdigit()), None)
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
x, y = cal.pixel_to_robot(u, v)
pp = PickPlace(c, robot, None, det, cal, tempfile.mktemp(suffix='.csv'), False)
rz = manual if manual is not None else pp._rz_para(color)
z = c['motion']['workspace']['z_min_mm'] + c['motion']['approach_height_mm']
print(f'{color}: pixel ({u},{v}) -> robot ({x:.1f}, {y:.1f}); voy a z={z:.1f} con rz={rz:.1f}' + (' (MANUAL)' if manual is not None else ' (automatico)'))
ok = robot.send_coords([x, y, z, 180, 0, rz], vel, config=c)
print('Llegue. MIRA la pinza:' if ok else 'No llegue dentro de tolerancia (igual mira donde quedo):')
print('  - centrada sobre el cubo?  - dedos paralelos a las caras?')
print('Coords reales:', robot.get_coords())
