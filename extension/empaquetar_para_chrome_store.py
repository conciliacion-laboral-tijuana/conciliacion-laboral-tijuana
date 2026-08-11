# -*- coding: utf-8 -*-
"""
Empaqueta la extensión para subirla a la Chrome Web Store.

Reglas de la tienda que cumple este script:
  - manifest.json en la RAÍZ del .zip (sin carpeta contenedora)
  - Se excluyen archivos de documentación interna (LEEME.md)
  - Solo se incluyen los archivos que la extensión necesita

Uso:
    uv run python extension/empaquetar_para_chrome_store.py

Genera: conciliacion_bc_chrome_store.zip en la raíz del proyecto.
"""
import json
import sys
import zipfile
from pathlib import Path

# Archivos que NO deben ir al paquete de la tienda
EXCLUIR_POR_NOMBRE = {'LEEME.md', 'empaquetar_para_chrome_store.py'}
# Archivos que SÍ deben ir (referenciados por el manifest)
REQUERIDOS = [
    'manifest.json',
    'background.js',
    'content.js',
    'popup.html',
    'popup.js',
    'options.html',
    'options.js',
    'icons/icon16.png',
    'icons/icon48.png',
    'icons/icon128.png',
]

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
CARPETA_EXTENSION = RAIZ_PROYECTO / 'extension'
ZIP_SALIDA = RAIZ_PROYECTO / 'conciliacion_bc_chrome_store.zip'


def main():
    if not CARPETA_EXTENSION.exists():
        print(f'❌ No existe la carpeta {CARPETA_EXTENSION}')
        return 1

    with zipfile.ZipFile(ZIP_SALIDA, 'w', zipfile.ZIP_DEFLATED) as zf:
        for archivo in sorted(CARPETA_EXTENSION.rglob('*')):
            if not archivo.is_file():
                continue
            if archivo.name in EXCLUIR_POR_NOMBRE:
                print(f'  - excluido: {archivo.name}')
                continue
            # Ruta relativa a extension/ → manifest.json en la raíz
            arcname = archivo.relative_to(CARPETA_EXTENSION)
            zf.write(archivo, arcname)

    # ─── Validación final ───────────────────────────────────────────
    nombres = zipfile.ZipFile(ZIP_SALIDA).namelist()
    errores = []
    if 'manifest.json' not in nombres:
        errores.append('Falta manifest.json en la raíz')
    if any(n.startswith('extension/') for n in nombres):
        errores.append('Hay carpeta contenedora extension/ (no permitida)')
    if any('LEEME' in n for n in nombres):
        errores.append('Se incluyó LEEME.md (no permitido)')
    for req in REQUERIDOS:
        if req not in nombres:
            errores.append(f'Falta archivo referenciado: {req}')

    if errores:
        print('❌ ZIP inválido para la Chrome Web Store:')
        for e in errores:
            print(f'   - {e}')
        return 1

    try:
        with zipfile.ZipFile(ZIP_SALIDA) as zf:
            json.loads(zf.read('manifest.json'))
    except Exception as e:
        print(f'❌ manifest.json no es JSON válido: {e}')
        return 1

    print('✅ ZIP listo para la Chrome Web Store:')
    print(f'   {ZIP_SALIDA.name} ({ZIP_SALIDA.stat().st_size:,} bytes)')
    print('   Estructura:')
    for n in nombres:
        print(f'     {n}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
