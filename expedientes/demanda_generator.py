"""
Generador de Demanda Laboral (Word .docx)
==========================================

Genera un documento profesional de Demanda Laboral Mexicana
con todos los datos del expediente, cálculos integrados y
formato apto para impresión y firma.

Autor: Conciliacion Laboral Tijuana - Módulo de Demandas
"""

import re
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import nsdecls
from docx.oxml import parse_xml

from django.utils import timezone

from .models import Expediente
from .laboral_calculator import calcular_desde_expediente, conceptos_por_tipo_despido


# ─── Meses en español ──────────────────────────────────────────────────────

MESES_ES = [
    "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def importe_en_letras(monto) -> str:
    """MXN amounts with the same rounded cents used in the document."""
    unidades = ('cero', 'un', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete',
                'ocho', 'nueve', 'diez', 'once', 'doce', 'trece', 'catorce',
                'quince', 'dieciséis', 'diecisiete', 'dieciocho', 'diecinueve',
                'veinte', 'veintiún', 'veintidós', 'veintitrés', 'veinticuatro',
                'veinticinco', 'veintiséis', 'veintisiete', 'veintiocho', 'veintinueve')
    decenas = ('', '', '', 'treinta', 'cuarenta', 'cincuenta', 'sesenta',
               'setenta', 'ochenta', 'noventa')
    centenas = ('', 'ciento', 'doscientos', 'trescientos', 'cuatrocientos',
                'quinientos', 'seiscientos', 'setecientos', 'ochocientos', 'novecientos')

    def numero(n):
        if n < 30:
            return unidades[n]
        if n < 100:
            return decenas[n // 10] + (' y ' + unidades[n % 10] if n % 10 else '')
        if n == 100:
            return 'cien'
        if n < 1000:
            return centenas[n // 100] + (' ' + numero(n % 100) if n % 100 else '')
        if n < 1000000:
            return ('mil' if n // 1000 == 1 else numero(n // 1000) + ' mil') + (
                ' ' + numero(n % 1000) if n % 1000 else '')
        return ('un millón' if n // 1000000 == 1 else numero(n // 1000000) + ' millones') + (
            ' ' + numero(n % 1000000) if n % 1000000 else '')

    valor = Decimal(str(monto)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    entero = int(abs(valor))
    centavos = int((abs(valor) - entero) * 100)
    moneda = 'peso' if entero == 1 else ('de pesos' if entero and entero % 1000000 == 0 else 'pesos')
    return f"{'menos ' if valor < 0 else ''}{numero(entero)} {moneda} {centavos:02d}/100 M.N."


def _importe_demanda(monto):
    valor = Decimal(str(monto)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return f'${valor:,.2f} ({importe_en_letras(valor)})'


# ─── Plantillas de Demanda (tipos de despido) ──────────────────────────────

PLANTILLAS_INFO = {
    'injustificado': {
        'nombre': 'Despido Injustificado',
        'descripcion': 'El patrón despidió al trabajador sin causa justificada. Reclama indemnización completa (3 meses + antigüedad + prestaciones).',
        'icono': '⚡',
        'recomendado': True,
    },
    'justificado': {
        'nombre': 'Despido Justificado (con responsabilidad al patrón)',
        'descripcion': 'El trabajador rescinde la relación laboral por causas imputables al patrón (falta de pago, maltrato, etc.).',
        'icono': '🛡️',
        'recomendado': False,
    },
    'voluntario': {
        'nombre': 'Renuncia Voluntaria',
        'descripcion': 'El trabajador renunció voluntariamente. Solo reclama prestaciones proporcionales adeudadas (aguinaldo, vacaciones, prima vacacional).',
        'icono': '✍️',
        'recomendado': False,
    },
    'rescision': {
        'nombre': 'Rescisión de la Relación Laboral',
        'descripcion': 'Rescisión imputable al patrón por incumplimiento grave (Art. 51 LFT). Reclama indemnización completa.',
        'icono': '⚖️',
        'recomendado': False,
    },
    'otro': {
        'nombre': 'Otro / Personalizado',
        'descripcion': 'Plantilla genérica para cualquier otra causa de terminación laboral. Edita libremente el contenido.',
        'icono': '📄',
        'recomendado': False,
    },
}


def _fecha_espanol(fecha) -> str:
    """Formatea una fecha en español: '1 de enero de 2024'."""
    if not fecha:
        return "[FECHA]"
    return f"{fecha.day} de {MESES_ES[fecha.month]} de {fecha.year}"


# ─── Estilos ───────────────────────────────────────────────────────────────

TITLE_FONT_SIZE = Pt(14)
SUBTITLE_FONT_SIZE = Pt(12)
SECTION_FONT_SIZE = Pt(11)
BODY_FONT_SIZE = Pt(10)
TABLE_FONT_SIZE = Pt(9.5)

MARGIN_TOP = Cm(2.5)
MARGIN_BOTTOM = Cm(2.5)
MARGIN_LEFT = Cm(3)
MARGIN_RIGHT = Cm(2.5)

COLOR_PRIMARY = RGBColor(0x1F, 0x29, 0x37)   # Azul oscuro
COLOR_ACCENT = RGBColor(0x1D, 0x4E, 0xD8)    # Azul acento
COLOR_HEADER_BG = "1F2937"                    # Fondo encabezado tabla
COLOR_ALT_ROW = "F3F4F6"                      # Fila alterna tabla
COLOR_BLACK = RGBColor(0x00, 0x00, 0x00)
COLOR_GRAY = RGBColor(0x6B, 0x72, 0x80)


def _configurar_documento(doc: Document) -> None:
    """Configura márgenes, fuente base y orientación."""
    seccion = doc.sections[0]
    seccion.top_margin = MARGIN_TOP
    seccion.bottom_margin = MARGIN_BOTTOM
    seccion.left_margin = MARGIN_LEFT
    seccion.right_margin = MARGIN_RIGHT

    estilo = doc.styles['Normal']
    estilo.font.name = 'Calibri'
    estilo.font.size = BODY_FONT_SIZE
    estilo.font.color.rgb = COLOR_BLACK
    estilo.paragraph_format.space_after = Pt(6)
    estilo.paragraph_format.line_spacing = 1.15


def _agregar_encabezado_tribunal(doc: Document) -> None:
    """Agrega el encabezado con el nombre del tribunal."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("TRIBUNAL LABORAL COMPETENTE")
    run.bold = True
    run.font.size = TITLE_FONT_SIZE
    run.font.color.rgb = COLOR_PRIMARY

    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run2 = p2.add_run("TIJUANA, BAJA CALIFORNIA")
    run2.font.size = SUBTITLE_FONT_SIZE
    run2.font.color.rgb = COLOR_GRAY

    # Línea separadora
    p_linea = doc.add_paragraph()
    p_linea.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_linea = p_linea.add_run("─" * 70)
    run_linea.font.color.rgb = COLOR_ACCENT
    run_linea.font.size = Pt(8)
    doc.add_paragraph()


def _celda_sombreada(celda, color: str) -> None:
    """Aplica color de fondo a una celda de tabla."""
    sombreado = parse_xml(
        f'<w:shd {nsdecls("w")} w:fill="{color}"/>'
    )
    celda._tc.get_or_add_tcPr().append(sombreado)


def _agregar_materia(doc: Document, expediente: Expediente) -> None:
    """Agrega la materia, tipo de juicio y expediente."""
    tabla = doc.add_table(rows=3, cols=2)
    tabla.style = 'Table Grid'
    tabla.alignment = WD_TABLE_ALIGNMENT.CENTER

    datos = [
        ("MATERIA:", "LABORAL"),
        ("TIPO DE JUICIO:", "ORDINARIO LABORAL"),
        ("N° EXPEDIENTE CONCILIACIÓN:", expediente.folio or "—"),
    ]

    for i, (label, valor) in enumerate(datos):
        celda_label = tabla.cell(i, 0)
        celda_valor = tabla.cell(i, 1)

        p_label = celda_label.paragraphs[0]
        run_label = p_label.add_run(label)
        run_label.bold = True
        run_label.font.size = BODY_FONT_SIZE

        p_valor = celda_valor.paragraphs[0]
        run_valor = p_valor.add_run(valor)
        run_valor.bold = True
        run_valor.font.size = BODY_FONT_SIZE
        run_valor.font.color.rgb = COLOR_ACCENT

        celda_label.width = Cm(5.5)
        celda_valor.width = Cm(7)
        _celda_sombreada(celda_label, COLOR_ALT_ROW)

    doc.add_paragraph()


def _agregar_actor(doc: Document, expediente: Expediente) -> None:
    """Agrega la sección del ACTOR (trabajador)."""
    cliente = expediente.cliente

    p = doc.add_paragraph()
    run = p.add_run("—  A C T O R  —")
    run.bold = True
    run.font.size = SECTION_FONT_SIZE
    run.font.color.rgb = COLOR_PRIMARY

    items = [(cliente.nombre, True)]
    if cliente.direccion_completa:
        items.append((f"Domicilio: {cliente.direccion_completa}", False))
    if cliente.curp:
        items.append((f"CURP: {cliente.curp}", False))
    if cliente.rfc:
        items.append((f"RFC: {cliente.rfc}", False))
    if cliente.telefono:
        items.append((f"Teléfono: {cliente.telefono}", False))

    for texto, negrita in items:
        p = doc.add_paragraph()
        run = p.add_run(f"  {texto}")
        run.bold = negrita
        run.font.size = BODY_FONT_SIZE
        p.paragraph_format.space_after = Pt(2)

    doc.add_paragraph()


def _agregar_demandado(doc: Document, expediente: Expediente) -> None:
    """Agrega la sección del DEMANDADO (patrón/empresa)."""
    cliente = expediente.cliente

    p = doc.add_paragraph()
    run = p.add_run("—  D E M A N D A D O  —")
    run.bold = True
    run.font.size = SECTION_FONT_SIZE
    run.font.color.rgb = COLOR_PRIMARY

    razon_social = cliente.empresa_razon_social or cliente.empresa
    items = [(razon_social or "—", True)]

    partes_dir = []
    if cliente.empresa_calle:
        partes_dir.append(cliente.empresa_calle)
    if cliente.empresa_numero:
        partes_dir.append(f"#{cliente.empresa_numero}")
    if cliente.empresa_colonia:
        partes_dir.append(f"Col. {cliente.empresa_colonia}")
    if cliente.empresa_cp:
        partes_dir.append(f"CP {cliente.empresa_cp}")
    if partes_dir:
        items.append((f"Domicilio: {', '.join(partes_dir)}", False))

    if cliente.empresa_telefono:
        items.append((f"Teléfono: {cliente.empresa_telefono}", False))
    if cliente.empresa_actividad:
        items.append((f"Actividad: {cliente.empresa_actividad}", False))

    for texto, negrita in items:
        p = doc.add_paragraph()
        run = p.add_run(f"  {texto}")
        run.bold = negrita
        run.font.size = BODY_FONT_SIZE
        p.paragraph_format.space_after = Pt(2)

    doc.add_paragraph()


def _narrativa_despido(tipo_despido_key: str) -> str:
    """Devuelve la frase legal correcta según el tipo de despido."""
    narrativas = {
        'injustificado': "el demandado dio por terminada la relación laboral de manera injustificada",
        'justificado': "el actor dio por terminada la relación laboral por causas imputables al demandado",
        'voluntario': "la relación laboral concluyó por renuncia voluntaria del actor",
        'rescision': "el actor se vio en la necesidad de rescindir la relación laboral",
        'otro': "la relación laboral concluyó",
    }
    return narrativas.get(tipo_despido_key,
                          "el demandado dio por terminada la relación laboral de manera injustificada")


def _conceptos_para_demanda(tipo_despido_key: str, años_completos: int = 0) -> dict:
    """Selección de conceptos que se reclaman en la demanda según el tipo de despido.

    Delega en `core.laboral.rules` (arts. 50 y 162 LFT), de modo que la demanda,
    la pantalla de cálculo y el recálculo apliquen la MISMA regla:

    - Despido injustificado / rescisión: 3 meses (art. 50 fr. III) + 20 días por
      año (art. 50 fr. II) + prima de antigüedad (art. 162 fr. III).
    - Despido justificado: sin indemnización del art. 50 (el art. 46 LFT excluye
      la responsabilidad del patrón en la rescisión justificada), pero SÍ prima
      de antigüedad (art. 162 fr. III: "se pagará a los que se separen por causa
      justificada").
    - Renuncia voluntaria: sin art. 50, y prima de antigüedad sólo con 15 años o
      más de servicios (art. 162 fr. III).

    Las prestaciones ordinarias (aguinaldo, vacaciones, prima vacacional, horas
    extras) se reclaman en todos los casos.
    """
    return conceptos_por_tipo_despido(tipo_despido_key, años_completos)


def _años_completos_de(cliente) -> int:
    """Años completos del cliente (para el umbral de 15 años del art. 162)."""
    from core.laboral.periodo import construir_periodo

    periodo = construir_periodo(cliente.fecha_ingreso, cliente.fecha_salida)
    return periodo.años_completos if periodo else 0


def calculo_para_demanda(expediente: Expediente,
                         tipo_despido: Optional[str] = None) -> dict:
    """Cálculo que la demanda debe usar, en este orden:

    1. El `CalculoLaboral` guardado: es lo que el asesor revisó y aprobó en la
       pantalla de Cálculo Laboral (conceptos marcados, horas extras por tipo,
       días de vacaciones, salario integrado, etc.).  La demanda NO puede
       calcular por su cuenta e inventarse un total distinto al que se le
       mostró al cliente.
    2. Si no existe todavía, se deriva del tipo de despido con las reglas de los
       arts. 50 y 162 LFT.
    """
    from .laboral_calculator import CONCEPTOS_CALCULO, datos_extra_de
    from .models import CalculoLaboral

    tipo = tipo_despido or expediente.tipo_despido or 'injustificado'
    calculo = CalculoLaboral.objects.filter(expediente=expediente).first()

    if calculo is not None:
        conceptos = {
            f'incluir_{key}': getattr(calculo, f'incluir_{key}', True)
            for key in CONCEPTOS_CALCULO
        }
        return calcular_desde_expediente(
            expediente,
            conceptos_seleccionados=conceptos,
            datos_extra=datos_extra_de(calculo),
            tipo_despido=tipo,
        )

    return calcular_desde_expediente(
        expediente,
        conceptos_seleccionados=_conceptos_para_demanda(
            tipo, _años_completos_de(expediente.cliente)),
        tipo_despido=tipo,
    )


def _texto_como_lista(valor: str | None) -> str:
    """Convierte texto multilínea (uno por línea) en lista legible 'a), b), c)...'.
    Para un solo elemento (o sin saltos de línea) devuelve el texto tal cual."""
    if not valor:
        return ""
    lineas = [l.strip().rstrip('.') for l in valor.splitlines() if l.strip()]
    if len(lineas) <= 1:
        return (lineas[0] if lineas else "").strip()
    letras = "abcdefghijklm".upper()
    return "; ".join(f"{letras[i]}) {l}" for i, l in enumerate(lineas[:13])) + "."


ORDINALES = (
    'PRIMERO', 'SEGUNDO', 'TERCERO', 'CUARTO', 'QUINTO', 'SEXTO', 'SEPTIMO',
    'OCTAVO', 'NOVENO', 'DECIMO', 'DECIMO PRIMERO', 'DECIMO SEGUNDO',
    'DECIMO TERCERO', 'DECIMO CUARTO', 'DECIMO QUINTO', 'DECIMO SEXTO',
    'DECIMO SEPTIMO', 'DECIMO OCTAVO', 'DECIMO NOVENO', 'VIGESIMO',
)


def _ordinal(numero: int) -> str:
    """Ordinal en mayúsculas para los HECHOS (PRIMERO, SEGUNDO, ...)."""
    if 1 <= numero <= len(ORDINALES):
        return ORDINALES[numero - 1]
    return f'NUMERO {numero}'


def _hecho_circunstancias(cliente) -> str:
    """Redactado del hecho de separación según la modalidad capturada.

    Cada modalidad tiene su propio redactado porque el artículo 47 LFT exige que
    el patrón que despide entregue aviso escrito donde referencie claramente la
    conducta y su fecha: si no hay documento, el patrono queda expuesto a que
    la separación se presuma injustificada.
    """
    modalidad = (cliente.modalidad_despido or '').strip()

    comun = []
    lugar = (cliente.despido_lugar or '').strip()
    quien = (cliente.despido_comunicado_por or '').strip()
    frase = (cliente.despido_frase or '').strip()
    motivo = (cliente.despido_documento_motivo or '').strip()
    otra = (cliente.despido_otra_modalidad or '').strip()

    if modalidad == 'verbal':
        texto = ('El trabajador fue separado de su empleo mediante un despido '
                 'verbal, sin que se le entregara documento alguno de la '
                 'terminación de la relación laboral.')
        if quien:
            texto += f' La separación le fue comunicada por {quien}.'
        if lugar:
            texto += f' Los hechos ocurrieron en {lugar}.'
        if frase:
            texto += f' En dicho momento se le manifestó, en esencia, lo siguiente: \"{frase}\".'
        texto += (' La falta de aviso escritoilibrium viola el artículo 47 de la Ley Federal '
                  'del Trabajo, que obliga al patrón a entregar aviso escrito referenciando '
                  'claramente la conducta que motiva la rescisión, por lo que la separación '
                  'debe tenerse por injustificada.')
        return texto

    if modalidad == 'escrito':
        texto = ('El trabajador recibió un documento mediante el cual la parte '
                 'demandada comunicó la terminación de la relación laboral.')
        if motivo:
            texto += f' El documento señala como motivo: \"{motivo}\".'
        else:
            texto += (' El documento no consigna causa alguna que justifique la '
                      'rescisión.')
        if quien:
            texto += f' La entrega fue feita por {quien}.'
        if lugar:
            texto += f' Los hechos ocurrieron en {lugar}.'
        if frase:
            texto += f' Al respecto, se le manifestó lo siguiente: \"{frase}\".'
        return texto

    if modalidad == 'acceso':
        texto = ('El trabajador se presentó a su centro de trabajo en la fecha de '
                 'terminación; sin embargo, se le impidió el acceso y se le negó '
                 'la posibilidad de continuar prestando sus servicios.')
        if quien:
            texto += f' La negativa le fue comunicada por {quien}.'
        if lugar:
            texto += f' Los hechos ocurrieron en {lugar}.'
        if frase:
            texto += f' Se le manifestó lo siguiente: \"{frase}\".'
        texto += (' La negativa de acceso a las instalaciones equivale a la '
                  'separación, pues el acceso al centro de trabajo es '
                  'indispensable para prestar el servicio.')
        return texto

    if modalidad == 'otro':
        texto = 'Sobre la forma en que se produjo la separación, el actor manifiesta lo siguiente:'
        texto += f' {otra}' if otra else ''
        if lugar:
            texto += f' Los hechos ocurrieron en {lugar}.'
        return texto

    # Sin modalidad capturada: se conserva la narrativa del tipo de despido, que
    # es lo que siempre se ha usado.
    return ''


def html_escape(texto: str) -> str:
    """Escapa el texto para insertarlo en el HTML de la demanda."""
    return (str(texto)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;'))


def construir_hechos(expediente: Expediente, calculo: dict,
                     tipo_despido: str = 'injustificado') -> list:
    """Lista de HECHOS numerados, en párrafos separados.

    Fuente ÚNICA de la narrativa: la consumen tanto el generador DOCX como el
    HTML, de modo que ambas salidas dicen exactamente lo mismo.
    """
    cliente = expediente.cliente
    hechos = []

    f_ingreso = _fecha_espanol(cliente.fecha_ingreso)
    f_salida = _fecha_espanol(cliente.fecha_salida)
    puesto = cliente.puesto or '[PUESTO DESEMPEÑADO]'
    empresa = cliente.empresa_razon_social or cliente.empresa or '[EMPRESA DEMANDADA]'
    folio = expediente.folio or '[FOLIO DE CONCILIACIÓN]'
    f_tramite = _fecha_espanol(expediente.fecha_tramite)

    # 1. Ingreso
    ingreso = (f'El {f_ingreso}, el actor inició su relación laboral con el '
               f'demandado {empresa}, desempeñando el puesto de {puesto}')
    lugar_trabajo = (cliente.lugar_trabajo or '').strip()
    if lugar_trabajo:
        ingreso += f', en el centro de trabajo ubicado en {lugar_trabajo}'
    ingreso += ', en la forma y términos convenidos.'
    hechos.append(ingreso)

    # 2. Salario: diario y diario integrado (arts. 84 y 89 LFT)
    if calculo.get('success'):
        sd = calculo['salario_diario']
        sdi = calculo['salario_diario_integrado']
        salario = (f'Durante la relación laboral el actor percibió un salario '
                   f'diario de ${sd:,.2f}')
        if sdi > sd:
            salario += (f', que corresponde a un salario diario integrado de '
                        f'${sdi:,.2f}, conforme a los artículos 84 y 89 de la Ley '
                        f'Federal del Trabajo')
            componentes = calculo.get('salario_integrado_componentes') or {}
            detalle = ', '.join(f'{_nombre_componente(k)}: ${v:,.2f}'
                                for k, v in componentes.items() if v)
            if detalle:
                salario += f' (incluye {detalle})'
        else:
            salario += ', y cuyo salario diario integrado es equivalente al '\
                        'salario diario ordinario por no haber prestaciones '\
                        'integrantes declaradas'
        salario += '.'
        hechos.append(salario)
    elif cliente.salario:
        hechos.append(
            f'Durante la relación laboral el actor percibió un salario mensual '
            f'de ${cliente.salario:,.2f}, pagaderos en la forma y términos convenidos.')

    # 3. Jornada
    jornada = (cliente.jornada or '').strip()
    if jornada:
        hechos.append(
            f'La jornada laboral se desarrollaba en régimen {jornada}, con una '
            f'jornada de {cliente.horas_semanales or 48} horas semanales.')

    # 4. Antigüedad: la calcula el motor (aniversarios cumplidos), no días/365
    if calculo.get('success'):
        años = calculo['años_completos']
        anios_txt = (f'{años} año' + ('' if años == 1 else 's') + ' completos')
        if calculo['años_trabajados'] != float(años):
            anios_txt += (f' ({calculo["años_trabajados"]} años al momento de '
                          f'la terminación, contando la fracción del año en curso)')
        hechos.append(
            f'La relación laboral tuvo una duración de {anios_txt}, '
            f'transcurridos entre el {f_ingreso} y el {f_salida}.')

    # 5. Separación
    hechos.append(
        f'El {f_salida}, {_narrativa_despido(tipo_despido)}, violando en '
        f'perjuicio del actor lo dispuesto por los artículos 46, 47 y 48 de la '
        f'Ley Federal del Trabajo.')

    # 6. Modalidad de la separación (redactado estructurado)
    circunstancias = _hecho_circunstancias(cliente)
    if circunstancias:
        hechos.append(circunstancias)

    # 7. Instancia conciliatoria
    hechos.append(
        f'El actor agotó la instancia conciliatoria ante el Centro de '
        f'Conciliación Laboral, según consta en el expediente número {folio} '
        f'de fecha {f_tramite}, sin que se lograra acuerdo conciliatorio alguno, '
        f'por lo que se expidió la constancia de no conciliación correspondiente.')

    # 8. Falta de pago
    hechos.append(
        'A la fecha de presentación de esta demanda, el demandado no ha '
        'cubierto el pago de las prestaciones laborales que se reclaman, a '
        'pesar de haber sido requerido para ello.')

    # 9. Elección de acción (art. 48 LFT)
    accion = (calculo or {}).get('accion') or {}
    if accion.get('accion') == 'reinstalacion':
        hechos.append(
            'En atención a lo dispuesto por el artículo 48 de la Ley Federal '
            'del Trabajo, el actor opta por la REINSTALACIÓN en el puesto que '
            'venía desempeñando, por lo que no se reclama la indemnización '
            'equivalente a tres meses de salario.')

    # 10. Anotaciones libres del asesor
    texto_libre = (cliente.circunstancias_despido or '').strip()
    if texto_libre:
        hechos.append(
            f'Sobre las circunstancias de la separación, el actor manifiesta '
            f'adicionalmente lo siguiente: {texto_libre}')

    # 11. Testigos
    testigos = _texto_como_lista(cliente.testigos)
    if testigos:
        hechos.append(
            f'Los hechos anteriores podrán ser corroborados por las personas '
            f'que oportunamente se señalarán como testigos: {testigos}')

    # 12. Documentos entregados en la separación
    if cliente.hubo_documento_despido:
        hechos.append(
            'La parte demandada entregó al trabajador documentación relacionada '
            'con la terminación de la relación laboral, misma que será ofrecida '
            'como prueba en lo que resulte conducente.')

    # Numerar
    return [f'{_ordinal(i)}.- {texto}' for i, texto in enumerate(hechos, start=1)]


def _agregar_hechos(doc: Document, expediente: Expediente, calculo: dict,
                    tipo_despido: str = 'injustificado') -> None:
    """Agrega la sección de HECHOS (DOCX) desde la narrativa compartida."""
    p = doc.add_paragraph()
    run = p.add_run('—  H E C H O S  —')
    run.bold = True
    run.font.size = SECTION_FONT_SIZE
    run.font.color.rgb = COLOR_PRIMARY

    for hecho in construir_hechos(expediente, calculo, tipo_despido):
        p_hecho = doc.add_paragraph()
        run_hecho = p_hecho.add_run(hecho)
        run_hecho.font.size = BODY_FONT_SIZE
        p_hecho.paragraph_format.space_after = Pt(6)

    doc.add_paragraph()


def _agregar_pruebas(doc: Document, expediente: Expediente) -> None:
    """Agrega la sección de PRUEBAS (documental, testimonial, instrumental, presuncional)."""
    p = doc.add_paragraph()
    run = p.add_run("—  P R U E B A S  —")
    run.bold = True
    run.font.size = SECTION_FONT_SIZE
    run.font.color.rgb = COLOR_PRIMARY

    documentos_txt = _texto_como_lista(expediente.cliente.documentos_prueba)
    numero = 1
    if documentos_txt:
        p = doc.add_paragraph()
        run = p.add_run(f"  {numero}. DOCUMENTAL. Consistente en los documentos siguientes: {documentos_txt}.")
        run.font.size = BODY_FONT_SIZE
        numero += 1
    if (expediente.cliente.testigos or '').strip():
        p = doc.add_paragraph()
        run = p.add_run(f"  {numero}. TESTIMONIAL. A cargo de las personas que oportunamente se señalarán, respecto de los hechos controvertidos.")
        run.font.size = BODY_FONT_SIZE
        numero += 1

    fijas = [
        "INSTRUMENTAL DE ACTUACIONES, consistente en todo lo actuado que favorezca a los intereses del trabajador.",
        "PRESUNCIONAL LEGAL Y HUMANA, en todo aquello que beneficie a los intereses de la parte actora.",
    ]
    for f in fijas:
        p = doc.add_paragraph()
        run = p.add_run(f"  {numero}. {f}")
        run.font.size = BODY_FONT_SIZE
        numero += 1

    doc.add_paragraph()


def _filas_prestaciones(calculo: dict, expediente: Expediente) -> list:
    """Renglones de la tabla de prestaciones: (concepto, fundamento, monto).

    Se listan TODOS los conceptos con monto mayor a cero, para que la tabla
    cuadre con el total del cálculo.  DOCX y HTML usan esta misma función, así
    que ambas salidas muestran exactamente las mismas cifras.
    """
    if not calculo.get('success'):
        filas = [
            ("Aguinaldo Proporcional", "Art. 87 LFT", None),
            ("Vacaciones", "Art. 76 LFT", None),
            ("Prima Vacacional", "Art. 80 LFT", None),
        ]
        tipo = expediente.tipo_despido or 'injustificado'
        if tipo != 'voluntario':
            filas.append(("Prima de Antigüedad", "Art. 162 LFT", None))
            filas.append(("Indemnización Constitucional (3 meses)", "Art. 50 LFT", None))
        return filas

    c = calculo
    filas = [
        ("Aguinaldo Proporcional", "Art. 87 LFT", c['aguinaldo']['monto']),
        ("Vacaciones", _fundamento_vacaciones(c), c['vacaciones']['monto']),
        ("Prima Vacacional", f"Art. 80 LFT ({_pct(c['prima_vacacional'])})",
         c['prima_vacacional']['monto']),
    ]
    if c['vacaciones_vencidas']['monto'] > 0:
        filas.append((
            "Vacaciones de ciclos anteriores",
            f"Art. 79 LFT ({c['vacaciones_vencidas']['dias']} días)",
            c['vacaciones_vencidas']['monto'],
        ))
    if c['prima_antiguedad']['monto'] > 0:
        tope = " (con tope)" if c['prima_antiguedad']['tope_aplicado'] else ""
        filas.append((
            "Prima de Antigüedad",
            f"Art. 162 LFT{tope}",
            c['prima_antiguedad']['monto'],
        ))
    if c['indemnizacion']['monto'] > 0:
        filas.append((
            "Indemnización Constitucional (3 meses)",
            "Art. 50 fr. III LFT",
            c['indemnizacion']['monto'],
        ))
    if c['indemnizacion_20dias']['monto'] > 0:
        filas.append((
            "Indemnización 20 días por año",
            "Art. 50 fr. II LFT",
            c['indemnizacion_20dias']['monto'],
        ))
    if c['horas_extras']['monto'] > 0:
        filas.append((
            "Horas Extras",
            _fundamento_horas_extras(c),
            c['horas_extras']['monto'],
        ))
    if c['salarios_devengados']['monto'] > 0:
        filas.append(("Salarios Devengados", "Art. 48 LFT",
                      c['salarios_devengados']['monto']))
    if c['dias_festivos']['monto'] > 0:
        filas.append((
            "Días Festivos laborados",
            f"Art. 74-75 LFT ({c['dias_festivos']['dias']} días)",
            c['dias_festivos']['monto'],
        ))
    if c['descanso_semanal']['monto'] > 0:
        filas.append((
            "Días de Descanso Semanal laborados",
            f"Art. 69 y 73 LFT ({c['descanso_semanal']['dias']} días)",
            c['descanso_semanal']['monto'],
        ))
    return filas


def _fundamento_vacaciones(calculo: dict) -> str:
    """Fundamento con el desglose de días de vacaciones (arts. 76 y 81 LFT)."""
    v = calculo['vacaciones']
    partes = []
    if v.get('dias_causadas_anteriores'):
        partes.append(f"{_num(v['dias_causadas_anteriores'])} de años cumplidos")
    if v.get('dias_proporcionales'):
        partes.append(f"{_num(v['dias_proporcionales'])} proporcionales")
    detalle = f" ({' + '.join(partes)} días)" if partes else ""
    return f"Art. 76 y 81 LFT{detalle}"


def _fundamento_horas_extras(calculo: dict) -> str:
    """Fundamento con el desglose dobles/triples (arts. 66 y 68 LFT)."""
    h = calculo['horas_extras']
    if h.get('dobles') and h.get('triples'):
        return (f"Art. 66 y 68 LFT ({_num(h['dobles'])} dobles + "
                f"{_num(h['triples'])} excedentes)")
    return "Art. 66-68 LFT"


def _pct(concepto: dict) -> str:
    try:
        return f"{float(concepto.get('porcentaje', 0)):.0f}%"
    except (TypeError, ValueError):
        return "25%"


def _num(valor) -> str:
    """Número sin ceros sobrantes (12, 12.5, 12.45)."""
    try:
        d = Decimal(str(valor)).normalize()
    except Exception:
        return str(valor)
    return format(d, 'f')


def _agregar_prestaciones(doc: Document, expediente: Expediente, calculo: dict,
                          tipo_despido: str = 'injustificado') -> None:
    """Agrega la sección de PRESTACIONES RECLAMADAS con tabla de montos."""
    p = doc.add_paragraph()
    run = p.add_run("—  P R E S T A C I O N E S   R E C L A M A D A S  —")
    run.bold = True
    run.font.size = SECTION_FONT_SIZE
    run.font.color.rgb = COLOR_PRIMARY

    intro = doc.add_paragraph()
    run_intro = intro.add_run(
        "Con fundamento en lo dispuesto por la Ley Federal del Trabajo, se reclaman "
        "las siguientes prestaciones:"
    )
    run_intro.font.size = BODY_FONT_SIZE
    doc.add_paragraph()

    # Construir filas de la tabla
    rows = [("PRESTACIÓN", "FUNDAMENTO", "IMPORTE")]
    for concepto, fundamento, monto in _filas_prestaciones(calculo, expediente):
        rows.append((concepto, fundamento, _importe_demanda(monto) if monto is not None else "—"))

    if calculo.get('success'):
        rows.append(("", "TOTAL:", f"${calculo['total']:,.2f}"))
    elif expediente.monto_reclamado:
        rows.append(("", "MONTO RECLAMADO:", f"${expediente.monto_reclamado:,.2f}"))
    else:
        rows.append(("", "MONTO RECLAMADO:", "—"))

    tabla = doc.add_table(rows=len(rows), cols=3)
    tabla.alignment = WD_TABLE_ALIGNMENT.CENTER
    tabla.style = 'Table Grid'

    for i, (col1, col2, col3) in enumerate(rows):
        row = tabla.rows[i]
        es_encabezado = (i == 0)
        es_total = (i == len(rows) - 1)

        for j, celda in enumerate(row.cells):
            p_celda = celda.paragraphs[0]
            texto = [col1, col2, col3][j]

            # Alineación
            if j == 2 or (j == 1 and es_total):
                p_celda.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            elif j == 0:
                p_celda.alignment = WD_ALIGN_PARAGRAPH.LEFT
            else:
                p_celda.alignment = WD_ALIGN_PARAGRAPH.CENTER

            run_celda = p_celda.add_run(texto)
            run_celda.font.size = TABLE_FONT_SIZE
            run_celda.bold = es_encabezado or es_total

            if es_encabezado:
                run_celda.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                _celda_sombreada(celda, COLOR_HEADER_BG)
            elif es_total:
                run_celda.font.color.rgb = COLOR_ACCENT
            elif i % 2 == 0:
                _celda_sombreada(celda, COLOR_ALT_ROW)

    # Base de cálculo: el salario diario y el diario integrado (art. 89 LFT)
    # deben quedar asentados en la demanda.
    if calculo.get('success'):
        p_base = doc.add_paragraph()
        run_base = p_base.add_run(_texto_base_salarial(calculo))
        run_base.font.size = TABLE_FONT_SIZE

    doc.add_paragraph()


def _texto_base_salarial(calculo: dict) -> str:
    """Renglón con el salario diario y el diario integrado (art. 89 LFT)."""
    sd = calculo['salario_diario']
    sdi = calculo['salario_diario_integrado']
    texto = (f"Salario diario: ${sd:,.2f}. Salario diario integrado: ${sdi:,.2f} "
             f"(arts. 84 y 89 de la Ley Federal del Trabajo).")
    if sdi > sd:
        componentes = calculo.get('salario_integrado_componentes') or {}
        detalle = ', '.join(
            f"{_nombre_componente(k)}: ${v:,.2f}"
            for k, v in componentes.items() if v
        )
        if detalle:
            texto += f" Incluye {detalle}."
    return texto


def _nombre_componente(clave: str) -> str:
    return {
        'cuota_diaria': 'cuota diaria',
        'gratificaciones': 'gratificaciones',
        'ayudas': 'ayudas y prestaciones',
        'comisiones': 'comisiones',
        'prestaciones_especie': 'prestaciones en especie',
    }.get(clave, clave)


def _agregar_derecho(doc: Document, tipo_despido: str = 'injustificado') -> None:
    """Agrega la sección de FUNDAMENTOS DE DERECHO adaptados al tipo de despido."""
    p = doc.add_paragraph()
    run = p.add_run("—  F U N D A M E N T O S   D E   D E R E C H O  —")
    run.bold = True
    run.font.size = SECTION_FONT_SIZE
    run.font.color.rgb = COLOR_PRIMARY

    articulos = _fundamentos_derecho_docx(tipo_despido)

    for art in articulos:
        p = doc.add_paragraph()
        run = p.add_run(f"  • {art}")
        run.font.size = BODY_FONT_SIZE
        p.paragraph_format.space_after = Pt(1)

    doc.add_paragraph()


def _puntos_petitorios(calculo: dict, expediente: Expediente) -> list:
    """Lista de petitorios.

    El artículo 48 LFT es una ELECCIÓN: si el actor optó por la reinstalación,
    el petitorio pide la reinstalación y NO la indemnización de tres meses.
    """
    accion = (calculo or {}).get('accion') or {}
    if accion.get('accion') == 'reinstalacion' and accion.get('procede'):
        total_str = f"${calculo['total']:,.2f}"
        return [
            "PRIMERO.- Se declare que existió una relación laboral entre el "
            "actor y el demandado, en los términos que acreditan.",
            "SEGUNDO.- Se condene al demandado a la REINSTALACIÓN del actor en "
            "el puesto que venía desempeñando, con las prestaciones que "
            "correspondan conforme a la Ley Federal del Trabajo.",
            f"TERCERO.- Se condene al demandado al pago de {total_str} por "
            f"concepto de las prestaciones laborales detalladas en el cuerpo "
            f"de esta demanda.",
            "CUARTO.- Se ordene el pago de los salarios caídos que se sigan "
            "generando desde la fecha de la separación hasta que se cumpla la "
            "sentencia.",
            "QUINTO.- Se condene al demandado al pago de los gastos y costas "
            "que se originen con motivo del presente juicio.",
        ]

    if (calculo or {}).get('success') and calculo['total'] > 0:
        total_str = f"${calculo['total']:,.2f}"
    elif expediente.monto_reclamado:
        total_str = f"${expediente.monto_reclamado:,.2f}"
    else:
        total_str = "la cantidad que resulte"

    return [
        "PRIMERO.- Se declare que existió una relación laboral entre el "
        "actor y el demandado.",
        f"SEGUNDO.- Se condene al demandado al pago de {total_str} por "
        f"concepto de las prestaciones laborales detalladas en el cuerpo de "
        f"esta demanda.",
        "TERCERO.- Se ordene el pago de los salarios caídos que se sigan "
        "generando hasta la fecha en que se cumpla la sentencia.",
        "CUARTO.- Se condene al demandado al pago de los gastos y costas que "
        "se originen con motivo del presente juicio.",
    ]


def _agregar_puntos_petitorios(doc: Document, expediente: Expediente, calculo: dict) -> None:
    """Agrega los PUNTOS PETITORIOS."""
    p = doc.add_paragraph()
    run = p.add_run("—  P U N T O S   P E T I T O R I O S  —")
    run.bold = True
    run.font.size = SECTION_FONT_SIZE
    run.font.color.rgb = COLOR_PRIMARY

    for pet in _puntos_petitorios(calculo, expediente):
        p_pet = doc.add_paragraph()
        run_pet = p_pet.add_run(f"  {pet}")
        run_pet.font.size = BODY_FONT_SIZE
        p_pet.paragraph_format.space_after = Pt(4)

    doc.add_paragraph()


def _agregar_firma(doc: Document, expediente: Expediente) -> None:
    """Agrega la sección de FIRMA."""
    p = doc.add_paragraph()
    run = p.add_run("—  F I R M A  —")
    run.bold = True
    run.font.size = SECTION_FONT_SIZE
    run.font.color.rgb = COLOR_PRIMARY

    # Fecha en español
    hoy = timezone.now()
    fecha_str = _fecha_espanol(hoy)

    p = doc.add_paragraph()
    run = p.add_run(f"Presentado en Tijuana, Baja California, a los {fecha_str}.")
    run.font.size = BODY_FONT_SIZE

    doc.add_paragraph()

    # Línea de firma
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("_" * 40)
    run.font.size = BODY_FONT_SIZE
    run.font.color.rgb = COLOR_GRAY

    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run2 = p2.add_run(expediente.cliente.nombre)
    run2.bold = True
    run2.font.size = SUBTITLE_FONT_SIZE

    p3 = doc.add_paragraph()
    p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run3 = p3.add_run("Actor")
    run3.font.size = BODY_FONT_SIZE
    run3.font.color.rgb = COLOR_GRAY

    doc.add_paragraph()

    # Asesor
    p4 = doc.add_paragraph()
    p4.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    asesor = expediente.asesor.get_full_name() or expediente.asesor.username
    run4 = p4.add_run(f"Asesor jurídico: {asesor}")
    run4.font.size = Pt(8)
    run4.font.color.rgb = COLOR_GRAY


def _agregar_pie_generacion(doc: Document, expediente: Expediente) -> None:
    """Agrega metadata de generación al final del documento."""
    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("─" * 70)
    run.font.size = Pt(6)
    run.font.color.rgb = COLOR_GRAY

    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ahora = timezone.now().strftime('%d/%m/%Y %H:%M')
    asesor = expediente.asesor.get_full_name() or expediente.asesor.username
    run2 = p2.add_run(
        f"Documento generado el {ahora} por {asesor} | "
        f"Exp: {expediente.numero} | "
        f"Sistema de Gestión Laboral"
    )
    run2.font.size = Pt(7)
    run2.font.color.rgb = COLOR_GRAY


def generar_demanda_word(expediente: Expediente, desde_cero=True,
                          tipo_despido_override: str | None = None) -> Document:
    """
    Genera un documento Word de Demanda Laboral completo.

    Args:
        expediente: Instancia de Expediente con datos del cliente
        desde_cero: Si es True, genera el documento completo desde cero.
                    Si es False, solo configura márgenes y fuente (para usar con html_a_docx).
        tipo_despido_override: Si se proporciona, usa este tipo de despido
                               en lugar del que tiene el expediente.

    Returns:
        Documento python-docx listo para guardar/enviar
    """
    doc = Document()
    _configurar_documento(doc)

    if desde_cero:
        tipo_despido = tipo_despido_override or expediente.tipo_despido or 'injustificado'
        calculo = calculo_para_demanda(expediente, tipo_despido)
        _agregar_encabezado_tribunal(doc)
        _agregar_materia(doc, expediente)
        _agregar_actor(doc, expediente)
        _agregar_demandado(doc, expediente)
        _agregar_hechos(doc, expediente, calculo, tipo_despido)
        _agregar_prestaciones(doc, expediente, calculo, tipo_despido)
        _agregar_derecho(doc, tipo_despido)
        _agregar_pruebas(doc, expediente)
        _agregar_puntos_petitorios(doc, expediente, calculo)
        _agregar_firma(doc, expediente)
        _agregar_pie_generacion(doc, expediente)

    return doc


# ════════════════════════════════════════════════════════════════════════
# GENERADOR HTML (para el editor WYSIWYG)
# ════════════════════════════════════════════════════════════════════════

def _fecha_espanol_html(fecha) -> str:
    """Igual que _fecha_espanol pero para HTML."""
    if not fecha:
        return "[FECHA]"
    return f"{fecha.day} de {MESES_ES[fecha.month]} de {fecha.year}"


def _narrativa_despido_html(tipo_despido_key: str) -> str:
    """Igual que _narrativa_despido pero para HTML."""
    narrativas = {
        'injustificado': "el demandado dio por terminada la relación laboral de manera injustificada",
        'justificado': "el actor dio por terminada la relación laboral por causas imputables al demandado",
        'voluntario': "la relación laboral concluyó por renuncia voluntaria del actor",
        'rescision': "el actor se vio en la necesidad de rescindir la relación laboral",
        'otro': "la relación laboral concluyó",
    }
    return narrativas.get(tipo_despido_key,
                          "el demandado dio por terminada la relación laboral de manera injustificada")


def _fundamentos_derecho_html(tipo_despido_key: str) -> str:
    """Genera los fundamentos de derecho adaptados al tipo de despido."""
    articulos_base = [
        "Artículo 84 LFT — Salario integrado",
        "Artículo 87 LFT — Aguinaldo anual (15 días mínimo)",
        "Artículo 76 LFT — Vacaciones",
        "Artículo 79 LFT — Prima vacacional (mínimo 25%)",
        "Artículo 80 LFT — Pago de prima vacacional",
        "Artículo 518 LFT — Procedimiento ordinario laboral",
    ]

    if tipo_despido_key in ('injustificado', 'rescision'):
        adicionales = [
            "Artículo 46 LFT — Terminación de la relación laboral",
            "Artículo 47 LFT — Causas de rescisión sin responsabilidad",
            "Artículo 48 LFT — Indemnización por despido injustificado",
            "Artículo 49 LFT — Exención de responsabilidad al patrón",
            "Artículo 50 LFT — Indemnización de 3 meses",
            "Artículo 162 LFT — Prima de antigüedad",
        ]
    elif tipo_despido_key == 'justificado':
        adicionales = [
            "Artículo 46 LFT — Terminación de la relación laboral",
            "Artículo 51 LFT — Causas de rescisión imputables al patrón",
            "Artículo 52 LFT — Aviso de rescisión al patrón",
            "Artículo 48 LFT — Indemnización por despido injustificado",
            "Artículo 50 LFT — Indemnización de 3 meses",
            "Artículo 162 LFT — Prima de antigüedad",
        ]
    elif tipo_despido_key == 'voluntario':
        adicionales = [
            "Artículo 53 LFT — Causas de terminación de la relación laboral (Fracción I)",
        ]
    else:
        adicionales = [
            "Artículo 46 LFT — Terminación de la relación laboral",
        ]

    return "\n".join(f"<p>• {art}</p>" for art in articulos_base + adicionales)


def _fundamentos_derecho_docx(tipo_despido_key: str) -> list:
    """Genera lista de fundamentos de derecho adaptados al tipo de despido para docx."""
    articulos_base = [
        "Artículo 84 LFT — Salario integrado",
        "Artículo 87 LFT — Aguinaldo anual (15 días mínimo)",
        "Artículo 76 LFT — Vacaciones",
        "Artículo 79 LFT — Prima vacacional (mínimo 25%)",
        "Artículo 80 LFT — Pago de prima vacacional",
        "Artículo 518 LFT — Procedimiento ordinario laboral",
    ]

    if tipo_despido_key in ('injustificado', 'rescision'):
        adicionales = [
            "Artículo 46 LFT — Terminación de la relación laboral",
            "Artículo 47 LFT — Causas de rescisión sin responsabilidad",
            "Artículo 48 LFT — Indemnización por despido injustificado",
            "Artículo 49 LFT — Exención de responsabilidad al patrón",
            "Artículo 50 LFT — Indemnización de 3 meses",
            "Artículo 162 LFT — Prima de antigüedad",
        ]
    elif tipo_despido_key == 'justificado':
        adicionales = [
            "Artículo 46 LFT — Terminación de la relación laboral",
            "Artículo 51 LFT — Causas de rescisión imputables al patrón",
            "Artículo 52 LFT — Aviso de rescisión al patrón",
            "Artículo 48 LFT — Indemnización por despido injustificado",
            "Artículo 50 LFT — Indemnización de 3 meses",
            "Artículo 162 LFT — Prima de antigüedad",
        ]
    elif tipo_despido_key == 'voluntario':
        adicionales = [
            "Artículo 53 LFT — Causas de terminación de la relación laboral (Fracción I)",
        ]
    else:
        adicionales = [
            "Artículo 46 LFT — Terminación de la relación laboral",
        ]

    return articulos_base + adicionales


def generar_demanda_html(expediente: Expediente, tipo_despido_override: str | None = None) -> str:
    """
    Genera el contenido de la Demanda Laboral como HTML
    para ser usado en el editor WYSIWYG (Quill.js).

    Args:
        expediente: Instancia de Expediente con datos del cliente
        tipo_despido_override: Si se proporciona, usa este tipo de despido
                               en lugar del que tiene el expediente.
    """
    cliente = expediente.cliente
    tipo_despido = tipo_despido_override or expediente.tipo_despido or 'injustificado'
    calculo = calculo_para_demanda(expediente, tipo_despido)
    hoy = timezone.now()
    asesor = expediente.asesor.get_full_name() or expediente.asesor.username
    ahora_str = hoy.strftime('%d/%m/%Y %H:%M')

    # ─── Fechas ───
    f_ingreso = _fecha_espanol_html(cliente.fecha_ingreso)
    f_salida = _fecha_espanol_html(cliente.fecha_salida)
    puesto = cliente.puesto or "[PUESTO DESEMPEÑADO]"
    salario = f"${cliente.salario:,.2f}" if cliente.salario else "[SALARIO]"
    empresa = cliente.empresa_razon_social or cliente.empresa or "[EMPRESA DEMANDADA]"
    folio = expediente.folio or "[FOLIO DE CONCILIACIÓN]"
    f_tramite = _fecha_espanol_html(expediente.fecha_tramite)
    frase_despido = _narrativa_despido_html(tipo_despido)
    fecha_str = _fecha_espanol_html(hoy)

    # ─── Prestaciones ───
    prestaciones_rows = ""
    for concepto, fundamento, monto in _filas_prestaciones(calculo, expediente):
        importe = (f'<td style="text-align:right">{_importe_demanda(monto)}</td>'
                   if monto is not None
                   else '<td style="text-align:right">—</td>')
        prestaciones_rows += (
            f'<tr><td>{concepto}</td><td>{fundamento}</td>{importe}</tr>\n'
        )

    if calculo.get('success'):
        prestaciones_rows += (
            '<tr style="font-weight:bold;border-top:2px solid #000"><td></td>'
            '<td style="text-align:right">TOTAL:</td>'
            f'<td style="text-align:right">${calculo["total"]:,.2f}</td></tr>'
        )
        texto_base_salarial = _texto_base_salarial(calculo)
    elif expediente.monto_reclamado:
        prestaciones_rows += (
            '<tr style="font-weight:bold;border-top:2px solid #000"><td></td>'
            '<td style="text-align:right">MONTO RECLAMADO:</td>'
            f'<td style="text-align:right">${expediente.monto_reclamado:,.2f}</td></tr>'
        )
        texto_base_salarial = ''
    else:
        prestaciones_rows += (
            '<tr style="font-weight:bold;border-top:2px solid #000"><td></td>'
            '<td style="text-align:right">MONTO RECLAMADO:</td>'
            '<td style="text-align:right">—</td></tr>'
        )
        texto_base_salarial = ''


    # Petitorios: misma lista que el DOCX (_puntos_petitorios)
    petitorios_html = "\n".join(
        f"<p>{html_escape(p)}</p>"
        for p in _puntos_petitorios(calculo, expediente)
    )

    # PRUEBAS (misma lista que el DOCX: documental, testimonial, instrumental,
    # presuncional).  Solo se ofrece la TESTIMONIAL si hay testigos capturados.
    pruebas_items_html = []
    documentos_texto = _texto_como_lista(cliente.documentos_prueba)
    n = 1
    if documentos_texto:
        pruebas_items_html.append(
            f"<p>{n}. <strong>DOCUMENTAL.</strong> Consistente en los "
            f"documentos siguientes: {html_escape(documentos_texto)}.</p>"
        )
        n += 1
    if (cliente.testigos or '').strip():
        pruebas_items_html.append(
            f"<p>{n}. <strong>TESTIMONIAL.</strong> A cargo de las personas que "
            f"oportunamente se señalarán, respecto de los hechos controvertidos.</p>"
        )
        n += 1
    pruebas_items_html.append(
        f"<p>{n}. <strong>INSTRUMENTAL DE ACTUACIONES</strong>, consistente en todo "
        f"lo actuado que favorezca a los intereses de la parte actora.</p>"
    )
    n += 1
    pruebas_items_html.append(
        f"<p>{n}. <strong>PRESUNCIONAL LEGAL Y HUMANA</strong>, en todo aquello que "
        f"beneficie a los intereses de la parte actora.</p>"
    )
    pruebas_html = "\n".join(pruebas_items_html)

    # HECHOS: misma narrativa que el DOCX (construir_hechos)
    hechos_html = "\n\n".join(
        f"<p>{html_escape(h)}</p>" for h in
        construir_hechos(expediente, calculo, tipo_despido)
    )

    # ─── Datos actor ───
    actor_direccion = cliente.direccion_completa
    actor_items = [f"<strong>{html_escape(cliente.nombre)}</strong>"]
    if actor_direccion:
        actor_items.append(f"Domicilio: {html_escape(actor_direccion)}")
    if cliente.curp:
        actor_items.append(f"CURP: {html_escape(cliente.curp)}")
    if cliente.rfc:
        actor_items.append(f"RFC: {html_escape(cliente.rfc)}")
    if cliente.telefono:
        actor_items.append(f"Teléfono: {html_escape(cliente.telefono)}")

    # ─── Datos demandado ───
    razon_social = cliente.empresa_razon_social or cliente.empresa
    demandado_items = [f"<strong>{html_escape(razon_social or '—')}</strong>"]
    partes_dir = []
    if cliente.empresa_calle:
        partes_dir.append(cliente.empresa_calle)
    if cliente.empresa_numero:
        partes_dir.append(f"#{cliente.empresa_numero}")
    if cliente.empresa_colonia:
        partes_dir.append(f"Col. {cliente.empresa_colonia}")
    if cliente.empresa_cp:
        partes_dir.append(f"CP {cliente.empresa_cp}")
    if partes_dir:
        demandado_items.append(f"Domicilio: {html_escape(', '.join(partes_dir))}")
    if cliente.empresa_telefono:
        demandado_items.append(f"Teléfono: {html_escape(cliente.empresa_telefono)}")
    if cliente.empresa_actividad:
        demandado_items.append(f"Actividad: {html_escape(cliente.empresa_actividad)}")

    html = f"""
<h2 style="text-align:center;">ESCRITO INICIAL DE DEMANDA</h2>
<p style="text-align:center;">{html_escape(PLANTILLAS_INFO.get(tipo_despido, {}).get('nombre', tipo_despido))}</p>
<h2 style="text-align:center;color:#1F2937;">TRIBUNAL LABORAL COMPETENTE</h2>
<p style="text-align:center;color:#6B7280;">TIJUANA, BAJA CALIFORNIA</p>
<hr style="border:none;border-top:1px solid #1D4ED8;width:70%;margin:10px auto;">

<table style="width:100%;border-collapse:collapse;margin:15px 0;">
    <tr><td style="background:#F3F4F6;padding:5px 8px;border:1px solid #ccc;font-weight:bold;">MATERIA:</td><td style="padding:5px 8px;border:1px solid #ccc;font-weight:bold;color:#1D4ED8;">LABORAL</td></tr>
    <tr><td style="background:#F3F4F6;padding:5px 8px;border:1px solid #ccc;font-weight:bold;">TIPO DE JUICIO:</td><td style="padding:5px 8px;border:1px solid #ccc;font-weight:bold;color:#1D4ED8;">ORDINARIO LABORAL</td></tr>
    <tr><td style="background:#F3F4F6;padding:5px 8px;border:1px solid #ccc;font-weight:bold;">N° EXPEDIENTE CONCILIACIÓN:</td><td style="padding:5px 8px;border:1px solid #ccc;font-weight:bold;color:#1D4ED8;">{html_escape(expediente.folio or '—')}</td></tr>
</table>

<h3 style="color:#1F2937;">—  A C T O R  —</h3>
"""

    for item in actor_items:
        html += f"<p style='margin:2px 0;'>{item}</p>\n"

    html += f"""

<h3 style="color:#1F2937;">—  D E M A N D A D O  —</h3>
"""

    for item in demandado_items:
        html += f"<p style='margin:2px 0;'>{item}</p>\n"

    html += f"""

<h3 style="color:#1F2937;">—  P R E S T A C I O N E S  —</h3>
<table style="width:100%;border-collapse:collapse;">
<thead><tr><th>Prestación</th><th>Fundamento</th><th>Importe</th></tr></thead>
<tbody>{prestaciones_rows}</tbody>
</table>
<p>{html_escape(texto_base_salarial)}</p>

<h3 style="color:#1F2937;">—  H E C H O S  —</h3>

{hechos_html}

<h3 style="color:#1F2937;">—  F U N D A M E N T O S   D E   D E R E C H O  —</h3>

{_fundamentos_derecho_html(tipo_despido)}

<h3 style="color:#1F2937;">—  P R U E B A S  —</h3>

{pruebas_html}

<h3 style="color:#1F2937;">—  P U N T O S   P E T I T O R I O S  —</h3>

{petitorios_html}

<h3 style="color:#1F2937;">—  F I R M A  —</h3>

<p>Presentado en Tijuana, Baja California, a los {fecha_str}.</p>

<br>
<p style="text-align:center;">________________________________________</p>
<p style="text-align:center;font-weight:bold;font-size:14px;">{html_escape(cliente.nombre)}</p>
<p style="text-align:center;color:#6B7280;">Actor</p>

<br>
<p style="text-align:right;font-size:10px;color:#6B7280;">Asesor jurídico: {html_escape(asesor)}</p>

<hr style="border:none;border-top:1px solid #ccc;width:70%;margin:10px auto;">
<p style="text-align:center;font-size:9px;color:#6B7280;">Documento generado el {ahora_str} por {html_escape(asesor)} | Exp: {html_escape(expediente.numero)} | Sistema de Gestión Laboral</p>
"""

    return html


def html_a_docx(html: str, doc: Document) -> None:
    """
    Convierte HTML básico (generado por Quill.js) a elementos de python-docx.
    Se agrega al documento existente.

    Soporta: p, h1-h3, strong, em, u, br, ol/ul/li, table.
    """
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    # Limpiar el HTML de Quill: reemplazar br
    html = html.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')

    def _estilo_parrafo(paragraph, align_text=None):
        """Aplica formato básico a un párrafo."""
        paragraph.paragraph_format.space_after = Pt(6)
        paragraph.paragraph_format.line_spacing = 1.15
        if align_text == 'center':
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif align_text == 'right':
            paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    def _agregar_run(paragraph, texto, bold=False, italic=False, underline=False, size=None, color=None):
        """Agrega un run con formato al párrafo."""
        run = paragraph.add_run(texto)
        run.bold = bold
        run.italic = italic
        run.underline = underline
        if size:
            run.font.size = Pt(size)
        if color:
            run.font.color.rgb = RGBColor(*color)
        return run

    def _procesar_inline(text, paragraph):
        """
        Procesa etiquetas inline (strong, em, u, s) dentro de un párrafo.
        Maneja múltiples etiquetas en un mismo párrafo.
        """
        remaining = text
        while remaining:
            # Buscar la siguiente etiqueta de apertura
            tag_match = re.search(r'<(strong|b|em|i|u|s)>(.*?)</\1>', remaining, re.DOTALL)
            if tag_match:
                # Texto antes de la etiqueta
                before = remaining[:tag_match.start()]
                if before:
                    paragraph.add_run(before)
                # La etiqueta con formato
                tag = tag_match.group(1)
                content = tag_match.group(2)
                run = paragraph.add_run(content)
                if tag in ('strong', 'b'):
                    run.bold = True
                if tag in ('em', 'i'):
                    run.italic = True
                if tag == 'u':
                    run.underline = True
                if tag == 's':
                    run.font.strike = True
                # Avanzar
                remaining = remaining[tag_match.end():]
            else:
                # No hay más etiquetas, agregar el resto
                if remaining:
                    paragraph.add_run(remaining)
                break

    # Procesar líneas del HTML
    lines = html.split('\n')
    i = 0
    in_list = False
    list_type = None
    current_list_items = []
    in_table = False
    table_data = []

    while i < len(lines):
        line = lines[i].strip()

        if not line:
            i += 1
            continue

        # Tablas
        if '<table' in line:
            in_table = True
            table_data = []
            table_row = []
            # Buscar celdas dentro de la tabla
            table_html = ''
            while i < len(lines) and '</table>' not in lines[i]:
                table_html += lines[i] + '\n'
                i += 1
            table_html += lines[i] + '\n'  # </table>
            i += 1

            # Extraer filas
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.DOTALL | re.IGNORECASE)
            if rows:
                parsed_rows = []
                for row_html in rows:
                    # Encontrar cada celda individualmente para saber si es <th> o <td>
                    cell_pattern = re.findall(r'<(th|td)[^>]*>(.*?)</\1>', row_html, re.DOTALL | re.IGNORECASE)
                    parsed_cells = []
                    for tag, content in cell_pattern:
                        # Limpiar etiquetas HTML internas
                        clean_text = re.sub(r'<[^>]+>', '', content).strip()
                        parsed_cells.append({'text': clean_text, 'is_header': tag == 'th'})
                    if parsed_cells:
                        parsed_rows.append(parsed_cells)

                if parsed_rows:
                    num_cols = max(len(r) for r in parsed_rows)
                    table = doc.add_table(rows=len(parsed_rows), cols=num_cols)
                    table.style = 'Table Grid'
                    for ri, row_data in enumerate(parsed_rows):
                        for ci, cell_data in enumerate(row_data):
                            if ci < num_cols:
                                cell = table.rows[ri].cells[ci]
                                cell.text = ''
                                p = cell.paragraphs[0]
                                run = p.add_run(cell_data['text'])
                                run.font.size = Pt(9.5)
                                if cell_data['is_header']:
                                    run.bold = True
                                    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                                    from docx.oxml.ns import nsdecls
                                    from docx.oxml import parse_xml
                                    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="1F2937"/>')
                                    cell._tc.get_or_add_tcPr().append(shading)
                                # Alinear a la derecha la última columna
                                if ci == num_cols - 1:
                                    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

            doc.add_paragraph()  # espacio después de tabla
            continue

        # Listas
        if '<ol>' in line or '<ul>' in line:
            in_list = True
            list_type = 'ol' if '<ol>' in line else 'ul'
            i += 1
            continue
        if '</ol>' in line or '</ul>' in line:
            # Escribir items de lista
            for idx, item_text in enumerate(current_list_items):
                p = doc.add_paragraph()
                _estilo_parrafo(p)
                prefix = f"{idx + 1}. " if list_type == 'ol' else "  • "
                _procesar_inline(f"{prefix}{item_text}", p)
            current_list_items = []
            in_list = False
            list_type = None
            i += 1
            continue
        if in_list:
            li_match = re.search(r'<li>(.*?)</li>', line)
            if li_match:
                current_list_items.append(li_match.group(1))
            i += 1
            continue

        # Encabezados
        h_match = re.match(r'<(h[123])[^>]*>(.*?)</\1>', line, re.DOTALL)
        if h_match:
            tag = h_match.group(1)
            content = h_match.group(2)
            clean_content = re.sub(r'<[^>]+>', '', content).strip()
            p = doc.add_paragraph()
            size_map = {'h1': 14, 'h2': 12, 'h3': 11}
            _agregar_run(p, clean_content, bold=True, size=size_map.get(tag, 11), color=(0x1F, 0x29, 0x37))
            _estilo_parrafo(p)
            i += 1
            continue

        # Párrafos normales
        p_match = re.match(r'<p[^>]*>(.*?)</p>', line, re.DOTALL)
        if p_match:
            p_content = p_match.group(1).strip()
            # Detectar align
            align = None
            align_match = re.search(r'style="[^"]*text-align:\s*(center|right)"', line)
            if align_match:
                align = align_match.group(1)

            p = doc.add_paragraph()
            _estilo_parrafo(p, align)
            _procesar_inline(p_content, p)
            i += 1
            continue

        # Línea horizontal
        if '<hr' in line:
            p = doc.add_paragraph()
            _agregar_run(p, "─" * 70, size=8, color=(0x6B, 0x72, 0x80))
            i += 1
            continue

        # Cualquier otra línea
        clean = re.sub(r'<[^>]+>', '', line).strip()
        if clean:
            p = doc.add_paragraph()
            _estilo_parrafo(p)
            p.add_run(clean)
        i += 1
