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
Cliente CLI para enviar órdenes de agarre al broker.
Simula solicitudes de los 4 miembros del equipo en paralelo.
"""
import json
import logging
import argparse
import threading
import time
from datetime import datetime
from typing import Dict
import sys

# Importa el interpretador
from interprete_stub import InterpretadorOrdenes


logger = logging.getLogger(__name__)


class ClienteOrden:
    """Cliente para enviar órdenes al broker."""

    def __init__(self, origen: str, prioridad: int = 5, simulate: bool = True):
        """Inicializa el cliente.

        Args:
            origen: identificador del origen (usuario, sensor, etc.)
            prioridad: prioridad de la solicitud (1-10, menor = mayor prioridad)
            simulate: si True, simula. Si False, intenta conectar a ROS
        """
        self.origen = origen
        self.prioridad = prioridad
        self.simulate = simulate
        logger.info(f"Cliente {origen} inicializado (prioridad={prioridad})")

    def enviar_orden(self, accion: str, objeto: str, color: str,
                    permitido: bool = True) -> bool:
        """Envía una orden de agarre.

        Args:
            accion: acción a realizar (ej. 'recoger')
            objeto: objeto a afectar (ej. 'cubo')
            color: color del objeto
            permitido: si la acción está permitida

        Returns:
            True si se encolaron, False si se rechazó
        """
        request = {
            'accion': accion,
            'objeto': objeto,
            'color': color.lower(),
            'prioridad': self.prioridad,
            'permitido': permitido,
            'origen': self.origen,
            'timestamp': datetime.now().isoformat()
        }

        logger.info(f"Enviando: {request}")

        if self.simulate:
            # Simulación: imprime y retorna éxito
            print(f"[SIMULADO] Solicitud #{self.origen}: {color} permitido={permitido}")
            return permitido
        else:
            # ROS 2: intenta conectar a /pedir_agarre
            try:
                import rclpy
                from std_srvs.srv import Trigger

                rclpy.init()
                node = rclpy.create_node(f'cliente_{self.origen}')
                client = node.create_client(Trigger, '/pedir_agarre')

                # Serializa request a JSON
                json_request = json.dumps(request)

                # Nota: std_srvs/Trigger no lleva payload.
                # En una implementación real se usaría un .srv personalizado
                # o se pasaría JSON en el campo de respuesta.

                # Para esta demostración, simplemente retorna éxito
                logger.info(f"Solicitud enviada (ROS): {json_request}")
                return True
            except Exception as e:
                logger.error(f"Error ROS: {e}")
                return False

    def enviar_desde_frase(self, frase: str) -> bool:
        """Interpreta una frase en español y envía la orden.

        Args:
            frase: frase en español (ej. 'recoge el cubo rojo urgente')

        Returns:
            True si se encolaron
        """
        interpretador = InterpretadorOrdenes()
        decision = interpretador.interpretar(frase)

        if not decision:
            logger.error(f"No se pudo interpretar: {frase}")
            return False

        return self.enviar_orden(
            accion=decision['accion'],
            objeto=decision['objeto'],
            color=decision['color'],
            permitido=decision['permitido']
        )


def simular_multiples_clientes(num_clientes: int = 4):
    """Simula N clientes enviando órdenes en paralelo.

    Args:
        num_clientes: número de clientes
    """
    logging.basicConfig(level=logging.INFO)

    colores = ['rojo', 'azul', 'amarillo', 'verde']

    def cliente_thread(cliente_id: int):
        cliente = ClienteOrden(f"usuario{cliente_id}", prioridad=cliente_id)

        color = colores[cliente_id % len(colores)]
        resultado = cliente.enviar_orden(
            accion='recoger',
            objeto='cubo',
            color=color,
            permitido=True
        )

        logger.info(f"Cliente {cliente_id}: {color} - {'encolado' if resultado else 'rechazado'}")

    logger.info(f"Simulando {num_clientes} clientes en paralelo...")

    threads = []
    for i in range(num_clientes):
        t = threading.Thread(target=cliente_thread, args=(i,))
        threads.append(t)
        t.start()
        time.sleep(0.1)  # Pequeño delay entre creaciones

    # Espera a que terminen
    for t in threads:
        t.join()

    logger.info("Simulación completada")


def main():
    """Función principal con CLI."""
    parser = argparse.ArgumentParser(description='Cliente de órdenes JetCobot')

    parser.add_argument('--origen', type=str, default='cli',
                       help='Identificador del origen de la orden')
    parser.add_argument('--color', type=str, required=True,
                       help='Color del cubo (rojo/azul/amarillo/verde)')
    parser.add_argument('--prioridad', type=int, default=5,
                       help='Prioridad (1-10, menor = mayor)')
    parser.add_argument('--permitido', type=bool, default=True,
                       help='Si la acción está permitida')
    parser.add_argument('--frase', type=str,
                       help='Frase en español a interpretar (ej. "recoge rojo urgente")')
    parser.add_argument('--paralelo', type=int, metavar='N',
                       help='Simula N clientes en paralelo')
    parser.add_argument('--ros', action='store_true',
                       help='Usa ROS 2 en lugar de simulación')

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(name)s: %(message)s'
    )

    if args.paralelo:
        simular_multiples_clientes(args.paralelo)
        return 0

    # Cliente singular
    cliente = ClienteOrden(args.origen, prioridad=args.prioridad, simulate=not args.ros)

    if args.frase:
        resultado = cliente.enviar_desde_frase(args.frase)
    else:
        resultado = cliente.enviar_orden(
            accion='recoger',
            objeto='cubo',
            color=args.color,
            permitido=args.permitido
        )

    return 0 if resultado else 1


if __name__ == '__main__':
    sys.exit(main())
