# -*- coding: utf-8 -*-
"""
Verificación de cálculos laborales para demandas.

Revisa que los conceptos que se reclaman en la demanda coincidan con el tipo
de despido y que el total del cálculo coincida con el CalculoLaboral guardado.

Uso:
    uv run python verify_demandas_calculos.py

Los tests de CI importan la función `verificar_calculos()`.
"""
import os
import sys

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db.models import Q

from expedientes.models import Expediente, CalculoLaboral
from expedientes.laboral_calculator import (
    calcular_desde_expediente,
    _aplicar_conceptos_excluidos,
)
from expedientes.demanda_generator import _conceptos_para_demanda


def _tiene_datos_completos(expediente) -> bool:
    """¿El cliente tiene los datos mínimos para calcular la demanda?"""
    cliente = expediente.cliente
    return bool(
        cliente.fecha_ingreso
        and cliente.fecha_salida
        and cliente.salario
        and cliente.salario > 0
    )


def verificar_calculos() -> dict:
    """
    Recorre los expedientes en estado 'demanda' y verifica:

    1. Datos completos del cliente (fechas + salario)
    2. Conceptos reclamados coherentes con el tipo de despido:
       - Renuncia voluntaria → NO debe reclamar indemnización (Art. 50 LFT)
         ni prima de antigüedad (Art. 162 LFT)
    3. El total del cálculo coincide con el CalculoLaboral guardado

    Returns:
        dict con:
          - 'con_datos': int, expedientes con datos completos
          - 'problemas': list[str], vacío si todo correcto
          - 'resumen': list[dict], un item por expediente en demanda
    """
    problemas = []
    resumen = []
    con_datos = 0

    expedientes = (
        Expediente.objects.filter(estado='demanda')
        .select_related('cliente')
        .order_by('numero')
    )

    for exp in expedientes:
        tipo = exp.tipo_despido or 'injustificado'
        cliente = exp.cliente
        completo = _tiene_datos_completos(exp)
        if completo:
            con_datos += 1

        item = {
            'numero': exp.numero,
            'cliente': cliente.nombre,
            'tipo': tipo,
            'estado': exp.get_estado_display(),
            'completo': completo,
            'total_calculo': None,
            'total_demanda': None,
        }

        if not completo:
            faltantes = []
            if not cliente.fecha_ingreso:
                faltantes.append('fecha de ingreso')
            if not cliente.fecha_salida:
                faltantes.append('fecha de salida')
            if not cliente.salario or cliente.salario <= 0:
                faltantes.append('salario')
            problemas.append(
                f'{exp.numero}: FALTAN DATOS del cliente ({", ".join(faltantes)})'
            )
            resumen.append(item)
            continue

        # Cálculo con los conceptos que la demanda reclama según tipo de despido
        conceptos = _conceptos_para_demanda(tipo)
        resultado = calcular_desde_expediente(
            exp, conceptos_seleccionados=conceptos
        )

        if not resultado.get('success'):
            problemas.append(
                f'{exp.numero}: no se pudo calcular ({resultado.get("error", "error desconocido")})'
            )
            resumen.append(item)
            continue

        item['total_demanda'] = float(resultado['total'])

        # ── Renuncia voluntaria: no debe reclamar conceptos que no proceden ──
        if tipo == 'voluntario':
            if resultado['indemnizacion']['monto'] > 0:
                problemas.append(
                    f'{exp.numero}: RENUNCIA VOLUNTARIA pero la demanda reclama '
                    f'indemnización constitucional (${resultado["indemnizacion"]["monto"]:,.2f}). '
                    f'No procede (Art. 50 LFT).'
                )
            if resultado['prima_antiguedad']['monto'] > 0:
                problemas.append(
                    f'{exp.numero}: RENUNCIA VOLUNTARIA pero la demanda reclama '
                    f'prima de antigüedad (${resultado["prima_antiguedad"]["monto"]:,.2f}). '
                    f'No procede (Art. 162 LFT).'
                )

        # ── Total coincide con el CalculoLaboral guardado ────────────────
        try:
            cl = CalculoLaboral.objects.get(expediente=exp)
        except CalculoLaboral.DoesNotExist:
            problemas.append(
                f'{exp.numero}: no existe CalculoLaboral guardado para el expediente.'
            )
            resumen.append(item)
            continue

        # Alinear conceptos como lo hace la app (renuncia → desmarcar) y recalcular
        cambio = _aplicar_conceptos_excluidos(cl, exp)
        if cambio:
            from expedientes.laboral_calculator import recalcular_calculo
            recalcular_calculo(cl)
            cl.save()

        item['total_calculo'] = float(cl.total)

        # Comparar con tolerancia de centavos
        if abs(float(cl.total) - float(resultado['total'])) > 0.01:
            problemas.append(
                f'{exp.numero}: CalculoLaboral.total (${cl.total:,.2f}) difiere del '
                f'total de la demanda (${resultado["total"]:,.2f}). '
                f'Revisa los conceptos seleccionados o recalcula el cálculo.'
            )

        resumen.append(item)

    return {
        'con_datos': con_datos,
        'problemas': problemas,
        'resumen': resumen,
    }


def main():
    resultado = verificar_calculos()

    print('=' * 72)
    print('VERIFICACIÓN DE CÁLCULOS PARA DEMANDAS')
    print('=' * 72)
    print(f'  Expedientes en demanda: {len(resultado["resumen"])}')
    print(f'  Con datos completos:    {resultado["con_datos"]}')
    print()

    if resultado['resumen']:
        print(f'  {"N°":<12}{"Cliente":<28}{"Tipo":<14}{"Total demanda":>16}{"Total cálculo":>16}')
        print('  ' + '-' * 86)
        for r in resultado['resumen']:
            td = f'${r["total_demanda"]:,.2f}' if r['total_demanda'] is not None else '—'
            tc = f'${r["total_calculo"]:,.2f}' if r['total_calculo'] is not None else '—'
            print(f'  {r["numero"]:<12}{r["cliente"]:<28}{r["tipo"]:<14}{td:>16}{tc:>16}')
    print()

    if not resultado['problemas']:
        print('  ✅ Sin problemas detectados.')
        return 0

    print(f'  ⚠️  Problemas ({len(resultado["problemas"])}):')
    for p in resultado['problemas']:
        print(f'    - {p}')
    return 1


if __name__ == '__main__':
    sys.exit(main())
