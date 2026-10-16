#!/usr/bin/env python3
"""
Orquestador principal para el robot JetCobot.
Flujo: HOME -> OBSERVATION -> detección -> recogida y depósito de cubos.
"""
import json
import copy
import logging
import csv
import argparse
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import os

from robot import create_robot, RobotAdapter, SimRobot
from vision import CameraCapture, ColorDetector, capture_and_detect
from calibration import HomographyCalibrator, CalibrationUI


def setup_logging(log_dir: str = 'logs') -> logging.Logger:
    """Configura logging a archivo y consola."""
    os.makedirs(log_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(log_dir, f'run_{timestamp}.log')
    csv_file = os.path.join(log_dir, f'run_{timestamp}.csv')

    # Logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Handler de archivo
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)

    # Handler de consola
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    # Formato
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(name)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.info(f"Logging en {log_file}")
    logger.info(f"CSV en {csv_file}")

    return logger, csv_file


class PickPlace:
    """Controlador principal del flujo de recogida y depósito."""

    def __init__(self, config: dict, robot: RobotAdapter, camera: Optional[CameraCapture],
                 detector: Optional[ColorDetector], calibrator: HomographyCalibrator,
                 csv_file: str, step_by_step: bool = False):
        """Inicializa el controlador.

        Args:
            config: diccionario de configuración
            robot: instancia del robot
            camera: instancia de cámara (None en modo simulado puro)
            detector: detector de colores (None en modo simulado puro)
            calibrator: calibrador de homografía
            csv_file: archivo CSV para logging
            step_by_step: si True, espera Enter entre movimientos
        """
        self.config = config
        self.robot = robot
        self.camera = camera
        self.detector = detector
        self.calibrator = calibrator
        self.csv_file = csv_file
        self.step_by_step = step_by_step
        self.logger = logging.getLogger(__name__)

        self.csv_writer = None
        self._init_csv()

    def _init_csv(self):
        """Inicializa el archivo CSV de logging."""
        try:
            with open(self.csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                headers = [
                    'timestamp', 'accion', 'angulos_comandados', 'angulos_leidos',
                    'coords_comandadas', 'coords_leidas', 'color_detectado',
                    'pixel_uv', 'estado'
                ]
                writer.writerow(headers)
            self.logger.info(f"CSV inicializado: {self.csv_file}")
        except Exception as e:
            self.logger.error(f"Error al inicializar CSV: {e}")

    def _log_motion(self, action: str, commanded_angles: Optional[List[float]] = None,
                   commanded_coords: Optional[List[float]] = None,
                   color: Optional[str] = None, pixel_uv: Optional[Tuple[int, int]] = None,
                   status: str = "OK"):
        """Registra una acción en CSV."""
        try:
            read_angles = self.robot.get_angles()
            read_coords = self.robot.get_coords()

            row = [
                datetime.now().isoformat(),
                action,
                commanded_angles,
                read_angles,
                commanded_coords,
                read_coords,
                color,
                pixel_uv,
                status
            ]

            with open(self.csv_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(row)
        except Exception as e:
            self.logger.error(f"Error al registrar en CSV: {e}")

    def _wait_step(self, message: str = ""):
        """Si step_by_step, espera Enter."""
        if self.step_by_step:
            if message:
                self.logger.info(message)
            input("Presiona Enter para continuar...")

    def power_on(self) -> bool:
        """Enciende el robot."""
        self.logger.info("Encendiendo robot...")
        if self.robot.power_on():
            self.logger.info("Robot encendido")
            return True
        else:
            self.logger.error("Error al encender robot")
            return False

    def go_to_pose(self, pose_name: str, use_angles: bool = True) -> bool:
        """Va a una posición preconfigurada.

        Args:
            pose_name: nombre de la posición (ej. 'home', 'observation')
            use_angles: si True usa ángulos, si False usa coords

        Returns:
            True si se alcanzó la posición
        """
        if pose_name not in self.config['poses']:
            self.logger.error(f"Posición {pose_name} no definida")
            return False

        pose = self.config['poses'][pose_name]
        speed = self.config['motion']['default_speed']

        if use_angles:
            angles = pose['angles']
            self.logger.info(f"Moviendo a {pose_name}: {angles}")
            self._wait_step(f"Movimiento: {pose_name}")

            if self.robot.send_angles(angles, speed, self.config):
                self._log_motion(f"goto_{pose_name}", commanded_angles=angles)
                return True
            else:
                self.logger.error(f"Error al mover a {pose_name}")
                self._log_motion(f"goto_{pose_name}", commanded_angles=angles, status="FAIL")
                return False
        else:
            # Usa coordenadas si están definidas
            if 'coords' in pose:
                coords = pose['coords']
                self.logger.info(f"Moviendo a {pose_name}: {coords}")

                if self.robot.send_coords(coords, speed, config=self.config):
                    self._log_motion(f"goto_{pose_name}", commanded_coords=coords)
                    return True

            return False

    def detect_colors(self) -> Optional[Dict[str, Tuple[int, int, int]]]:
        """Detecta todos los colores visibles.

        Returns:
            Diccionario color -> (u, v, area) o None si falla
        """
        if self.camera is None or self.detector is None:
            # SEGURIDAD: con el robot REAL nunca se inventan posiciones de cubos.
            if not isinstance(self.robot, SimRobot):
                self.logger.error("Cámara no disponible con robot real: no se mueve nada")
                return {}
            self.logger.warning("Cámara no disponible, usando detecciones simuladas")
            # Retorna detecciones simuladas para testing
            return {
                'rojo': (320, 240, 500),
                'azul': (150, 240, 450),
                'amarillo': (400, 200, 480),
                'verde': (250, 280, 520)
            }

        self.logger.info("Detectando colores...")
        detections = capture_and_detect(self.camera, self.detector)

        if detections:
            self.logger.info(f"Colores detectados: {list(detections.keys())}")
            for color, (u, v, area) in detections.items():
                self._log_motion("detect", color=color, pixel_uv=(u, v))
            return detections
        else:
            self.logger.error("No se detectaron colores")
            return {}

    def _rz_para(self, color: str) -> float:
        """PARCHE_GIRO: giro rz de la pinza = base + giro del cubo medido por la camara.

        El cubo es simetrico cada 90 grados, asi que el giro se lleva a [-45, 45).
        Sin camara, sin rectangulo o sin calibracion: usa la base (grasp_rz_deg).
        """
        import math
        m = self.config['motion']
        base = m.get('grasp_rz_deg', 0)
        if not m.get('auto_rz', True) or self.detector is None or self.calibrator.H is None:
            return base
        rect = getattr(self.detector, 'last_rect', {}).get(color)
        if rect is None:
            return base
        (cx, cy), _, ang = rect
        a = math.radians(ang)
        p0 = self.calibrator.pixel_to_robot(cx, cy)
        p1 = self.calibrator.pixel_to_robot(cx + 40 * math.cos(a), cy + 40 * math.sin(a))
        if p0 is None or p1 is None:
            return base
        theta = math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0]))
        theta = ((theta + 45) % 90) - 45
        rz = base + m.get('grasp_rz_sign', 1) * theta
        rz = ((rz + 180) % 360) - 180
        self.logger.info(f"Giro del cubo {color}: {theta:.1f} grados -> pinza rz={rz:.1f} (base {base})")
        return rz

    def _aplicar_offset(self, x: float, y: float, rz: float):
        """PARCHE_OFFSET: suma el desfase pinza-camara, rotado segun el giro de la pinza."""
        import math
        mo = self.config['motion']
        dx, dy = mo.get('grasp_offset_mm', [0.0, 0.0])
        if not dx and not dy:
            return x, y
        g = math.radians(rz - mo.get('grasp_offset_ref_rz', rz))
        ox = dx * math.cos(g) - dy * math.sin(g)
        oy = dx * math.sin(g) + dy * math.cos(g)
        self.logger.info(f"Desfase de pinza: ({ox:+.1f}, {oy:+.1f}) mm")
        return x + ox, y + oy

    def pick_and_place_single_color(self, color: str, detections: Dict[str, Tuple[int, int, int]]) -> bool:
        """Recoge y deposita un cubo de un color específico.

        Args:
            color: nombre del color
            detections: diccionario de detecciones actuales

        Returns:
            True si éxito
        """
        self.logger.info(f"=== Recogiendo {color} ===")

        # Verifica que el color esté detectado
        if color not in detections:
            self.logger.error(f"{color} no detectado")
            return False

        u, v, area = detections[color]
        self.logger.info(f"{color} detectado en píxel ({u}, {v}), área={area}")

        # Convierte píxel a coordenadas robot
        xy = self.calibrator.pixel_to_robot(u, v)
        if xy is None:
            self.logger.error("No hay calibración para convertir píxeles")
            return False

        x, y = xy
        rz_agarre = self._rz_para(color)
        # PARCHE_OFFSET: la pinza no esta donde apunta la camara; el desfase medido
        # (grasp_offset_mm, a un giro de referencia) se rota con el giro actual de la pinza
        x, y = self._aplicar_offset(x, y, rz_agarre)
        # Alturas RELATIVAS a la mesa medida (z_min_mm): así nunca quedan por debajo del límite.
        z_mesa = self.config['motion']['workspace']['z_min_mm']
        z_approach = z_mesa + self.config['motion']['approach_height_mm']
        z_grasp = z_mesa + self.config['motion']['grasp_height_mm']

        self.logger.info(f"Coordenadas robot: ({x:.1f}, {y:.1f})")

        # 1. Abre gripper
        self.logger.info("Abriendo gripper...")
        gripper_open = self.config['gripper']['open_value']
        gripper_speed = self.config['gripper']['gripper_speed']

        if not self.robot.set_gripper_value(gripper_open, gripper_speed):
            self.logger.error("Error al abrir gripper")
            return False

        self._wait_step("Gripper abierto")

        # 2. Va a altura de aproximación
        self.logger.info(f"Moviendo a altura de aproximación ({z_approach} mm)...")
        approach_coords = [x, y, z_approach, 180, 0, rz_agarre]

        if not self.robot.send_coords(approach_coords, self.config['motion']['default_speed'], config=self.config):
            self.logger.error("Error moviendo a altura de aproximación")
            return False

        self._wait_step("En altura de aproximación")
        self._log_motion("approach", commanded_coords=approach_coords, color=color)

        # 3. Desciende lentamente hasta grasp
        step = self.config['motion']['step_descent_mm']
        current_z = z_approach

        while current_z > z_grasp:
            current_z = max(current_z - step, z_grasp)
            coords = [x, y, current_z, 180, 0, rz_agarre]

            self.logger.debug(f"Descendiendo a z={current_z:.1f}...")
            if not self.robot.send_coords(coords, self.config['motion']['default_speed'], mode=1, config=self.config):
                self.logger.error(f"Error descendiendo a z={current_z:.1f}")
                return False

            self._log_motion("descend", commanded_coords=coords, color=color)

        self._wait_step("En altura de agarre")

        # 4. Cierra gripper
        self.logger.info("Cerrando gripper...")
        gripper_close = self.config['gripper']['close_value']

        if not self.robot.set_gripper_value(gripper_close, gripper_speed):
            self.logger.error("Error al cerrar gripper")
            return False

        self._wait_step("Gripper cerrado")
        self._log_motion("grasp", color=color, status="GRASP_CLOSE")

        # 5. Levanta el objeto
        self.logger.info("Levantando objeto...")
        lift_coords = [x, y, z_approach, 180, 0, rz_agarre]

        # PARCHE_LEVANTE: con el cubo agarrado y lejos de la base el brazo cae unos mm;
        # subir es un movimiento en el aire, asi que usa la tolerancia de transito.
        cfg_levante = copy.deepcopy(self.config)
        tol_lev = self.config['motion'].get('transit_tolerance_mm', 20)
        cfg_levante['motion']['tolerance_coords_mm'] = tol_lev
        cfg_levante['motion']['tolerance_z_mm'] = tol_lev
        if not self.robot.send_coords(lift_coords, self.config['motion']['default_speed'], config=cfg_levante):
            self.logger.error("Error levantando objeto")
            return False

        self._wait_step("Objeto levantado")
        self._log_motion("lift", commanded_coords=lift_coords, color=color)

        # 6. Va a zona de depósito
        if color not in self.config['deposits']:
            self.logger.error(f"Zona de depósito para {color} no definida")
            return False

        deposit_coords = self.config['deposits'][color]['coords']
        # PARCHE_DEPOSITO: viajar ALTO para no chocar con los otros cubos
        z_transito = z_mesa + self.config['motion'].get('transit_height_mm', 120)
        vel = self.config['motion']['default_speed']
        for nombre, pt in (("subiendo a altura de tránsito", [x, y, z_transito, 180, 0, rz_agarre]),
                           ("tránsito sobre el depósito", [deposit_coords[0], deposit_coords[1], z_transito,
                                                          deposit_coords[3], deposit_coords[4], deposit_coords[5]])):
            self.logger.info(f"Moviendo: {nombre} (z={z_transito:.1f})")
            # PARCHE_DEPOSITO2: el tránsito es solo un paso intermedio para ir alto;
            # no necesita precisión de agarre (el depósito final sí la exige)
            cfg_transito = copy.deepcopy(self.config)
            tol_t = self.config['motion'].get('transit_tolerance_mm', 20)
            cfg_transito['motion']['tolerance_coords_mm'] = tol_t
            cfg_transito['motion']['tolerance_z_mm'] = tol_t
            if not self.robot.send_coords(pt, vel, config=cfg_transito):
                self.logger.error(f"Error {nombre}")
                return False
            self._log_motion("transit", commanded_coords=pt, color=color)
        self._wait_step("Sobre la zona de depósito (alto)")
        self.logger.info(f"Bajando a zona de depósito: {deposit_coords}")

        if not self.robot.send_coords(deposit_coords, self.config['motion']['default_speed'], config=self.config):
            self.logger.error(f"Error moviendo a zona de depósito")
            return False

        self._wait_step("En zona de depósito")
        self._log_motion("deposit_approach", commanded_coords=deposit_coords, color=color)

        # 7. Abre gripper en zona de depósito
        self.logger.info("Abriendo gripper en zona de depósito...")
        if not self.robot.set_gripper_value(gripper_open, gripper_speed):
            self.logger.error("Error al abrir gripper en depósito")
            return False

        self._wait_step("Objeto depositado")
        self._log_motion("deposit_release", commanded_coords=deposit_coords, color=color, status="DEPOSIT_OK")

        # 8. Levanta y retira gripper
        z_safe = max(z_approach + 30, z_transito)
        safe_coords = [deposit_coords[0], deposit_coords[1], z_safe,
                       deposit_coords[3], deposit_coords[4], deposit_coords[5]]

        self.logger.info("Retirando gripper...")
        if not self.robot.send_coords(safe_coords, self.config['motion']['default_speed'], config=cfg_transito):
            self.logger.error("Error retirando gripper")
            return False

        self._log_motion("retract", commanded_coords=safe_coords, color=color)
        self.logger.info(f"=== {color} recogido y depositado exitosamente ===")

        return True

    def run_full_cycle(self) -> bool:
        """Ejecuta ciclo completo: HOME -> OBSERVATION -> detección -> recogida.

        Returns:
            True si ciclo completado
        """
        self.logger.info("=== INICIANDO CICLO COMPLETO ===")

        # 1. Power on
        if not self.power_on():
            return False

        # 2. Va a HOME
        self.logger.info("Moviendo a HOME...")
        if not self.go_to_pose('home'):
            return False

        # 3. Va a OBSERVATION
        self.logger.info("Moviendo a OBSERVATION...")
        if not self.go_to_pose('observation'):
            return False

        # 4. Detecta colores
        detections = self.detect_colors()
        if not detections:
            self.logger.error("No se detectaron colores")
            return False

        # 5. Recoge cubos en orden configurado
        color_order = self.config['workflow']['color_order']
        for color in color_order:
            if color in detections:
                self._wait_step(f"¿Proceder con {color}?")

                # Re-detecta si está configurado (sin pisar las detecciones previas si falla)
                if self.config['workflow']['re_detect_each_cycle']:
                    # PARCHE_CICLO: la calibracion solo vale desde OBSERVACION;
                    # despues de depositar el brazo esta en otro lado: volver antes de mirar
                    if not self.go_to_pose('observation'):
                        self.logger.error('No pude volver a OBSERVACION: CICLO DETENIDO')
                        return False
                    self.logger.info("Re-detectando...")
                    nuevas = self.detect_colors()
                    if nuevas:
                        detections = nuevas
                    else:
                        self.logger.warning("Re-detección falló, usando detecciones anteriores")
                    if color not in detections:
                        self.logger.warning(f"{color} ya no se detecta; se omite")
                        continue

                # SEGURIDAD: si un movimiento falla, el ciclo se DETIENE aquí.
                # No se mueve más el brazo (ni siquiera a HOME) y la pinza queda como está:
                # el operador revisa el log y decide.
                if not self.pick_and_place_single_color(color, detections):
                    self.logger.error(f"Fallo recogiendo {color}: CICLO DETENIDO sin más movimientos. Revise el log.")
                    return False

        # 6. Retorna a HOME
        if self.config['workflow']['return_to_home']:
            self.logger.info("Retornando a HOME...")
            if not self.go_to_pose('home'):
                self.logger.warning("Error al retornar a HOME")

        self.logger.info("=== CICLO COMPLETADO ===")
        return True

    def teach_pose(self, pose_name: str) -> bool:
        """Enseña (guarda) una nueva posición.

        Args:
            pose_name: nombre para guardar

        Returns:
            True si guardada
        """
        self.logger.info(f"Enseñando posición '{pose_name}'")
        self.logger.info("Presiona 'r' para liberar servos, jog el gripper a la posición deseada")
        self.logger.info("Presiona 'p' para guardar la posición actual")
        self.logger.info("Presiona 'q' para cancelar")

        try:
            while True:
                key = input("Comando (r/p/q): ").strip().lower()

                if key == 'r':
                    self.logger.info("Liberando servos...")
                    if self.robot.release_all_servos():
                        self.logger.info("Servos liberados para movimiento manual")

                elif key == 'p':
                    angles = self.robot.get_angles()
                    coords = self.robot.get_coords()

                    if angles and coords:
                        # Guarda en config
                        if pose_name not in self.config['poses']:
                            self.config['poses'][pose_name] = {}

                        self.config['poses'][pose_name]['angles'] = angles
                        self.config['poses'][pose_name]['coords'] = coords
                        self.config['poses'][pose_name]['description'] = f"Posición enseñada: {datetime.now().isoformat()}"

                        # Guarda config
                        with open('config.json', 'w') as f:
                            json.dump(self.config, f, indent=2)

                        self.logger.info(f"Posición '{pose_name}' guardada")
                        self.logger.info(f"Ángulos: {angles}")
                        self.logger.info(f"Coords: {coords}")

                        return True
                    else:
                        self.logger.error("No se pudieron leer ángulos/coords")

                elif key == 'q':
                    self.logger.info("Cancelado")
                    return False

        except KeyboardInterrupt:
            return False


def main():
    """Función principal con CLI."""
    parser = argparse.ArgumentParser(description='JetCobot Pick & Place')

    parser.add_argument('--simular', action='store_true',
                       help='Simula sin hardware')
    parser.add_argument('--color', type=str,
                       help='Recoge solo este color (rojo/azul/amarillo/verde)')
    parser.add_argument('--paso-a-paso', action='store_true',
                       help='Espera Enter entre movimientos')
    parser.add_argument('--velocidad', type=int, default=20,
                       help='Velocidad por defecto (1-100)')
    parser.add_argument('--calibrar', action='store_true',
                       help='Modo de calibración interactiva')
    parser.add_argument('--ensenar', type=str, metavar='NOMBRE',
                       help='Enseña una nueva posición con este nombre')
    parser.add_argument('--detectar', action='store_true',
                       help='Solo detecta colores, no mueve robot')
    parser.add_argument('--estado', action='store_true',
                       help='Muestra estado actual del robot y calibración')
    parser.add_argument('--debug', action='store_true',
                       help='Modo depuración (guarda imágenes)')

    args = parser.parse_args()

    # Carga configuración
    with open('config.json', 'r') as f:
        config = json.load(f)

    if args.velocidad:
        config['motion']['default_speed'] = args.velocidad

    logger, csv_file = setup_logging()
    logger.info("="*60)
    logger.info("JetCobot Pick & Place")
    logger.info("="*60)

    try:
        # Crea robot
        robot = create_robot(args.simular, config)
        logger.info(f"Robot inicializado ({'simulado' if args.simular else 'real'})")

        # Crea calibrador
        calibrator = HomographyCalibrator(config)
        status = calibrator.get_status()
        logger.info(f"Calibración: {status['num_points']} puntos, calibrado={status['calibrated']}")

        # Crea cámara y detector (si no es --calibrar ni --detectar ni --estado)
        camera = None
        detector = None

        if not args.simular and (args.calibrar or args.detectar or args.color or not any([args.calibrar, args.ensenar, args.detectar, args.estado])):
            try:
                camera = CameraCapture(
                    device=0,
                    width=config['camera']['width'],
                    height=config['camera']['height'],
                    fps=config['camera']['fps']
                )
                detector = ColorDetector(config, debug=args.debug)
                logger.info("Cámara y detector inicializados")
            except Exception as e:
                logger.warning(f"Cámara no disponible: {e}")
                if args.detectar:
                    logger.error("Error: --detectar requiere cámara")
                    return 1

        # Ejecuta comandos
        if args.estado:
            logger.info("=== ESTADO DEL SISTEMA ===")
            angles = robot.get_angles()
            coords = robot.get_coords()
            logger.info(f"Ángulos actuales: {angles}")
            logger.info(f"Coords actuales: {coords}")
            logger.info(f"Calibración: {status}")
            return 0

        elif args.calibrar:
            logger.info("=== MODO CALIBRACIÓN ===")
            if args.simular:
                logger.error("Calibración requiere robot real")
                return 1

            from calibration import interactive_calibration_mode
            success = interactive_calibration_mode(config, robot)
            return 0 if success else 1

        elif args.ensenar:
            logger.info(f"=== ENSEÑAR POSICIÓN '{args.ensenar}' ===")
            pick_place = PickPlace(config, robot, camera, detector, calibrator, csv_file, args.paso_a_paso)
            success = pick_place.teach_pose(args.ensenar)
            return 0 if success else 1

        elif args.detectar:
            logger.info("=== MODO DETECCIÓN ===")
            pick_place = PickPlace(config, robot, camera, detector, calibrator, csv_file, False)
            detections = pick_place.detect_colors()
            if detections:
                logger.info(f"Detectados: {detections}")
                return 0
            else:
                logger.error("No se detectaron colores")
                return 1

        elif args.color:
            logger.info(f"=== RECOGIENDO SOLO {args.color.upper()} ===")

            if calibrator.H is None:
                logger.error("Se requiere calibración primero")
                return 1

            pick_place = PickPlace(config, robot, camera, detector, calibrator, csv_file, args.paso_a_paso)

            if not pick_place.power_on():
                return 1

            if not pick_place.go_to_pose('home'):
                return 1

            if not pick_place.go_to_pose('observation'):
                return 1

            detections = pick_place.detect_colors()
            if not detections or args.color not in detections:
                logger.error(f"{args.color} no detectado")
                return 1

            success = pick_place.pick_and_place_single_color(args.color, detections)

            # SEGURIDAD: igual que el ciclo completo, tras un fallo el brazo NO se mueve más.
            if success and not pick_place.go_to_pose('home'):
                logger.warning("Error retornando a HOME")

            return 0 if success else 1

        else:
            # Ciclo completo
            if calibrator.H is None:
                logger.error("Se requiere calibración primero (python3 pick_place.py --calibrar)")
                return 1

            pick_place = PickPlace(config, robot, camera, detector, calibrator, csv_file, args.paso_a_paso)
            success = pick_place.run_full_cycle()

            return 0 if success else 1

    except KeyboardInterrupt:
        logger.info("Cancelado por usuario")
        return 130
    except Exception as e:
        logger.error(f"Error fatal: {e}", exc_info=True)
        return 1
    finally:
        if camera:
            camera.release()


if __name__ == '__main__':
    sys.exit(main())
