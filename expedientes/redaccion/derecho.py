"""Capítulo 7 — CAPÍTULO DE DERECHO.

El estándar del despacho cierra con una lista de artículos (pág. 14).  La
versión de la referencia dice:

    En cuanto al fondo del presente negocio, son aplicables los Artículos 123
    Constitucional Frac. XXII, 8, 10, 11, 13, 16, 17, 19, 20, 22, 24, 25, 37,
    47 frac. XV últimos párrafos, 48, 50, 59, 60, 66, 67, 68, 69, 70, 73, 74,
    75, 76, 77, 78, 84, 89, 162, 346 y demás relativos y en cuanto al
    procedimiento del 685 al 891 de la Ley Federal del Trabajo.

Se conserva esa redacción y se agregan o quitan artículos según lo que
realmente se reclame, para no invocar fundamentos que no correspondan a los
hechos (p. ej. los artículos de horas extras cuando no se reclaman).
"""

# Artículos de fondo que siempre aplican al despido injustificado
ARTICULOS_BASE = [
    '123 Constitucional Frac. XXII', '8', '10', '11', '13', '16', '17', '19',
    '20', '22', '24', '25', '37', '47 frac. XV últimos párrafos', '48', '50',
    '59', '60', '69', '70', '73', '74', '75', '76', '77', '78', '84', '89',
    '162', '346',
]

# Sólo cuando se reclaman horas extras (arts. 66 a 68 LFT)
ARTICULOS_HORAS_EXTRAS = ['66', '67', '68']

# Artículos de derecho procesal (procedimiento ordinario)
ARTICULOS_PROCEDIMIENTO = 'del 685 al 891'


def _ordenar(articulos: list) -> list:
    """Ordena los artículos dejando al frente los constitucionales.

    El estándar abre con "123 Constitucional Frac. XXII" y luego sigue el orden
    numérico de la ley, así que los constitucionales no se mezclan con los
    numerales de la LFT.
    """
    constitucionales, numericos, especiales = [], [], []
    for art in articulos:
        if 'Constitucional' in art:
            constitucionales.append(art)
            continue
        try:
            numericos.append((int(art.split()[0]), art))
        except (ValueError, IndexError):
            especiales.append(art)
    numericos.sort(key=lambda par: par[0])
    return sorted(set(constitucionales)) + [art for _, art in numericos] + especiales


def derecho(datos: dict, condiciones: dict, tipo_despido: str = 'injustificado') -> str:
    """Párrafo del capítulo de derecho."""
    articulos = list(ARTICULOS_BASE)

    if condiciones.get('incluir_horas_extras') or condiciones.get('reclama_horas_extras'):
        articulos.extend(ARTICULOS_HORAS_EXTRAS)

    if tipo_despido == 'rescision':
        articulos.extend(['51', '52'])

    articulos = _ordenar(set(articulos))
    lista = ', '.join(articulos)

    return (
        f'En cuanto al fondo del presente negocio, son aplicables los Artículos '
        f'{lista} y demás relativos, y en cuanto al procedimiento '
        f'{ARTICULOS_PROCEDIMIENTO} de la Ley Federal del Trabajo.'
    )


def encabezado() -> str:
    return 'CAPÍTULO DE DERECHO:'
