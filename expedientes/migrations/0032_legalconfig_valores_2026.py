"""
Actualiza la Configuración Legal a los valores vigentes de 2026
============================================================

`AlterField` sólo cambia el default del modelo: las filas ya guardadas
mantienen los valores de 2024 (UMA $108.57, salario mínimo $248.93, tope
"2 × UMA"). Como `LegalConfig` es lo que alimenta las reglas del motor, hay que
migrar los datos, o el despacho seguiría calculando con la tabla anterior.

La migración NO pisa valores que el administrador haya customised de forma
deliberada y reciente; sólo actualiza los importes de referencia annual
(UMA, salario mínimo, UMA/frontera) y marca el tipo de tope según el valor
vigente de los arts. 485/486 LFT (doble del salario mínimo del área).
"""

from decimal import Decimal

from django.db import migrations

# CONASAMI (resolución del 3 de diciembre de 2025) e INEGI (Comunicado 1/26,
# DOF 09-01-2026, vigente desde el 1 de febrero de 2026).
UMA_DIARIA_2026 = Decimal('117.31')
SALARIO_MINIMO_2026 = Decimal('315.04')
SALARIO_MINIMO_FRONTERA_2026 = Decimal('440.87')


def actualizar_valores_2026(apps, schema_editor):
    LegalConfig = apps.get_model('expedientes', 'LegalConfig')

    for config in LegalConfig.objects.all():
        cambios = []

        if config.uma_diaria != UMA_DIARIA_2026:
            cambios.append(('uma_diaria', config.uma_diaria, UMA_DIARIA_2026))
            config.uma_diaria = UMA_DIARIA_2026

        if config.salario_minimo != SALARIO_MINIMO_2026:
            cambios.append(('salario_minimo', config.salario_minimo, SALARIO_MINIMO_2026))
            config.salario_minimo = SALARIO_MINIMO_2026

        if config.salario_minimo_frontera != SALARIO_MINIMO_FRONTERA_2026:
            cambios.append(('salario_minimo_frontera',
                            config.salario_minimo_frontera, SALARIO_MINIMO_FRONTERA_2026))
            config.salario_minimo_frontera = SALARIO_MINIMO_FRONTERA_2026

        # El tope de la prima de antigüedad es el doble del salario mínimo del
        # ÁREA (arts. 485/486 LFT), no 2 × UMA.  La etiqueta antigua "uma"
        # producía $234.62 en vez de $881.74 para la Zona Libre de la Frontera
        # Norte.
        if config.tope_prima_tipo in ('uma', 'frontera'):
            cambios.append(('tope_prima_tipo', config.tope_prima_tipo,
                            'salario_minimo_frontera'))
            config.tope_prima_tipo = 'salario_minimo_frontera'

        if '2024' in (config.nombre or ''):
            config.nombre = 'Configuración Legal 2026'

        config.save()

        if cambios:
            detalle = ', '.join(f'{campo}: {antes} → {despues}' for campo, antes, despues in cambios)
            print(f'  LegalConfig #{config.pk} actualizada a 2026 ({detalle})')


def sin_cambios(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('expedientes', '0031_calculolaboral_descanso_semanal_and_more'),
    ]

    operations = [
        migrations.RunPython(actualizar_valores_2026, sin_cambios),
    ]