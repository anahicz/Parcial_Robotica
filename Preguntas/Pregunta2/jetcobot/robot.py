"""
Módulo adaptador para el robot myCobot 280.
Proporciona una interfaz uniforme con la clase SimRobot para simulación.
"""
import time
import json
import logging
from typing import List, Tuple, Dict, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class RobotAdapter(ABC):
    """Interfaz base para interactuar con el robot."""

    @abstractmethod
    def power_on(self) -> bool:
        """Enciende el robot."""
        pass

    @abstractmethod
    def get_angles(self) -> Optional[List[float]]:
        """Obtiene los ángulos actuales de las articulaciones (grados)."""
        pass

    @abstractmethod
    def send_angles(self, angles: List[float], speed: int) -> bool:
        """Envía ángulos de articulación y espera a que se alcancen."""
        pass

    @abstractmethod
    def get_coords(self) -> Optional[List[float]]:
        """Obtiene las coordenadas cartesianas actuales [x, y, z, rx, ry, rz]."""
        pass

    @abstractmethod
    def send_coords(self, coords: List[float], speed: int, mode: int = 1) -> bool:
        """Envía coordenadas cartesianas y espera a que se alcancen.

        Args:
            coords: [x, y, z, rx, ry, rz]
            speed: velocidad (1-100)
            mode: 0=articulación, 1=lineal
        """
        pass

    @abstractmethod
    def is_moving(self) -> bool:
        """Comprueba si el robot está en movimiento."""
        pass

    @abstractmethod
    def set_gripper_state(self, flag: int, speed: int) -> bool:
        """Controla el gripper.

        Args:
            flag: 0=abrir, 1=cerrar
            speed: velocidad (1-100)
        """
        pass

    @abstractmethod
    def set_gripper_value(self, value: int, speed: int) -> bool:
        """Establece el valor del gripper (0-100).

        Args:
            value: 0=abierto, 100=cerrado
            speed: velocidad (1-100)
        """
        pass

    @abstractmethod
    def release_all_servos(self) -> bool:
        """Libera todos los servos para movimiento manual."""
        pass

    @abstractmethod
    def stop(self) -> bool:
        """Detiene todo movimiento inmediatamente."""
        pass


class MyCoBot280(RobotAdapter):
    """Adaptador para el robot real myCoBot 280."""

    def __init__(self, port: str, baudrate: int = 1000000, timeout: float = 5):
        """Inicializa la conexión con el robot real.

        Args:
            port: puerto serial (e.g., '/dev/ttyUSB0')
            baudrate: velocidad en bauds (por defecto 1000000)
            timeout: timeout en segundos para operaciones de lectura
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.robot = None

        try:
            # Intenta importar pymycobot
            try:
                from pymycobot.mycobot280 import MyCobot280 as MC280
            except ImportError:
                from pymycobot.mycobot import MyCobot as MC280

            self.robot = MC280(port=port, baudrate=baudrate)
            logger.info(f"Robot real conectado en {port}")
        except Exception as e:
            logger.error(f"Error al conectar robot real en {port}: {e}")
            raise

    def power_on(self) -> bool:
        """Enciende el robot."""
        try:
            self.robot.power_on()
            time.sleep(0.5)
            return True
        except Exception as e:
            logger.error(f"Error al encender robot: {e}")
            return False

    def get_angles(self) -> Optional[List[float]]:
        """Obtiene los ángulos actuales."""
        try:
            angles = self.robot.get_angles()
            if angles:
                return list(angles)
            return None
        except Exception as e:
            logger.error(f"Error al leer ángulos: {e}")
            return None

    def send_angles(self, angles: List[float], speed: int, config: Optional[Dict] = None) -> bool:
        """Envía ángulos y espera a que se alcancen con tolerancia.

        Maneja race condition: espera a que el movimiento INICIE antes de verificar parada.
        """
        try:
            # Verifica límites
            joint_limits = [
                (-165, 165),  # J1
                (-165, 165),  # J2
                (-165, 165),  # J3
                (-165, 165),  # J4
                (-165, 165),  # J5
                (-175, 175)   # J6
            ]
            for i, (angle, (min_a, max_a)) in enumerate(zip(angles, joint_limits)):
                if not (min_a <= angle <= max_a):
                    logger.error(f"Ángulo J{i+1}={angle} fuera de límites [{min_a}, {max_a}]")
                    return False

            # Envía los ángulos
            self.robot.send_angles(angles, speed)

            # Espera a que se alcancen con tolerancia
            tolerance = 2.5  # grados
            max_wait = 30  # segundos
            start_window = config.get('motion', {}).get('motion_start_window_s', 1.5) if config else 1.5

            start_time = time.time()
            pose_started = False
            last_angles = self.get_angles()

            # Fase 1: Espera a que el movimiento inicie
            while time.time() - start_time < start_window:
                if self.is_moving():
                    pose_started = True
                    logger.debug("Movimiento iniciado (is_moving=True)")
                    break

                current = self.get_angles()
                if current and last_angles:
                    angle_change = max(abs(c - l) for c, l in zip(current, last_angles))
                    if angle_change > 0.5:  # 0.5° cambio
                        pose_started = True
                        logger.debug(f"Movimiento detectado: {angle_change:.2f}°")
                        break

                time.sleep(0.05)

            # Si ya estamos en posición, retorna True
            current = self.get_angles()
            if current:
                error = max(abs(c - a) for c, a in zip(current, angles))
                if error <= tolerance:
                    logger.info(f"Ya en posición destino: error={error:.2f}°")
                    return True

            if not pose_started:
                logger.info(f"Movimiento no detectado en {start_window}s, esperando...")

            # Fase 2: Espera a que se termine el movimiento
            while time.time() - start_time < max_wait:
                if not self.is_moving():
                    current = self.get_angles()
                    if current:
                        error = max(abs(c - a) for c, a in zip(current, angles))
                        if error <= tolerance:
                            logger.info(f"Ángulos alcanzados: error={error:.2f}°")
                            return True
                        else:
                            logger.warning(f"Error de posición: {error:.2f}° (tolerancia={tolerance}°)")
                            return False
                time.sleep(0.1)

            logger.error(f"Timeout esperando ángulos después de {max_wait}s")
            return False
        except Exception as e:
            logger.error(f"Error al enviar ángulos: {e}")
            return False

    def get_coords(self) -> Optional[List[float]]:
        """Obtiene las coordenadas actuales."""
        try:
            coords = self.robot.get_coords()
            if coords:
                return list(coords)
            return None
        except Exception as e:
            logger.error(f"Error al leer coordenadas: {e}")
            return None

    def send_coords(self, coords: List[float], speed: int, mode: int = 1,
                   config: Optional[Dict] = None) -> bool:
        """Envía coordenadas cartesianas y espera a que se alcancen.

        Valida workspace (reach, z_min/max, orientación) si config disponible.
        Maneja race condition inicial: espera a que el movimiento INICIE antes de verificar parada.
        """
        try:
            # Validación de workspace si config disponible
            if config:
                workspace = config.get('motion', {}).get('workspace', {})

                x, y, z = coords[0], coords[1], coords[2]
                rx, ry, rz = coords[3], coords[4], coords[5]

                # Chequea límite radial (reach)
                reach_max = workspace.get('reach_max_mm', 280)
                radial_dist = (x**2 + y**2)**0.5
                if radial_dist > reach_max:
                    logger.error(f"Coords fuera de reach: sqrt({x}²+{y}²)={radial_dist:.1f} > {reach_max}")
                    return False

                # Chequea límite Z mínimo (mesa/seguridad)
                z_min = workspace.get('z_min_mm', 90)
                if z < z_min:
                    logger.error(f"Z={z} por debajo de z_min={z_min} (mesa). Mide tu tabla con --ensenar")
                    return False

                # Chequea límite Z máximo
                z_max = workspace.get('z_max_mm', 400)
                if z > z_max:
                    logger.error(f"Z={z} por encima de z_max={z_max}")
                    return False

                # Chequea orientación
                orient_limit = workspace.get('orientation_limit_deg', 180)
                for name, val in [('rx', rx), ('ry', ry), ('rz', rz)]:
                    if abs(val) > orient_limit:
                        logger.error(f"{name}={val} fuera de [-{orient_limit}, {orient_limit}]")
                        return False

            self.robot.send_coords(coords, speed, mode)

            # Espera a que el movimiento INICIE antes de verificar parada (evita race condition)
            # PARCHE_TOLERANCIA: tolerancia desde config.json (antes fija en 5 mm)
            tolerance = (config or {}).get('motion', {}).get('tolerance_coords_mm', 5)
            # PARCHE_TOLERANCIA2: z con su propia tolerancia; x/y siguen estrictas
            tol_z = (config or {}).get('motion', {}).get('tolerance_z_mm', tolerance)
            def _dentro(cur):
                ejes = [round(c - co, 1) for c, co in zip(cur[:3], coords[:3])]
                return max(abs(ejes[0]), abs(ejes[1])) <= tolerance and abs(ejes[2]) <= tol_z, ejes
            max_wait = 30  # segundos
            start_window = config.get('motion', {}).get('motion_start_window_s', 1.5) if config else 1.5

            start_time = time.time()
            pose_started = False
            last_pose = self.get_coords()

            # Fase 1: Espera a que el movimiento inicie (is_moving() True o pose cambia)
            while time.time() - start_time < start_window:
                if self.is_moving():
                    pose_started = True
                    logger.debug("Movimiento iniciado (is_moving=True)")
                    break

                current = self.get_coords()
                if current and last_pose:
                    pose_change = max(abs(c - l) for c, l in zip(current[:3], last_pose[:3]))
                    if pose_change > 1.0:
                        pose_started = True
                        logger.debug(f"Movimiento detectado por cambio de pose: {pose_change:.2f}mm")
                        break

                time.sleep(0.05)

            # Si ya estamos en la posición destino, retorna True
            current = self.get_coords() if not pose_started else None
            if current:
                ok_pos, ejes = _dentro(current)
                if ok_pos:
                    logger.info(f"Ya en posición destino: dx,dy,dz={ejes}")
                    return True

            if not pose_started:
                # PARCHE_REENVIO: el myCobot a veces descarta una orden que llega justo despues
                # de otra (por ejemplo, abrir la pinza). Si no arranco, se reenvia UNA vez.
                logger.warning(f"Movimiento no detectado en {start_window}s: reenvio la orden una vez")
                time.sleep(0.3)
                self.robot.send_coords(coords, speed, mode)
                t1 = time.time()
                while time.time() - t1 < start_window:
                    if self.is_moving():
                        pose_started = True
                        break
                    time.sleep(0.05)
                start_time = time.time()

            # Fase 2: Espera a que se termine el movimiento
            while time.time() - start_time < max_wait:
                if not self.is_moving():
                    # El brazo puede seguir asentándose: hasta 5 lecturas en 1 s
                    for _ in range(5):
                        current = self.get_coords()
                        if current:
                            ok_pos, ejes = _dentro(current)
                            if ok_pos:
                                logger.info(f"Coordenadas alcanzadas: dx,dy,dz={ejes}")
                                return True
                        time.sleep(0.2)
                    if current:
                        logger.warning(f"Error de posición: dx,dy,dz={ejes} (tol x/y={tolerance}, z={tol_z} mm)")
                    return False
                time.sleep(0.1)

            logger.error(f"Timeout esperando coordenadas después de {max_wait}s")
            return False
        except Exception as e:
            logger.error(f"Error al enviar coordenadas: {e}")
            return False

    def is_moving(self) -> bool:
        """Comprueba si está en movimiento."""
        try:
            # is_moving() retorna True si está moviendo, False si no
            return bool(self.robot.is_moving())
        except Exception as e:
            logger.error(f"Error al comprobar movimiento: {e}")
            return False

    def set_gripper_state(self, flag: int, speed: int) -> bool:
        """Controla el gripper (0=abrir, 1=cerrar)."""
        try:
            self.robot.set_gripper_state(flag, speed)
            time.sleep(1)  # Espera a que se cierre/abra
            return True
        except Exception as e:
            logger.error(f"Error al controlar gripper: {e}")
            return False

    def set_gripper_value(self, value: int, speed: int) -> bool:
        """Establece el valor del gripper (0-100)."""
        try:
            if not (0 <= value <= 100):
                logger.error(f"Valor de gripper {value} fuera de rango [0, 100]")
                return False

            self.robot.set_gripper_value(value, speed)
            time.sleep(1)  # Espera a que se complete
            return True
        except Exception as e:
            logger.error(f"Error al establecer valor de gripper: {e}")
            return False

    def release_all_servos(self) -> bool:
        """Libera todos los servos."""
        try:
            self.robot.release_all_servos()
            time.sleep(0.5)
            return True
        except Exception as e:
            logger.error(f"Error al liberar servos: {e}")
            return False

    def stop(self) -> bool:
        """Detiene el movimiento."""
        try:
            # Intenta detener el robot
            self.robot.stop()
            return True
        except Exception as e:
            logger.error(f"Error al detener robot: {e}")
            return False


class SimRobot(RobotAdapter):
    """Simulador del robot para pruebas sin hardware."""

    def __init__(self):
        """Inicializa el simulador con posición HOME."""
        self.angles = [0.0, 0.0, 0.0, 0.0, 0.0, -45.0]
        self.coords = None  # Se calcularía con cinemática directa
        self.gripper_value = 100  # 100=abierto, 0=cerrado
        self.is_moving_flag = False
        self.powered_on = False
        logger.info("SimRobot inicializado (sin hardware)")

    def power_on(self) -> bool:
        """Enciende el simulador."""
        self.powered_on = True
        logger.info("SimRobot: POWER_ON")
        return True

    def get_angles(self) -> Optional[List[float]]:
        """Retorna los ángulos actuales simulados."""
        logger.debug(f"SimRobot: GET_ANGLES -> {self.angles}")
        return self.angles.copy()

    def send_angles(self, angles: List[float], speed: int, config: Optional[Dict] = None) -> bool:
        """Simula el envío de ángulos con validación de límites."""
        # Verifica límites
        joint_limits = [
            (-165, 165),
            (-165, 165),
            (-165, 165),
            (-165, 165),
            (-165, 165),
            (-175, 175)
        ]
        for i, (angle, (min_a, max_a)) in enumerate(zip(angles, joint_limits)):
            if not (min_a <= angle <= max_a):
                logger.error(f"SimRobot: Ángulo J{i+1}={angle} fuera de límites [{min_a}, {max_a}]")
                return False

        logger.info(f"SimRobot: SEND_ANGLES {angles} speed={speed}")
        self.is_moving_flag = True

        # Simula movimiento con start delay configurable
        start_delay = 0.05
        if config:
            start_delay = min(0.05, config.get('motion', {}).get('motion_start_window_s', 1.5) * 0.1)

        time.sleep(start_delay)  # Simula delay antes de que inicie el movimiento
        time.sleep(0.15)  # Simula movimiento

        # Actualiza posición
        self.angles = [float(a) for a in angles]
        self.is_moving_flag = False
        logger.info(f"SimRobot: Ángulos alcanzados")
        return True

    def get_coords(self) -> Optional[List[float]]:
        """Retorna coordenadas simuladas (aproximadas)."""
        # Simplificación: retorna valores plausibles
        if self.coords is None:
            self.coords = [100.0, 0.0, 100.0, 180.0, 0.0, 0.0]
        logger.debug(f"SimRobot: GET_COORDS -> {self.coords}")
        return self.coords.copy()

    def send_coords(self, coords: List[float], speed: int, mode: int = 1,
                   config: Optional[Dict] = None) -> bool:
        """Simula el envío de coordenadas con validación de workspace."""
        # Validación de workspace
        if config:
            workspace = config.get('motion', {}).get('workspace', {})

            x, y, z = coords[0], coords[1], coords[2]
            rx, ry, rz = coords[3], coords[4], coords[5]

            # Chequea límites
            reach_max = workspace.get('reach_max_mm', 280)
            radial_dist = (x**2 + y**2)**0.5
            if radial_dist > reach_max:
                logger.error(f"SimRobot: Coords fuera de reach: {radial_dist:.1f} > {reach_max}")
                return False

            z_min = workspace.get('z_min_mm', 90)
            if z < z_min:
                logger.error(f"SimRobot: Z={z} por debajo de z_min={z_min}")
                return False

            z_max = workspace.get('z_max_mm', 400)
            if z > z_max:
                logger.error(f"SimRobot: Z={z} por encima de z_max={z_max}")
                return False

            orient_limit = workspace.get('orientation_limit_deg', 180)
            for name, val in [('rx', rx), ('ry', ry), ('rz', rz)]:
                if abs(val) > orient_limit:
                    logger.error(f"SimRobot: {name}={val} fuera de límites")
                    return False

        logger.info(f"SimRobot: SEND_COORDS {coords} speed={speed} mode={mode}")
        self.is_moving_flag = True

        # Simula delay antes de iniciar (reproduce race condition potential)
        start_delay = 0.05
        if config:
            start_delay = min(0.05, config.get('motion', {}).get('motion_start_window_s', 1.5) * 0.1)

        time.sleep(start_delay)
        time.sleep(0.15)  # Simula movimiento

        self.coords = [float(c) for c in coords]
        self.is_moving_flag = False
        logger.info(f"SimRobot: Coordenadas alcanzadas")
        return True

    def is_moving(self) -> bool:
        """Retorna si está en movimiento (simulado)."""
        return self.is_moving_flag

    def set_gripper_state(self, flag: int, speed: int) -> bool:
        """Simula control del gripper por estado."""
        state_str = "ABRIR" if flag == 0 else "CERRAR"
        logger.info(f"SimRobot: GRIPPER {state_str} speed={speed}")
        self.gripper_value = 100 if flag == 0 else 60
        time.sleep(0.2)
        return True

    def set_gripper_value(self, value: int, speed: int) -> bool:
        """Simula control del gripper por valor."""
        if not (0 <= value <= 100):
            logger.error(f"SimRobot: Valor de gripper {value} fuera de rango")
            return False
        logger.info(f"SimRobot: GRIPPER_VALUE {value} speed={speed}")
        self.gripper_value = value
        time.sleep(0.2)
        return True

    def release_all_servos(self) -> bool:
        """Simula liberar servos."""
        logger.info("SimRobot: RELEASE_ALL_SERVOS")
        return True

    def stop(self) -> bool:
        """Simula detener movimiento."""
        logger.info("SimRobot: STOP")
        self.is_moving_flag = False
        return True


def create_robot(simulate: bool, config: dict) -> RobotAdapter:
    """Factory para crear instancia del robot real o simulado.

    Args:
        simulate: si True, crea SimRobot; si False, crea MyCoBot280 real
        config: diccionario de configuración

    Returns:
        Instancia de RobotAdapter
    """
    if simulate:
        return SimRobot()
    else:
        port = config['robot']['serial_port']
        baudrate = config['robot']['baudrate']
        return MyCoBot280(port=port, baudrate=baudrate)
