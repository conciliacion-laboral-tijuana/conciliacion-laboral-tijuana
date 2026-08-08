"""
Parser del Acuse de Solicitud de Conciliación (Centro de Conciliación Laboral BC)
===============================================================================

Extrae los datos clave del acuse PDF oficial descargado del portal
(app.conciliacionbc.gob.mx) para popularizar automáticamente el expediente:

    ACUSE DE SOLICITUD DE CONCILIACIÓN
    FECHA DE SOLICITUD: 07 de Agosto de 2026
    SOLICITANTE(S): JOSE LIMON DIAZ
    CITADO(S): TAQUERIA LOS ALBAÑILES
    FECHA DE CONFLICTO: 30 de Julio de 2026
    OBJETO DE LA CONCILIACIÓN: Despido
    UNIDAD DE CONCILIACIÓN TIJUANA
    ... con folio TIJ/26427/2026 ...

Uso:
    from .acuse_parser import parsear_acuse_pdf
    datos = parsear_acuse_pdf(contenido_bytes)
"""
import re
import unicodedata
from datetime import date

# ─── Meses en español (formato del acuse: "07 de Agosto de 2026") ─────────

MESES_ES = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
    'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11,
    'diciembre': 12,
}

# ─── Objeto de la conciliación → tipo de despido del expediente ───────────

OBJETO_A_TIPO_DESPIDO = {
    'despido': 'injustificado',
    'despido injustificado': 'injustificado',
    'despido justificado': 'justificado',
    'terminacion voluntaria': 'voluntario',
    'renuncia voluntaria': 'voluntario',
    'rescision': 'rescision',
    'rescisión': 'rescision',
    'abandono': 'otro',
}


def _normalizar(texto):
    """Reemplaza ligaduras tipográficas (fi/ﬂ) que PyMuPDF suele emitir."""
    if not texto:
        return texto
    return (texto.replace('\ufb01', 'fi').replace('\ufb02', 'fl')
                .replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"'))


def extraer_texto_pdf(contenido_bytes):
    """Extrae el texto plano de un PDF usando PyMuPDF (fitz).

    Retorna string con el texto completo del documento, o '' si falla.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return ''
    try:
        doc = fitz.open(stream=contenido_bytes, filetype='pdf')
        try:
            return _normalizar('\n'.join(page.get_text() for page in doc))
        finally:
            doc.close()
    except Exception:
        return ''


def _parsear_fecha_es(texto):
    """Parsea '07 de Agosto de 2026' → date(2026, 8, 7). Retorna None si falla."""
    if not texto:
        return None
    m = re.search(r'(\d{1,2})\s+de\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]+)\s+de\s+(\d{4})', texto)
    if not m:
        return None
    dia = int(m.group(1))
    mes_nombre = m.group(2).strip().lower()
    anio = int(m.group(3))
    mes = MESES_ES.get(mes_nombre)
    if not mes:
        return None
    try:
        return date(anio, mes, dia)
    except ValueError:
        return None


# ─── Regex por campo (en el orden en que aparecen en el acuse) ─────────────

_CAMPOS = [
    ('fecha_solicitud', re.compile(r'FECHA\s+DE\s+SOLICITUD\s*:\s*(.+)', re.IGNORECASE)),
    ('solicitante', re.compile(r'SOLICITANTE\(?S?\)?\s*:\s*(.+)', re.IGNORECASE)),
    ('citado', re.compile(r'CITADO\(?S?\)?\s*:\s*(.+)', re.IGNORECASE)),
    ('fecha_conflicto', re.compile(r'FECHA\s+DE\s+CONFLICTO\s*:\s*(.+)', re.IGNORECASE)),
    ('objeto', re.compile(r'OBJETO\s+DE\s+LA\s+CONCILIACI[OÓ]N\s*:\s*(.+)', re.IGNORECASE)),
    ('unidad', re.compile(r'UNIDAD\s+DE\s+CONCILIACI[OÓ]N\s+([A-ZÁÉÍÓÚÑ ]{2,})', re.IGNORECASE)),
]


def parsear_acuse(texto):
    """Parsea el texto del acuse y retorna dict con los campos detectados.

    Campos retornados (solo los que se encontraron):
        folio, fecha_solicitud (date), solicitante, citado,
        fecha_conflicto (date), objeto, unidad, tipo_despido (mapeado)
    """
    if not texto:
        return {}
    texto = _normalizar(texto)
    datos = {}

    # Folio: "... con folio TIJ/26427/2026 ..."
    m = re.search(r'folio\s+([A-Za-z0-9]{1,5}\s*/\s*\d+\s*/\s*\d{4})', texto, re.IGNORECASE)
    if not m:
        m = re.search(r'folio\s+([A-Za-z0-9/.\-]{5,30})', texto, re.IGNORECASE)
    if m:
        datos['folio'] = m.group(1).strip().replace(' ', '')

    # Campos con etiqueta
    for campo, patron in _CAMPOS:
        m = patron.search(texto)
        if m:
            valor = m.group(1).strip()
            if campo in ('fecha_solicitud', 'fecha_conflicto'):
                fecha = _parsear_fecha_es(valor)
                if fecha:
                    datos[campo] = fecha
            elif campo == 'objeto':
                datos['objeto'] = valor
                # Mapear a tipo de despido (normalizando acentos: 'terminación' → 'terminacion')
                clave = unicodedata.normalize('NFD', valor.strip().lower())
                clave = ''.join(c for c in clave if unicodedata.category(c) != 'Mn')
                datos['tipo_despido'] = OBJETO_A_TIPO_DESPIDO.get(clave)
            elif campo == 'unidad':
                datos['unidad'] = valor
            else:
                datos[campo] = valor

    return datos


def parsear_acuse_pdf(contenido_bytes):
    """Extrae el texto del PDF y lo parsea en un solo paso."""
    return parsear_acuse(extraer_texto_pdf(contenido_bytes))


# ─── Mapeo a campos del modelo (para la vista previa) ─────────────────────

def mapear_campos_modelo(datos, expediente):
    """Convierte los datos parseados en la lista de campos aplicables.

    Retorna lista de dicts:
        {
            'key': 'folio' | 'nombre' | 'empresa' | ...,
            'label': 'Folio de trámite',
            'valor_detectado': 'TIJ/26427/2026',
            'valor_actual': '...' (o '' ),
            'nuevo': bool (el campo destino está vacío),
        }
    """
    cliente = expediente.cliente
    campos = []

    def _agregar(key, label, detectado, actual):
        if not detectado:
            return
        actual = actual or ''
        campos.append({
            'key': key,
            'label': label,
            'valor_detectado': detectado,
            'valor_actual': actual,
            'nuevo': not actual,
            'difiere': bool(actual) and str(detectado).strip().upper() != str(actual).strip().upper(),
        })

    _agregar('folio', 'Folio de trámite', datos.get('folio'), expediente.folio)
    _agregar('fecha_solicitud', 'Fecha de solicitud', datos.get('fecha_solicitud'), expediente.fecha_tramite)
    _agregar('nombre', 'Nombre del solicitante (trabajador)', datos.get('solicitante'), cliente.nombre)
    _agregar('citado', 'Empresa / patrón citado', datos.get('citado'),
             cliente.empresa_razon_social or cliente.empresa)
    _agregar('fecha_conflicto', 'Fecha del conflicto', datos.get('fecha_conflicto'), cliente.fecha_salida)
    _agregar('tipo_despido', 'Tipo de despido', datos.get('tipo_despido'), expediente.tipo_despido)

    # Unidad de conciliación (solo si ya existe la solicitud con unidad registrada)
    unidad_actual = ''
    try:
        unidad_actual = expediente.solicitud.unidad_sede or ''
    except Exception:
        unidad_actual = ''
    _agregar('unidad', 'Unidad de conciliación', datos.get('unidad'), unidad_actual)

    return campos
