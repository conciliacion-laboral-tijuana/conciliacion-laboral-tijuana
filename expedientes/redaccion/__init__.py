"""Motor de redacción de demandas por capítulos.

Produce la demanda con la estructura del estándar del despacho
(ver `docs/referencia/demanda_injustificado_estandar.pdf`):

    1. PROEMIO          — actor, domicilio, apoderados con cédula, autorizados
    2. DEMANDADOS       — patrón "quien resulte responsable" + moral
    3. PRESTACIONES     — numerales con monto en número y letra
    4. JORNADA/HORAS EXTRA — anexo con la tabla semanal
    5. HECHOS           — numerados, con los condicionales
    6. PRUEBAS          — confesional, interrogatorio, inspección, documental…
    7. DERECHO          — fundamentos

El módulo es deliberadamente independiente del ORM en su núcleo: los capítulos
reciben un `dict` de datos y un `dict` de cálculos.  El adaptador
(`adaptador.py`) es la única pieza que conoce Django, y los NÚMEROS nunca los
inventa la redacción: vienen del motor legal determinista.
"""

from .adaptador import datos_de_expediente, datos_desde_post
from .condiciones import evaluar_condiciones
from .demanda import capitulos, encabezado_capitulo, generar_texto_completo
from .salida import (
    ORDEN_HTML,
    capitulos_html,
    generar_demanda_capitulos_docx,
    generar_demanda_capitulos_html,
    guardar_demanda_capitulos,
)

__all__ = [
    'datos_de_expediente',
    'datos_desde_post',
    'evaluar_condiciones',
    'capitulos',
    'capitulos_html',
    'encabezado_capitulo',
    'generar_texto_completo',
    'generar_demanda_capitulos_html',
    'generar_demanda_capitulos_docx',
    'guardar_demanda_capitulos',
    'ORDEN_HTML',
]
