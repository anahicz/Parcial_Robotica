# ==============================================================================
# UNIVERSIDAD ESAN
# ROBÓTICA 08079
# EXAMEN PARCIAL - GRAN RETO JETCOBOT
# Grupo 7
#
# Integrantes:
#   - Sebastian Pedro Aguirre Acosta
#   - Anahi Cortez Chinchay
#   - Ramirez Quevedo Karen Noelia
#   - Vara Vargas Valentino Uziel
#
# Archivo: interprete_ordenes.py
# Descripción:
#   Nodo ROS 2 encargado de exponer el servicio /interpretar_orden.
#   Utiliza LAYA como método principal y un clasificador por palabras clave
#   como respaldo cuando LAYA falla o supera el tiempo límite.
# ==============================================================================

import rclpy
from rclpy.node import Node

from arm_broker_interfaces.srv import InterpretarOrden

from interprete_ordenes.clasificador import clasificar
from interprete_ordenes.laya_client import consultar_laya


class InterpreteOrdenes(Node):

    def __init__(self):
        super().__init__('interprete_ordenes')

        # Parámetros configurables.
        self.declare_parameter('laya_url', '')
        self.declare_parameter('timeout_laya_s', 2.0)

        self.laya_url = str(
            self.get_parameter('laya_url').value
        ).strip()

        self.timeout_laya_s = float(
            self.get_parameter('timeout_laya_s').value
        )

        self.servicio = self.create_service(
            InterpretarOrden,
            '/interpretar_orden',
            self.interpretar_callback
        )

        self.get_logger().info(
            'Nodo interprete_ordenes listo. '
            'Servicio /interpretar_orden disponible.'
        )

        self.get_logger().info(
            f'Timeout LAYA = {self.timeout_laya_s:.2f} s'
        )

        if self.laya_url:
            self.get_logger().info(
                f'LAYA configurado en {self.laya_url}'
            )
        else:
            self.get_logger().warn(
                'LAYA todavía no está configurado. '
                'Se utilizará el clasificador por palabras clave.'
            )

    def usar_keywords(self, frase, response, causa_fallback):
        resultado = clasificar(frase)

        response.accion = resultado['accion']
        response.objeto = resultado['objeto']
        response.color = resultado['color']
        response.prioridad = resultado['prioridad']
        response.permitido = resultado['permitido']

        response.degradado = True
        response.metodo = 'keywords'

        # En modo degradado no hubo una respuesta válida de LAYA.
        response.latencia_laya_ms = 0.0
        response.tiempo_servidor_ms = 0.0
        response.tiempo_red_estimado_ms = 0.0

        if resultado['causa']:
            response.causa = resultado['causa']
        else:
            response.causa = causa_fallback

        return response

    def interpretar_callback(self, request, response):
        frase = request.frase.strip()

        self.get_logger().info(
            f'Frase recibida: "{frase}"'
        )

        # ------------------------------------------------------------------
        # Si LAYA no está configurado, se usa directamente el respaldo.
        # ------------------------------------------------------------------
        if not self.laya_url:
            self.get_logger().warn(
                'LAYA no configurado. Usando clasificador de respaldo.'
            )

            return self.usar_keywords(
                frase,
                response,
                'LAYA no configurado'
            )

        # ------------------------------------------------------------------
        # Método principal: LAYA
        # ------------------------------------------------------------------
        try:
            resultado = consultar_laya(
                frase,
                self.laya_url,
                self.timeout_laya_s
            )

            response.accion = resultado['accion']
            response.objeto = resultado['objeto']
            response.color = resultado['color']
            response.prioridad = resultado['prioridad']
            response.permitido = resultado['permitido']

            response.degradado = False
            response.metodo = 'laya'

            # Métricas de la consulta HTTP a LAYA.
            response.latencia_laya_ms = float(
                resultado['latencia_total_ms']
            )

            response.tiempo_servidor_ms = float(
                resultado['tiempo_servidor_ms']
                if resultado['tiempo_servidor_ms'] is not None
                else 0.0
            )

            response.tiempo_red_estimado_ms = float(
                resultado['tiempo_red_estimado_ms']
                if resultado['tiempo_red_estimado_ms'] is not None
                else 0.0
            )

            if response.permitido:
                response.causa = ''
            else:
                response.causa = 'Orden no permitida por LAYA'

            self.get_logger().info(
                f'LAYA: accion={response.accion}, '
                f'objeto={response.objeto}, '
                f'color={response.color}, '
                f'prioridad={response.prioridad}, '
                f'permitido={response.permitido}'
            )

            self.get_logger().info(
                f'Latencia total={resultado["latencia_total_ms"]:.2f} ms'
            )

            if resultado['tiempo_servidor_ms'] is not None:
                self.get_logger().info(
                    f'Tiempo servidor='
                    f'{resultado["tiempo_servidor_ms"]:.2f} ms'
                )

            if resultado['tiempo_red_estimado_ms'] is not None:
                self.get_logger().info(
                    f'Red/resto estimado='
                    f'{resultado["tiempo_red_estimado_ms"]:.2f} ms'
                )

            return response

        # ------------------------------------------------------------------
        # Cualquier fallo de LAYA activa el método de respaldo.
        # Incluye timeout, servidor inaccesible o respuesta inválida.
        # ------------------------------------------------------------------
        except Exception as error:
            causa = (
                f'Fallo o timeout de LAYA: '
                f'{type(error).__name__}'
            )

            self.get_logger().warn(causa)

            return self.usar_keywords(
                frase,
                response,
                causa
            )


def main(args=None):
    rclpy.init(args=args)

    nodo = InterpreteOrdenes()

    try:
        rclpy.spin(nodo)
    except KeyboardInterrupt:
        pass
    finally:
        nodo.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
