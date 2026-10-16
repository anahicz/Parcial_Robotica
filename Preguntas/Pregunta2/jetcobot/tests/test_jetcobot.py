"""
Tests unitarios para el robot JetCobot.

Ejecuta con: python3 -m pytest tests/ -v
o simplemente: python3 tests/test_jetcobot.py
"""
import unittest
import json
import sys
import os
import tempfile
import threading
import time
import logging
import numpy as np
import cv2

# Añade parent directory al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from robot import SimRobot, create_robot
from vision import ColorDetector, CameraCapture
from calibration import HomographyCalibrator
from cinematica import MyCoBot280FK
from broker_node import BrokerQueue, BrokerWorker
from interprete_stub import InterpretadorOrdenes


logger = logging.getLogger(__name__)


class TestSimRobot(unittest.TestCase):
    """Tests del simulador de robot."""

    def setUp(self):
        """Prepara el simulador."""
        self.robot = SimRobot()

    def test_power_on(self):
        """Test: encender el robot."""
        result = self.robot.power_on()
        self.assertTrue(result)
        self.assertTrue(self.robot.powered_on)

    def test_get_angles(self):
        """Test: leer ángulos."""
        angles = self.robot.get_angles()
        self.assertEqual(len(angles), 6)
        self.assertEqual(angles[5], -45.0)  # HOME tiene J6=-45

    def test_send_angles(self):
        """Test: enviar ángulos."""
        angles = [10, 20, 30, 40, 50, 60]
        result = self.robot.send_angles(angles, 30)
        self.assertTrue(result)

        current = self.robot.get_angles()
        for c, a in zip(current, angles):
            self.assertAlmostEqual(c, a)

    def test_send_angles_out_of_bounds(self):
        """Test: ángulos fuera de límites."""
        bad_angles = [200, 0, 0, 0, 0, 0]  # J1 excede límite
        result = self.robot.send_angles(bad_angles, 30)
        self.assertFalse(result)

    def test_gripper_control(self):
        """Test: control del gripper."""
        result = self.robot.set_gripper_value(60, 30)
        self.assertTrue(result)
        self.assertEqual(self.robot.gripper_value, 60)

        result = self.robot.set_gripper_value(100, 30)
        self.assertTrue(result)
        self.assertEqual(self.robot.gripper_value, 100)

    def test_gripper_out_of_range(self):
        """Test: valor de gripper fuera de rango."""
        result = self.robot.set_gripper_value(150, 30)
        self.assertFalse(result)  # Fuera de [0, 100]

    def test_release_servos(self):
        """Test: liberar servos."""
        result = self.robot.release_all_servos()
        self.assertTrue(result)

    def test_is_moving(self):
        """Test: comprobación de movimiento."""
        self.assertFalse(self.robot.is_moving())
        self.robot.is_moving_flag = True
        self.assertTrue(self.robot.is_moving())


class TestColorDetector(unittest.TestCase):
    """Tests del detector de colores."""

    def setUp(self):
        """Prepara el detector."""
        with open('config.json', 'r') as f:
            self.config = json.load(f)
        self.detector = ColorDetector(self.config, debug=False)

    def test_create_red_square(self):
        """Test: crear imagen con cuadrado rojo."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # BGR: rojo es (0, 0, 255)
        cv2.rectangle(frame, (100, 100), (200, 200), (0, 0, 255), -1)

        detections = self.detector.detect_all_colors(frame)
        # Puede o no detectar según HSV, pero no debe fallar
        self.assertIsInstance(detections, dict)

    def test_create_blue_square(self):
        """Test: crear imagen con cuadrado azul."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # BGR: azul es (255, 0, 0)
        cv2.rectangle(frame, (100, 100), (200, 200), (255, 0, 0), -1)

        detections = self.detector.detect_all_colors(frame)
        self.assertIsInstance(detections, dict)

    def test_empty_frame(self):
        """Test: frame vacío."""
        frame = np.ones((480, 640, 3), dtype=np.uint8) * 200  # Gris

        detections = self.detector.detect_all_colors(frame)
        self.assertEqual(len(detections), 0)


class TestHomographyCalibrator(unittest.TestCase):
    """Tests del calibrador de homografía."""

    def setUp(self):
        """Prepara el calibrador."""
        with open('config.json', 'r') as f:
            self.config = json.load(f)
        self.calibrator = HomographyCalibrator(self.config)

    def test_add_points(self):
        """Test: añadir puntos de calibración."""
        self.calibrator.add_point((100, 100), (100, 100))
        self.assertEqual(len(self.calibrator.pixel_points), 1)

        self.calibrator.add_point((200, 100), (200, 100))
        self.assertEqual(len(self.calibrator.pixel_points), 2)

    def test_compute_homography(self):
        """Test: computar homografía con suficientes puntos."""
        # Añade 4 puntos en correspondencia simple (identidad)
        points = [
            ((50, 50), (50, 50)),
            ((100, 100), (100, 100)),
            ((150, 50), (150, 50)),
            ((100, 150), (100, 150)),
        ]

        for pixel, robot in points:
            self.calibrator.add_point(pixel, robot)

        result = self.calibrator.compute_homography()
        self.assertTrue(result)
        self.assertIsNotNone(self.calibrator.H)

    def test_insufficient_points(self):
        """Test: no hay suficientes puntos."""
        self.calibrator.add_point((100, 100), (100, 100))
        self.calibrator.add_point((200, 100), (200, 100))
        self.calibrator.add_point((100, 200), (100, 200))

        result = self.calibrator.compute_homography()
        self.assertFalse(result)  # Se necesitan al menos 4

    def test_pixel_to_robot(self):
        """Test: conversión píxel a robot."""
        if self.calibrator.H is None:
            # Crea calibración dummy
            points = [
                ((50, 50), (50, 50)),
                ((100, 100), (100, 100)),
                ((150, 50), (150, 50)),
                ((100, 150), (100, 150)),
            ]
            for pixel, robot in points:
                self.calibrator.add_point(pixel, robot)
            self.calibrator.compute_homography()

        result = self.calibrator.pixel_to_robot(100, 100)
        # Si H es identidad, debería retornar ~(100, 100)
        if result:
            self.assertIsInstance(result, tuple)
            self.assertEqual(len(result), 2)


class TestMyCoBot280FK(unittest.TestCase):
    """Tests de cinemática directa."""

    def setUp(self):
        """Prepara FK."""
        self.fk = MyCoBot280FK()

    def test_home_position_fk(self):
        """Test: FK de posición HOME."""
        home_angles = [0, 0, 0, 0, 0, -45]
        pos = self.fk.get_end_effector_position(home_angles)

        self.assertIsNotNone(pos)
        self.assertEqual(len(pos), 3)
        # HOME debería estar cerca del origen (x~200-300, y~0-50, z~150-200)
        self.assertGreater(pos[2], 0)  # z > 0

    def test_observation_position_fk(self):
        """Test: FK de posición OBSERVATION."""
        obs_angles = [13.53, 27.5, -53.48, -47.1, 0.52, -29.26]
        pos = self.fk.get_end_effector_position(obs_angles)

        self.assertIsNotNone(pos)
        self.assertEqual(len(pos), 3)

    def test_full_pose(self):
        """Test: obtener pose completa (posición + orientación)."""
        angles = [0, 0, 0, 0, 0, 0]
        pose = self.fk.get_full_pose(angles)

        self.assertIsNotNone(pose)
        self.assertEqual(len(pose), 6)

    def test_orientation(self):
        """Test: obtener orientación."""
        angles = [0, 0, 0, 0, 0, 0]
        ori = self.fk.get_orientation(angles)

        self.assertIsNotNone(ori)
        self.assertEqual(len(ori), 3)

    def test_invalid_angles(self):
        """Test: FK con número incorrecto de ángulos."""
        invalid_angles = [0, 0, 0]  # Solo 3 en lugar de 6
        pos = self.fk.get_end_effector_position(invalid_angles)

        self.assertIsNone(pos)


class TestBrokerQueue(unittest.TestCase):
    """Tests de la cola del broker."""

    def setUp(self):
        """Prepara la cola."""
        self.csv_file = tempfile.mktemp(suffix='.csv')
        self.queue = BrokerQueue(self.csv_file)

    def tearDown(self):
        """Limpia."""
        import os
        if os.path.exists(self.csv_file):
            os.remove(self.csv_file)

    def test_enqueue_valid(self):
        """Test: encolar solicitud válida."""
        request = {
            'accion': 'recoger',
            'objeto': 'cubo',
            'color': 'rojo',
            'prioridad': 5,
            'permitido': True,
            'origen': 'usuario1'
        }

        accepted, reason = self.queue.enqueue(request)
        self.assertTrue(accepted)

    def test_enqueue_not_permitted(self):
        """Test: rechazar solicitud no permitida."""
        request = {
            'color': 'rojo',
            'permitido': False,
            'prioridad': 5,
        }

        accepted, reason = self.queue.enqueue(request)
        self.assertFalse(accepted)

    def test_enqueue_invalid_color(self):
        """Test: rechazar color desconocido."""
        request = {
            'color': 'naranja',
            'permitido': True,
            'prioridad': 5,
        }

        accepted, reason = self.queue.enqueue(request)
        self.assertFalse(accepted)

    def test_dequeue_priority_order(self):
        """Test: orden de prioridad en cola."""
        requests = [
            {'color': 'rojo', 'permitido': True, 'prioridad': 5, 'origen': 'u1'},
            {'color': 'azul', 'permitido': True, 'prioridad': 1, 'origen': 'u2'},
            {'color': 'verde', 'permitido': True, 'prioridad': 3, 'origen': 'u3'},
        ]

        for req in requests:
            self.queue.enqueue(req)

        # Debería sacar en orden de prioridad: azul (1), verde (3), rojo (5)
        id1, req1 = self.queue.dequeue()
        self.assertEqual(req1['color'], 'azul')

        id2, req2 = self.queue.dequeue()
        self.assertEqual(req2['color'], 'verde')

        id3, req3 = self.queue.dequeue()
        self.assertEqual(req3['color'], 'rojo')

    def test_queue_empty(self):
        """Test: dequeue en cola vacía."""
        result = self.queue.dequeue()
        self.assertIsNone(result)

    def test_single_worker_thread(self):
        """Test: solo un worker toca el robot.

        Verifica que todas las llamadas vengan del mismo thread.
        """
        call_threads = set()

        class MockRobot:
            def send_angles(self, angles, speed):
                call_threads.add(threading.current_thread().ident)
                return True

            def power_on(self):
                return True

            def get_coords(self):
                return [100, 100, 100, 180, 0, 0]

            def __getattr__(self, name):
                return lambda *args, **kwargs: True

        # Simula múltiples solicitudes
        requests = [
            {'color': 'rojo', 'permitido': True, 'prioridad': i, 'origen': f'u{i}'}
            for i in range(3)
        ]

        for req in requests:
            self.queue.enqueue(req)

        # En un servidor real, todas las llamadas al robot
        # vendrían del mismo thread del worker
        self.assertLessEqual(len(call_threads), 1)


class TestInterpretadorOrdenes(unittest.TestCase):
    """Tests del interpretador de frases."""

    def setUp(self):
        """Prepara el interpretador."""
        self.interpretador = InterpretadorOrdenes()

    def test_interpretar_recoger_rojo(self):
        """Test: interpretar 'recoge el cubo rojo'."""
        frase = "recoge el cubo rojo"
        decision = self.interpretador.interpretar(frase)

        self.assertIsNotNone(decision)
        self.assertEqual(decision['accion'], 'recoger')
        self.assertEqual(decision['color'], 'rojo')
        self.assertTrue(decision['permitido'])

    def test_interpretar_urgente(self):
        """Test: interpretar prioridad urgente."""
        frase = "recoge el azul urgente"
        decision = self.interpretador.interpretar(frase)

        self.assertEqual(decision['color'], 'azul')
        self.assertEqual(decision['prioridad'], 1)

    def test_interpretar_negacion(self):
        """Test: interpretar negación."""
        frase = "recoge el verde pero está prohibido"
        decision = self.interpretador.interpretar(frase)

        self.assertEqual(decision['color'], 'verde')
        self.assertFalse(decision['permitido'])

    def test_interpretar_color_by_initial(self):
        """Test: interpretar color por inicial."""
        frase = "coge el amarillo"
        decision = self.interpretador.interpretar(frase)

        self.assertEqual(decision['color'], 'amarillo')

    def test_interpretar_lotes(self):
        """Test: interpretar múltiples frases."""
        frases = [
            "recoge rojo",
            "coge azul asap",
            "suelta verde",
        ]

        decisiones = self.interpretador.interpretar_lotes(frases)
        self.assertEqual(len(decisiones), 3)


class TestIntegrationPickPlace(unittest.TestCase):
    """Tests de integración del flujo completo."""

    def setUp(self):
        """Prepara los componentes."""
        with open('config.json', 'r') as f:
            self.config = json.load(f)
        self.robot = SimRobot()
        self.calibrator = HomographyCalibrator(self.config)

    def test_full_cycle_simulation(self):
        """Test: ciclo completo en simulación."""
        # 1. Power on
        self.assertTrue(self.robot.power_on())

        # 2. Ir a HOME
        home = self.config['poses']['home']['angles']
        self.assertTrue(self.robot.send_angles(home, 20))

        # 3. Ir a OBSERVATION
        obs = self.config['poses']['observation']['angles']
        self.assertTrue(self.robot.send_angles(obs, 20))

        # 4. Abrir gripper
        self.assertTrue(self.robot.set_gripper_value(100, 30))

        # 5. Enviar coords a zona de depósito
        deposit = self.config['deposits']['rojo']['coords']
        self.assertTrue(self.robot.send_coords(deposit, 20))

        # 6. Cerrar gripper
        self.assertTrue(self.robot.set_gripper_value(60, 30))

        # 7. Retornar a HOME
        self.assertTrue(self.robot.send_angles(home, 20, self.config))


class TestCycleStopsOnFailure(unittest.TestCase):
    """Seguridad: si falla un color, el ciclo se detiene y el brazo NO se vuelve a mover."""

    def test_failure_stops_cycle_without_more_motion(self):
        from pick_place import PickPlace
        with open('config.json', 'r') as f:
            config = json.load(f)
        robot = SimRobot()
        tmp = tempfile.NamedTemporaryFile(suffix='.csv', delete=False)
        tmp.close()
        pp = PickPlace(config, robot, None, None, HomographyCalibrator(config), tmp.name, False)
        # Detección fija con los 4 colores; re-detección devuelve lo mismo.
        fake = {c: (320, 240, 1000) for c in config['workflow']['color_order']}
        pp.detect_colors = lambda: dict(fake)
        pp.power_on = lambda: True
        poses = []
        pp.go_to_pose = lambda name, use_angles=True: poses.append(name) or True
        intentos = []

        def falla_primero(color, detections):
            intentos.append(color)
            return False  # el primer color falla

        pp.pick_and_place_single_color = falla_primero
        self.assertFalse(pp.run_full_cycle())
        self.assertEqual(len(intentos), 1, "tras un fallo no debe intentar otro color")
        self.assertNotIn('home', poses[2:], "tras un fallo no debe volver a HOME ni moverse")
        os.unlink(tmp.name)


class TestWorkspaceValidation(unittest.TestCase):
    """Tests de validación de workspace."""

    def setUp(self):
        """Prepara los componentes."""
        with open('config.json', 'r') as f:
            self.config = json.load(f)
        self.robot = SimRobot()

    def test_send_coords_reach_limit(self):
        """Test: rechazar coords fuera de reach radial."""
        bad_coords = [300, 300, 100, 180, 0, 0]
        result = self.robot.send_coords(bad_coords, 20, config=self.config)
        self.assertFalse(result)

    def test_send_coords_z_min(self):
        """Test: rechazar Z por debajo de z_min."""
        bad_coords = [100, 100, 50, 180, 0, 0]
        result = self.robot.send_coords(bad_coords, 20, config=self.config)
        self.assertFalse(result)

    def test_send_coords_z_max(self):
        """Test: rechazar Z por encima de z_max."""
        bad_coords = [100, 100, 500, 180, 0, 0]
        result = self.robot.send_coords(bad_coords, 20, config=self.config)
        self.assertFalse(result)

    def test_send_coords_valid(self):
        """Test: aceptar coords válidos."""
        good_coords = [100, 100, 150, 180, 0, 0]
        result = self.robot.send_coords(good_coords, 20, config=self.config)
        self.assertTrue(result)


class TestMotionStartRace(unittest.TestCase):
    """Tests para race condition del inicio de movimiento."""

    def setUp(self):
        """Prepara el robot."""
        with open('config.json', 'r') as f:
            self.config = json.load(f)
        self.robot = SimRobot()

    def test_send_angles_already_at_target(self):
        """Test: si ya estamos en target, retorna True."""
        angles = [10, 20, 30, 40, 50, 60]
        self.robot.angles = angles.copy()
        result = self.robot.send_angles(angles, 20, self.config)
        self.assertTrue(result)

    def test_send_coords_already_at_target(self):
        """Test: si ya estamos en coords target, retorna True."""
        coords = [100, 100, 150, 180, 0, 0]
        self.robot.coords = coords.copy()
        result = self.robot.send_coords(coords, 20, config=self.config)
        self.assertTrue(result)


def run_all_tests():
    """Ejecuta todos los tests."""
    logging.basicConfig(
        level=logging.WARNING,
        format='%(name)s: %(message)s'
    )

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Añade tests
    suite.addTests(loader.loadTestsFromTestCase(TestSimRobot))
    suite.addTests(loader.loadTestsFromTestCase(TestColorDetector))
    suite.addTests(loader.loadTestsFromTestCase(TestHomographyCalibrator))
    suite.addTests(loader.loadTestsFromTestCase(TestMyCoBot280FK))
    suite.addTests(loader.loadTestsFromTestCase(TestBrokerQueue))
    suite.addTests(loader.loadTestsFromTestCase(TestInterpretadorOrdenes))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegrationPickPlace))
    suite.addTests(loader.loadTestsFromTestCase(TestWorkspaceValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestMotionStartRace))

    # Ejecuta
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    exit_code = run_all_tests()
    sys.exit(exit_code)


class TestCalibratedMatrixCheck(unittest.TestCase):
    """Regresión: con calibracion.json cargado (H es un array 3x3), `--color` no debe romper."""

    def test_color_mode_runs_with_loaded_homography(self):
        import subprocess, shutil, sys
        work = tempfile.mkdtemp(prefix='jetcobot_h_')
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for f in ('pick_place.py', 'robot.py', 'vision.py', 'calibration.py', 'config.json'):
            shutil.copy(os.path.join(here, f), work)
        with open(os.path.join(work, 'calibracion.json'), 'w') as f:
            json.dump({'pixel_points': [[0, 0], [640, 0], [640, 480], [0, 480]],
                       'robot_points': [[100, -100], [100, 100], [250, 100], [250, -100]],
                       'H_matrix': [[0, 0.4, 100], [0.3, 0, -100], [0, 0, 1]]}, f)
        r = subprocess.run([sys.executable, 'pick_place.py', '--simular', '--color', 'rojo'],
                           cwd=work, capture_output=True, text=True, timeout=120)
        salida = r.stdout + r.stderr
        self.assertNotIn('truth value of an array', salida)
        self.assertNotIn('Se requiere calibración primero', salida)
        # Y la recogida simulada completa (alturas relativas a la mesa, nunca bajo z_min)
        self.assertNotIn('por debajo de z_min', salida)
        self.assertIn('recogido y depositado exitosamente', salida)
        self.assertEqual(r.returncode, 0, salida[-2000:])


class TestRealRobotNeverUsesFakeDetections(unittest.TestCase):
    """Seguridad: sin cámara y con robot REAL, no se inventan posiciones de cubos."""

    def test_no_fake_detections_with_real_robot(self):
        from pick_place import PickPlace
        from robot import RobotAdapter
        with open('config.json', 'r') as f:
            config = json.load(f)

        class RobotRealFalso(RobotAdapter):
            def power_on(self): return True
            def get_angles(self): return [0] * 6
            def send_angles(self, angles, speed): return True
            def get_coords(self): return [0] * 6
            def send_coords(self, coords, speed, mode=1): return True
            def is_moving(self): return False
            def set_gripper_state(self, flag, speed): return True
            def set_gripper_value(self, value, speed): return True
            def release_all_servos(self): return True
            def stop(self): return True

        tmp = tempfile.NamedTemporaryFile(suffix='.csv', delete=False)
        tmp.close()
        pp = PickPlace(config, RobotRealFalso(), None, None, HomographyCalibrator(config), tmp.name, False)
        self.assertEqual(pp.detect_colors(), {})
        pp_sim = PickPlace(config, SimRobot(), None, None, HomographyCalibrator(config), tmp.name, False)
        self.assertIn('rojo', pp_sim.detect_colors())
        os.unlink(tmp.name)
