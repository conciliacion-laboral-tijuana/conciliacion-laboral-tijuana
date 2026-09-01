from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from expedientes.models import Expediente, Movimiento
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Envía recordatorios automáticos de próximas acciones y audiencias'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=3,
            help='Días de anticipación para recordatorios (default: 3)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula el envío sin registrar movimientos'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        hoy = timezone.now().date()
        fecha_limite = hoy + timedelta(days=days)
        contador = 0

        self.stdout.write(f'Buscando recordatorios para los proximos {days} dias...')
        self.stdout.write(f'   Desde: {hoy} hasta: {fecha_limite}')
        self.stdout.write(f'   Dry run: {"Sí" if dry_run else "No"}')
        self.stdout.write('-' * 50)

        # 1. Próximas acciones
        proximas_acciones = Expediente.objects.filter(
            proxima_accion__gte=hoy,
            proxima_accion__lte=fecha_limite,
        ).exclude(estado='cerrado')

        for exp in proximas_acciones:
            self.stdout.write(self.style.WARNING(f'Proxima accion: {exp.numero} - {exp.cliente.nombre} - Vence: {exp.proxima_accion}'))
            if not dry_run:
                Movimiento.objects.create(
                    expediente=exp,
                    usuario=exp.asesor,
                    accion='actualizacion',
                    detalle=f'🔔 Recordatorio automático: Próxima acción vence el {exp.proxima_accion.strftime("%d/%m/%Y")}'
                )
            contador += 1

        # 2. Audiencias próximas
        proximas_audiencias = Expediente.objects.filter(
            fecha_audiencia__date__gte=hoy,
            fecha_audiencia__date__lte=fecha_limite,
        ).exclude(estado='cerrado')

        for exp in proximas_audiencias:
            self.stdout.write(self.style.WARNING(f'Audiencia proxima: {exp.numero} - {exp.cliente.nombre} - Fecha: {exp.fecha_audiencia.strftime("%d/%m/%Y %H:%M")}'))
            if not dry_run:
                Movimiento.objects.create(
                    expediente=exp,
                    usuario=exp.asesor,
                    accion='actualizacion',
                    detalle=f'🔔 Recordatorio automático: Audiencia programada para el {exp.fecha_audiencia.strftime("%d/%m/%Y %H:%M")}'
                )
            contador += 1

        # 3. Casos sin movimiento en +30 días
        hace_30_dias = timezone.now() - timedelta(days=30)
        casos_inactivos = Expediente.objects.filter(
            updated_at__lte=hace_30_dias
        ).exclude(estado='cerrado')

        for exp in casos_inactivos:
            self.stdout.write(self.style.WARNING(f'Caso inactivo: {exp.numero} - {exp.cliente.nombre} - Ultima actualizacion: {exp.updated_at.strftime("%d/%m/%Y")}'))
            if not dry_run:
                Movimiento.objects.create(
                    expediente=exp,
                    usuario=exp.asesor,
                    accion='actualizacion',
                    detalle=f'🔔 Recordatorio automático: Caso sin actividad desde {exp.updated_at.strftime("%d/%m/%Y")}'
                )
            contador += 1

        self.stdout.write('-' * 50)
        if contador > 0:
            self.stdout.write(self.style.SUCCESS(f'OK {contador} recordatorio(s) procesado(s).'))
        else:
            self.stdout.write(self.style.SUCCESS('OK No hay recordatorios pendientes.'))
