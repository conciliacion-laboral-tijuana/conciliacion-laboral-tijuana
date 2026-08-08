"""
Comando de gestión: importar_empresas

Importa 'Empresas y Domicilios.xlsx' al catálogo de empresas y domicilios
(modelo Empresa, tabla expedientes_empresa).

El archivo crece con el tiempo (base de datos oficial del despacho).
El comando es IDEMPOTENTE:
  - Si la empresa ya existe (mismo nombre normalizado), actualiza sus datos.
  - Si no existe, la crea.

Estructura del archivo (sin encabezados, fila 2 en adelante):
    A: Empresa / patrón
    B: Domicilio oficial completo
    C: Abogado / representante (opcional)
    D: Teléfono (opcional)

Uso:
    uv run python manage.py importar_empresas                        # Importa Empresas y Domicilios.xlsx (raíz)
    uv run python manage.py importar_empresas --archivo ruta/archivo.xlsx

El tipo de persona se detecta automáticamente:
    - moral  → nombres con razón social (S.A., S. DE R.L., S.A.P.I., A.C., S.C., ...) o instituciones
    - fisica → nombres de persona / comercios a nombre de persona física
(Siempre puede corregirse después desde el panel de admin.)

NOTA: el archivo es la fuente de verdad; cada re-ejecución actualiza todos
los campos (incluido tipo_persona), sobrescribiendo correcciones manuales
hechas en el panel de admin.
"""
import re

from django.core.management.base import BaseCommand

from expedientes.models import Empresa
from .importar_clt import _normalizar


# ─── Detección de tipo de persona ─────────────────────────────────────────
_SUFIJOS_RAZON_SOCIAL = re.compile(
    r'\b(?:S\.?\s*A\.?\s*(?:P\.?\s*I\.?)?|S\.?\s*R\.?\s*L\.?'
    r'|S\.?\s*D\.?\s*E\.?\s*R\.?\s*L\.?|S\.?\s*C\.?|A\.?\s*C\.?'
    r'|S\.?\s*P\.?\s*R\.?|L\.?\s*L\.?\s*C\.?|I\.?\s*N\.?\s*C\.?'
    r'|D\.?\s*E\.?\s*C\.?\s*V\.?)\b'
)
_INSTITUCIONES = re.compile(
    r'\b(SECRETARIA|INSTITUTO|COMISION|GOBIERNO|AYUNTAMIENTO|UNIVERSIDAD|HOSPITAL|BANCO)\b'
)


def _detectar_tipo_persona(nombre):
    """Retorna 'moral' o 'fisica' según el nombre de la empresa (mejor esfuerzo)."""
    if not nombre:
        return 'moral'
    n = _normalizar(nombre)
    if _SUFIJOS_RAZON_SOCIAL.search(n):
        return 'moral'
    if _INSTITUCIONES.search(n):
        return 'moral'
    return 'fisica'


# ─── Desglose del domicilio (mejor esfuerzo) ──────────────────────────────
_CIUDADES = r'(TIJUANA|TECATE|ENSENADA|MEXICALI|ROSARITO|CIUDAD\s+DE\s+MEXICO|MEXICO|ALVARO\s+OBREGON|CHALCO|BAJA\s+CALIFORNIA|B\.?\s*C\.?)'
_TIPO_VIA = r'^(C\.|CALLE|CALLA|AV\.?|AVENIDA|BLVD\.?|BOULEVARD|CARRETERA|PRIV\.?|PRIVADA|CALZADA|DR\.?|CIRCUITO|RAMPA)\s+'
_NUMERO = re.compile(
    r'\b(?:NO\.?|NUMERO|NUM|N\.?)\s*[.:]?\s*([0-9]{1,6}(?:\s*[-–/]\s*[0-9A-Z]{1,6})?)'
)


def _desglosar_domicilio(domicilio):
    """Divide un domicilio libre en (calle, numero, colonia, cp).

    El texto completo siempre se conserva en el campo 'domicilio';
    este desglose es solo para autocompletar formularios.
    """
    if not domicilio:
        return '', '', '', ''
    texto = _normalizar(domicilio)

    # Código postal: con prefijo "C.P." o 5 dígitos que aparecen DESPUÉS de la ciudad
    # (evita confundir el número de la calle con el CP, ej. "NO. 15510")
    cp = ''
    m = re.search(r'\bC\.?\s*P\.?\s*[:.]?\s*(\d{5})\b', texto)
    if m:
        cp = m.group(1)
    else:
        m = re.search(rf'{_CIUDADES}[^,]*?\b(\d{{5}})\b', texto)
        if m:
            cp = m.group(2)

    # Número exterior: "NO. 729", "NUMERO 7937", "NO.15000"
    m_num = _NUMERO.search(texto)
    numero = m_num.group(1).strip() if m_num else ''

    # Calle: todo lo anterior al número (o el primer segmento por coma)
    if m_num:
        calle = texto[:m_num.start()].strip(' ,')
    else:
        calle = texto.split(',')[0].strip(' ,')
    calle = re.sub(_TIPO_VIA, '', calle, flags=re.I).strip().rstrip(' .,')

    # Colonia: el segmento anterior a la última ciudad; si ese segmento es solo
    # el nombre de la ciudad ("TIJUANA"), probar con la primera ciudad.
    partes = [p.strip().rstrip('.').strip() for p in texto.split(',') if p.strip()]
    colonia = ''
    idxs_ciudad = [i for i, p in enumerate(partes) if re.search(rf'{_CIUDADES}\s*$', p)]
    if idxs_ciudad:
        candidata = partes[idxs_ciudad[-1] - 1] if idxs_ciudad[-1] > 0 else ''
        if candidata:
            # Quitar ciudad pegada al final ("CENTRO TIJUANA" → "CENTRO")
            candidata = re.sub(rf'\s*{_CIUDADES}$', '', candidata).strip(' ,')
            # Si incluye dirección con número ("NO. 92 PARQUE INDUSTRIAL..."),
            # quedarse con lo posterior al número
            m2 = _NUMERO.search(candidata)
            if m2:
                candidata = candidata[m2.end():].strip(' ,')
        if not candidata and idxs_ciudad[0] > 0:
            # el segmento anterior era solo "TIJUANA" → usar el anterior a la primera ciudad
            candidata = partes[idxs_ciudad[0] - 1]
        colonia = candidata
    elif len(partes) > 1:
        colonia = partes[-1]  # sin ciudad: último segmento tras la dirección

    colonia = re.sub(r'^(COL\.?|COLONIA)\s+', '', colonia, flags=re.I)
    colonia = re.sub(r'\s*C\.?P\.?\s*[:.]?\s*\d{5}\s*$', '', colonia).strip()

    return calle, numero, colonia, cp


class Command(BaseCommand):
    help = 'Importa Empresas y Domicilios.xlsx al catálogo de empresas (idempotente)'

    def add_arguments(self, parser):
        parser.add_argument('--archivo', default='Empresas y Domicilios.xlsx',
                            help='Ruta del archivo xlsx (default: Empresas y Domicilios.xlsx en la raíz)')

    def handle(self, *args, **options):
        import openpyxl

        ruta = options['archivo']
        self.stdout.write(f'Leyendo {ruta}...')

        wb = openpyxl.load_workbook(ruta, data_only=True)
        ws = wb.active

        creadas = actualizadas = sin_domicilio = 0
        saltadas = []

        for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
            if not row or not row[0]:
                continue  # fila vacía

            nombre = _normalizar(row[0])
            if not nombre:
                continue

            domicilio = str(row[1]).strip() if len(row) > 1 and row[1] else ''
            # Se guarda tal cual (sin quitar acentos/Ñ) para conservar el nombre
            abogado = str(row[2]).strip() if len(row) > 2 and row[2] else ''
            telefono = str(row[3]).strip() if len(row) > 3 and row[3] else ''

            calle, numero, colonia, cp = _desglosar_domicilio(domicilio)
            tipo_persona = _detectar_tipo_persona(nombre)

            emp, creado = Empresa.objects.get_or_create(
                nombre=nombre,
                defaults={
                    'domicilio': domicilio,
                    'abogado': abogado,
                    'telefono': telefono,
                    'tipo_persona': tipo_persona,
                    'domicilio_calle': calle,
                    'domicilio_numero': numero,
                    'domicilio_colonia': colonia,
                    'domicilio_cp': cp,
                },
            )
            if creado:
                creadas += 1
            else:
                emp.domicilio = domicilio
                emp.abogado = abogado
                emp.telefono = telefono
                emp.tipo_persona = tipo_persona
                emp.domicilio_calle = calle
                emp.domicilio_numero = numero
                emp.domicilio_colonia = colonia
                emp.domicilio_cp = cp
                emp.save(update_fields=[
                    'domicilio', 'abogado', 'telefono', 'tipo_persona',
                    'domicilio_calle', 'domicilio_numero',
                    'domicilio_colonia', 'domicilio_cp', 'updated_at',
                ])
                actualizadas += 1

            if not domicilio:
                sin_domicilio += 1
                saltadas.append(f'fila {i}: {nombre}')

        self.stdout.write(self.style.SUCCESS(
            f'  [OK] Empresas creadas: {creadas} | actualizadas: {actualizadas}'
        ))
        self.stdout.write(f'  Total en catálogo: {Empresa.objects.count()}')
        if saltadas:
            self.stdout.write(self.style.WARNING(
                f'  [!] {sin_domicilio} empresa(s) sin domicilio en el archivo:'
            ))
            for s in saltadas:
                self.stdout.write(f'      - {s}')
        self.stdout.write(self.style.SUCCESS('Importación completada.'))
