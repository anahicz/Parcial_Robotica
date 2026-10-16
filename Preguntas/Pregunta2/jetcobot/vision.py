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

"""
Módulo de visión para detectar cubos de colores.
Usa HSV para detección robusta contra cambios de iluminación.
"""
import cv2
import numpy as np
import logging
import time
from typing import Dict, Tuple, Optional, List
from collections import deque
import os

logger = logging.getLogger(__name__)


class ColorDetector:
    """Detecta cubos de colores en imágenes usando HSV."""

    def __init__(self, config: dict, debug: bool = False):
        """Inicializa el detector de colores.

        Args:
            config: diccionario con configuración de colores HSV y parámetros
            debug: si True, guarda imágenes anotadas para depuración
        """
        self.config = config
        self.debug = debug
        self.color_config = config['vision']['colors']
        self.min_area = config['vision']['min_area_px2']
        self.stability_frames = config['vision']['stability_frames']
        self.pixel_tolerance = config['vision']['pixel_tolerance']

        # Historial de detecciones para estabilidad
        self.detection_history = {
            color: deque(maxlen=self.stability_frames)
            for color in self.color_config.keys()
        }

        # Directorio para imágenes de depuración
        if self.debug:
            self.debug_dir = config['logging'].get('debug_images_dir', 'debug_images')
            os.makedirs(self.debug_dir, exist_ok=True)
            self.frame_count = 0

    def _get_hsv_ranges(self, color: str) -> List[Tuple[np.ndarray, np.ndarray]]:
        """Obtiene los rangos HSV para un color.

        Args:
            color: nombre del color (e.g., 'rojo', 'azul')

        Returns:
            Lista de tuplas (lower, upper) para cv2.inRange()
        """
        if color not in self.color_config:
            return []

        ranges = self.color_config[color].get('hsv_ranges', [])
        result = []
        for r in ranges:
            lower = np.array(r['lower'], dtype=np.uint8)
            upper = np.array(r['upper'], dtype=np.uint8)
            result.append((lower, upper))

        return result

    def _detect_color_in_frame(self, hsv: np.ndarray, color: str) -> Optional[Tuple[int, int, int]]:
        """Detecta un color específico en una imagen HSV.

        Args:
            hsv: imagen en espacio HSV
            color: nombre del color

        Returns:
            Tupla (u, v, area) del centroide y área, o None si no se detecta
        """
        ranges = self._get_hsv_ranges(color)
        if not ranges:
            return None

        # Combina todas las máscaras para este color
        mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
        for lower, upper in ranges:
            m = cv2.inRange(hsv, lower, upper)
            mask = cv2.bitwise_or(mask, m)

        # Morfología para limpiar
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)

        # Encuentra contornos
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return None

        # Busca el contorno más grande
        largest_contour = max(contours, key=cv2.contourArea)
        # PARCHE_GIRO: rectangulo girado del cubo (centro, lados, angulo) para alinear la pinza
        if not hasattr(self, 'last_rect'):
            self.last_rect = {}
        self.last_rect[color] = cv2.minAreaRect(largest_contour)
        area = cv2.contourArea(largest_contour)

        if area < self.min_area:
            return None

        # Calcula centroide
        M = cv2.moments(largest_contour)
        if M['m00'] > 0:
            u = int(M['m10'] / M['m00'])
            v = int(M['m01'] / M['m00'])
            return (u, v, int(area))

        return None

    def _is_stable_detection(self, color: str, uv: Tuple[int, int]) -> bool:
        """Comprueba si una detección es estable en los últimos N frames.

        Args:
            color: nombre del color
            uv: posición actual (u, v)

        Returns:
            True si la detección es estable (coherente en últimos frames)
        """
        history = self.detection_history[color]

        if len(history) < self.stability_frames:
            history.append(uv)
            return len(history) >= 1  # Al menos 1 frame es suficiente para empezar

        # Comprueba si todas las detecciones recientes están dentro de tolerancia
        for prev_uv in history:
            dist = np.sqrt((uv[0] - prev_uv[0])**2 + (uv[1] - prev_uv[1])**2)
            if dist > self.pixel_tolerance:
                history.clear()
                history.append(uv)
                return False

        history.append(uv)
        return True

    def detect_all_colors(self, frame: np.ndarray) -> Dict[str, Tuple[int, int, int]]:
        """Detecta todos los colores en un frame.

        Args:
            frame: imagen BGR de OpenCV

        Returns:
            Diccionario color -> (u, v, area), solo colores detectados
        """
        # Convierte a HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        detections = {}
        annotated = frame.copy() if self.debug else None

        for color in self.color_config.keys():
            result = self._detect_color_in_frame(hsv, color)

            if result:
                u, v, area = result

                # Comprueba estabilidad
                if self._is_stable_detection(color, (u, v)):
                    detections[color] = (u, v, area)
                    logger.debug(f"Detectado {color} en ({u}, {v}) área={area}")

                    if annotated is not None:
                        cv2.circle(annotated, (u, v), 5, (0, 255, 0), -1)
                        cv2.putText(annotated, f"{color} ({u},{v})", (u+10, v),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # Guarda imagen de depuración si está activado
        if self.debug and annotated is not None:
            self.frame_count += 1
            filename = os.path.join(self.debug_dir, f"frame_{self.frame_count:04d}.jpg")
            cv2.imwrite(filename, annotated)
            logger.debug(f"Imagen de depuración guardada: {filename}")

        return detections

    def reset_history(self):
        """Reinicia el historial de detecciones (ej. después de recolocar cubos)."""
        for color in self.color_config.keys():
            self.detection_history[color].clear()
        logger.info("Historial de detecciones reiniciado")


class CameraCapture:
    """Captura de video de la cámara con manejo de errores."""

    def __init__(self, device: int = 0, width: int = 640, height: int = 480, fps: int = 30):
        """Inicializa la cámara.

        Args:
            device: índice del dispositivo de video (0 para /dev/video0)
            width: ancho de resolución
            height: alto de resolución
            fps: frames por segundo
        """
        self.device = device
        self.width = width
        self.height = height
        self.fps = fps
        self.cap = None
        self.connect()

    def connect(self) -> bool:
        """Conecta a la cámara."""
        try:
            self.cap = cv2.VideoCapture(self.device)

            if not self.cap.isOpened():
                logger.error(f"Cámara {self.device} no disponible (posiblemente bloqueada por otro proceso)")
                return False

            # Configura resolución y FPS
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)

            # Calentamiento: los primeros frames salen oscuros mientras ajusta la exposicion
            for _ in range(10):
                self.cap.read()

            logger.info(f"Cámara conectada en /dev/video{self.device} ({self.width}x{self.height}@{self.fps}fps)")
            return True
        except Exception as e:
            logger.error(f"Error al conectar cámara: {e}")
            return False

    def capture(self, timeout_s: float = 5) -> Optional[np.ndarray]:
        """Captura un frame con reintentos.

        Args:
            timeout_s: timeout en segundos

        Returns:
            Frame BGR o None si falla
        """
        if self.cap is None or not self.cap.isOpened():
            if not self.connect():
                return None

        start_time = time.time()
        while time.time() - start_time < timeout_s:
            ret, frame = self.cap.read()

            if ret and frame is not None:
                return frame

            time.sleep(0.1)

        logger.error(f"Timeout capturando frame después de {timeout_s}s")
        return None

    def release(self):
        """Libera la cámara."""
        if self.cap is not None:
            self.cap.release()
            logger.info("Cámara liberada")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


def capture_and_detect(camera: CameraCapture, detector: ColorDetector,
                      max_attempts: int = 3) -> Optional[Dict[str, Tuple[int, int, int]]]:
    """Captura un frame y detecta todos los colores.

    Args:
        camera: instancia de CameraCapture
        detector: instancia de ColorDetector
        max_attempts: número máximo de intentos si falla

    Returns:
        Diccionario de detecciones o None si falla
    """
    for attempt in range(max_attempts):
        frame = camera.capture()

        if frame is None:
            logger.warning(f"Intento {attempt+1}/{max_attempts} falló")
            continue

        try:
            detections = detector.detect_all_colors(frame)
            return detections
        except Exception as e:
            logger.error(f"Error al detectar colores en intento {attempt+1}: {e}")
            continue

    return None
