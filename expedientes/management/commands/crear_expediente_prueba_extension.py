"""
Crea un expediente de prueba COMPLETO para probar la Extension de Chrome.

Genera un cliente con TODOS los campos que la extension necesita para llenar
el portal de conciliacion: CURP, nombre completo, domicilio, datos laborales,
datos de la empresa, etc.

Uso:
    uv run python manage.py crear_expediente_prueba_extension
    uv run python manage.py crear_expediente_prueba_extension --asesor juan
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from expedientes.models import Cliente, Expediente, TareaConciliacion


class Command(BaseCommand):
    help = 'Crea un expediente de prueba completo para probar la extension de Chrome'

    def add_arguments(self, parser):
        parser.add_argument(
            '--asesor', type=str, default='',
            help='Username del asesor (default: primer asesor disponible)'
        )

    def handle(self, *args, **options):
        # -- Buscar asesor --
        asesor_username = options.get('asesor', '')
        if asesor_username:
            asesor = User.objects.filter(username=asesor_username).first()
            if not asesor:
                self.stdout.write(self.style.ERROR(
                    f'No se encontro el asesor "{asesor_username}". '
                    f'Usuarios disponibles: {list(User.objects.filter(profile__rol="asesor").values_list("username", flat=True))}'
                ))
                return
        else:
            asesor = User.objects.filter(profile__rol='asesor').first()
            if not asesor:
                self.stdout.write(self.style.ERROR('No hay asesores registrados.'))
                return

        hoy = date.today()

        # -- CURP de prueba (formato valido, NO real) --
        # El portal valida contra RENAPO, asi que esta CURP sera rechazada
        # por el portal real. Para una prueba completa, reemplaza por una
        # CURP REAL de un trabajador existente.
        CURP_PRUEBA = 'GARC800515HTCPBN07'

        # -- Crear cliente con TODOS los campos --
        cliente, created = Cliente.objects.get_or_create(
            curp=CURP_PRUEBA,
            defaults={
                'nombre': 'Carlos Garcia Torres',
                'rfc': 'GARC800515HBC',
                'telefono': '6641234567',
                'whatsapp': '6641234567',
                'email': 'carlos.garcia@email.com',
                'fecha_nacimiento': date(1980, 5, 15),
                'genero': 'masculino',
                # -- Domicilio particular --
                'direccion_calle': 'Av. Revolucion',
                'direccion_numero': '1234',
                'direccion_cp': '22000',
                'direccion_colonia': 'Zona Centro',
                # -- Empresa / Patron --
                'empresa': 'Maquiladora Tijuana SA de CV',
                'empresa_razon_social': 'Maquiladora Tijuana, S.A. de C.V.',
                'empresa_actividad': 'Manufactura electronica',
                'empresa_telefono': '6647654321',
                'empresa_calle': 'Blvd. Industrial',
                'empresa_numero': '500',
                'empresa_colonia': 'Otay',
                'empresa_cp': '22400',
                'empresa_referencias': 'Frente al parque industrial Otay',
                'tipo_persona_citado': 'moral',
                # -- Datos laborales --
                'puesto': 'Operador de produccion',
                'salario': Decimal('8500.00'),
                'periodo_pago': 'semanal',
                'horas_semanales': 44,
                'jornada': 'diurna',
                'fecha_ingreso': hoy - timedelta(days=365),
                'fecha_salida': hoy - timedelta(days=3),
                # -- Otros --
                'oficina': 'plaza_patria',
                'como_supo': 'google',
            }
        )

        if not created:
            self.stdout.write(self.style.WARNING(
                f'Ya existe un cliente con CURP {CURP_PRUEBA}: {cliente.nombre}'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(f'OK Cliente creado: {cliente.nombre}'))

        # -- Crear expediente --
        expediente, exp_created = Expediente.objects.get_or_create(
            cliente=cliente,
            asesor=asesor,
            defaults={
                'estado': 'nuevo',
                'tipo_despido': 'injustificado',
                'prestaciones_reclamadas': (
                    'Aguinaldo proporcional, vacaciones, prima vacacional, '
                    'prima de antiguedad, indemnizacion constitucional'
                ),
                'prioridad': 'alta',
                'notas': 'Expediente de prueba para testing de la extension de Chrome.',
            }
        )

        if not exp_created:
            self.stdout.write(self.style.WARNING(
                f'Ya existe expediente #{expediente.pk} para este cliente.'
            ))
        else:
            expediente.save()
            self.stdout.write(self.style.SUCCESS(f'OK Expediente creado: #{expediente.pk} - {expediente.numero}'))

        # -- Resumen --
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('  EXPEDIENTE DE PRUEBA LISTO PARA LA EXTENSION'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')
        self.stdout.write(f'  Expediente:  #{expediente.pk} - {expediente.numero}')
        self.stdout.write(f'  Cliente:     {cliente.nombre}')
        self.stdout.write(f'  CURP:        {cliente.curp}')
        self.stdout.write(f'  Empresa:     {cliente.empresa}')
        self.stdout.write(f'  Puesto:      {cliente.puesto}')
        self.stdout.write(f'  Salario:     ${cliente.salario}')
        self.stdout.write(f'  Ingreso:     {cliente.fecha_ingreso}')
        self.stdout.write(f'  Salida:      {cliente.fecha_salida}')
        self.stdout.write(f'  Domicilio:   {cliente.direccion_calle} {cliente.direccion_numero}, CP {cliente.direccion_cp}')
        self.stdout.write(f'  Empresa dir: {cliente.empresa_calle} {cliente.empresa_numero}, CP {cliente.empresa_cp}')
        self.stdout.write(f'  Asesor:      {asesor.get_full_name() or asesor.username}')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('-' * 60))
        self.stdout.write('  PARA PROBAR LA EXTENSION:')
        self.stdout.write('')
        self.stdout.write(f'  1. Abre la app: http://127.0.0.1:8080/expedientes/{expediente.pk}/')
        self.stdout.write(f'  2. Haz clic en "Enviar a Conciliacion"')
        self.stdout.write(f'  3. Elige "Desde mi navegador (Extension de Chrome)"')
        self.stdout.write(f'  4. Abre la extension en Chrome, veras la tarea, "Llenar en el portal"')
        self.stdout.write(f'  5. La extension llenara el formulario automaticamente')
        self.stdout.write(f'  6. Tu solo resuelves el CAPTCHA y das clic en "Enviar solicitud"')
        self.stdout.write('')
        self.stdout.write(self.style.WARNING(
            '  NOTA: El portal valida la CURP contra RENAPO. Si la CURP '
            'no es real, el portal la rechazara en Fase 4 (Solicitante).'
        ))
        self.stdout.write(self.style.WARNING(
            '  Para una prueba completa, edita el cliente y pon una CURP real.'
        ))
        self.stdout.write(self.style.SUCCESS('=' * 60))
