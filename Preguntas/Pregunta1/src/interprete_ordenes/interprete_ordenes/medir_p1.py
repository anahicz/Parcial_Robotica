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
# Archivo: medir_p1.py
# Descripción:
#   Ejecuta el conjunto de frases de P1 mediante /interpretar_orden,
#   compara LAYA contra el clasificador por keywords, registra latencias
#   y genera las métricas de mediana, P95 y exactitud.
# ==============================================================================

import csv
import math
import statistics
import sys
import time
from pathlib import Path

import rclpy
from rclpy.node import Node

from arm_broker_interfaces.srv import InterpretarOrden
from interprete_ordenes.clasificador import clasificar


CAMPOS_ESPERADOS = [
    'esperado_accion',
    'esperado_objeto',
    'esperado_color',
    'esperado_prioridad',
    'esperado_permitido',
]


def normalizar(texto):
    return str(texto).strip().lower()


def convertir_bool(valor):
    valor = normalizar(valor)

    if valor in ('true', '1', 'si', 'sí'):
        return True

    if valor in ('false', '0', 'no'):
        return False

    raise ValueError(
        f'Booleano inválido: "{valor}". '
        'Usa true/false, si/no o 1/0.'
    )


def percentil_95(valores):
    if not valores:
        return 0.0

    valores = sorted(valores)

    if len(valores) == 1:
        return valores[0]

    posicion = (len(valores) - 1) * 0.95

    inferior = math.floor(posicion)
    superior = math.ceil(posicion)

    if inferior == superior:
        return valores[inferior]

    fraccion = posicion - inferior

    return (
        valores[inferior]
        + (valores[superior] - valores[inferior]) * fraccion
    )


def porcentaje(aciertos, total):
    if total == 0:
        return 0.0

    return 100.0 * aciertos / total


class MedidorP1(Node):

    def __init__(self):
        super().__init__('medidor_p1')

        self.cliente = self.create_client(
            InterpretarOrden,
            '/interpretar_orden'
        )

        print('Esperando /interpretar_orden...')

        if not self.cliente.wait_for_service(timeout_sec=10.0):
            raise RuntimeError(
                'El servicio /interpretar_orden no está disponible.'
            )

        print('Servicio disponible.')

    def consultar(self, frase):
        request = InterpretarOrden.Request()
        request.frase = frase

        inicio = time.perf_counter()

        future = self.cliente.call_async(request)

        rclpy.spin_until_future_complete(
            self,
            future,
            timeout_sec=5.0
        )

        latencia_servicio_ms = (
            time.perf_counter() - inicio
        ) * 1000.0

        if not future.done():
            raise TimeoutError(
                'El servicio ROS superó 5 segundos.'
            )

        if future.exception() is not None:
            raise future.exception()

        return future.result(), latencia_servicio_ms


def validar_csv(filas):
    if not filas:
        raise ValueError('El CSV no contiene frases.')

    requeridos = [
        'id',
        'frase',
        *CAMPOS_ESPERADOS
    ]

    for campo in requeridos:
        if campo not in filas[0]:
            raise ValueError(
                f'Falta la columna obligatoria: {campo}'
            )

    for numero, fila in enumerate(filas, start=1):
        if not fila['frase'].strip():
            raise ValueError(
                f'Fila {numero}: falta la frase.'
            )

        for campo in CAMPOS_ESPERADOS:
            if not str(fila[campo]).strip():
                raise ValueError(
                    f'Fila {numero}: falta {campo}. '
                    'Debes registrar el valor esperado '
                    'ANTES de ejecutar las mediciones.'
                )

        int(fila['esperado_prioridad'])
        convertir_bool(fila['esperado_permitido'])


def main():
    if len(sys.argv) != 4:
        print(
            'Uso:\n'
            'python3 -m interprete_ordenes.medir_p1 '
            '<entrada.csv> <salida.csv> <escenario>\n\n'
            'Ejemplo:\n'
            'python3 -m interprete_ordenes.medir_p1 '
            'frases_50.csv resultados_calma.csv calma'
        )
        return

    entrada = Path(sys.argv[1])
    salida = Path(sys.argv[2])
    escenario = sys.argv[3]

    with entrada.open(
        newline='',
        encoding='utf-8'
    ) as archivo:
        filas = list(csv.DictReader(archivo))

    validar_csv(filas)

    print()
    print(f'Escenario: {escenario}')
    print(f'Frases: {len(filas)}')
    print(
        'Valores esperados verificados '
        'ANTES de medir: OK'
    )
    print()

    rclpy.init()

    nodo = None

    resultados = []

    latencias_servicio = []
    latencias_laya = []
    tiempos_servidor = []
    tiempos_red = []

    aciertos_laya = 0
    total_laya_validos = 0
    aciertos_keywords = 0

    aciertos_laya_campos = {
        'accion': 0,
        'objeto': 0,
        'color': 0,
        'prioridad': 0,
        'permitido': 0,
    }

    aciertos_kw_campos = {
        'accion': 0,
        'objeto': 0,
        'color': 0,
        'prioridad': 0,
        'permitido': 0,
    }

    try:
        nodo = MedidorP1()

        print()
        print('Warm-up: ejecutando consulta no medida...')

        try:
            nodo.consultar('recoge el cubo rojo')
            print('Warm-up completado.')
        except Exception as error:
            print(
                f'Advertencia durante warm-up: '
                f'{type(error).__name__}: {error}'
            )

        print()
        print('Iniciando mediciones oficiales...')
        print()

        for indice, fila in enumerate(filas, start=1):

            frase = fila['frase'].strip()

            esperado = {
                'accion': normalizar(
                    fila['esperado_accion']
                ),
                'objeto': normalizar(
                    fila['esperado_objeto']
                ),
                'color': normalizar(
                    fila['esperado_color']
                ),
                'prioridad': int(
                    fila['esperado_prioridad']
                ),
                'permitido': convertir_bool(
                    fila['esperado_permitido']
                ),
            }

            print(
                f'[{indice}/{len(filas)}] '
                f'{frase}'
            )

            response, latencia_servicio_ms = (
                nodo.consultar(frase)
            )

            kw = clasificar(frase)

            laya = {
                'accion': normalizar(response.accion),
                'objeto': normalizar(response.objeto),
                'color': normalizar(response.color),
                'prioridad': int(response.prioridad),
                'permitido': bool(response.permitido),
            }

            keywords = {
                'accion': normalizar(kw['accion']),
                'objeto': normalizar(kw['objeto']),
                'color': normalizar(kw['color']),
                'prioridad': int(kw['prioridad']),
                'permitido': bool(kw['permitido']),
            }

            laya_valido = (
                response.metodo == 'laya'
                and not response.degradado
            )

            laya_ok_campos = {}
            kw_ok_campos = {}

            for campo in esperado:
                laya_ok_campos[campo] = (
                    laya[campo] == esperado[campo]
                )

                kw_ok_campos[campo] = (
                    keywords[campo] == esperado[campo]
                )

            laya_ok_total = (
                laya_valido
                and all(laya_ok_campos.values())
            )

            kw_ok_total = all(
                kw_ok_campos.values()
            )

            if laya_valido:
                total_laya_validos += 1

                if laya_ok_total:
                    aciertos_laya += 1

                for campo in esperado:
                    if laya_ok_campos[campo]:
                        aciertos_laya_campos[campo] += 1

                latencias_laya.append(
                    response.latencia_laya_ms
                )

                tiempos_servidor.append(
                    response.tiempo_servidor_ms
                )

                tiempos_red.append(
                    response.tiempo_red_estimado_ms
                )

            if kw_ok_total:
                aciertos_keywords += 1

            for campo in esperado:
                if kw_ok_campos[campo]:
                    aciertos_kw_campos[campo] += 1

            latencias_servicio.append(
                latencia_servicio_ms
            )

            registro = {
                'escenario': escenario,
                'id': fila['id'],
                'frase': frase,

                'esperado_accion': esperado['accion'],
                'esperado_objeto': esperado['objeto'],
                'esperado_color': esperado['color'],
                'esperado_prioridad': esperado['prioridad'],
                'esperado_permitido': esperado['permitido'],

                'laya_accion': laya['accion'],
                'laya_objeto': laya['objeto'],
                'laya_color': laya['color'],
                'laya_prioridad': laya['prioridad'],
                'laya_permitido': laya['permitido'],

                'laya_valido': laya_valido,
                'laya_correcto_total': laya_ok_total,

                'laya_ok_accion': laya_ok_campos['accion'],
                'laya_ok_objeto': laya_ok_campos['objeto'],
                'laya_ok_color': laya_ok_campos['color'],
                'laya_ok_prioridad': laya_ok_campos['prioridad'],
                'laya_ok_permitido': laya_ok_campos['permitido'],

                'kw_accion': keywords['accion'],
                'kw_objeto': keywords['objeto'],
                'kw_color': keywords['color'],
                'kw_prioridad': keywords['prioridad'],
                'kw_permitido': keywords['permitido'],

                'kw_correcto_total': kw_ok_total,

                'kw_ok_accion': kw_ok_campos['accion'],
                'kw_ok_objeto': kw_ok_campos['objeto'],
                'kw_ok_color': kw_ok_campos['color'],
                'kw_ok_prioridad': kw_ok_campos['prioridad'],
                'kw_ok_permitido': kw_ok_campos['permitido'],

                'metodo': response.metodo,
                'degradado': response.degradado,
                'causa': response.causa,

                'latencia_servicio_ms': round(latencia_servicio_ms, 3),
                'latencia_laya_ms': round(response.latencia_laya_ms, 3),
                'tiempo_servidor_ms': round(response.tiempo_servidor_ms, 3),
                'tiempo_red_estimado_ms': round(response.tiempo_red_estimado_ms, 3),
            }

            resultados.append(registro)

    finally:
        if nodo is not None:
            nodo.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()

    campos = list(resultados[0].keys())

    with salida.open(
        'w',
        newline='',
        encoding='utf-8'
    ) as archivo:

        writer = csv.DictWriter(
            archivo,
            fieldnames=campos
        )

        writer.writeheader()
        writer.writerows(resultados)

    total = len(resultados)

    exactitud_laya = porcentaje(
        aciertos_laya,
        total_laya_validos
    )

    exactitud_keywords = porcentaje(
        aciertos_keywords,
        total
    )

    resumen = []

    resumen.append('========================================')
    resumen.append('RESUMEN P1 - INTERPRETACIÓN DE ÓRDENES')
    resumen.append('========================================')

    resumen.append(f'Escenario: {escenario}')
    resumen.append(f'Frases totales: {total}')
    resumen.append(
        f'Respuestas LAYA válidas: '
        f'{total_laya_validos}/{total}'
    )
    resumen.append('')
    resumen.append(
        f'Exactitud total LAYA: '
        f'{exactitud_laya:.2f}%'
    )
    resumen.append(
        f'Exactitud total keywords: '
        f'{exactitud_keywords:.2f}%'
    )
    resumen.append('')
    resumen.append('Exactitud LAYA por campo:')

    for campo in aciertos_laya_campos:
        valor = porcentaje(
            aciertos_laya_campos[campo],
            total_laya_validos
        )
        resumen.append(
            f'  {campo}: {valor:.2f}%'
        )

    resumen.append('')
    resumen.append('Exactitud keywords por campo:')

    for campo in aciertos_kw_campos:
        valor = porcentaje(
            aciertos_kw_campos[campo],
            total
        )
        resumen.append(
            f'  {campo}: {valor:.2f}%'
        )

    resumen.append('')
    resumen.append('Latencia servicio ROS:')
    resumen.append(
        f'  Mediana: '
        f'{statistics.median(latencias_servicio):.2f} ms'
    )
    resumen.append(
        f'  P95: '
        f'{percentil_95(latencias_servicio):.2f} ms'
    )

    if latencias_laya:
        resumen.append('')
        resumen.append('Latencia HTTP LAYA:')
        resumen.append(
            f'  Mediana: '
            f'{statistics.median(latencias_laya):.2f} ms'
        )
        resumen.append(
            f'  P95: '
            f'{percentil_95(latencias_laya):.2f} ms'
        )
        resumen.append('')
        resumen.append('Tiempo servidor LAYA:')
        resumen.append(
            f'  Mediana: '
            f'{statistics.median(tiempos_servidor):.2f} ms'
        )
        resumen.append(
            f'  P95: '
            f'{percentil_95(tiempos_servidor):.2f} ms'
        )
        resumen.append('')
        resumen.append('Red/resto estimado:')
        resumen.append(
            f'  Mediana: '
            f'{statistics.median(tiempos_red):.2f} ms'
        )
        resumen.append(
            f'  P95: '
            f'{percentil_95(tiempos_red):.2f} ms'
        )

    resumen_texto = '\n'.join(resumen)

    print()
    print(resumen_texto)

    archivo_resumen = salida.with_name(
        salida.stem + '_resumen.txt'
    )

    archivo_resumen.write_text(
        resumen_texto + '\n',
        encoding='utf-8'
    )

    print()
    print(f'CSV generado: {salida}')
    print(f'Resumen generado: {archivo_resumen}')


if __name__ == '__main__':
    main()
