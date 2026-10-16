"""
Módulo de calibración.
Mapea píxeles de la cámara a coordenadas cartesianas del robot usando homografía.
"""
import cv2
import numpy as np
import json
import logging
from typing import Dict, List, Tuple, Optional
import os

logger = logging.getLogger(__name__)


class HomographyCalibrator:
    """Calibra la relación píxel-robot usando homografía."""

    def __init__(self, config: dict):
        """Inicializa el calibrador.

        Args:
            config: diccionario de configuración
        """
        self.config = config
        self.camera_width = config['camera']['width']
        self.camera_height = config['camera']['height']
        self.calibration_file = 'calibracion.json'
        self.H = None  # Matriz de homografía
        self.H_inv = None  # Matriz inversa
        self.pixel_points = []
        self.robot_points = []
        self.load_or_create()

    def load_or_create(self):
        """Carga calibración si existe, si no, la crea vacía."""
        if os.path.exists(self.calibration_file):
            try:
                with open(self.calibration_file, 'r') as f:
                    data = json.load(f)
                    self.pixel_points = data.get('pixel_points', [])
                    self.robot_points = data.get('robot_points', [])
                    H_list = data.get('H_matrix', None)
                    if H_list:
                        self.H = np.array(H_list, dtype=np.float32)
                        self.H_inv = np.linalg.inv(self.H)
                    logger.info(f"Calibración cargada: {len(self.pixel_points)} puntos")
            except Exception as e:
                logger.warning(f"Error al cargar calibración: {e}")
                self._init_empty()
        else:
            self._init_empty()

    def _init_empty(self):
        """Inicializa estructura vacía."""
        self.pixel_points = []
        self.robot_points = []
        self.H = None
        self.H_inv = None
        logger.info("Calibración inicializada vacía")

    def save(self):
        """Guarda la calibración a archivo."""
        data = {
            'camera_width': self.camera_width,
            'camera_height': self.camera_height,
            'pixel_points': self.pixel_points,
            'robot_points': self.robot_points,
            'H_matrix': self.H.tolist() if self.H is not None else None
        }
        with open(self.calibration_file, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Calibración guardada a {self.calibration_file}")

    def add_point(self, pixel_uv: Tuple[int, int], robot_xy: Tuple[float, float]):
        """Añade un punto de calibración.

        Args:
            pixel_uv: coordenadas en píxeles (u, v)
            robot_xy: coordenadas del robot (x, y) en mm
        """
        self.pixel_points.append(list(pixel_uv))
        self.robot_points.append(list(robot_xy))
        logger.info(f"Punto añadido: píxel {pixel_uv} -> robot {robot_xy}")

    def compute_homography(self) -> bool:
        """Computa la homografía a partir de los puntos calibrados.

        Returns:
            True si se computó exitosamente
        """
        if len(self.pixel_points) < 4:
            logger.error(f"Se necesitan al menos 4 puntos, tenemos {len(self.pixel_points)}")
            return False

        src_pts = np.array(self.pixel_points, dtype=np.float32)
        dst_pts = np.array(self.robot_points, dtype=np.float32)

        try:
            # Computa homografía 2D
            H, mask = cv2.findHomography(src_pts, dst_pts)

            if H is None:
                logger.error("No se pudo computar homografía")
                return False

            self.H = H
            self.H_inv = np.linalg.inv(H)

            # Reporta error de reproyección
            reproj_error = self._compute_reprojection_error()
            logger.info(f"Homografía computada. Error de reproyección: {reproj_error:.2f} píxeles")

            return True
        except Exception as e:
            logger.error(f"Error al computar homografía: {e}")
            return False

    def _compute_reprojection_error(self) -> float:
        """Calcula el error de reproyección de los puntos calibrados."""
        if self.H is None or len(self.pixel_points) == 0:
            return float('inf')

        src_pts = np.array(self.pixel_points, dtype=np.float32)
        dst_pts = np.array(self.robot_points, dtype=np.float32)

        # Transforma puntos de píxel a robot usando H
        ones = np.ones((src_pts.shape[0], 1))
        pts_homo = np.hstack([src_pts, ones])
        transformed = (self.H @ pts_homo.T).T
        transformed = transformed[:, :2] / transformed[:, 2:3]

        # Calcula error euclidiano
        errors = np.linalg.norm(transformed - dst_pts, axis=1)
        mean_error = np.mean(errors)

        return mean_error

    def pixel_to_robot(self, u: int, v: int) -> Optional[Tuple[float, float]]:
        """Convierte píxeles a coordenadas del robot (x, y).

        Args:
            u, v: coordenadas de píxel

        Returns:
            Tupla (x, y) en mm, o None si no hay calibración
        """
        if self.H is None:
            logger.error("Calibración no disponible")
            return None

        try:
            pt = np.array([[[u, v]]], dtype=np.float32)
            transformed = cv2.perspectiveTransform(pt, self.H)
            x, y = transformed[0, 0]
            return (float(x), float(y))
        except Exception as e:
            logger.error(f"Error al transformar píxel ({u}, {v}): {e}")
            return None

    def robot_to_pixel(self, x: float, y: float) -> Optional[Tuple[int, int]]:
        """Convierte coordenadas del robot a píxeles (inversa de pixel_to_robot).

        Args:
            x, y: coordenadas en mm

        Returns:
            Tupla (u, v) en píxeles, o None si no hay calibración
        """
        if self.H_inv is None:
            logger.error("Calibración no disponible")
            return None

        try:
            pt = np.array([[[x, y]]], dtype=np.float32)
            transformed = cv2.perspectiveTransform(pt, self.H_inv)
            u, v = transformed[0, 0]
            return (int(u), int(v))
        except Exception as e:
            logger.error(f"Error al transformar robot ({x}, {y}): {e}")
            return None

    def get_status(self) -> Dict:
        """Retorna estado actual de la calibración."""
        return {
            'num_points': len(self.pixel_points),
            'calibrated': self.H is not None,
            'reprojection_error': self._compute_reprojection_error() if self.H is not None else None,
            'points': {
                'pixel': self.pixel_points,
                'robot': self.robot_points
            }
        }


class CalibrationUI:
    """Interfaz para calibración interactiva."""

    def __init__(self, calibrator: HomographyCalibrator):
        self.calibrator = calibrator
        self.clicked_point = None
        self.current_frame = None

    def mouse_callback(self, event, x, y, flags, param):
        """Callback para clicks del ratón."""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.clicked_point = (x, y)

    def calibrate_interactive(self, camera_capture, robot) -> bool:
        """Calibración interactiva con interfaz gráfica.

        Proceso:
        1. Muestra lo que ve la cámara
        2. Usuario coloca marcador en la mesa visible en 4+ puntos
        3. Usuario hace click en cada posición en la imagen
        4. Usuario jog/enseña el gripper a ese punto real
        5. Script lee las coordenadas

        Args:
            camera_capture: instancia de CameraCapture
            robot: instancia del robot

        Returns:
            True si calibración exitosa
        """
        logger.info("=== CALIBRACIÓN INTERACTIVA ===")
        logger.info("Procedimiento:")
        logger.info("1. Coloca un marcador (tape de colores) en la mesa, visible en cámara")
        logger.info("2. Haz click en el marcador en la imagen")
        logger.info("3. Presiona 'r' para 'release servos', jog el gripper al punto")
        logger.info("4. Presiona 'p' para leer posición del robot")
        logger.info("5. Repite con 4-6 puntos diferentes")
        logger.info("6. Presiona 'c' para computar homografía, 'q' para salir")

        window_name = "Calibración - Click en marcadores"
        cv2.namedWindow(window_name)
        cv2.setMouseCallback(window_name, self.mouse_callback)

        try:
            while True:
                frame = camera_capture.capture()
                if frame is None:
                    logger.error("No se pudo capturar frame")
                    break

                self.current_frame = frame.copy()

                # Dibuja puntos ya calibrados
                for i, (pixel, robot_pt) in enumerate(
                    zip(self.calibrator.pixel_points, self.calibrator.robot_points)):
                    u, v = pixel
                    cv2.circle(self.current_frame, (u, v), 8, (0, 255, 0), -1)
                    cv2.putText(self.current_frame, f"P{i+1}", (u+10, v),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                # Dibuja punto clickeado (temporal)
                if self.clicked_point:
                    u, v = self.clicked_point
                    cv2.circle(self.current_frame, (u, v), 6, (0, 0, 255), 2)

                # Info
                info = f"Puntos: {len(self.calibrator.pixel_points)} | "
                info += f"Calibrado: {self.calibrator.H is not None}"
                cv2.putText(self.current_frame, info, (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                cv2.imshow(window_name, self.current_frame)

                key = cv2.waitKey(1) & 0xFF

                if key == ord('q'):
                    logger.info("Calibración cancelada")
                    return False

                elif key == ord('c'):
                    if self.calibrator.compute_homography():
                        logger.info("Homografía computada exitosamente")
                        self.calibrator.save()
                        return True
                    else:
                        logger.error("Error al computar homografía")

                elif key == ord('r'):
                    logger.info("Liberando servos para movimiento manual...")
                    if robot.release_all_servos():
                        logger.info("Servos liberados. Mueve el gripper manualmente.")
                        logger.info("Presiona 'p' cuando esté en posición")

                elif key == ord('p'):
                    if not self.clicked_point:
                        logger.warning("Primero haz click en el marcador")
                        continue

                    # Lee posición del robot
                    coords = robot.get_coords()
                    if coords:
                        x, y = coords[0], coords[1]
                        pixel_uv = self.clicked_point

                        self.calibrator.add_point(pixel_uv, (x, y))
                        logger.info(f"Punto calibrado: píxel {pixel_uv} -> robot ({x:.1f}, {y:.1f})")

                        self.clicked_point = None
                    else:
                        logger.error("No se pudo leer posición del robot")

        finally:
            cv2.destroyAllWindows()

        return False


def interactive_calibration_mode(config: dict, robot) -> bool:
    """Ejecuta el modo de calibración interactiva.

    Args:
        config: configuración
        robot: instancia del robot

    Returns:
        True si calibración completada
    """
    from vision import CameraCapture

    try:
        camera = CameraCapture(
            device=0,
            width=config['camera']['width'],
            height=config['camera']['height'],
            fps=config['camera']['fps']
        )

        calibrator = HomographyCalibrator(config)
        ui = CalibrationUI(calibrator)

        success = ui.calibrate_interactive(camera, robot)
        camera.release()

        return success
    except Exception as e:
        logger.error(f"Error en calibración interactiva: {e}")
        return False
