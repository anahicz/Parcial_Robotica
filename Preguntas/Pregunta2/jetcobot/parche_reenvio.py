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

import sys
r = open('robot.py', encoding='utf-8').read()
if 'PARCHE_REENVIO' in r:
    print('robot.py: ya estaba parcheado')
else:
    v = ("                    logger.info(f\"Ya en posición destino: dx,dy,dz={ejes}\")\n"
         "                    return True\n"
         "\n"
         "            if not pose_started:\n"
         "                logger.info(f\"Movimiento no detectado en {start_window}s, esperando...\")\n"
         "\n"
         "            # Fase 2: Espera a que se termine el movimiento\n")
    n = ("                    logger.info(f\"Ya en posición destino: dx,dy,dz={ejes}\")\n"
         "                    return True\n"
         "\n"
         "            if not pose_started:\n"
         "                # PARCHE_REENVIO: el myCobot a veces descarta una orden que llega justo despues\n"
         "                # de otra (por ejemplo, abrir la pinza). Si no arranco, se reenvia UNA vez.\n"
         "                logger.warning(f\"Movimiento no detectado en {start_window}s: reenvio la orden una vez\")\n"
         "                time.sleep(0.3)\n"
         "                self.robot.send_coords(coords, speed, mode)\n"
         "                t1 = time.time()\n"
         "                while time.time() - t1 < start_window:\n"
         "                    if self.is_moving():\n"
         "                        pose_started = True\n"
         "                        break\n"
         "                    time.sleep(0.05)\n"
         "                start_time = time.time()\n"
         "\n"
         "            # Fase 2: Espera a que se termine el movimiento\n")
    if r.count(v) != 1:
        sys.exit('robot.py: no encontre la linea esperada (falta parche_tolerancia2?); no toque nada')
    open('robot.py', 'w', encoding='utf-8').write(r.replace(v, n))
    print('robot.py: reenvia una vez la orden si el brazo no arranca')
