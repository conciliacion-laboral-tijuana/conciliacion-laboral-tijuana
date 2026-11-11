"""Captura de datos por voz: guion de preguntas e interpretación del dictado.

El asistente de voz pregunta, uno a uno, los datos que la demanda necesita y
convierte lo que el asesor dice en el valor que se guarda.  La app ya sabe qué
falta (`demanda_estado`), así que el guion no es un cuestionario genérico: es la
lista de datos del expediente, en el orden en que se capturan.

Reglas de diseño:

- **Nada se inventa.** Si el dictado no se entiende, el campo se queda vacío y se
  avisa; no se adivina una fecha ni un salario.
- **La interpretación es determinista.** Fechas, dinero, hora y modalidad se
  parsean con reglas y se muestran para que el asesor confirme antes de guardar.
- **El guardado es el mismo de la web.** La vista llama a
  `_validar_captura_demanda`, no a una segunda ruta de escritura.

Este módulo no toca la base de datos: recibe el cliente y devuelve valores.
"""

import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from .models import Cliente

# ─── Guion de captura ────────────────────────────────────────────────────────
#
# tipo: texto | relato | curp | telefono | dinero | fecha | hora | modalidad
# El orden es el de una entrevista: primero quién es, luego el trabajo, el
# patrón y al final cómo terminó la relación.

PASOS = (
    {
        'campo': 'nombre', 'grupo': 'Trabajador', 'tipo': 'texto',
        'pregunta': '¿Cuál es el nombre completo del trabajador?',
        'ayuda': 'Como aparece en su INE, empezando por apellidos.',
    },
    {
        'campo': 'curp', 'grupo': 'Trabajador', 'tipo': 'curp',
        'pregunta': '¿Me dictas su CURP?',
        'ayuda': 'Si no la tienes a la mano, omite y se captura después.',
    },
    {
        'campo': 'telefono', 'grupo': 'Trabajador', 'tipo': 'telefono',
        'pregunta': '¿Cuál es su número de teléfono?',
        'ayuda': 'Diez dígitos, sin lada del país.',
    },
    {
        'campo': 'direccion_calle', 'grupo': 'Trabajador', 'tipo': 'texto',
        'pregunta': '¿En qué calle y número vive?',
        'ayuda': 'Domicilio para notificaciones: calle, número y, si lo dice, colonia.',
    },
    {
        'campo': 'direccion_colonia', 'grupo': 'Trabajador', 'tipo': 'texto',
        'pregunta': '¿En qué colonia?',
        'ayuda': 'Si ya dijiste la colonia en la calle, puedes omitir.',
    },
    {
        'campo': 'puesto', 'grupo': 'Trabajo', 'tipo': 'texto',
        'pregunta': '¿Qué puesto desempeñaba?',
        'ayuda': 'El nombre del puesto, como se lo dijeron al contratarlo.',
    },
    {
        'campo': 'actividades', 'grupo': 'Trabajo', 'tipo': 'relato',
        'pregunta': '¿Qué hacía en el trabajo? Cuéntame sus funciones.',
        'ayuda': 'Habla con calma; se transcribe tal cual para el hecho del puesto.',
    },
    {
        'campo': 'salario', 'grupo': 'Trabajo', 'tipo': 'dinero',
        'pregunta': '¿Cuánto gana al mes?',
        'ayuda': 'Dime la cantidad mensual. Si te pagan por semana o quincena, '
                 'dime cuánto y cada cuándo para convertirlo.',
    },
    {
        'campo': 'fecha_ingreso', 'grupo': 'Trabajo', 'tipo': 'fecha',
        'pregunta': '¿Qué día empezó a trabajar?',
        'ayuda': 'Puedes decir «3 de mayo de 2022» o «03/05/2022».',
    },
    {
        'campo': 'fecha_salida', 'grupo': 'Trabajo', 'tipo': 'fecha',
        'pregunta': '¿Qué día terminó la relación laboral?',
        'ayuda': 'El día del despido o de la separación.',
    },
    {
        'campo': 'empresa', 'grupo': 'Patrón', 'tipo': 'texto',
        'pregunta': '¿Cómo se llama la empresa donde trabajaba?',
        'ayuda': 'El nombre comercial, como lo conoce el trabajador.',
    },
    {
        'campo': 'empresa_razon_social', 'grupo': 'Patrón', 'tipo': 'texto',
        'pregunta': '¿Sabes la razón social?',
        'ayuda': 'Si no la sabe, omite; se investiga después.',
    },
    {
        'campo': 'empresa_calle', 'grupo': 'Patrón', 'tipo': 'texto',
        'pregunta': '¿Dónde está el centro de trabajo? Calle y número.',
        'ayuda': 'El domicilio donde prestaba servicios.',
    },
    {
        'campo': 'empresa_colonia', 'grupo': 'Patrón', 'tipo': 'texto',
        'pregunta': '¿En qué colonia está?',
        'ayuda': 'Si no la sabe, omite.',
    },
    {
        'campo': 'modalidad_despido', 'grupo': 'Separación', 'tipo': 'modalidad',
        'pregunta': '¿Cómo le comunicaron la separación?',
        'ayuda': 'Puedes decir «verbal», «me dieron un papel», «no me dejaron entrar» '
                 'u «otra».',
    },
    {
        'campo': 'hora_despido', 'grupo': 'Separación', 'tipo': 'hora',
        'pregunta': '¿A qué hora ocurrió?',
        'ayuda': 'Solo si fue despido verbal. Ejemplo: «14:45» o «2 y 45».',
    },
    {
        'campo': 'despido_comunicado_por', 'grupo': 'Separación', 'tipo': 'texto',
        'pregunta': '¿Quién le comunicó la separación?',
        'ayuda': 'Nombre o puesto de quien se lo dijo.',
    },
    {
        'campo': 'despido_frase', 'grupo': 'Separación', 'tipo': 'relato',
        'pregunta': '¿Qué le dijeron exactamente?',
        'ayuda': 'La frase textual es el hecho más difícil de rebatir.',
    },
)

CAMPOS = tuple(paso['campo'] for paso in PASOS)

MODALIDAD_LABELS = dict(Cliente.MODALIDAD_DESPIDO_CHOICES)

MESES = (
    'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
    'septiembre', 'octubre', 'noviembre', 'diciembre',
)

# ─── Normalización ───────────────────────────────────────────────────────────

def _plano(texto) -> str:
    """Minúsculas y sin acentos, para comparar lo que dicta el reconocedor."""
    normalizado = unicodedata.normalize('NFKD', str(texto or ''))
    sin_acentos = ''.join(c for c in normalizado if not unicodedata.combining(c))
    return sin_acentos.lower().strip()


def _tokens(texto) -> list:
    return re.findall(r'[a-z]+|\d+', _plano(texto))


# ─── Números en español ──────────────────────────────────────────────────────

_UNIDADES = {
    'cero': 0, 'un': 1, 'uno': 1, 'una': 1, 'dos': 2, 'tres': 3, 'cuatro': 4,
    'cinco': 5, 'seis': 6, 'siete': 7, 'ocho': 8, 'nueve': 9, 'diez': 10,
    'once': 11, 'doce': 12, 'trece': 13, 'catorce': 14, 'quince': 15,
    'dieciseis': 16, 'diecisiete': 17, 'dieciocho': 18, 'diecinueve': 19,
    'veinte': 20, 'veintiun': 21, 'veintiuno': 21, 'veintidos': 22,
    'veintitres': 23, 'veinticuatro': 24, 'veinticinco': 25, 'veintiseis': 26,
    'veintisiete': 27, 'veintiocho': 28, 'veintinueve': 29, 'treinta': 30,
    'cuarenta': 40, 'cincuenta': 50, 'sesenta': 60, 'setenta': 70,
    'ochenta': 80, 'noventa': 90, 'cien': 100, 'ciento': 100,
    'doscientos': 200, 'trescientos': 300, 'cuatrocientos': 400,
    'quinientos': 500, 'seiscientos': 600, 'setecientos': 700,
    'ochocientos': 800, 'novecientos': 900,
}

_IGNORAR = frozenset((
    'y', 'con', 'de', 'del', 'pesos', 'peso', 'mensual', 'mensuales', 'al',
    'mes', 'son', 'gana', 'ganaba', 'ganamos', 'es', 'como', 'unos',
    'aproximadamente', 'm', 'n', 'quincena', 'semana', 'semanal', 'quincenal',
))


def _numero_de_palabras(tokens) -> int | None:
    """«dos mil cuatrocientos» → 2400.  None si hay una palabra desconocida."""
    total = 0
    parcial = 0
    for token in tokens:
        if token in _IGNORAR:
            continue
        if token == 'mil':
            total += (parcial or 1) * 1000
            parcial = 0
        elif token in _UNIDADES:
            parcial += _UNIDADES[token]
        elif token.isdigit():
            parcial += int(token)
        else:
            return None
    return total + parcial


# ─── Fechas ──────────────────────────────────────────────────────────────────

def _fecha_valida(anio: int, mes: int, dia: int) -> date | None:
    try:
        return date(anio, mes, dia)
    except ValueError:
        return None


def parse_fecha(texto) -> date | None:
    """Interpreta fechas dictadas: ISO, dd/mm/aaaa, «3 de mayo de 2022»."""
    plano = _plano(texto)
    tokens = _tokens(texto)

    # 2022-05-03 / 2022/05/03
    con_anio_primero = re.search(
        r'\b(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\b', plano)
    if con_anio_primero:
        anio, mes, dia = map(int, con_anio_primero.groups())
        return _fecha_valida(anio, mes, dia)

    # 03/05/2022 / 3-5-22
    con_separadores = re.search(
        r'\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})\b', plano)
    if con_separadores:
        dia, mes, anio = map(int, con_separadores.groups())
        if anio < 100:
            anio += 2000
        return _fecha_valida(anio, mes, dia)

    # «3 de mayo de 2022» / «tres de mayo del dos mil veintidós»
    indice_mes = next((i for i, t in enumerate(tokens) if t in MESES), None)
    if indice_mes is None:
        return None
    mes = MESES.index(tokens[indice_mes]) + 1
    antes = tokens[:indice_mes]
    despues = tokens[indice_mes + 1:]
    dia = _numero_de_palabras(antes)
    anio = _numero_de_palabras(despues)
    if dia is None or anio is None or not 1 <= dia <= 31 or not 1900 <= anio <= 2100:
        return None
    return _fecha_valida(anio, mes, dia)


def fecha_larga(valor: date) -> str:
    return f'{valor.day} de {MESES[valor.month - 1]} de {valor.year}'


# ─── Dinero ──────────────────────────────────────────────────────────────────

def parse_dinero(texto) -> Decimal | None:
    """Interpreta cantidades dictadas: «$2,400», «2 mil», «dos mil cuatrocientos»."""
    plano = _plano(texto)
    if not plano:
        return None
    tokens = _tokens(plano)

    # «2 mil» / «3 mil 500»: el reconocedor a veces entrega el número en dígitos.
    if 'mil' in tokens:
        numeros = [t for t in tokens if t.isdigit()]
        if numeros and not re.search(r'\d[.,]\d{3}', plano):
            if len(numeros) == 1:
                return _a_decimal(Decimal(numeros[0]) * 1000)
            if len(numeros) == 2 and len(numeros[1]) == 3:
                return _a_decimal(Decimal(numeros[0]) * 1000 + Decimal(numeros[1]))

    # Cifras con separadores de miles o decimales.
    crudo = re.sub(r'[^\d.,]', '', plano)
    if crudo:
        if ',' in crudo and '.' in crudo:
            if crudo.rfind(',') > crudo.rfind('.'):
                crudo = crudo.replace('.', '').replace(',', '.')
            else:
                crudo = crudo.replace(',', '')
        elif ',' in crudo:
            partes = crudo.split(',')
            if len(partes) == 2 and len(partes[1]) == 3 and len(partes[0]) <= 3:
                crudo = crudo.replace(',', '')
            else:
                crudo = crudo.replace(',', '.')
        try:
            return _a_decimal(Decimal(crudo))
        except InvalidOperation:
            pass

    valor = _numero_de_palabras(tokens)
    if valor is None:
        return None
    return _a_decimal(Decimal(valor))


def _a_decimal(valor: Decimal) -> Decimal | None:
    if valor <= 0:
        return None
    return valor.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def dinero_largo(valor: Decimal, periodo: str = 'mensual') -> str:
    return f'${valor:,.2f} {periodo}'


# ─── Hora ────────────────────────────────────────────────────────────────────

def parse_hora(texto) -> str | None:
    """«14:45», «2:45 pm», «2 y 45» → 'HH:MM' en 24 horas."""
    plano = _plano(texto)
    coincidencia = re.search(r'\b(\d{1,2})[:.](\d{2})\s*(am|pm)?\b', plano)
    if not coincidencia:
        coincidencia = re.search(r'\b(\d{1,2})\s*(?:y|con)\s*(\d{1,2})\s*(am|pm)?\b', plano)
    if not coincidencia:
        return None
    hora = int(coincidencia.group(1))
    minuto = int(coincidencia.group(2))
    sufijo = coincidencia.group(3) if (coincidencia.lastindex or 0) >= 3 else None
    if sufijo == 'pm' or (not sufijo and re.search(r'\b(tarde|noche)\b', plano)):
        if hora < 12:
            hora += 12
    elif sufijo == 'am' and hora == 12:
        hora = 0
    if not (0 <= hora <= 23 and 0 <= minuto <= 59):
        return None
    return f'{hora:02d}:{minuto:02d}'


# ─── Modalidad de la separación ──────────────────────────────────────────────

def parse_modalidad(texto) -> str | None:
    plano = _plano(texto)
    if re.search(r'\b(escrito|documento|papel|carta|acta|correo|whatsapp)\b', plano):
        return 'escrito'
    if re.search(r'\b(acceso|entrar|entrada|dejaron|negaron|candado|bloqueado)\b', plano):
        return 'acceso'
    if re.search(r'\b(verbal|palabra|boca|dijo|dijeron|comunico|hablado)\b', plano):
        return 'verbal'
    if re.search(r'\b(otro|otra|diferente)\b', plano):
        return 'otro'
    return None


# ─── Interpretación de un campo ──────────────────────────────────────────────

def interpretar(campo: str, texto) -> dict:
    """Convierte el dictado en el valor que se guarda.

    Returns:
        {'valor': str, 'etiqueta': str, 'aviso': str, 'error': str}
    """
    respuesta = {'valor': '', 'etiqueta': '', 'aviso': '', 'error': ''}
    paso = next((p for p in PASOS if p['campo'] == campo), None)
    if paso is None:
        respuesta['error'] = 'Ese dato no forma parte de la captura por voz.'
        return respuesta

    limpio = re.sub(r'\s+', ' ', str(texto or '')).strip()
    if not limpio:
        respuesta['error'] = 'No se escuchó nada. Intenta de nuevo.'
        return respuesta

    tipo = paso['tipo']
    if tipo in ('texto', 'relato'):
        respuesta['valor'] = limpio
        respuesta['etiqueta'] = limpio
        return respuesta

    if tipo == 'curp':
        valor = re.sub(r'[^A-Z0-9]', '', limpio.upper())
        respuesta['valor'] = valor
        respuesta['etiqueta'] = valor
        if len(valor) != 18:
            respuesta['aviso'] = ('La CURP debe tener 18 caracteres; revisa el '
                                  'dictado o escríbela.')
        return respuesta

    if tipo == 'telefono':
        digitos = re.sub(r'\D', '', limpio)
        respuesta['valor'] = digitos
        respuesta['etiqueta'] = digitos
        if len(digitos) < 10:
            respuesta['aviso'] = 'El teléfono parece incompleto (se esperan 10 dígitos).'
        return respuesta

    if tipo == 'dinero':
        valor = parse_dinero(limpio)
        if valor is None:
            respuesta['error'] = ('No entendí la cantidad. Di el salario mensual, '
                                  'por ejemplo «doce mil cuatrocientos».')
            return respuesta
        respuesta['valor'] = f'{valor:.2f}'
        respuesta['etiqueta'] = dinero_largo(valor)
        return respuesta

    if tipo == 'fecha':
        valor = parse_fecha(limpio)
        if valor is None:
            respuesta['error'] = ('No entendí la fecha. Dila como «3 de mayo de '
                                  '2022» o escríbela.')
            return respuesta
        respuesta['valor'] = valor.isoformat()
        respuesta['etiqueta'] = fecha_larga(valor)
        return respuesta

    if tipo == 'hora':
        valor = parse_hora(limpio)
        if valor is None:
            respuesta['error'] = 'No entendí la hora. Dila como «14:45».'
            return respuesta
        respuesta['valor'] = valor
        respuesta['etiqueta'] = valor
        return respuesta

    if tipo == 'modalidad':
        valor = parse_modalidad(limpio)
        if valor is None:
            respuesta['error'] = ('No entendí cómo le comunicaron la separación. '
                                  'Di «verbal», «documento», «no me dejaron entrar» '
                                  'u «otra».')
            return respuesta
        respuesta['valor'] = valor
        respuesta['etiqueta'] = MODALIDAD_LABELS.get(valor, valor)
        return respuesta

    respuesta['error'] = 'Tipo de dato desconocido.'
    return respuesta


# ─── Estado inicial de la pantalla ──────────────────────────────────────────

def _etiqueta_actual(paso: dict, valor) -> str:
    if valor in (None, ''):
        return ''
    if paso['tipo'] == 'fecha' and isinstance(valor, date):
        return fecha_larga(valor)
    if paso['tipo'] == 'dinero':
        return dinero_largo(Decimal(valor))
    if paso['tipo'] == 'modalidad':
        return MODALIDAD_LABELS.get(valor, valor)
    return str(valor)


def pasos_con_valores(cliente) -> list:
    """Guion + lo ya capturado, listo para la pantalla."""
    pasos = []
    for paso in PASOS:
        actual = getattr(cliente, paso['campo'], None)
        if isinstance(actual, date):
            valor = actual.isoformat()
        elif isinstance(actual, Decimal):
            valor = f'{actual:.2f}'
        else:
            valor = '' if actual is None else str(actual)
        paso_completo = dict(paso)
        paso_completo.update({
            'valor': valor,
            'etiqueta': _etiqueta_actual(paso, actual),
            'capturado': bool(actual),
        })
        if paso['tipo'] == 'modalidad':
            paso_completo['opciones'] = [
                {'valor': clave, 'etiqueta': etiqueta}
                for clave, etiqueta in Cliente.MODALIDAD_DESPIDO_CHOICES
            ]
        pasos.append(paso_completo)
    return pasos
