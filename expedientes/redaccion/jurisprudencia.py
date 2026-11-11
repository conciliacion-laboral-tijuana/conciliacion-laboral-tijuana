"""Apartado de JURISPRUDENCIA (después del capítulo de derecho).

El estándar del despacho cierra el escrito con los artículos aplicables.  Este
apartado agrega, cuando el abogado lo decide, las tesis o jurisprudencias que
sostienen la acción: primero el párrafo con el que se introduce cada criterio
(`argumento`) y después la tesis transcrita con su cita bibliográfica.

No es un capítulo obligatorio: una demanda puede presentarse sólo con los
artículos.  Por eso el motor NO escribe nada cuando no hay tesis seleccionadas
(ni un encabezado vacío ni un marcador de hueco).

Regla de diseño: este módulo no busca, no elige ni inventa jurisprudencia.  Lo
que imprime es exactamente lo que el abogado seleccionó de la biblioteca del
despacho (o capturó para ese caso).
"""


def encabezado() -> str:
    """Encabezado del apartado, como en el resto del escrito."""
    return 'JURISPRUDENCIA:'


def tesis(datos: dict) -> list:
    """Tesis seleccionadas que sí se pueden imprimir (tienen rubro)."""
    seleccionadas = datos.get('jurisprudencia') or []
    return [t for t in seleccionadas if str(t.get('rubro') or '').strip()]


def hay(datos: dict) -> bool:
    return bool(tesis(datos))


def introduccion(cantidad: int) -> str:
    """Párrafo que anuncia los criterios que se invocan."""
    if cantidad == 1:
        return ('Se invoca, en lo conducente, el siguiente criterio '
                'jurisprudencial:')
    return ('Se invocan, en lo conducente, los siguientes criterios '
            'jurisprudenciales:')


def cita(t: dict) -> str:
    """Cita bibliográfica de una tesis en una línea.

    Formato: «Jurisprudencia. Tesis 2a./J. 12/2020. Segunda Sala de la Suprema
    Corte de Justicia de la Nación. Undécima Época. Registro digital: 2020123.
    Semanario Judicial de la Federación.»
    """
    partes = [str(t.get('tipo') or 'Tesis').strip()]
    clave = str(t.get('clave_tesis') or '').strip()
    if clave:
        partes.append(f'Tesis {clave}')
    for campo in ('organo', 'epoca'):
        valor = str(t.get(campo) or '').strip().rstrip('.')
        if valor:
            partes.append(valor)
    texto = '. '.join(p for p in partes if p)
    registro = str(t.get('registro_digital') or '').strip()
    if registro:
        texto += f'. Registro digital: {registro}'
    fuente = str(t.get('fuente') or '').strip().rstrip('.')
    if fuente:
        texto += f'. {fuente}'
    return texto + '.'


def rubro(t: dict) -> str:
    """Rubro entre comillas, como se transcribe en el escrito."""
    titulo = str(t.get('rubro') or '').strip()
    return f'“{titulo}”'


def tema(t: dict) -> str:
    """Tema legible, para la pantalla de selección."""
    return str(t.get('tema_display') or t.get('tema') or '').strip()
