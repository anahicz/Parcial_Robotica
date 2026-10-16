"""Mide la mesa y calibra camara->robot desde la TERMINAL (sin ventanas graficas).

Uso:  python3 calibrar_terminal.py            (robot real; el brazo debe estar en OBSERVACION)
      python3 calibrar_terminal.py --simular  (prueba sin hardware)
"""
import json, sys
from robot import create_robot
from calibration import HomographyCalibrator
from vision import CameraCapture, ColorDetector

SIM = '--simular' in sys.argv
c = json.load(open('config.json', encoding='utf-8'))
robot = create_robot(SIM, c)
robot.power_on()

def esperar(msg):
    input(f'\n>>> {msg}\n    Presiona Enter cuando este listo (Ctrl+C cancela)... ')

def leer_coords():
    co = robot.get_coords()
    robot.power_on()                     # vuelve a trabar los servos
    if not co:
        sys.exit('No pude leer la posicion del robot. No se guardo nada.')
    return co

# 1) Foto de referencia en OBSERVACION
if SIM:
    det = {'rojo': (434, 294, 1), 'azul': (409, 92, 1), 'amarillo': (162, 102, 1), 'verde': (175, 312, 1)}
else:
    cam = CameraCapture(device=0, width=c['camera']['width'], height=c['camera']['height'], fps=c['camera']['fps'])
    frame = cam.capture(); cam.release()
    if frame is None:
        sys.exit('No pude leer la camara.')
    det = ColorDetector(c, debug=False).detect_all_colors(frame)
print('Cubos vistos desde OBSERVACION:', {k: v[:2] for k, v in det.items()})
if len(det) < 4:
    sys.exit('Necesito ver los 4 cubos. Revisa la mesa y vuelve a intentar. No se guardo nada.')
print('*** NO muevas los cubos desde ahora hasta terminar. ***')

# 2) Altura de la mesa
esperar('MESA: voy a SOLTAR los servos. SOSTEN el brazo (cae).')
robot.release_all_servos()
esperar('Baja la pinza, apuntando recto hacia abajo, hasta que TOQUE apenas la mesa (en una zona libre).')
z_mesa = round(leer_coords()[2], 1)
if SIM:
    z_mesa = 100.0
print(f'    Mesa medida: z = {z_mesa} mm')

# 3) Un punto por cubo
cal = HomographyCalibrator(c)
cal.pixel_points, cal.robot_points = [], []
sim_xy = iter([(150, -60), (150, 60), (230, 60), (230, -60)])
for color, (u, v, _) in det.items():
    esperar(f'{color.upper()}: voy a SOLTAR los servos. SOSTEN el brazo.')
    robot.release_all_servos()
    esperar(f'Pon la pinza recta hacia abajo, JUSTO ENCIMA del centro del cubo {color} (sin tocarlo).')
    x, y = next(sim_xy) if SIM else leer_coords()[:2]
    cal.add_point((u, v), (x, y))
    print(f'    {color}: pixel ({u},{v}) -> robot ({x:.1f}, {y:.1f}) mm')

# 4) Calcular y guardar
if not cal.compute_homography():
    sys.exit('No se pudo calcular (puntos alineados o repetidos). No se guardo nada.')
err = cal._compute_reprojection_error()
cal.save()
c['motion']['workspace']['z_min_mm'] = z_mesa
json.dump(c, open('config.json', 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
print(f'\nLISTO. calibracion.json guardado (error {err:.1f} px).')
print('OJO: con exactamente 4 puntos el error SIEMPRE da 0; no prueba precision. Verifica en la aproximacion del primer color.')
print(f'config.json: z_min_mm = {z_mesa}')
print('Siguiente: prueba un color (el programa lleva solo el brazo a HOME y OBSERVACION):')
print('  python3 pick_place.py --color rojo --paso-a-paso --velocidad 15')
