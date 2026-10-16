import sys
r = open('pick_place.py', encoding='utf-8').read()
if 'PARCHE_LEVANTE' in r:
    print('pick_place.py: ya estaba parcheado')
else:
    v = ("        if not self.robot.send_coords(lift_coords, self.config['motion']['default_speed'], config=self.config):\n"
         "            self.logger.error(\"Error levantando objeto\")\n")
    n = ("        # PARCHE_LEVANTE: con el cubo agarrado y lejos de la base el brazo cae unos mm;\n"
         "        # subir es un movimiento en el aire, asi que usa la tolerancia de transito.\n"
         "        cfg_levante = copy.deepcopy(self.config)\n"
         "        tol_lev = self.config['motion'].get('transit_tolerance_mm', 20)\n"
         "        cfg_levante['motion']['tolerance_coords_mm'] = tol_lev\n"
         "        cfg_levante['motion']['tolerance_z_mm'] = tol_lev\n"
         "        if not self.robot.send_coords(lift_coords, self.config['motion']['default_speed'], config=cfg_levante):\n"
         "            self.logger.error(\"Error levantando objeto\")\n")
    if r.count(v) != 1:
        sys.exit('pick_place.py: no encontre la linea esperada; no toque nada')
    if 'import copy' not in r:
        sys.exit('pick_place.py: falta import copy; no toque nada')
    open('pick_place.py', 'w', encoding='utf-8').write(r.replace(v, n))
    print('pick_place.py: levantar usa tolerancia de transito (20 mm)')
