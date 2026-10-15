"""Ensamblado de la demanda completa por capítulos.

Produce la estructura del estándar del despacho:

    [carátula]  INICIO / ACTOR / ACCIÓN + TRIBUNAL ... PRESENTE
    [proemio]   comparecencia, apoderados, autorizados, fundamento
    [demandados] I. fuente de trabajo  II. moral
    [introducción] "Demandando en virtud del despido injustificado..."
    CAPÍTULO DE PRESTACIONES
    [anexo jornada semanal / horas extras]
    CAPÍTULO DE HECHOS
    PRUEBAS
    CAPÍTULO DE DERECHO

`capitulos()` devuelve la estructura como datos (para pruebas y para la UI) y
los generadores de salida se construyen sobre ella, de modo que HTML, DOCX y
texto plano dicen exactamente lo mismo.
"""

from ..demanda_generator import _ordinal
from . import condiciones as mod_condiciones
from . import demandados as mod_demandados
from . import derecho as mod_derecho
from . import hechos as mod_hechos
from . import jornada as mod_jornada
from . import prestaciones as mod_prestaciones
from . import pruebas as mod_pruebas
from . import proemio as mod_proemio

TRIBUNAL = ('TRIBUNAL LABORAL DEL ESTADO DE BAJA CALIFORNIA CON RESIDENCIA '
            'EN TIJUANA')

ETIQUETAS_ACCION = {
    'injustificado': 'DESPIDO INJUSTIFICADO',
    'justificado': 'TERMINACIÓN DE LA RELACIÓN LABORAL',
    'voluntario': 'RENUNCIA VOLUNTARIA',
    'rescision': 'RESCISIÓN DE LA RELACIÓN LABORAL',
    'otro': 'TERMINACIÓN DE LA RELACIÓN LABORAL',
}


def capitulos(datos: dict, calculo: dict, tipo_despido: str = 'injustificado') -> dict:
    """Devuelve todos los capítulos ya redactados.

    Args:
        datos: dict del adaptador (`expedientes.redaccion.adaptador`)
        calculo: dict de `demanda_generator.calculo_para_demanda`
        tipo_despido: injustificado | justificado | voluntario | rescision | otro
    """
    cond = mod_condiciones.evaluar_condiciones(datos)

    renglones_prestaciones = mod_prestaciones.renglones(datos, calculo, cond)
    lista_hechos = mod_hechos.hechos(datos, calculo, cond, tipo_despido)
    lista_pruebas = mod_pruebas.pruebas(datos, cond)

    return {
        'caratula': {
            'actor': datos.get('actor_nombre') or '',
            'accion': ETIQUETAS_ACCION.get(tipo_despido, ETIQUETAS_ACCION['injustificado']),
            'tribunal': datos.get('tribunal') or TRIBUNAL,
        },
        'proemio': mod_proemio.proemio(datos),
        'demandados': mod_demandados.demandados(datos),
        'introduccion': mod_demandados.introduccion(tipo_despido),
        'prestaciones': renglones_prestaciones,
        'jornada': {
            'resumen': mod_jornada.resumen(datos, calculo),
            'filas': mod_jornada.filas_jornada(datos, calculo),
            'encabezados': mod_jornada.ENCABEZADOS,
        },
        'hechos': [
            f'{_ordinal(i)}.- {texto}' for i, texto in enumerate(lista_hechos, start=1)
        ],
        'pruebas': lista_pruebas,
        'derecho': mod_derecho.derecho(datos, cond, tipo_despido),
        'condiciones': cond,
    }


def encabezado_capitulo(titulo: str) -> str:
    """'CAPÍTULO DE PRESTACIONES:' — como en el estándar."""
    return f'CAPÍTULO DE {titulo}:'


# ══════════════════════════════════════════════════════════════════════════
# SALIDA EN TEXTO PLANO (para pruebas y vista previa simple)
# ══════════════════════════════════════════════════════════════════════════

def generar_texto_completo(datos: dict, calculo: dict,
                           tipo_despido: str = 'injustificado') -> str:
    """Demanda completa en texto plano, capítulo por capítulo."""
    cap = capitulos(datos, calculo, tipo_despido)
    bloques = []

    car = cap['caratula']
    bloques.append(f"INICIO.\nACTOR.- {car['actor']}\nACCIÓN.- {car['accion']}\n")
    bloques.append(f"{car['tribunal']}\nP R E S E N T E.-\n")
    bloques.append(cap['proemio'])

    if cap['demandados']:
        bloques.append('Que mediante el presente escrito y con fundamento en, '
                       'vengo a demandar a:')
        for i, numeral in enumerate(cap['demandados'], start=1):
            bloques.append(f'{_romano(i)}.- {numeral}')

    bloques.append(cap['introduccion'])

    if cap['prestaciones']:
        bloques.append(encabezado_capitulo('PRESTACIONES'))
        for i, renglon in enumerate(cap['prestaciones'], start=1):
            bloques.append(f'{i}. {renglon}')

    if cap['jornada']['filas']:
        bloques.append(encabezado_capitulo('JORNADA SEMANAL'))
        if cap['jornada']['resumen']:
            bloques.append(cap['jornada']['resumen'])
        enc = cap['jornada']['encabezados']
        bloques.append(' | '.join(enc))
        for fila in cap['jornada']['filas']:
            bloques.append(
                f"{fila['jornada_semanal']} | {fila['jornada_ordinaria']} | "
                f"{fila['jornada_extra']} | {fila['horas']}"
            )

    if cap['hechos']:
        bloques.append(encabezado_capitulo('HECHOS'))
        bloques.extend(cap['hechos'])

    if cap['pruebas']:
        bloques.append('PRUEBAS')
        for i, prueba in enumerate(cap['pruebas'], start=1):
            bloques.append(f'{i}.- {prueba["titulo"]}. {prueba["texto"]}')
            objeto = prueba.get('objeto')
            if isinstance(objeto, (list, tuple)):
                bloques.append('Lo anterior con el fin de acreditar el objeto:')
                for j, obj in enumerate(objeto, start=1):
                    bloques.append(f'  {j}.- {obj}')
            elif objeto:
                bloques.append(str(objeto))

    if cap['derecho']:
        bloques.append(encabezado_capitulo('DERECHO'))
        bloques.append(cap['derecho'])

    return '\n\n'.join(b for b in bloques if b)


def _romano(numero: int) -> str:
    """1 → 'I', 2 → 'II' (los demandados se numeran en romanos)."""
    valores = [(10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')]
    salida = ''
    for valor, letra in valores:
        while numero >= valor:
            salida += letra
            numero -= valor
    return salida or 'I'
