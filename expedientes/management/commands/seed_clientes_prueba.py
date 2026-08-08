"""
Comando de gestión: seed_clientes_prueba
=========================================

Genera clientes de prueba con DATOS COMPLETOS (fechas de ingreso/salida,
salario, puesto) por tipo de caso laboral, todos con su CalculoLaboral
recalculado y la mayoría en estado 'demanda'.

Objetivo: verificar que los cálculos laborales de las demandas sean
correctos (verify_demandas_calculos.py) y probar el dashboard de la
abogada / listas de demandas sin usar datos reales.

Uso:
    uv run python manage.py seed_clientes_prueba           # Crea los casos
    uv run python manage.py seed_clientes_prueba --clean   # Borra estos datos primero
    uv run python manage.py seed_clientes_prueba --borrar  # Solo elimina los casos de prueba

Los clientes se identifican por nombres fijos (marcador) para poder
borrarlos/recargarlos sin tocar datos reales.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from expedientes.models import Cliente, Expediente, CalculoLaboral, Movimiento
from expedientes.laboral_calculator import recalcular_calculo, _aplicar_conceptos_excluidos

# Marcador: nombres de los clientes de prueba (para --borrar / detección de duplicados)
NOMBRES_PRUEBA = [
    'Alma Ruiz Contreras',
    'Bruno Salas Nava',
    'Cecilia Ortega Vidal',
    'Diego Pineda Rojas',
    'Elena Campos Huerta',
    'Fabián Navarro Trejo',
    'Gabriela Luna Peña',
    'Héctor Ibarra Mora',
    'Irene Castillo Solís',
]


class Command(BaseCommand):
    help = 'Genera clientes de prueba con datos completos por tipo de caso (con cálculos laborales)'

    def add_arguments(self, parser):
        parser.add_argument('--clean', action='store_true',
                            help='Borra los casos de prueba existentes antes de crear')
        parser.add_argument('--borrar', action='store_true',
                            help='Solo elimina los casos de prueba y termina')

    def handle(self, *args, **options):
        asesores = list(User.objects.filter(profile__rol='asesor').order_by('username'))
        if not asesores:
            self.stdout.write(self.style.ERROR(
                'No hay asesores. Crea primero los usuarios (importar_clt --solo-asesores).'))
            return

        if options['borrar'] or options['clean']:
            self._borrar_prueba()

        if options['borrar']:
            return

        if Cliente.objects.filter(nombre__in=NOMBRES_PRUEBA).exists():
            self.stdout.write(self.style.WARNING(
                'Ya hay clientes de prueba cargados. Usa --clean para recargar.'))
            self._resumen()
            return

        hoy = date.today()
        casos = [
            # ── Casos en DEMANDA (verificación de cálculos) ────────────────
            {
                'nombre': 'Alma Ruiz Contreras', 'empresa': 'Maquiladora Frontera Norte SA',
                'puesto': 'Operadora de producción', 'salario': Decimal('18500.00'),
                'ingreso': hoy - timedelta(days=365 * 7 + 45), 'salida': hoy - timedelta(days=30),
                'tipo': 'injustificado', 'estado': 'demanda', 'prioridad': 'alta', 'genero': 'femenino',
            },
            {
                'nombre': 'Bruno Salas Nava', 'empresa': 'Logística Express BC SAPI',
                'puesto': 'Chofer repartidor', 'salario': Decimal('9800.00'),
                'ingreso': hoy - timedelta(days=365 * 2 + 90), 'salida': hoy - timedelta(days=12),
                'tipo': 'injustificado', 'estado': 'demanda', 'prioridad': 'media', 'genero': 'masculino',
            },
            {
                'nombre': 'Cecilia Ortega Vidal', 'empresa': 'Clínica San Ángel SA',
                'puesto': 'Enfermera general', 'salario': Decimal('25000.00'),
                'ingreso': hoy - timedelta(days=365 * 10 + 200), 'salida': hoy - timedelta(days=60),
                'tipo': 'voluntario', 'estado': 'demanda', 'prioridad': 'baja', 'genero': 'femenino',
            },
            {
                'nombre': 'Diego Pineda Rojas', 'empresa': 'Restaurante La Bahía SA',
                'puesto': 'Cocinero', 'salario': Decimal('12000.00'),
                'ingreso': hoy - timedelta(days=365 * 1 + 120), 'salida': hoy - timedelta(days=20),
                'tipo': 'voluntario', 'estado': 'demanda', 'prioridad': 'media', 'genero': 'masculino',
            },
            {
                'nombre': 'Elena Campos Huerta', 'empresa': 'Constructora Alpha BC',
                'puesto': 'Supervisora de obra', 'salario': Decimal('15000.00'),
                'ingreso': hoy - timedelta(days=365 * 4 + 30), 'salida': hoy - timedelta(days=45),
                'tipo': 'rescision', 'estado': 'demanda', 'prioridad': 'alta', 'genero': 'femenino',
            },
            # ── Otros estados (prueba de dashboards) ────────────────────────
            {
                'nombre': 'Fabián Navarro Trejo', 'empresa': 'Vidrios del Noroeste S de RL',
                'puesto': 'Cortador de vidrio', 'salario': Decimal('11000.00'),
                'ingreso': hoy - timedelta(days=365 * 3), 'salida': hoy - timedelta(days=15),
                'tipo': 'injustificado', 'estado': 'sin_conciliacion', 'prioridad': 'alta', 'genero': 'masculino',
            },
            {
                'nombre': 'Gabriela Luna Peña', 'empresa': 'Comercial Mexicana SA',
                'puesto': 'Cajera', 'salario': Decimal('9600.00'),
                'ingreso': hoy - timedelta(days=365 * 2), 'salida': hoy - timedelta(days=5),
                'tipo': 'injustificado', 'estado': 'audiencia', 'prioridad': 'media', 'genero': 'femenino',
            },
            {
                'nombre': 'Héctor Ibarra Mora', 'empresa': 'Empaque Tijuana SAPI',
                'puesto': 'Almacenista', 'salario': Decimal('9000.00'),
                'ingreso': hoy - timedelta(days=365 * 5), 'salida': hoy - timedelta(days=90),
                'tipo': 'injustificado', 'estado': 'convenio', 'prioridad': 'baja', 'genero': 'masculino',
            },
            {
                'nombre': 'Irene Castillo Solís', 'empresa': 'Tecnologías del Noroeste SAPI',
                'puesto': 'Desarrolladora de software', 'salario': Decimal('45000.00'),
                'ingreso': hoy - timedelta(days=365), 'salida': hoy - timedelta(days=3),
                'tipo': 'injustificado', 'estado': 'nuevo', 'prioridad': 'alta', 'genero': 'femenino',
            },
        ]

        for i, caso in enumerate(casos):
            asesor = asesores[i % len(asesores)]

            cliente = Cliente.objects.create(
                nombre=caso['nombre'],
                empresa=caso['empresa'],
                telefono=f'+52664{i:06d}',
                whatsapp=f'+52664{i:06d}',
                direccion_calle='Calle de Prueba',
                direccion_numero=str(100 + i),
                direccion_cp='22000',
                direccion_colonia='Zona Centro',
                empresa_telefono=f'+52664999{i:04d}',
                empresa_calle='Blvd. Industrial',
                empresa_numero=str(200 + i),
                empresa_colonia='Otay',
                empresa_cp='22400',
                puesto=caso['puesto'],
                salario=caso['salario'],
                periodo_pago='mensual',
                horas_semanales=48,
                jornada='diurna',
                fecha_ingreso=caso['ingreso'],
                fecha_salida=caso['salida'],
                genero=caso['genero'],
                oficina='plaza_patria',
                como_supo='internet',
            )

            exp = Expediente.objects.create(
                cliente=cliente,
                asesor=asesor,
                estado=caso['estado'],
                tipo_despido=caso['tipo'],
                monto_reclamado=caso['salario'] * 12,
                prioridad=caso['prioridad'],
                notas=f'Cliente de prueba ({caso["tipo"]}). Datos sintéticos para verificar cálculos.',
            )

            # Calcular laboral con conceptos alineados al tipo de despido
            cl = CalculoLaboral.objects.create(expediente=exp)
            _aplicar_conceptos_excluidos(cl, exp)
            recalcular_calculo(cl)
            cl.save()

            if exp.estado == 'demanda':
                # el monto reclamado coincide con el cálculo (update_fields evita re-validar)
                exp.monto_reclamado = cl.total
                exp.save(update_fields=['monto_reclamado'])

            Movimiento.objects.create(
                expediente=exp, usuario=asesor, accion='creacion',
                detalle=f'Caso de prueba creado ({caso["tipo"]}). Cálculo total: ${cl.total:,.2f}',
                created_at=timezone.now() - timedelta(days=i),
            )

            self.stdout.write(
                f'  {exp.numero} | {caso["nombre"]:<28} | {caso["tipo"]:<14} '
                f'| {exp.get_estado_display():<18} | ${cl.total:>12,.2f}')

        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('CLIENTES DE PRUEBA GENERADOS'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'  Clientes:    {Cliente.objects.count()}')
        self.stdout.write(f'  Expedientes: {Expediente.objects.count()}')
        self.stdout.write(f'  Cálculos:    {CalculoLaboral.objects.count()}')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            'Verifica los cálculos con:  uv run python verify_demandas_calculos.py'))
        self.stdout.write(self.style.WARNING(
            'Para limpiar:  uv run python manage.py seed_clientes_prueba --borrar'))

    def _borrar_prueba(self):
        """Elimina solo los casos de prueba (identificados por NOMBRES_PRUEBA)."""
        self.stdout.write(self.style.WARNING('Eliminando casos de prueba...'))
        clientes = Cliente.objects.filter(nombre__in=NOMBRES_PRUEBA)
        if not clientes:
            self.stdout.write('  No hay casos de prueba que borrar.')
            return
        for cli in clientes:
            for exp in cli.expediente_set.all():
                CalculoLaboral.objects.filter(expediente=exp).delete()
                Movimiento.objects.filter(expediente=exp).delete()
                exp.delete()
            cli.delete()
        self.stdout.write(self.style.SUCCESS(f'  Casos de prueba eliminados ({len(NOMBRES_PRUEBA)} marcadores).'))

    def _resumen(self):
        self.stdout.write(f'   Clientes: {Cliente.objects.count()} | '
                          f'Expedientes: {Expediente.objects.count()} | '
                          f'Cálculos: {CalculoLaboral.objects.count()}')
