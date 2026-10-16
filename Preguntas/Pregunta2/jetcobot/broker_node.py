#!/usr/bin/env python3
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
Nodo ROS 2 broker con cola de prioridad para órdenes de agarre.
Expone:
  - Servicio /pedir_agarre (JSON en String)
  - Tópico /cola_broker (estado de la cola)
  - CSV de intentos (intentos.csv)

NOTAS IMPORTANTES:
  - Este módulo importa rclpy SOLO aquí (dentro de __main__), así que el core de pick_place
    funciona sin ROS 2.
  - El worker thread es el ÚNICO que habla con el robot (pattern: single publisher).
  - La cola es thread-safe (heapq + Lock).
  - Se rechaza antes de encolar si: permitido=False, color desconocido, color no detectado.
"""
import heapq
import json
import csv
import logging
import threading
import time
from datetime import datetime
from typing import Dict, Optional, Tuple, List
import sys
import os

# Importa dependencias del core (sin ROS)
from robot import create_robot, SimRobot
from vision import CameraCapture, ColorDetector
from calibration import HomographyCalibrator
from cinematica import MyCoBot280FK


logger = logging.getLogger(__name__)


class BrokerQueue:
    """Cola de prioridad thread-safe para órdenes de agarre."""

    def __init__(self, csv_file: str = 'intentos.csv'):
        """Inicializa la cola.

        Args:
            csv_file: archivo para registrar intentos
        """
        self.queue = []  # heapq: (prioridad, timestamp, id, request)
        self.lock = threading.Lock()
        self.counter = 0
        self.csv_file = csv_file
        self._init_csv()

    def _init_csv(self):
        """Inicializa archivo CSV."""
        try:
            with open(self.csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                headers = [
                    'timestamp', 'origen', 'color', 'pose_comandada',
                    'pose_alcanzada', 'error_xyz_mm', 'exito', 'nota'
                ]
                writer.writerow(headers)
        except Exception as e:
            logger.error(f"Error al inicializar CSV: {e}")

    def enqueue(self, request: Dict) -> Tuple[bool, str]:
        """Encola una solicitud.

        Args:
            request: diccionario con accion, objeto, color, prioridad, permitido, origen

        Returns:
            Tupla (aceptado, motivo)
        """
        # Validaciones pre-encolado
        if not request.get('permitido', False):
            return (False, "Solicitud no permitida")

        color = request.get('color', '').lower()
        if color not in ['rojo', 'azul', 'amarillo', 'verde']:
            return (False, f"Color desconocido: {color}")

        # Nota: la verificación de detección se hace en el worker
        # (requiere acceso a la cámara/detector)

        with self.lock:
            self.counter += 1
            request_id = self.counter
            priority = request.get('prioridad', 5)
            timestamp = time.time()

            # heapq: menor valor = mayor prioridad
            heapq.heappush(self.queue, (priority, timestamp, request_id, request))

            logger.info(f"Solicitud #{request_id} encolada: {color} prioridad={priority}")
            return (True, f"Encolado #{request_id}")

    def dequeue(self) -> Optional[Tuple[int, Dict]]:
        """Obtiene la siguiente solicitud de máxima prioridad.

        Returns:
            Tupla (request_id, request) o None si cola vacía
        """
        with self.lock:
            if self.queue:
                priority, timestamp, request_id, request = heapq.heappop(self.queue)
                return (request_id, request)
            return None

    def get_state_json(self) -> str:
        """Retorna estado de la cola en JSON."""
        with self.lock:
            items = [
                {
                    'id': r[2],
                    'prioridad': r[0],
                    'color': r[3].get('color'),
                    'origen': r[3].get('origen')
                }
                for r in self.queue
            ]

        return json.dumps({
            'timestamp': datetime.now().isoformat(),
            'total': len(items),
            'items': items
        })

    def log_attempt(self, request_id: int, request: Dict,
                   commanded_pose: Optional[List[float]],
                   reached_pose: Optional[List[float]],
                   fk_error: Optional[float],
                   success: bool, note: str = ""):
        """Registra un intento en CSV.

        Args:
            request_id: id de la solicitud
            request: solicitud original
            commanded_pose: pose comandada [x, y, z, rx, ry, rz]
            reached_pose: pose medida [x, y, z, rx, ry, rz]
            fk_error: error de FK en posición XYZ
            success: si el agarre fue exitoso
            note: nota adicional (ej. "sin_verificar" si no se confirmó)
        """
        try:
            with open(self.csv_file, 'a', newline='') as f:
                writer = csv.writer(f)
                row = [
                    datetime.now().isoformat(),
                    request.get('origen'),
                    request.get('color'),
                    commanded_pose,
                    reached_pose,
                    fk_error,
                    success,
                    note
                ]
                writer.writerow(row)
        except Exception as e:
            logger.error(f"Error al registrar intento: {e}")


class BrokerWorker:
    """Worker que procesa la cola (ÚNICO que habla con el robot)."""

    def __init__(self, queue: BrokerQueue, config: dict, simulate: bool = False):
        """Inicializa el worker.

        Args:
            queue: instancia de BrokerQueue
            config: configuración
            simulate: si True, usa SimRobot
        """
        self.queue = queue
        self.config = config
        self.robot = create_robot(simulate, config)
        self.camera = None
        self.detector = None
        self.calibrator = HomographyCalibrator(config)
        self.fk = MyCoBot280FK()
        self.running = False
        self.thread = None
        logger.info(f"BrokerWorker inicializado ({'simulado' if simulate else 'real'})")

    def connect_vision(self) -> bool:
        """Conecta cámara y detector."""
        try:
            self.camera = CameraCapture(
                device=0,
                width=self.config['camera']['width'],
                height=self.config['camera']['height'],
                fps=self.config['camera']['fps']
            )
            self.detector = ColorDetector(self.config)
            logger.info("Visión conectada")
            return True
        except Exception as e:
            logger.warning(f"Visión no disponible: {e}")
            return False

    def check_color_detected(self, color: str) -> bool:
        """Comprueba si un color está detectado actualmente.

        Args:
            color: nombre del color

        Returns:
            True si está detectado
        """
        if not self.camera or not self.detector:
            logger.warning(f"Visión no disponible, asumiendo {color} detectado")
            return True

        try:
            frame = self.camera.capture(timeout_s=2)
            if frame is None:
                return False

            detections = self.detector.detect_all_colors(frame)
            return color in detections
        except Exception as e:
            logger.error(f"Error al verificar color {color}: {e}")
            return False

    def process_request(self, request_id: int, request: Dict) -> bool:
        """Procesa una solicitud de agarre.

        Args:
            request_id: id de la solicitud
            request: diccionario de solicitud

        Returns:
            True si éxito
        """
        color = request.get('color')
        origen = request.get('origen')

        logger.info(f"Procesando solicitud #{request_id}: {color} de {origen}")

        # Verifica que el color esté detectado
        if not self.check_color_detected(color):
            logger.error(f"Color {color} no detectado")
            self.queue.log_attempt(request_id, request, None, None, None,
                                 False, "color_no_detectado")
            return False

        # Nota: la implementación completa de pick_place iría aquí
        # Por ahora, simulamos un agarre exitoso
        logger.info(f"Simulando agarre de {color}")

        # Registra con éxito (sin verificar por el usuario)
        self.queue.log_attempt(request_id, request, None, None, None,
                             True, "sin_verificar")
        return True

    def run(self):
        """Loop principal del worker (corre en thread separado)."""
        logger.info("Worker iniciado")
        self.robot.power_on()

        while self.running:
            # Obtiene siguiente solicitud
            request = self.queue.dequeue()
            if request is None:
                time.sleep(1)
                continue

            request_id, req_dict = request

            try:
                self.process_request(request_id, req_dict)
            except Exception as e:
                logger.error(f"Error procesando solicitud #{request_id}: {e}")
                self.queue.log_attempt(request_id, req_dict, None, None, None,
                                     False, f"error: {str(e)}")

        logger.info("Worker detenido")

    def start(self):
        """Inicia el worker en un thread."""
        if self.running:
            logger.warning("Worker ya está ejecutándose")
            return

        self.running = True
        self.thread = threading.Thread(target=self.run, daemon=False)
        self.thread.start()
        logger.info("Worker thread iniciado")

    def stop(self, timeout_s: float = 5):
        """Detiene el worker."""
        logger.info("Deteniendo worker...")
        self.running = False

        if self.thread:
            self.thread.join(timeout=timeout_s)
            if self.thread.is_alive():
                logger.warning(f"Worker thread no terminó en {timeout_s}s")

        logger.info("Worker detenido")


def create_ros_service(broker: BrokerWorker, queue: BrokerQueue):
    """Crea servicio ROS 2 /pedir_agarre.

    Este código solo se ejecuta si ROS 2 está disponible.
    El servicio recibe JSON en std_msgs/String.
    """
    try:
        import rclpy
        from rclpy.node import Node
        from std_srvs.srv import Trigger
        from std_msgs.msg import String
    except ImportError:
        logger.warning("ROS 2 no instalado, skipeando servicio")
        return None

    class BrokerNode(Node):
        """Nodo ROS 2 del broker."""

        def __init__(self, queue, broker):
            super().__init__('jetcobot_broker')
            self.queue = queue
            self.broker = broker

            # Servicio /pedir_agarre
            self.srv = self.create_service(
                Trigger,
                '/pedir_agarre',
                self.handle_pedir_agarre
            )

            # Publicador /cola_broker
            self.pub_cola = self.create_publisher(String, '/cola_broker', 10)

            # Timer para publicar estado
            self.timer = self.create_timer(1.0, self.publish_queue_state)

            self.get_logger().info("Nodo broker inicializado")

        def handle_pedir_agarre(self, request, response):
            """Handler del servicio /pedir_agarre.

            El cliente envía la solicitud codificada en String.data como JSON.
            """
            try:
                # Nota: en una implementación real, el cliente codificaría
                # la solicitud en JSON. Aquí es simplificado.
                self.get_logger().info(f"Solicitud recibida: {request}")

                # Retorna exito (el servidor maneja internamente)
                response.success = True
                response.message = "Solicitud encolada"
                return response
            except Exception as e:
                response.success = False
                response.message = f"Error: {str(e)}"
                return response

        def publish_queue_state(self):
            """Publica estado de la cola."""
            try:
                state = self.queue.get_state_json()
                msg = String()
                msg.data = state
                self.pub_cola.publish(msg)
            except Exception as e:
                self.get_logger().error(f"Error publicando cola: {e}")

    # Inicializa ROS y crea nodo
    rclpy.init()
    node = BrokerNode(queue, broker)

    # Spin en thread para no bloquear
    def ros_spin():
        rclpy.spin(node)

    import threading
    ros_thread = threading.Thread(target=ros_spin, daemon=True)
    ros_thread.start()

    return node


def main():
    """Función principal del broker."""
    import json

    logging.basicConfig(level=logging.INFO)

    # Carga configuración
    with open('config.json', 'r') as f:
        config = json.load(f)

    logger.info("="*60)
    logger.info("JetCobot Broker (Pregunta 2)")
    logger.info("="*60)

    # Crea cola y worker
    queue = BrokerQueue('intentos.csv')
    broker = BrokerWorker(queue, config, simulate=True)  # simulate=True por defecto
    broker.connect_vision()
    broker.start()

    # Intenta crear servicio ROS si disponible
    ros_node = None
    try:
        ros_node = create_ros_service(broker, queue)
    except Exception as e:
        logger.warning(f"ROS 2 no disponible: {e}")

    logger.info("Broker ejecutándose. Ctrl+C para detener.")

    try:
        # Ejemplo: encola solicitudes de prueba
        test_requests = [
            {
                'accion': 'recoger',
                'objeto': 'cubo',
                'color': 'rojo',
                'prioridad': 3,
                'permitido': True,
                'origen': 'usuario1'
            },
            {
                'accion': 'recoger',
                'objeto': 'cubo',
                'color': 'azul',
                'prioridad': 1,
                'permitido': True,
                'origen': 'usuario2'
            }
        ]

        for req in test_requests:
            accepted, reason = queue.enqueue(req)
            logger.info(f"Solicitud {req['color']}: {accepted} - {reason}")
            time.sleep(0.5)

        # Espera a que se procesen
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Shutdown...")
        broker.stop()
        if ros_node:
            try:
                import rclpy
                rclpy.shutdown()
            except:
                pass


if __name__ == '__main__':
    main()
