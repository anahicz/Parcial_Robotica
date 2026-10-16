"""
Cinemática directa (FK) para myCobot 280.
Parámetros DH según Elephant Robotics / Yahboom.

myCobot 280 (6 DOF):
- Longitudes: L1=131.9mm, L2=136mm, L3=108.5mm, L4=55.5mm, L5=55.8mm, L6=74mm
- Espacio de trabajo: ~300mm de radio, altura 200-400mm
- Rango articular: J1..J5 ±165°, J6 ±175°
"""
import numpy as np
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


class MyCoBot280FK:
    """Cinemática directa para myCoBot 280."""

    # Parámetros DH (Denavit-Hartenberg)
    # d: distancia entre frames (mm)
    # a: longitud del eslabón (mm)
    # alpha: ángulo de torsión (rad)
    # theta0: offset de ángulo (rad)

    DH_PARAMS = [
        # J1
        {'d': 131.9, 'a': 0, 'alpha': 0, 'theta0': 0},
        # J2
        {'d': 0, 'a': 136, 'alpha': 0, 'theta0': 0},
        # J3
        {'d': 0, 'a': 108.5, 'alpha': 0, 'theta0': 0},
        # J4
        {'d': 0, 'a': 0, 'alpha': -np.pi/2, 'theta0': 0},
        # J5
        {'d': 55.5, 'a': 0, 'alpha': np.pi/2, 'theta0': 0},
        # J6 (gripper)
        {'d': 55.8, 'a': 0, 'alpha': 0, 'theta0': 0},
    ]

    def __init__(self):
        """Inicializa la cinemática."""
        self.dh = self.DH_PARAMS
        logger.info("FK myCoBot 280 inicializado")

    def _dh_matrix(self, theta: float, d: float, a: float, alpha: float) -> np.ndarray:
        """Crea matriz de transformación DH.

        Args:
            theta: ángulo de articulación (rad)
            d: desplazamiento d (mm)
            a: longitud a (mm)
            alpha: ángulo de torsión (rad)

        Returns:
            Matriz 4x4 de transformación homogénea
        """
        c_theta = np.cos(theta)
        s_theta = np.sin(theta)
        c_alpha = np.cos(alpha)
        s_alpha = np.sin(alpha)

        T = np.array([
            [c_theta, -s_theta*c_alpha, s_theta*s_alpha, a*c_theta],
            [s_theta, c_theta*c_alpha, -c_theta*s_alpha, a*s_theta],
            [0, s_alpha, c_alpha, d],
            [0, 0, 0, 1]
        ], dtype=np.float32)

        return T

    def forward_kinematics(self, angles_deg: List[float]) -> Optional[np.ndarray]:
        """Calcula la posición del efector final.

        Args:
            angles_deg: ángulos de las 6 articulaciones en grados

        Returns:
            Matriz 4x4 de transformación del efector final, o None si error
        """
        if len(angles_deg) != 6:
            logger.error(f"Se requieren 6 ángulos, se recibieron {len(angles_deg)}")
            return None

        try:
            # Convierte a radianes
            angles_rad = np.deg2rad(angles_deg)

            # Matriz de transformación acumulada
            T = np.eye(4, dtype=np.float32)

            # Multiplica transformaciones de cada eslabón
            for i, angle_rad in enumerate(angles_rad):
                d = self.dh[i]['d']
                a = self.dh[i]['a']
                alpha = self.dh[i]['alpha']

                Ti = self._dh_matrix(angle_rad, d, a, alpha)
                T = T @ Ti

            return T
        except Exception as e:
            logger.error(f"Error en FK: {e}")
            return None

    def get_end_effector_position(self, angles_deg: List[float]) -> Optional[Tuple[float, float, float]]:
        """Obtiene la posición XYZ del efector final.

        Args:
            angles_deg: ángulos de articulación en grados

        Returns:
            Tupla (x, y, z) en mm, o None si error
        """
        T = self.forward_kinematics(angles_deg)
        if T is None:
            return None

        # Extrae posición del último 4x4
        x = T[0, 3]
        y = T[1, 3]
        z = T[2, 3]

        return (x, y, z)

    def get_orientation(self, angles_deg: List[float]) -> Optional[Tuple[float, float, float]]:
        """Obtiene la orientación (rx, ry, rz) del efector final en grados.

        Args:
            angles_deg: ángulos de articulación en grados

        Returns:
            Tupla (rx, ry, rz) en grados, o None si error
        """
        T = self.forward_kinematics(angles_deg)
        if T is None:
            return None

        # Extrae matriz de rotación
        R = T[:3, :3]

        # Calcula ángulos de Euler (ZYX) - depende de convención
        # Usando convención Roll-Pitch-Yaw
        ry = np.arcsin(-R[2, 0])
        rx = np.arctan2(R[2, 1], R[2, 2])
        rz = np.arctan2(R[1, 0], R[0, 0])

        # Convierte a grados
        rx_deg = np.rad2deg(rx)
        ry_deg = np.rad2deg(ry)
        rz_deg = np.rad2deg(rz)

        return (rx_deg, ry_deg, rz_deg)

    def get_full_pose(self, angles_deg: List[float]) -> Optional[List[float]]:
        """Obtiene la pose completa (x, y, z, rx, ry, rz).

        Args:
            angles_deg: ángulos de articulación en grados

        Returns:
            Lista [x, y, z, rx, ry, rz] o None si error
        """
        pos = self.get_end_effector_position(angles_deg)
        ori = self.get_orientation(angles_deg)

        if pos is None or ori is None:
            return None

        return list(pos) + list(ori)

    def compute_position_error(self, commanded_angles: List[float],
                              actual_coords: List[float]) -> Optional[float]:
        """Calcula el error de posición entre FK y coords medidas.

        Args:
            commanded_angles: ángulos comandados (grados)
            actual_coords: coordenadas medidas [x, y, z, rx, ry, rz]

        Returns:
            Error euclidiano en posición XYZ (mm), o None si error
        """
        fk_pose = self.get_full_pose(commanded_angles)
        if fk_pose is None:
            return None

        fk_xyz = fk_pose[:3]
        actual_xyz = actual_coords[:3]

        error = np.linalg.norm(np.array(fk_xyz) - np.array(actual_xyz))
        return float(error)


def test_fk_known_positions():
    """Prueba FK con posiciones conocidas."""
    fk = MyCoBot280FK()

    # Posición HOME: todos los ángulos en 0 (excepto J6=-45)
    home_angles = [0, 0, 0, 0, 0, -45]
    pos = fk.get_end_effector_position(home_angles)
    logger.info(f"HOME FK: {pos}")

    # Posición OBSERVATION
    obs_angles = [13.53, 27.5, -53.48, -47.1, 0.52, -29.26]
    pos = fk.get_end_effector_position(obs_angles)
    logger.info(f"OBSERVATION FK: {pos}")

    # Posición RED (ejemplo)
    red_angles = [4.2, -15.44, -115.14, 42.49, 1.58, -43.33]
    pos = fk.get_end_effector_position(red_angles)
    logger.info(f"RED FK: {pos}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    test_fk_known_positions()
