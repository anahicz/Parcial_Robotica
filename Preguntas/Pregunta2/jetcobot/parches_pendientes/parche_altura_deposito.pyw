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

# PENDIENTE DE REVISION: la búsqueda x * k / y * k no coincide con el código actual.
# Archivo conservado como referencia; no aplicado a pick_place.py.

import sys
r = open('pick_place.py', encoding='utf-8').read()
if 'PARCHE_ALTURA_DEP' in r:
    print('pick_place.py: ya estaba parcheado')
    sys.exit()
cambios = [
    ("        for nombre, pt in ((\"subiendo a altura de tránsito\", [x * k, y * k, z_transito, 180, 0, rz_agarre]),\n"
     "                           (\"tránsito sobre el depósito\", [deposit_coords[0], deposit_coords[1], z_transito,\n",
     "        # PARCHE_ALTURA_DEP: lejos de la base el brazo no llega alto (mapa de alcance estimado (16-oct):\n"
     "        # hasta 235 mm llega a z=233; 250->213; 260->193; 272->173). Sobre el deposito se va a la\n"
     "        # altura mas alta que alcanza a esa distancia, siempre por encima del punto donde suelta.\n"
     "        tabla = self.config['motion'].get('transit_reach_table_mm',\n"
     "                                          [[235, 233], [250, 213], [260, 193], [272, 173]])\n"
     "        r_dep = (deposit_coords[0] ** 2 + deposit_coords[1] ** 2) ** 0.5\n"
     "        z_lim = next((zz for rr, zz in tabla if r_dep <= rr), tabla[-1][1])\n"
     "        z_dep_t = max(min(z_transito, z_lim), deposit_coords[2] + 20)\n"
     "        if z_dep_t < z_transito:\n"
     "            self.logger.info(f\"Deposito a {r_dep:.0f} mm de la base: transito sobre el a z={z_dep_t:.0f}\")\n"
     "        for nombre, pt in ((\"subiendo a altura de tránsito\", [x * k, y * k, z_transito, 180, 0, rz_agarre]),\n"
     "                           (\"tránsito sobre el depósito\", [deposit_coords[0], deposit_coords[1], z_dep_t,\n"),
    ("            self.logger.info(f\"Moviendo: {nombre} (z={z_transito:.1f})\")\n",
     "            self.logger.info(f\"Moviendo: {nombre} (z={pt[2]:.1f})\")\n"),
    ("        z_safe = max(z_approach + 30, z_transito)\n",
     "        z_safe = min(max(z_approach + 30, z_transito), z_dep_t)\n"),
]
for v, n in cambios:
    if r.count(v) != 1:
        sys.exit('pick_place.py: no encontre una linea esperada; no toque nada')
for v, n in cambios:
    r = r.replace(v, n)
open('pick_place.py', 'w', encoding='utf-8').write(r)
print('pick_place.py: transito sobre el deposito a la altura que alcanza segun la distancia')