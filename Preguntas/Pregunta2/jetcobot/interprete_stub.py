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
Intérprete stub para convertir frases en español a órdenes tipadas.

NOTAS:
  - Este es un stub (demostración). El curso usa LAYA (Pregunta 1) para voz/texto.
  - Aquí se muestra dónde enchufaría: entre voz y la cola del broker.
  - Usa keyword matching simple para demo.
"""
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class InterpretadorOrdenes:
    """Interpreta frases en español a decisiones tipadas."""

    def __init__(self):
        """Inicializa el interpretador."""
        # Palabras clave por acción
        self.acciones = {
            'recoger': ['recoge', 'coge', 'agarra', 'pick up', 'toma'],
            'soltar': ['suelta', 'deja', 'abre', 'drop', 'libera'],
            'mover': ['mueve', 'desplaza', 'pon', 'coloca', 'move'],
        }

        # Palabras clave por color
        # NOTA: orden importa (más específicas primero)
        self.colores = {
            'rojo': ['rojo', 'red'],
            'azul': ['azul', 'blue'],
            'amarillo': ['amarillo', 'yellow'],
            'verde': ['verde', 'green'],
        }

        # Palabras clave de prioridad
        self.prioridades = {
            'urgente': 1,
            'urgent': 1,
            'prioritario': 2,
            'asap': 1,
            'inmediato': 1,
            'normal': 5,
            'bajo': 8,
            'baja': 8,
        }

        # Palabras de negación
        self.negaciones = ['no', 'no permitido', 'está prohibido', 'prohibido']

    def interpretar(self, frase: str) -> Optional[Dict]:
        """Interpreta una frase en español.

        Args:
            frase: frase a interpretar (ej. "recoge el cubo rojo urgente")

        Returns:
            Diccionario con decisión tipada:
            {
                'accion': str,
                'objeto': str,
                'color': str,
                'prioridad': int,
                'permitido': bool
            }
            O None si no se puede interpretar.
        """
        frase_lower = frase.lower().strip()
        logger.info(f"Interpretando: {frase_lower}")

        # Por defecto
        decision = {
            'accion': 'recoger',
            'objeto': 'cubo',
            'color': 'rojo',
            'prioridad': 5,
            'permitido': True
        }

        # Detecta acción
        for accion, keywords in self.acciones.items():
            if any(kw in frase_lower for kw in keywords):
                decision['accion'] = accion
                break

        # Detecta color
        for color, keywords in self.colores.items():
            if any(kw in frase_lower for kw in keywords):
                decision['color'] = color
                break

        # Detecta objeto
        if 'cubo' in frase_lower:
            decision['objeto'] = 'cubo'
        elif 'bloque' in frase_lower:
            decision['objeto'] = 'bloque'
        elif 'pieza' in frase_lower:
            decision['objeto'] = 'pieza'

        # Detecta prioridad
        for palabra, prioridad in self.prioridades.items():
            if palabra in frase_lower:
                decision['prioridad'] = prioridad
                break

        # Detecta negación
        for negacion in self.negaciones:
            if negacion in frase_lower:
                decision['permitido'] = False
                logger.info("Acción detectada como NO permitida")
                break

        logger.info(f"Decisión: {decision}")
        return decision

    def interpretar_lotes(self, frases: list) -> list:
        """Interpreta un lote de frases.

        Args:
            frases: lista de frases

        Returns:
            Lista de decisiones interpretadas
        """
        return [self.interpretar(f) for f in frases if self.interpretar(f)]


def ejemplos():
    """Muestra ejemplos de interpretación."""
    interpretador = InterpretadorOrdenes()

    ejemplos_frases = [
        "recoge el cubo rojo",
        "recoge el cubo azul urgente",
        "coge el bloque amarillo bajo",
        "suelta el verde asap",
        "recoge rojo, está prohibido",
        "toma el cubo no permitido",
    ]

    print("Ejemplos de interpretación:")
    print("="*60)

    for frase in ejemplos_frases:
        decision = interpretador.interpretar(frase)
        if decision:
            print(f"Frase: {frase}")
            print(f"  -> Acción: {decision['accion']}")
            print(f"  -> Color: {decision['color']}")
            print(f"  -> Prioridad: {decision['prioridad']}")
            print(f"  -> Permitido: {decision['permitido']}")
            print()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    ejemplos()
