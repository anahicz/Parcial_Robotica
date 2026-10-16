"""Calibracion camara->robot con VARIAS rondas (mas puntos = mas precision).

Uso:  python3 calibrar_rondas.py            (3 rondas x 4 cubos = 12 puntos)
      python3 calibrar_rondas.py --rondas 4
      python3 calibrar_rondas.py --simular
La altura de mesa (z_min_mm) NO se toca: se usa la que ya mediste.
"""
import json, sys
import numpy as np, cv2
from robot import create_robot
from calibration import HomographyCalibrator
from vision import CameraCapture, ColorDetector

SIM = '--simular' in sys.argv
RONDAS = int(sys.argv[sys.argv.index('--rondas') + 1]) if '--rondas' in sys.argv else 3
c = json.load(open('config.json', encoding='utf-8'))
robot = create_robot(SIM, c)
robot.power_on()
VEL = 15

def esperar(msg):
    input(f'\n>>> {msg}\n    Enter cuando este listo (Ctrl+C cancela, no se guarda nada)... ')

def ir_a_observacion():
    if not robot.send_angles(c['poses']['observation']['angles'], VEL, config=c):
        sys.exit('No pude ir a OBSERVACION. No se guardo nada.')

def foto():
    if SIM:
        import random
        return {k: (random.randint(140, 440), random.randint(80, 320), 1) for k in ('rojo', 'azul', 'amarillo', 'verde')}
    cam = CameraCapture(device=0, width=c['camera']['width'], height=c['camera']['height'], fps=c['camera']['fps'])
    f = cam.capture(); cam.release()
    if f is None:
        sys.exit('No pude leer la camara. No se guardo nada.')
    return ColorDetector(c).detect_all_colors(f)

pix, rob = [], []
H_sim = np.array([[0.0, -0.21, 282.0], [-0.13, 0.0, 247.0], [0, 0, 1]])   # solo para --simular
for ronda in range(1, RONDAS + 1):
    if ronda > 1:
        esperar(f'RONDA {ronda}: mueve los 4 cubos a OTRAS posiciones (repartidos, incluidas las orillas de lo que ve la camara)')
    ir_a_observacion()
    det = foto()
    print(f'Ronda {ronda}: cubos vistos', {k: v[:2] for k, v in det.items()})
    if len(det) < 2:
        print('  Veo menos de 2 cubos en esta ronda; la salteo.'); continue
    for color, (u, v, _) in det.items():
        esperar(f'{color.upper()}: suelto los servos. SOSTEN el brazo.')
        robot.release_all_servos()
        esperar(f'Pinza RECTA hacia abajo (vertical, mirala de frente y de costado), JUSTO encima del centro del cubo {color}.')
        if SIM:
            p = H_sim @ np.array([u, v, 1.0]); x, y = p[0] / p[2] + np.random.normal(0, 2), p[1] / p[2] + np.random.normal(0, 2)
        else:
            co = robot.get_coords(); robot.power_on()
            if not co:
                sys.exit('No pude leer la posicion. No se guardo nada.')
            x, y = co[0], co[1]
        pix.append([u, v]); rob.append([x, y])
        print(f'    punto {len(pix)}: pixel ({u},{v}) -> robot ({x:.1f}, {y:.1f})')
    ir_a_observacion()   # sube y vuelve antes de la proxima ronda

if len(pix) < 6:
    sys.exit(f'Solo {len(pix)} puntos; necesito al menos 6. No se guardo nada.')
H, _ = cv2.findHomography(np.float32(pix), np.float32(rob), 0)   # minimos cuadrados con TODOS los puntos
if H is None:
    sys.exit('No se pudo calcular. No se guardo nada.')
pred = cv2.perspectiveTransform(np.float32(pix).reshape(-1, 1, 2), H).reshape(-1, 2)
err = np.linalg.norm(pred - np.float32(rob), axis=1)
print('\nError por punto (mm):', ' '.join(f'{e:.1f}' for e in err))
print(f'Error medio {err.mean():.1f} mm, maximo {err.max():.1f} mm  (bueno: medio < 5 mm)')
peor = int(err.argmax())
if err.max() > 3 * max(err.mean(), 1):
    print(f'OJO: el punto {peor + 1} parece mal tomado (pinza inclinada o corrida). Si querés, repetí la calibracion.')
cal = HomographyCalibrator(c)
cal.pixel_points, cal.robot_points = pix, rob
cal.H = H; cal.H_inv = np.linalg.inv(H)
cal.save()
print('LISTO: calibracion.json guardado con', len(pix), 'puntos.')
