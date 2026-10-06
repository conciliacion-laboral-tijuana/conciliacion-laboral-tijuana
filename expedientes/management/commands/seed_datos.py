"""
Comando para sembrar datos de prueba con diferentes casos laborales.
Cubre todos los estados del expediente y distintos perfiles de clientes.

Uso:
    uv run python manage.py seed_datos          # Carga datos de prueba
    uv run python manage.py seed_datos --clean   # Limpia datos existentes primero
"""
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone

from expedientes.models import (
    Cliente, Expediente, SolicitudConciliacion, Movimiento, Nota,
    LegalConfig, WhatsAppMessage
)


class Command(BaseCommand):
    help = 'Siembra datos de prueba con 10 casos laborales distintos'

    def add_arguments(self, parser):
        parser.add_argument('--clean', action='store_true', help='Elimina datos existentes primero')

    def handle(self, *args, **options):
        if options['clean']:
            self._clean_data()

        asesores = list(User.objects.filter(profile__rol='asesor'))
        if not asesores:
            self.stdout.write(self.style.ERROR('No hay asesores. Ejecuta primero: crear_usuarios_prueba'))
            return

        admin = User.objects.filter(profile__rol__in=['admin', 'superadmin']).first()
        if not admin:
            admin = User.objects.filter(is_superuser=True).first()

        if Cliente.objects.filter(curp__in=['HERG900315MDFRRN09', 'LOMJ850722HBCNRN05', 'JIDR900101HBCLRN06']).exists():
            self.stdout.write(self.style.WARNING('Ya hay datos de prueba cargados. Usa --clean para recargar.'))
            self.stdout.write(self.style.SUCCESS(f'   Clientes: {Cliente.objects.count()}'))
            self.stdout.write(self.style.SUCCESS(f'   Expedientes: {Expediente.objects.count()}'))
            return

        hoy = date.today()

        # ====================================================================
        # CASO 1: Expediente NUEVO — Despido injustificado, recién ingresado
        # ====================================================================
        c1 = Cliente.objects.create(
            nombre='María Guadalupe Hernández Ramírez',
            curp='HERG900315MDFRRN09',
            rfc='HERG900315',
            telefono='+526641234567',
            whatsapp='+526641234567',
            email='guadalupe.hernandez@email.com',
            direccion_calle='Av. Revolución',
            direccion_numero='1234',
            direccion_cp='22000',
            direccion_colonia='Zona Centro',
            empresa='Maquiladora Tijuana SA de CV',
            empresa_actividad='Manufactura electrónica',
            empresa_telefono='+526647654321',
            empresa_razon_social='Maquiladora Tijuana, S.A. de C.V.',
            empresa_calle='Blvd. Industrial',
            empresa_numero='500',
            empresa_colonia='Otay',
            empresa_cp='22400',
            empresa_referencias='Frente al parque industrial',
            puesto='Operadora de producción',
            salario=Decimal('8500.00'),
            fecha_ingreso=hoy - timedelta(days=365),
            fecha_salida=hoy - timedelta(days=3),
        )
        e1 = Expediente.objects.create(
            cliente=c1, asesor=asesores[0], estado='nuevo',
            tipo_despido='injustificado',
            prestaciones_reclamadas='Aguinaldo proporcional, vacaciones, prima vacacional, prima de antigüedad, indemnización constitucional',
            prioridad='alta',
            notas='Cliente fue despedida sin previo aviso después de 1 año. Solicita asesoría urgente.',
            created_at=timezone.now() - timedelta(hours=2),
        )
        Movimiento.objects.create(
            expediente=e1, usuario=admin or asesores[0], accion='creacion',
            detalle='Cliente ingresó por primera vez. Solicita asesoría por despido injustificado.',
            created_at=timezone.now() - timedelta(hours=2),
        )

        # ====================================================================
        # CASO 2: Expediente en SOLICITUD — Renuncia voluntaria, solicitud creada
        # ====================================================================
        c2 = Cliente.objects.create(
            nombre='Juan Carlos López Moreno',
            curp='LOMJ850722HBCNRN05',
            rfc='LOMJ850722',
            telefono='+526641112233',
            email='juan.lopez@correo.com',
            direccion_calle='Calle 5 de Mayo',
            direccion_numero='456',
            direccion_cp='22450',
            direccion_colonia='La Mesa',
            empresa='Construcciones del Noroeste SAPI',
            empresa_actividad='Construcción',
            empresa_telefono='+526644455667',
            puesto='Albañil',
            salario=Decimal('12000.00'),
            fecha_ingreso=hoy - timedelta(days=730),
            fecha_salida=hoy - timedelta(days=15),
        )
        e2 = Expediente.objects.create(
            cliente=c2, asesor=asesores[1], estado='solicitud',
            tipo_despido='voluntario',
            monto_reclamado=Decimal('25000.00'),
            folio='C-2024-0158',
            fecha_tramite=hoy - timedelta(days=10),
            prestaciones_reclamadas='Aguinaldo proporcional, vacaciones, prima vacacional',
            prioridad='media',
            notas='Renuncia voluntaria. No hubo despido. Se elaboró solicitud de conciliación.',
            created_at=timezone.now() - timedelta(days=12),
        )
        SolicitudConciliacion.objects.create(
            expediente=e2, unidad_sede='Tijuana',
            fecha_solicitud=hoy - timedelta(days=10),
            edad=39, horas_semanales=48, periodo_pago='semanal',
            fecha_conflicto=hoy - timedelta(days=15),
            objeto_terminacion_voluntaria=True, objeto_prestaciones=True,
            citatorio_entrega='solicitante',
            firma_nombre='Juan Carlos López Moreno',
            firma_fecha=hoy - timedelta(days=10),
        )
        Movimiento.objects.create(expediente=e2, usuario=asesores[1], accion='creacion',
                                   detalle='Cliente registró renuncia voluntaria. Se inició expediente.')
        Movimiento.objects.create(
            expediente=e2, usuario=asesores[1], accion='cambio_estado',
            detalle='Solicitud de conciliación creada y turnada a centro de conciliación.',
            created_at=timezone.now() - timedelta(days=10),
        )

        # ====================================================================
        # CASO 3: CITATORIO generado — Despido justificado
        # ====================================================================
        c3 = Cliente.objects.create(
            nombre='Roberto Ángel Jiménez Díaz',
            curp='JIDR900101HBCLRN06',
            rfc='JIDR900101',
            telefono='+526647778899',
            direccion_calle='Calle Roble', direccion_numero='789',
            direccion_cp='22100', direccion_colonia='Río Tijuana',
            empresa='Seguridad Privada MX S de RL',
            empresa_actividad='Servicios de seguridad privada',
            empresa_telefono='+526649990011',
            puesto='Vigilante',
            salario=Decimal('7500.00'),
            fecha_ingreso=hoy - timedelta(days=180),
            fecha_salida=hoy - timedelta(days=20),
        )
        e3 = Expediente.objects.create(
            cliente=c3, asesor=asesores[2], estado='citatorio',
            tipo_despido='justificado',
            monto_reclamado=Decimal('15000.00'),
            folio='C-2024-0162',
            fecha_tramite=hoy - timedelta(days=18),
            prestaciones_reclamadas='Aguinaldo proporcional, vacaciones, prima vacacional',
            prioridad='media',
            notas='Despido justificado por faltas. Citatorio generado para audiencia de conciliación.',
            created_at=timezone.now() - timedelta(days=19),
        )
        SolicitudConciliacion.objects.create(
            expediente=e3, unidad_sede='Tijuana',
            fecha_solicitud=hoy - timedelta(days=18),
            edad=34, horas_semanales=40, periodo_pago='semanal',
            fecha_conflicto=hoy - timedelta(days=20),
            objeto_despido=True, objeto_antiguedad=True, objeto_prestaciones=True,
            citatorio_entrega='notificador',
            firma_nombre='Roberto Ángel Jiménez Díaz',
            firma_fecha=hoy - timedelta(days=18),
        )
        Movimiento.objects.create(expediente=e3, usuario=asesores[2], accion='creacion',
                                   detalle='Cliente ingresó por despido justificado. Se abrió expediente.')
        Movimiento.objects.create(
            expediente=e3, usuario=asesores[2], accion='cambio_estado',
            detalle='Solicitud de conciliación presentada. Citatorio generado.',
            created_at=timezone.now() - timedelta(days=15),
        )

        # ====================================================================
        # CASO 4: AUDIENCIA programada — Prestaciones mixtas
        # ====================================================================
        c4 = Cliente.objects.create(
            nombre='Ana Patricia Mendoza García',
            curp='MEGA920510MMCDRR05',
            rfc='MEGA920510',
            telefono='+526642223344',
            email='ana.mendoza@email.com',
            direccion_calle='Paseo de los Héroes', direccion_numero='2000',
            direccion_cp='22320', direccion_colonia='Zona Río',
            empresa='Comercial Mexicana SA',
            empresa_actividad='Comercio minorista',
            empresa_telefono='+526645556677',
            puesto='Cajera',
            salario=Decimal('9600.00'),
            fecha_ingreso=hoy - timedelta(days=1095),
            fecha_salida=hoy - timedelta(days=30),
        )
        e4 = Expediente.objects.create(
            cliente=c4, asesor=asesores[3], estado='audiencia',
            tipo_despido='injustificado',
            monto_reclamado=Decimal('85000.00'),
            folio='C-2024-0170',
            fecha_tramite=hoy - timedelta(days=25),
            fecha_audiencia=timezone.now() + timedelta(days=3),
            prestaciones_reclamadas='Aguinaldo proporcional, vacaciones, prima vacacional, prima de antigüedad, indemnización',
            prioridad='alta',
            notas='Audiencia programada para el viernes. Cliente con 3 años de antigüedad.',
            created_at=timezone.now() - timedelta(days=28),
        )
        SolicitudConciliacion.objects.create(
            expediente=e4, unidad_sede='Tijuana',
            fecha_solicitud=hoy - timedelta(days=25),
            edad=32, horas_semanales=40, periodo_pago='quincenal',
            fecha_conflicto=hoy - timedelta(days=30),
            objeto_despido=True, objeto_antiguedad=True, objeto_prestaciones=True, objeto_ascenso=True,
            citatorio_entrega='notificador',
            firma_nombre='Ana Patricia Mendoza García',
            firma_fecha=hoy - timedelta(days=25),
        )
        Movimiento.objects.create(expediente=e4, usuario=asesores[3], accion='creacion',
                                   detalle='Cliente con 3 años de antigüedad. Despido injustificado.')
        Movimiento.objects.create(
            expediente=e4, usuario=asesores[3], accion='cambio_estado',
            detalle='Citatorio entregado. Audiencia programada.',
            created_at=timezone.now() - timedelta(days=5),
        )

        # ====================================================================
        # CASO 5: CONVENIO alcanzado — Ejemplo exitoso
        # ====================================================================
        c5 = Cliente.objects.create(
            nombre='Luis Fernando Torres Aguilar',
            curp='TOAL780514HBCRRN04',
            rfc='TOAL780514',
            telefono='+526647778800',
            email='luis.torres@correo.com',
            direccion_calle='Calle Olivo', direccion_numero='320',
            direccion_cp='22600', direccion_colonia='Playas de Tijuana',
            empresa='Restaurante La Costa SA',
            empresa_actividad='Restaurante',
            empresa_telefono='+526643336699',
            puesto='Cocinero',
            salario=Decimal('15000.00'),
            fecha_ingreso=hoy - timedelta(days=1825),
            fecha_salida=hoy - timedelta(days=60),
        )
        e5 = Expediente.objects.create(
            cliente=c5, asesor=asesores[4], estado='convenio',
            tipo_despido='injustificado',
            monto_reclamado=Decimal('180000.00'),
            monto_convenio=Decimal('95000.00'),
            folio='C-2024-0145',
            fecha_tramite=hoy - timedelta(days=55),
            resultado_audiencia='convenio',
            prestaciones_reclamadas='Aguinaldo, vacaciones, prima vacacional, prima de antigüedad, indemnización, salarios caídos',
            prioridad='baja',
            notas='Convenio alcanzado exitosamente. Cliente recibió $95,000.00 como liquidación.',
            created_at=timezone.now() - timedelta(days=60),
        )
        SolicitudConciliacion.objects.create(
            expediente=e5, unidad_sede='Tijuana',
            fecha_solicitud=hoy - timedelta(days=55),
            edad=46, horas_semanales=48, periodo_pago='semanal',
            fecha_conflicto=hoy - timedelta(days=60),
            objeto_despido=True, objeto_antiguedad=True, objeto_prestaciones=True,
            citatorio_entrega='notificador',
            firma_nombre='Luis Fernando Torres Aguilar',
            firma_fecha=hoy - timedelta(days=55),
        )
        Movimiento.objects.create(expediente=e5, usuario=asesores[4], accion='creacion',
                                   detalle='Cliente con 5 años de antigüedad. Despido injustificado.')
        Movimiento.objects.create(
            expediente=e5, usuario=asesores[4], accion='cambio_estado',
            detalle='Audiencia de conciliación. Se alcanzó convenio por $95,000.00.',
            created_at=timezone.now() - timedelta(days=7),
        )

        # ====================================================================
        # CASO 6: SIN CONCILIACIÓN — No hubo acuerdo, se prepara demanda
        # ====================================================================
        c6 = Cliente.objects.create(
            nombre='Gabriela Ivonne Ríos Martínez',
            curp='RIMG880210MDGRRN06',
            rfc='RIMG880210',
            telefono='+526645551122',
            direccion_calle='Calle Laurel', direccion_numero='150',
            direccion_cp='22500', direccion_colonia='El Florido',
            empresa='Fábrica Textil BC SAPI',
            empresa_actividad='Industria textil',
            empresa_telefono='+526648881100',
            puesto='Costurera',
            salario=Decimal('7800.00'),
            fecha_ingreso=hoy - timedelta(days=540),
            fecha_salida=hoy - timedelta(days=45),
        )
        e6 = Expediente.objects.create(
            cliente=c6, asesor=asesores[5], estado='sin_conciliacion',
            tipo_despido='injustificado',
            monto_reclamado=Decimal('65000.00'),
            folio='C-2024-0155',
            fecha_tramite=hoy - timedelta(days=40),
            resultado_audiencia='sin_conciliacion',
            prestaciones_reclamadas='Aguinaldo proporcional, vacaciones, prima vacacional, prima de antigüedad',
            prioridad='alta',
            notas='No hubo acuerdo en conciliación. El patrón no se presentó. Preparar demanda.',
            created_at=timezone.now() - timedelta(days=42),
        )
        SolicitudConciliacion.objects.create(
            expediente=e6, unidad_sede='Tijuana',
            fecha_solicitud=hoy - timedelta(days=40),
            edad=36, horas_semanales=45, periodo_pago='semanal',
            fecha_conflicto=hoy - timedelta(days=45),
            objeto_despido=True, objeto_prestaciones=True,
            citatorio_entrega='notificador',
            discapacidad_motriz=True,
            requiere_traductor=False,
            firma_nombre='Gabriela Ivonne Ríos Martínez',
            firma_fecha=hoy - timedelta(days=40),
        )
        Movimiento.objects.create(expediente=e6, usuario=asesores[5], accion='creacion',
                                   detalle='Cliente ingresó por despido injustificado. Inicia proceso.')
        Movimiento.objects.create(
            expediente=e6, usuario=asesores[5], accion='resultado_audiencia',
            detalle='Sin conciliación. Patrón no asistió. Se procederá a demanda.',
            created_at=timezone.now() - timedelta(days=2),
        )

        # ====================================================================
        # CASO 7: REPROGRAMACIÓN — Audiencia reagendada
        # ====================================================================
        c7 = Cliente.objects.create(
            nombre='Miguel Ángel Cruz Valdez',
            curp='CUVG850305HPLRNN01',
            rfc='CUVG850305',
            telefono='+526649997788',
            direccion_calle='Calle Michoacán', direccion_numero='88',
            direccion_cp='22700', direccion_colonia='La Presa',
            empresa='Autotransportes Fronterizos SA',
            empresa_actividad='Transporte de carga',
            empresa_telefono='+526643332211',
            puesto='Chofer',
            salario=Decimal('18000.00'),
            fecha_ingreso=hoy - timedelta(days=1460),
            fecha_salida=hoy - timedelta(days=35),
        )
        e7 = Expediente.objects.create(
            cliente=c7, asesor=asesores[6], estado='reprogramacion',
            tipo_despido='rescision',
            monto_reclamado=Decimal('95000.00'),
            folio='C-2024-0168',
            fecha_tramite=hoy - timedelta(days=32),
            resultado_audiencia='reprogramada',
            prestaciones_reclamadas='Aguinaldo proporcional, vacaciones, prima vacacional, prima de antigüedad, indemnización',
            prioridad='media',
            notas='Audiencia fue reprogramada por inasistencia del patrón. Nueva fecha pendiente.',
            created_at=timezone.now() - timedelta(days=35),
        )
        SolicitudConciliacion.objects.create(
            expediente=e7, unidad_sede='Tijuana',
            fecha_solicitud=hoy - timedelta(days=32),
            edad=39, horas_semanales=55, periodo_pago='semanal',
            fecha_conflicto=hoy - timedelta(days=35),
            objeto_rescision=True, objeto_antiguedad=True, objeto_prestaciones=True,
            citatorio_entrega='notificador',
            firma_nombre='Miguel Ángel Cruz Valdez',
            firma_fecha=hoy - timedelta(days=32),
        )
        Movimiento.objects.create(expediente=e7, usuario=asesores[6], accion='creacion',
                                   detalle='Cliente rescindió relación laboral. Se abrió expediente.')
        Movimiento.objects.create(
            expediente=e7, usuario=asesores[6], accion='resultado_audiencia',
            detalle='Audiencia reprogramada por inasistencia del patrón.',
            created_at=timezone.now() - timedelta(days=5),
        )

        # ====================================================================
        # CASO 8: NO NOTIFICADO — Citatorio no se pudo entregar
        # ====================================================================
        c8 = Cliente.objects.create(
            nombre='Jorge Alberto Sandoval Moreno',
            curp='SAMJ910820HDFNRR03',
            rfc='SAMJ910820',
            telefono='+526641002030',
            direccion_calle='Calle Sinaloa', direccion_numero='500',
            direccion_cp='22640', direccion_colonia='Buena Vista',
            empresa='Vidrios y Aluminios del Noroeste S de RL',
            empresa_actividad='Fabricación de vidrio y aluminio',
            empresa_telefono='+526647771122',
            puesto='Cortador de vidrio',
            salario=Decimal('11000.00'),
            fecha_ingreso=hoy - timedelta(days=900),
            fecha_salida=hoy - timedelta(days=25),
        )
        e8 = Expediente.objects.create(
            cliente=c8, asesor=asesores[7], estado='no_notificado',
            tipo_despido='injustificado',
            monto_reclamado=Decimal('72000.00'),
            folio='C-2024-0165',
            fecha_tramite=hoy - timedelta(days=22),
            resultado_audiencia='no_notificado',
            prestaciones_reclamadas='Aguinaldo, vacaciones, prima vacacional, prima de antigüedad',
            prioridad='alta',
            notas='Citatorio no pudo ser notificado. Domicilio del patrón incorrecto. Se investigará.',
            created_at=timezone.now() - timedelta(days=28),
        )
        SolicitudConciliacion.objects.create(
            expediente=e8, unidad_sede='Tijuana',
            fecha_solicitud=hoy - timedelta(days=22),
            edad=33, horas_semanales=48, periodo_pago='semanal',
            fecha_conflicto=hoy - timedelta(days=25),
            objeto_despido=True, objeto_antiguedad=True, objeto_prestaciones=True,
            citatorio_entrega='notificador',
            firma_nombre='Jorge Alberto Sandoval Moreno',
            firma_fecha=hoy - timedelta(days=22),
        )
        Movimiento.objects.create(expediente=e8, usuario=asesores[7], accion='creacion',
                                   detalle='Despido injustificado. Se inició proceso de conciliación.')
        Movimiento.objects.create(
            expediente=e8, usuario=asesores[7], accion='cambio_estado',
            detalle='Citatorio devuelto: no notificado. Domicilio del patrón no localizado.',
            created_at=timezone.now() - timedelta(days=10),
        )

        # ====================================================================
        # CASO 9: DEMANDA — Caso escaló a demanda laboral
        # ====================================================================
        c9 = Cliente.objects.create(
            nombre='Patricia Lizbeth Navarro Esquivel',
            curp='NAEP850220MBCRRT09',
            rfc='NAEP850220',
            telefono='+526646661234',
            email='patricia.navarro@correo.com',
            direccion_calle='Calle Jalisco', direccion_numero='777',
            direccion_cp='22440', direccion_colonia='Francisco Villa',
            empresa='Clínica Médica Del Ángel SA',
            empresa_actividad='Servicios médicos',
            empresa_telefono='+526644449988',
            puesto='Enfermera',
            salario=Decimal('14000.00'),
            fecha_ingreso=hoy - timedelta(days=2190),
            fecha_salida=hoy - timedelta(days=90),
        )
        e9 = Expediente.objects.create(
            cliente=c9, asesor=asesores[8], estado='demanda',
            tipo_despido='injustificado',
            monto_reclamado=Decimal('250000.00'),
            folio='C-2024-0100',
            fecha_tramite=hoy - timedelta(days=85),
            resultado_audiencia='sin_conciliacion',
            prestaciones_reclamadas='Aguinaldo, vacaciones, prima vacacional, prima de antigüedad, indemnización constitucional, salarios caídos',
            prioridad='alta',
            notas='Caso escaló a demanda laboral. Cliente con 6 años de antigüedad. Monto considerable.',
            created_at=timezone.now() - timedelta(days=92),
        )
        SolicitudConciliacion.objects.create(
            expediente=e9, unidad_sede='Tijuana',
            fecha_solicitud=hoy - timedelta(days=85),
            edad=39, horas_semanales=40, periodo_pago='quincenal',
            fecha_conflicto=hoy - timedelta(days=90),
            objeto_despido=True, objeto_antiguedad=True, objeto_prestaciones=True, objeto_ascenso=True,
            citatorio_entrega='notificador',
            discapacidad_visual=True,
            requiere_traductor=False,
            firma_nombre='Patricia Lizbeth Navarro Esquivel',
            firma_fecha=hoy - timedelta(days=85),
        )
        Movimiento.objects.create(expediente=e9, usuario=asesores[8], accion='creacion',
                                   detalle='Cliente con 6 años de antigüedad. Monto reclamado alto.')
        Movimiento.objects.create(
            expediente=e9, usuario=asesores[8], accion='cambio_estado',
            detalle='Sin acuerdo en conciliación. Se presentó demanda laboral ante Junta.',
            created_at=timezone.now() - timedelta(days=30),
        )

        # ====================================================================
        # CASO 10: CERRADO — Caso concluido
        # ====================================================================
        c10 = Cliente.objects.create(
            nombre='Ricardo Daniel Osuna Méndez',
            curp='OUMR830910HBCLNC07',
            rfc='OUMR830910',
            telefono='+526644001122',
            direccion_calle='Av. Constitución', direccion_numero='1500',
            direccion_cp='22700', direccion_colonia='La Presa',
            empresa='Empaque y Embalaje Tijuana SAPI',
            empresa_actividad='Empaque industrial',
            empresa_telefono='+526647774433',
            puesto='Almacenista',
            salario=Decimal('9000.00'),
            fecha_ingreso=hoy - timedelta(days=2555),
            fecha_salida=hoy - timedelta(days=180),
        )
        e10 = Expediente.objects.create(
            cliente=c10, asesor=asesores[9], estado='cerrado',
            tipo_despido='injustificado',
            monto_reclamado=Decimal('120000.00'),
            monto_convenio=Decimal('85000.00'),
            folio='C-2024-0090',
            fecha_tramite=hoy - timedelta(days=175),
            resultado_audiencia='convenio',
            prestaciones_reclamadas='Aguinaldo, vacaciones, prima vacacional, prima de antigüedad, indemnización',
            prioridad='baja',
            notas='CASO CERRADO. Convenio pagado en su totalidad. Cliente satisfecho.',
            created_at=timezone.now() - timedelta(days=182),
        )
        SolicitudConciliacion.objects.create(
            expediente=e10, unidad_sede='Tijuana',
            fecha_solicitud=hoy - timedelta(days=175),
            edad=41, horas_semanales=48, periodo_pago='semanal',
            fecha_conflicto=hoy - timedelta(days=180),
            objeto_despido=True, objeto_antiguedad=True, objeto_prestaciones=True,
            citatorio_entrega='notificador',
            firma_nombre='Ricardo Daniel Osuna Méndez',
            firma_fecha=hoy - timedelta(days=175),
        )
        Movimiento.objects.create(expediente=e10, usuario=asesores[9], accion='creacion',
                                    detalle='Cliente con 7 años de antigüedad. Caso de liquidación.')
        Movimiento.objects.create(
            expediente=e10, usuario=asesores[9], accion='cambio_estado',
            detalle='Convenio alcanzado en audiencia. Monto: $85,000.00.',
            created_at=timezone.now() - timedelta(days=120),
        )
        Movimiento.objects.create(
            expediente=e10, usuario=asesores[9], accion='actualizacion',
            detalle='Convenio pagado en su totalidad. Caso cerrado exitosamente.',
            created_at=timezone.now() - timedelta(days=90),
        )

        # ====================================================================
        # CASO 11: Recién creado con salario alto — Ejecutivo
        # ====================================================================
        c11 = Cliente.objects.create(
            nombre='Alejandro González del Valle',
            curp='GOVA950201HDFLNN02',
            rfc='GOVA950201',
            telefono='+526641234589',
            email='alejandro.gv@empresa.com',
            direccion_calle='Blvd. Agua Caliente', direccion_numero='4550',
            direccion_cp='22040', direccion_colonia='Hipódromo',
            empresa='Tecnologías del Noroeste SAPI',
            empresa_actividad='Desarrollo de software',
            empresa_telefono='+526646661100',
            empresa_razon_social='Tecnologías del Noroeste, S.A.P.I. de C.V.',
            empresa_calle='Blvd. Sánchez Taboada',
            empresa_numero='10400',
            empresa_colonia='Zona Urbana Río',
            empresa_cp='22010',
            puesto='Ingeniero de Software Sr.',
            salario=Decimal('45000.00'),
            fecha_ingreso=hoy - timedelta(days=400),
            fecha_salida=hoy - timedelta(days=1),
        )
        e11 = Expediente.objects.create(
            cliente=c11, asesor=asesores[10], estado='nuevo',
            tipo_despido='injustificado',
            monto_reclamado=Decimal('180000.00'),
            prestaciones_reclamadas='Aguinaldo proporcional, vacaciones, prima vacacional, prima de antigüedad, indemnización constitucional',
            prioridad='alta',
            notas='Despido injustificado. Salario alto. Cliente ejecutivo. Urgente.',
            created_at=timezone.now() - timedelta(hours=1),
        )
        Movimiento.objects.create(
            expediente=e11, usuario=admin or asesores[10], accion='creacion',
            detalle='Ejecutivo despedido sin causa justificada. Ingreso urgente.',
            created_at=timezone.now() - timedelta(hours=1),
        )

        # ─── ✅ LegalConfig por defecto ─────────────────────────────────────
        if not LegalConfig.objects.exists():
            LegalConfig.objects.create(
                nombre='Configuración Legal 2026',
                activo=True,
                # CONASAMI (dic 2025) e INEGI (ene 2026, vigente desde 1-feb-2026)
                uma_diaria=Decimal('117.31'),
                salario_minimo=Decimal('315.04'),
                salario_minimo_frontera=Decimal('440.87'),
                aguinaldo_dias=15,
                prima_vacacional_porcentaje=Decimal('25.00'),
                prima_antiguedad_dias_por_ano=12,
                prima_antiguedad_anios_voluntaria=15,
                vacaciones_antes_de_un_ano='proporcional',
                indemnizacion_dias=90,
                indemnizacion_20dias_dias_por_ano=20,
                # Arts. 485/486 LFT: el tope es el doble del salario mínimo del
                # ÁREA, no 2 × UMA
                tope_prima_tipo='salario_minimo_frontera',
                tope_prima_multiplo=2,
                salario_integrado_modo='explicit',
                salario_integrado_porcentaje=Decimal('0.00'),
            )

        # ─── Notas en algunos expedientes ──────────────────────────────────
        Nota.objects.create(
            expediente=e1, usuario=asesores[0],
            contenido='Cliente muy afectada emocionalmente. Se le explicó el proceso.',
        )
        Nota.objects.create(
            expediente=e4, usuario=asesores[3],
            contenido='Recordatorio: audiencia en 3 días. Preparar documentos.',
        )
        Nota.objects.create(
            expediente=e5, usuario=asesores[4],
            contenido='Convenio pagado. Cliente contento. Dejar en seguimiento 1 mes.',
        )
        Nota.objects.create(
            expediente=e9, usuario=asesores[8],
            contenido='Abogado de la parte contraria solicitó prórroga. Pendiente de resolver.',
        )
        Nota.objects.create(
            expediente=e10, usuario=asesores[9],
            contenido='Todo pagado. Expediente cerrado definitivamente.',
        )

        # ─── WhatsApp messages en algunos ──────────────────────────────────
        WhatsAppMessage.objects.create(
            expediente=e4, destino=c4.telefono,
            mensaje='Hola Ana, te recordamos que tu audiencia de conciliación es este viernes a las 10:00 AM. Favor de llegar 15 minutos antes.',
            tipo='recordatorio_audiencia', via='deep_link', estado='enviado',
            enviado_por=asesores[3],
            link_generado='https://wa.me/526642223344?text=Recordatorio%20de%20audiencia',
        )
        WhatsAppMessage.objects.create(
            expediente=e5, destino=c5.telefono,
            mensaje='Hola Luis, felicidades por tu convenio. El pago de $95,000 ya está en proceso. Te avisaremos cuando esté listo.',
            tipo='convenio', via='deep_link', estado='enviado',
            enviado_por=asesores[4],
            link_generado='https://wa.me/526647778800?text=Seguimiento%20de%20convenio',
        )
        WhatsAppMessage.objects.create(
            expediente=e6, destino=c6.telefono,
            mensaje='Hola Gabriela, el patrón no asistió a la audiencia. Vamos a preparar la demanda. Te contacto pronto.',
            tipo='seguimiento', via='deep_link', estado='enviado',
            enviado_por=asesores[5],
            link_generado='https://wa.me/526645551122?text=Seguimiento%20de%20caso',
        )

        # ─── Resumen final ──────────────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS('=' * 55))
        self.stdout.write(self.style.SUCCESS('DATOS DE PRUEBA CARGADOS EXITOSAMENTE'))
        self.stdout.write(self.style.SUCCESS('=' * 55))
        self.stdout.write(f'   Clientes:     {Cliente.objects.count()}')
        self.stdout.write(f'   Expedientes:  {Expediente.objects.count()}')
        self.stdout.write(f'   Solicitudes:  {SolicitudConciliacion.objects.count()}')
        self.stdout.write(f'   Movimientos:  {Movimiento.objects.count()}')
        self.stdout.write(f'   Notas:        {Nota.objects.count()}')
        self.stdout.write(f'   WhatsApp:     {WhatsAppMessage.objects.count()}')
        self.stdout.write(f'   Config Legal: {LegalConfig.objects.count()}')
        self.stdout.write('')
        self.stdout.write('CASOS CREADOS:')
        for e in Expediente.objects.all().select_related('cliente', 'asesor').order_by('created_at'):
            self.stdout.write(f'   {e.numero} | {e.cliente.nombre:<35} | {e.get_estado_display():<20} | {e.asesor.get_full_name()}')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Listo! Inicia sesion y explora los datos.'))

    def _clean_data(self):
        """Elimina todos los datos de prueba."""
        self.stdout.write(self.style.WARNING('Limpiando datos existentes...'))
        WhatsAppMessage.objects.all().delete()
        Nota.objects.all().delete()
        Movimiento.objects.all().delete()
        SolicitudConciliacion.objects.all().delete()
        CalculoLaboral.objects.all().delete()
        Expediente.objects.all().delete()
        Cliente.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('Datos eliminados.'))
