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

"""Re-ajusta calibracion.json SIN mover el robot: descarta puntos mal tomados y usa un modelo afin.

Uso:  python3 ajustar_calibracion.py
Guarda una copia del original en calibracion.json.antes antes de escribir.
"""
import json, shutil
import numpy as np

d = json.load(open('calibracion.json', encoding='utf-8'))
P = np.float64(d['pixel_points']); R = np.float64(d['robot_points'])

def ajustar(idx):
    A = np.c_[P[idx], np.ones(len(idx))]
    C, *_ = np.linalg.lstsq(A, R[idx], rcond=None)    # x,y = a*u + b*v + c
    return C

def loo(idx):
    e = {}
    for i in idx:
        C = ajustar([j for j in idx if j != i])
        e[i] = float(np.linalg.norm(np.r_[P[i], 1] @ C - R[i]))
    return e

idx = list(range(len(P)))
descartados = []
while len(idx) > 6:
    e = loo(idx)
    peor = max(e, key=e.get)
    med = float(np.median(list(e.values())))
    if e[peor] > max(15.0, 3 * med):
        descartados.append((peor + 1, round(e[peor], 1))); idx.remove(peor)
    else:
        break
e = loo(idx)
print('Puntos descartados (numero, error mm):', descartados or 'ninguno')
print(f'Error de prediccion (cada punto con un modelo que NO lo uso): medio {np.mean(list(e.values())):.1f} mm, maximo {max(e.values()):.1f} mm')
C = ajustar(idx)
H = np.array([[C[0, 0], C[1, 0], C[2, 0]], [C[0, 1], C[1, 1], C[2, 1]], [0.0, 0.0, 1.0]])
shutil.copyfile('calibracion.json', 'calibracion.json.antes')
d['H_matrix'] = H.tolist()
d['pixel_points'] = [d['pixel_points'][i] for i in idx]
d['robot_points'] = [d['robot_points'][i] for i in idx]
json.dump(d, open('calibracion.json', 'w', encoding='utf-8'), indent=2)
print('LISTO: calibracion.json con', len(idx), 'puntos (original en calibracion.json.antes).')
