"""Conversión entre el salario por periodo de pago y el salario mensual.

`Cliente.salario` se guarda siempre como importe MENSUAL (el motor legal deriva
de ahí el diario y el integrado). El asesor, en cambio, captura lo que el
trabajador recibe en cada pago según su `periodo_pago`. Equivalencias (art. 89
LFT: el mes se cuenta de 30 días): diario ×30, semanal ×30/7, quincenal ×2.
"""

from decimal import ROUND_HALF_UP, Decimal

# Cuántos pagos del periodo equivalen a un mes.
PAGOS_POR_MES = {
    'diario': Decimal(30),
    'semanal': Decimal(30) / Decimal(7),
    'quincenal': Decimal(2),
    'mensual': Decimal(1),
}

CENTAVO = Decimal('0.01')


def _factor(periodo):
    return PAGOS_POR_MES.get(periodo or 'mensual', Decimal(1))


def a_mensual(monto, periodo):
    """Importe por periodo → importe mensual (redondeado a centavos)."""
    if monto is None:
        return None
    return (Decimal(monto) * _factor(periodo)).quantize(CENTAVO, ROUND_HALF_UP)


def por_periodo(mensual, periodo):
    """Importe mensual → lo que se paga en cada periodo (redondeado a centavos)."""
    if mensual is None:
        return None
    return (Decimal(mensual) / _factor(periodo)).quantize(CENTAVO, ROUND_HALF_UP)
