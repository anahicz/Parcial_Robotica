# Parches recibidos — pendientes de revisión

Estos archivos fueron entregados por el equipo y se conservan **sin aplicarlos** al núcleo de `pick_place.py`. Se añadió la firma institucional del Grupo 7 y se eliminó la atribución ajena del primer archivo.

- **`parche_altura_deposito.pyw`:** pretende adaptar la altura de tránsito en función de la distancia a la zona de depósito. La primera cadena de sustitución busca `x * k, y * k`, mientras que el `pick_place.py` actual contiene `x, y`. **No se aplica automáticamente** en la versión presente.
- **`parche_seguir.pyw`:** pretende continuar el ciclo ante errores y modifica `config.json` para habilitar `continue_on_error`. Puede informar éxito aunque no se haya alcanzado la posición, **ocultando un fallo de movimiento**. No debe habilitarse en el brazo sin una revisión de seguridad y pruebas de verificación de posición.

Los módulos `pick_place.py`, `robot.py`, `vision.py`, `calibration.py` y la configuración permanecen sin cambios. Ambos parches son materiales de referencia, no correcciones verificadas.
