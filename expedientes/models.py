from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError


class Cliente(models.Model):
    GENERO_CHOICES = [
        ('masculino', 'Masculino'),
        ('femenino', 'Femenino'),
    ]

    PERIODO_PAGO_CHOICES = [
        ('diario', 'Diario'),
        ('semanal', 'Semanal'),
        ('quincenal', 'Quincenal'),
        ('mensual', 'Mensual'),
    ]

    JORNADA_CHOICES = [
        ('diurna', 'Diurna'),
        ('nocturna', 'Nocturna'),
        ('mixta', 'Mixta'),
    ]

    TIPO_PERSONA_CHOICES = [
        ('fisica', 'Persona Física'),
        ('moral', 'Persona Moral'),
    ]

    nombre = models.CharField('Nombre completo', max_length=200)
    curp = models.CharField('CURP', max_length=18, unique=True, null=True, blank=True,
                            help_text='Opcional al importar citas CLT; se captura después')
    rfc = models.CharField('RFC', max_length=13, blank=True)
    telefono = models.CharField('Teléfono', max_length=15, null=True, blank=True)
    whatsapp = models.CharField('WhatsApp', max_length=15, blank=True)
    email = models.EmailField('Email', blank=True)

    # Datos personales complementarios (para conciliación)
    fecha_nacimiento = models.DateField('Fecha de nacimiento', null=True, blank=True)
    genero = models.CharField('Género', max_length=10, choices=GENERO_CHOICES, default='masculino')

    # Dirección particular (detallada)
    direccion_calle = models.CharField('Calle', max_length=200, blank=True)
    direccion_numero = models.CharField('Número', max_length=20, blank=True)
    direccion_cp = models.CharField('Código Postal', max_length=10, blank=True)
    direccion_colonia = models.CharField('Colonia / Ejido / Poblado', max_length=200, blank=True)

    # Información laboral
    empresa = models.CharField('Empresa/Patrón', max_length=200, blank=True)
    empresa_actividad = models.CharField('Actividad económica del patrón', max_length=200, blank=True)
    empresa_telefono = models.CharField('Teléfono de la empresa', max_length=15, blank=True)
    empresa_razon_social = models.CharField('Razón social / Nombre comercial', max_length=200, blank=True)
    empresa_calle = models.CharField('Calle (empresa)', max_length=200, blank=True)
    empresa_numero = models.CharField('Número (empresa)', max_length=20, blank=True)
    empresa_colonia = models.CharField('Colonia (empresa)', max_length=200, blank=True)
    empresa_cp = models.CharField('Código Postal (empresa)', max_length=10, blank=True)
    empresa_referencias = models.TextField('Referencias del domicilio', blank=True)

    # Tipo de persona del patrón (para conciliación)
    tipo_persona_citado = models.CharField('Tipo de persona del patrón', max_length=10,
                                            choices=TIPO_PERSONA_CHOICES, default='fisica',
                                            help_text='¿El patrón es persona física o moral?')

    # Datos laborales
    puesto = models.CharField('Puesto', max_length=100, blank=True)
    salario = models.DecimalField('Salario mensual', max_digits=10, decimal_places=2, null=True, blank=True)
    periodo_pago = models.CharField('Periodo de pago', max_length=10, choices=PERIODO_PAGO_CHOICES,
                                     default='mensual', help_text='¿Cada cuándo le pagan?')
    horas_semanales = models.PositiveIntegerField('Horas semanales', null=True, blank=True, default=40,
                                                    help_text='Horas trabajadas por semana')
    jornada = models.CharField('Jornada', max_length=10, choices=JORNADA_CHOICES, default='diurna',
                                help_text='Tipo de jornada laboral')
    fecha_ingreso = models.DateField('Fecha de ingreso', null=True, blank=True)
    fecha_salida = models.DateField('Fecha de salida/despido', null=True, blank=True)

    # Cómo se enteró del despacho
    COMO_SUPO_CHOICES = [
        ('facebook', 'Facebook / Instagram'),
        ('google', 'Google / Internet'),
        ('recomendacion', 'Recomendación'),
        ('whatsapp', 'WhatsApp'),
        ('tiktok', 'TikTok'),
        ('tv_radio', 'Televisión / Radio'),
        ('volante', 'Volante / Folleto'),
        ('otro', 'Otro'),
    ]

    OFICINA_CHOICES = [
        ('plaza_patria', 'Plaza Patria'),
        ('otay', 'Otay'),
        ('clt', 'CLT'),
    ]

    como_supo = models.CharField(
        '¿Cómo supo de nosotros?', max_length=20,
        choices=COMO_SUPO_CHOICES, blank=True,
        help_text='¿Cómo se enteró el cliente de Conciliación Laboral Tijuana?'
    )
    oficina = models.CharField(
        'Oficina que atendió', max_length=30,
        choices=OFICINA_CHOICES,
        help_text='¿Cuál oficina atendió al cliente?'
    )

    # Asesoría gratuita
    asesoria_gratuita_ofrecida = models.BooleanField(
        'Asesoría gratuita ofrecida', default=False,
        help_text='Al cliente se le ofreció la asesoría gratuita semanal'
    )
    asesoria_gratuita_agendada = models.BooleanField(
        'Asesoría agendada', default=False,
        help_text='El cliente agendó una fecha para la asesoría gratuita'
    )
    fecha_asesoria_gratuita = models.DateField(
        'Fecha de asesoría gratuita', null=True, blank=True,
        help_text='Fecha programada para la asesoría gratuita'
    )

    created_by = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Creado por',
        help_text='Asesor que registró al cliente'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['curp']),
            models.Index(fields=['nombre']),
            models.Index(fields=['fecha_asesoria_gratuita']),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.curp})"

    @property
    def direccion_completa(self):
        partes = [self.direccion_calle]
        if self.direccion_numero:
            partes.append(f'#{self.direccion_numero}')
        if self.direccion_colonia:
            partes.append(f'Col. {self.direccion_colonia}')
        if self.direccion_cp:
            partes.append(f'CP {self.direccion_cp}')
        return ', '.join(filter(None, partes))

    def clean(self):
        """Validación: si está agendada, debe tener fecha."""
        super().clean()
        if self.asesoria_gratuita_agendada and not self.fecha_asesoria_gratuita:
            from django.core.exceptions import ValidationError
            raise ValidationError({
                'fecha_asesoria_gratuita': 'Si el cliente agendó la asesoría, debes proporcionar una fecha.'
            })


class Empresa(models.Model):
    """Catálogo de empresas y domicilios.

    Se importa desde 'Empresas y Domicilios.xlsx' (base de datos que va
    creciendo). El nombre se guarda normalizado (mayúsculas, sin acentos,
    espacios compactados) para que la importación sea idempotente al crecer
    el archivo.
    """

    TIPO_PERSONA_CHOICES = [
        ('fisica', 'Persona Física'),
        ('moral', 'Persona Moral'),
    ]

    nombre = models.CharField('Empresa', max_length=200, unique=True,
                               help_text='Nombre normalizado (mayúsculas, sin acentos)')
    domicilio = models.TextField('Domicilio', blank=True,
                                  help_text='Domicilio completo tal como viene en el archivo')
    abogado = models.CharField('Abogado', max_length=200, blank=True,
                                help_text='Abogado/representante de la empresa (opcional)')
    telefono = models.CharField('Teléfono', max_length=30, blank=True)
    tipo_persona = models.CharField('Tipo de persona', max_length=10,
                                     choices=TIPO_PERSONA_CHOICES, default='moral',
                                     help_text='Detectado automáticamente al importar')

    # Domicilio desglosado (para autocompletar el formulario del cliente)
    domicilio_calle = models.CharField('Calle (domicilio)', max_length=200, blank=True)
    domicilio_numero = models.CharField('Número (domicilio)', max_length=20, blank=True)
    domicilio_colonia = models.CharField('Colonia (domicilio)', max_length=200, blank=True)
    domicilio_cp = models.CharField('Código Postal (domicilio)', max_length=10, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Empresa (catálogo)'
        verbose_name_plural = 'Empresas y Domicilios'
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['nombre']),
        ]

    def __str__(self):
        return self.nombre


class Expediente(models.Model):
    ESTADO_CHOICES = [
        ('nuevo', 'Nuevo'),
        ('solicitud', 'Solicitud creada'),
        ('citatorio', 'Citatorio generado'),
        ('audiencia', 'Audiencia programada'),
        ('no_notificado', 'No notificado'),
        ('reprogramacion', 'Reprogramación'),
        ('convenio', 'Convenio'),
        ('sin_conciliacion', 'Sin conciliación'),
        ('demanda', 'Demanda'),
        ('cerrado', 'Cerrado'),
    ]

    TIPO_DESPIDO_CHOICES = [
        ('justificado', 'Despido justificado'),
        ('injustificado', 'Despido injustificado'),
        ('voluntario', 'Renuncia voluntaria'),
        ('rescision', 'Rescisión'),
        ('otro', 'Otro'),
    ]

    RESULTADO_AUDIENCIA_CHOICES = [
        ('no_notificado', 'No notificado'),
        ('convenio', 'Convenio alcanzado'),
        ('sin_conciliacion', 'Sin conciliación'),
        ('inasistencia', 'Inasistencia'),
        ('reprogramada', 'Reprogramada'),
    ]

    # Transiciones permitidas: estado_actual -> [estados_permitidos]
    TRANSICIONES = {
        'nuevo': ['solicitud', 'cerrado'],
        'solicitud': ['citatorio', 'convenio', 'cerrado'],
        'citatorio': ['audiencia', 'convenio', 'cerrado'],
        'audiencia': ['no_notificado', 'convenio', 'sin_conciliacion', 'reprogramacion', 'cerrado'],
        'no_notificado': ['audiencia', 'reprogramacion', 'cerrado'],
        'reprogramacion': ['audiencia', 'convenio', 'sin_conciliacion', 'demanda', 'cerrado'],
        'convenio': ['audiencia', 'demanda', 'cerrado'],
        'sin_conciliacion': ['demanda', 'audiencia', 'cerrado'],
        'demanda': ['audiencia', 'convenio', 'cerrado'],
        'cerrado': ['nuevo'],
    }

    numero = models.CharField('Número de expediente', max_length=20, unique=True, editable=False)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, verbose_name='Cliente')
    asesor = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='Asesor asignado',
                                limit_choices_to={'profile__rol': 'asesor'})
    estado = models.CharField('Estado', max_length=20, choices=ESTADO_CHOICES, default='nuevo')

    # Montos
    monto_reclamado = models.DecimalField('Monto reclamado', max_digits=12, decimal_places=2, null=True, blank=True)
    monto_convenio = models.DecimalField('Monto convenio', max_digits=12, decimal_places=2, null=True, blank=True)

    # Audiencia
    fecha_audiencia = models.DateTimeField('Fecha de audiencia', null=True, blank=True)
    resultado_audiencia = models.CharField('Resultado de audiencia', max_length=20,
                                            choices=RESULTADO_AUDIENCIA_CHOICES, null=True, blank=True)

    # Formulario de conciliación
    tipo_despido = models.CharField('Tipo de despido', max_length=20,
                                     choices=TIPO_DESPIDO_CHOICES, null=True, blank=True)
    prestaciones_reclamadas = models.TextField('Prestaciones reclamadas', blank=True)
    folio = models.CharField('Folio de trámite', max_length=50, blank=True)
    fecha_tramite = models.DateField('Fecha de trámite', null=True, blank=True)

    # Seguimiento
    proxima_accion = models.DateField('Próxima acción', null=True, blank=True)
    notas = models.TextField('Notas internas', blank=True)
    prioridad = models.CharField('Prioridad', max_length=10,
                                  choices=[('baja', 'Baja'), ('media', 'Media'), ('alta', 'Alta')],
                                  default='media')

    # Automatización WhatsApp
    notificar_whatsapp_auto = models.BooleanField(
        'Notificaciones WhatsApp automáticas', default=True,
        help_text='Enviar mensajes automáticos al cliente cuando cambia el estado del expediente'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Expediente'
        verbose_name_plural = 'Expedientes'
        ordering = ['-created_at']
        permissions = [
            ('puede_ver_todos_expedientes', 'Puede ver todos los expedientes'),
        ]
        indexes = [
            models.Index(fields=['numero']),
            models.Index(fields=['estado']),
            models.Index(fields=['asesor']),
        ]

    def __str__(self):
        return f"{self.numero} - {self.cliente.nombre}"

    def clean(self):
        super().clean()
        if self.pk:
            try:
                original = Expediente.objects.get(pk=self.pk)
                if original.estado != self.estado:
                    if self.estado not in self.TRANSICIONES.get(original.estado, []):
                        raise ValidationError({
                            'estado': f'No se puede cambiar de "{self._estado_label(original.estado)}" '
                                      f'a "{self._estado_label(self.estado)}". '
                                      f'Transiciones permitidas: {", ".join(self._estado_label(e) for e in self.TRANSICIONES.get(original.estado, []))}'
                        })
            except Expediente.DoesNotExist:
                pass

    def _estado_label(self, estado_key):
        return dict(self.ESTADO_CHOICES).get(estado_key, estado_key)

    def save(self, *args, **kwargs):
        if not self.numero:
            year = timezone.now().year
            last = Expediente.objects.filter(numero__startswith=f"{year}").order_by('-numero').first()
            if last and '-' in last.numero:
                last_num = int(last.numero.split('-')[1])
                self.numero = f"{year}-{last_num + 1:04d}"
            else:
                self.numero = f"{year}-0001"
        self.full_clean()
        super().save(*args, **kwargs)

    def get_estado_color(self):
        colors = {
            'nuevo': 'blue',
            'solicitud': 'purple',
            'citatorio': 'indigo',
            'audiencia': 'yellow',
            'no_notificado': 'red',
            'reprogramacion': 'orange',
            'convenio': 'green',
            'sin_conciliacion': 'gray',
            'demanda': 'rose',
            'cerrado': 'slate',
        }
        return colors.get(self.estado, 'gray')


class SolicitudConciliacion(models.Model):
    """Formato para iniciar la solicitud de conciliación (Baja California)."""

    PERIODO_PAGO_CHOICES = [
        ('diario', 'Diario'),
        ('semanal', 'Semanal'),
        ('quincenal', 'Quincenal'),
    ]

    CITATORIO_CHOICES = [
        ('solicitante', 'Solicitante'),
        ('notificador', 'El notificador del centro'),
    ]

    OBJETO_CHOICES = [
        ('despido', 'Despido'),
        ('terminacion_voluntaria', 'Terminación voluntaria'),
        ('antiguedad', 'Derecho de antigüedad'),
        ('rescision', 'Rescisión de la relación laboral'),
        ('prestaciones', 'Pago de prestaciones'),
        ('preferencia', 'Derecho de preferencia'),
        ('ascenso', 'Derecho de ascenso'),
        ('acoso', 'Acoso laboral'),
    ]

    DISCAPACIDAD_CHOICES = [
        ('motriz', 'Motriz'),
        ('visual', 'Visual'),
        ('auditiva', 'Auditiva'),
        ('psicosocial', 'Psicosocial-Cognitiva'),
        ('habla', 'Habla o lenguaje'),
    ]

    expediente = models.OneToOneField(Expediente, on_delete=models.CASCADE,
                                        related_name='solicitud', verbose_name='Expediente')

    # Encabezado
    unidad_sede = models.CharField('Unidad Sede', max_length=100, default='Tijuana')
    fecha_solicitud = models.DateField('Fecha de solicitud', null=True, blank=True)

    # Trabajador
    edad = models.PositiveIntegerField('Edad', null=True, blank=True)

    # Empleo
    fecha_conflicto = models.DateField('Fecha del conflicto', null=True, blank=True)
    horas_semanales = models.PositiveIntegerField('Horas semanales trabajadas', null=True, blank=True)
    periodo_pago = models.CharField('Periodo de pago', max_length=15,
                                     choices=PERIODO_PAGO_CHOICES, null=True, blank=True)

    # Objeto de la solicitud (múltiple)
    objeto_despido = models.BooleanField('Despido', default=False)
    objeto_terminacion_voluntaria = models.BooleanField('Terminación voluntaria', default=False)
    objeto_antiguedad = models.BooleanField('Derecho de antigüedad', default=False)
    objeto_rescision = models.BooleanField('Rescisión de la relación laboral', default=False)
    objeto_prestaciones = models.BooleanField('Pago de prestaciones', default=False)
    objeto_preferencia = models.BooleanField('Derecho de preferencia', default=False)
    objeto_ascenso = models.BooleanField('Derecho de ascenso', default=False)
    objeto_acoso = models.BooleanField('Acoso laboral', default=False)

    # Citatorio
    citatorio_entrega = models.CharField('Quién entregará el citatorio', max_length=20,
                                          choices=CITATORIO_CHOICES, default='solicitante')

    # Discapacidad (múltiple)
    discapacidad_motriz = models.BooleanField('Discapacidad motriz', default=False)
    discapacidad_visual = models.BooleanField('Discapacidad visual', default=False)
    discapacidad_auditiva = models.BooleanField('Discapacidad auditiva', default=False)
    discapacidad_psicosocial = models.BooleanField('Discapacidad psicosocial-cognitiva', default=False)
    discapacidad_habla = models.BooleanField('Discapacidad habla o lenguaje', default=False)

    # Traductor
    requiere_traductor = models.BooleanField('Requiere traductor', default=False)
    traductor_lengua = models.CharField('Lengua de origen', max_length=100, blank=True)

    # Firma
    firma_nombre = models.CharField('Nombre del firmante', max_length=200, blank=True)
    firma_fecha = models.DateField('Fecha de firma', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Solicitud de Conciliación'
        verbose_name_plural = 'Solicitudes de Conciliación'

    def __str__(self):
        return f'Solicitud {self.expediente.numero} - {self.expediente.cliente.nombre}'

    def get_objetos_lista(self):
        """Retorna lista de objetos seleccionados."""
        items = []
        for key, label in self.OBJETO_CHOICES:
            field = getattr(self, f'objeto_{key}', False)
            if field:
                items.append(label)
        return items

    def get_discapacidades_lista(self):
        """Retorna lista de discapacidades seleccionadas."""
        items = []
        for key, label in self.DISCAPACIDAD_CHOICES:
            field = getattr(self, f'discapacidad_{key}', False)
            if field:
                items.append(label)
        return items


class Documento(models.Model):
    TIPO_CHOICES = [
        ('ine', 'INE/Identificación'),
        ('contrato', 'Contrato laboral'),
        ('evidencia', 'Evidencia'),
        ('screenshot', 'Screenshot/Captura'),
        ('citatorio', 'Citatorio'),
        ('pdf', 'PDF/Documento'),
        ('otro', 'Otro'),
    ]

    expediente = models.ForeignKey(Expediente, on_delete=models.CASCADE, related_name='documentos',
                                    verbose_name='Expediente')
    archivo = models.FileField('Archivo', upload_to='documentos/%Y/%m/')
    descripcion = models.CharField('Descripción', max_length=200)
    tipo = models.CharField('Tipo', max_length=20, choices=TIPO_CHOICES, default='pdf')
    subido_por = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='Subido por')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Documento'
        verbose_name_plural = 'Documentos'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_tipo_display()}] {self.descripcion}"


class Movimiento(models.Model):
    ACCION_CHOICES = [
        ('creacion', 'Creación'),
        ('cambio_estado', 'Cambio de estado'),
        ('actualizacion', 'Actualización'),
        ('subida_documento', 'Subida de documento'),
        ('nota_agregada', 'Nota agregada'),
        ('resultado_audiencia', 'Resultado de audiencia'),
    ]

    expediente = models.ForeignKey(Expediente, on_delete=models.CASCADE, related_name='movimientos',
                                    verbose_name='Expediente')
    usuario = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='Usuario')
    accion = models.CharField('Acción', max_length=30, choices=ACCION_CHOICES)
    detalle = models.TextField('Detalle', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Movimiento'
        verbose_name_plural = 'Movimientos'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.expediente.numero} - {self.get_accion_display()} - {self.usuario.username}"


class Nota(models.Model):
    expediente = models.ForeignKey(Expediente, on_delete=models.CASCADE, related_name='notas_lista',
                                    verbose_name='Expediente')
    usuario = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='Usuario')
    contenido = models.TextField('Contenido')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Nota'
        verbose_name_plural = 'Notas'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.expediente.numero} - {self.created_at.strftime('%d/%m/%Y %H:%M')}"


from .whatsapp import generar_deep_link as _generar_deep_link


class LegalConfig(models.Model):
    """Configuración legal parametrizable para cálculos laborales.
    
    El administrador modifica estos valores desde el panel de admin
    SIN necesidad de tocar código cuando cambian las leyes.
    """

    # Solo debe existir UNA fila
    nombre = models.CharField('Nombre de la configuración', max_length=100, default='Configuración Legal 2024')
    activo = models.BooleanField('Configuración activa', default=True,
                                  help_text='Solo una configuración puede estar activa a la vez')

    # UMA y Salario Mínimo
    uma_diaria = models.DecimalField('UMA diaria', max_digits=10, decimal_places=2,
                                      default=108.57, help_text='Valor de la UMA diaria (2024: $108.57)')
    salario_minimo = models.DecimalField('Salario mínimo general', max_digits=10, decimal_places=2,
                                          default=248.93, help_text='Salario mínimo general diario (2024: $248.93)')
    salario_minimo_frontera = models.DecimalField('Salario mínimo frontera', max_digits=10, decimal_places=2,
                                                    default=374.89, help_text='Salario mínimo ZLF (2024: $374.89)')

    # Aguinaldo
    aguinaldo_dias = models.PositiveIntegerField('Días de aguinaldo', default=15,
                                                   help_text='Mínimo legal: 15 días')

    # Prima Vacacional
    prima_vacacional_porcentaje = models.DecimalField('% Prima vacacional', max_digits=5, decimal_places=2,
                                                       default=25.00, help_text='Mínimo 25%')

    # Prima de Antigüedad
    prima_antiguedad_dias_por_ano = models.PositiveIntegerField('Días por año (prima antigüedad)', default=12,
                                                                  help_text='Normalmente 12 días por año')
    tope_prima_tipo = models.CharField('Tipo de tope', max_length=20, default='uma',
                                        choices=[
                                            ('uma', '2 × UMA'),
                                            ('salario_minimo', '2 × Salario Mínimo'),
                                            ('frontera', '2 × Salario Mínimo Frontera'),
                                        ],
                                        help_text='Tope salarial para prima de antigüedad')
    tope_prima_multiplo = models.PositiveIntegerField('Múltiplo del tope', default=2,
                                                       help_text='Normalmente 2 × UMA o 2 × SM')

    # Indemnización
    indemnizacion_dias = models.PositiveIntegerField('Días de indemnización', default=90,
                                                      help_text='3 meses = 90 días')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Configuración Legal'
        verbose_name_plural = 'Configuraciones Legales'

    def __str__(self):
        return f'{self.nombre} (UMA: ${self.uma_diaria})'

    def save(self, *args, **kwargs):
        # Si esta es la configuración activa, desactivar las demás
        if self.activo:
            LegalConfig.objects.filter(activo=True).exclude(pk=self.pk).update(activo=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_active(cls):
        """Retorna la configuración legal activa, o la primera creada."""
        config = cls.objects.filter(activo=True).first()
        if not config:
            config = cls.objects.first()
        return config


class CalculoLaboral(models.Model):
    """Resultado de cálculos laborales vinculado a un expediente.
    
    Se recalcula automáticamente si cambian los datos del cliente/expediente.
    El asesor puede seleccionar qué conceptos incluir mediante checkboxes.
    """

    PERIODO_PAGO_CHOICES = [
        ('diario', 'Diario'),
        ('semanal', 'Semanal'),
        ('quincenal', 'Quincenal'),
        ('mensual', 'Mensual'),
    ]

    expediente = models.OneToOneField(Expediente, on_delete=models.CASCADE,
                                        related_name='calculo_laboral', verbose_name='Expediente')

    # Datos usados para el cálculo (copia, para mantener histórico)
    salario_mensual = models.DecimalField('Salario mensual', max_digits=12, decimal_places=2, default=0)
    salario_diario = models.DecimalField('Salario diario calculado', max_digits=12, decimal_places=2, default=0)
    periodo_pago = models.CharField('Periodo de pago', max_length=20, choices=PERIODO_PAGO_CHOICES, default='mensual')
    fecha_ingreso = models.DateField('Fecha de ingreso', null=True, blank=True)
    fecha_salida = models.DateField('Fecha de salida', null=True, blank=True)
    dias_trabajados = models.PositiveIntegerField('Días trabajados', default=0)
    años_trabajados = models.DecimalField('Años trabajados', max_digits=6, decimal_places=4, default=0)

    # ─── Checkboxes de selección de conceptos ───────────────────────
    incluir_aguinaldo = models.BooleanField('Incluir aguinaldo', default=True)
    incluir_vacaciones = models.BooleanField('Incluir vacaciones', default=True)
    incluir_prima_vacacional = models.BooleanField('Incluir prima vacacional', default=True)
    incluir_prima_antiguedad = models.BooleanField('Incluir prima antigüedad', default=True)
    incluir_indemnizacion = models.BooleanField('Incluir indemnización 90 días', default=True)
    incluir_indemnizacion_20dias = models.BooleanField('Incluir 20 días por año', default=False)
    incluir_vacaciones_vencidas = models.BooleanField('Incluir vacaciones vencidas', default=False)
    incluir_horas_extras = models.BooleanField('Incluir horas extras', default=False)
    incluir_salarios_devengados = models.BooleanField('Incluir salarios devengados', default=False)
    incluir_dias_festivos = models.BooleanField('Incluir días festivos', default=False)

    # ─── Resultados existentes ──────────────────────────────────────
    aguinaldo = models.DecimalField('Aguinaldo proporcional', max_digits=12, decimal_places=2, default=0)
    vacaciones = models.DecimalField('Vacaciones proporcionales', max_digits=12, decimal_places=2, default=0)
    dias_vacaciones = models.PositiveIntegerField('Días de vacaciones según antigüedad', default=0)
    dias_vacaciones_override = models.PositiveIntegerField(
        'Días de vacaciones a pagar (manual)', null=True, blank=True,
        help_text='Si el caso no corresponde al total por antigüedad (ej. ya se pagaron o disfrutaron '
                   'algunos años), captura aquí los días realmente adeudados. Vacío = usa la tabla LFT.')
    prima_vacacional = models.DecimalField('Prima vacacional', max_digits=12, decimal_places=2, default=0)
    prima_antiguedad = models.DecimalField('Prima de antigüedad', max_digits=12, decimal_places=2, default=0)
    tope_salarial_aplicado = models.BooleanField('Tope salarial aplicado', default=False)
    indemnizacion = models.DecimalField('Indemnización constitucional (90 días)', max_digits=12, decimal_places=2, default=0)

    # ─── Nuevos resultados ──────────────────────────────────────────
    indemnizacion_20dias = models.DecimalField('Indemnización 20 días por año', max_digits=12, decimal_places=2, default=0)

    # Vacaciones vencidas (input manual de días)
    dias_vacaciones_vencidos = models.PositiveIntegerField('Días de vacaciones vencidas', default=0,
        help_text='Días de vacaciones de años anteriores que no se pagaron')
    vacaciones_vencidas = models.DecimalField('Vacaciones vencidas', max_digits=12, decimal_places=2, default=0)

    # Horas extras (input manual de horas)
    horas_extra_cantidad = models.DecimalField('Cantidad de horas extra', max_digits=8, decimal_places=2, default=0,
        help_text='Número total de horas extra trabajadas')
    horas_extras = models.DecimalField('Horas extras', max_digits=12, decimal_places=2, default=0)

    # Salarios devengados (input manual de monto)
    salarios_devengados = models.DecimalField('Salarios devengados', max_digits=12, decimal_places=2, default=0,
        help_text='Monto de salarios no pagados')

    # Días festivos (input manual de días)
    dias_festivos_cantidad = models.PositiveIntegerField('Cantidad de días festivos', default=0,
        help_text='Número de días festivos laborados no pagados')
    dias_festivos = models.DecimalField('Días festivos', max_digits=12, decimal_places=2, default=0)

    total = models.DecimalField('Total prestaciones', max_digits=12, decimal_places=2, default=0)

    # Metadatos
    recalculado_en = models.DateTimeField('Último recálculo', null=True, blank=True)
    notas = models.TextField('Notas del cálculo', blank=True,
                              help_text='Anotaciones del asesor sobre este cálculo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cálculo Laboral'
        verbose_name_plural = 'Cálculos Laborales'

    def __str__(self):
        return f'Cálculo {self.expediente.numero} - Total: ${self.total}'

    def recalcular(self, guardar=True):
        """Recalcula todas las prestaciones desde los datos guardados.
        
        Útil cuando cambian las reglas legales (UMA, etc.) y se quiere
        actualizar todos los cálculos existentes.
        """
        from .laboral_calculator import recalcular_calculo
        recalcular_calculo(self)
        if guardar:
            self.save()


class SolicitudTransferencia(models.Model):
    """
    Solicitud de transferencia de un expediente de un asesor a otro.
    
    El asesor actual solicita la transferencia (ej: no puede asistir a una audiencia)
    y el área administrativa revisa, reasigna y aprueba.
    """

    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
        ('cancelada', 'Cancelada'),
    ]

    expediente = models.ForeignKey('Expediente', on_delete=models.CASCADE,
                                    related_name='solicitudes_transferencia',
                                    verbose_name='Expediente')
    solicitante = models.ForeignKey(User, on_delete=models.PROTECT,
                                     related_name='transferencias_solicitadas',
                                     verbose_name='Solicitante (asesor actual)')
    asesor_destino = models.ForeignKey(User, on_delete=models.SET_NULL,
                                        null=True, blank=True,
                                        related_name='transferencias_recibidas',
                                        limit_choices_to={'profile__rol': 'asesor'},
                                        verbose_name='Asesor destino (opcional)',
                                        help_text='Puedes sugerir un asesor específico o dejarlo vacío para que administración lo asigne')
    motivo = models.TextField('Motivo de la transferencia',
                               help_text='Explica por qué necesitas transferir el caso (ej: conflicto de horario, audiencia simultánea, etc.)')
    estado = models.CharField('Estado', max_length=15, choices=ESTADO_CHOICES, default='pendiente')

    # Resolución (admin)
    resuelto_por = models.ForeignKey(User, on_delete=models.SET_NULL,
                                      null=True, blank=True,
                                      related_name='transferencias_resueltas',
                                      verbose_name='Resuelto por')
    asesor_asignado = models.ForeignKey(User, on_delete=models.SET_NULL,
                                         null=True, blank=True,
                                         related_name='transferencias_asignadas',
                                         limit_choices_to={'profile__rol': 'asesor'},
                                         verbose_name='Asesor asignado (reasignación)')
    comentario_admin = models.TextField('Comentario del administrador', blank=True,
                                         help_text='Nota del admin al aprobar/rechazar')
    fecha_resolucion = models.DateTimeField('Fecha de resolución', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Solicitud de Transferencia'
        verbose_name_plural = 'Solicitudes de Transferencia'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['estado']),
            models.Index(fields=['expediente', 'estado']),
        ]

    def __str__(self):
        return f"Transferencia {self.expediente.numero} - {self.get_estado_display()}"


class Notificacion(models.Model):
    """
    Notificaciones internas del sistema.
    Se muestran en el icono de campana en el header.
    """

    TIPO_CHOICES = [
        ('transferencia', 'Transferencia'),
        ('aviso', 'Aviso'),
        ('sistema', 'Sistema'),
        ('recordatorio', 'Recordatorio'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE,
                                 related_name='notificaciones',
                                 verbose_name='Usuario')
    titulo = models.CharField('Título', max_length=200)
    mensaje = models.TextField('Mensaje', blank=True)
    tipo = models.CharField('Tipo', max_length=20, choices=TIPO_CHOICES, default='sistema')
    leida = models.BooleanField('Leída', default=False)
    link = models.CharField('Enlace', max_length=500, blank=True,
                             help_text='URL opcional a la que lleva la notificación')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['usuario', 'leida']),
        ]

    def __str__(self):
        return f"[{self.get_tipo_display()}] {self.titulo} - {self.usuario.username}"


class Aviso(models.Model):
    """
    Avisos y pendientes semanales creados por el administrador.
    Se muestran en el dashboard de todos los asesores y administradores.
    """

    PRIORIDAD_CHOICES = [
        ('alta', 'Alta'),
        ('media', 'Media'),
        ('baja', 'Baja'),
    ]

    titulo = models.CharField('Título', max_length=200)
    contenido = models.TextField('Contenido', blank=True,
                                  help_text='Detalles del aviso o pendiente')
    prioridad = models.CharField('Prioridad', max_length=10,
                                  choices=PRIORIDAD_CHOICES, default='media')
    activo = models.BooleanField('Activo', default=True,
                                  help_text='Desmarca para ocultar el aviso')
    fecha_vencimiento = models.DateTimeField(
        'Vence', null=True, blank=True,
        help_text='Opcional. Si se define, el aviso deja de mostrarse automáticamente a partir de esta fecha.'
    )
    leido_por = models.ManyToManyField(
        User, blank=True, related_name='avisos_leidos',
        verbose_name='Leído por',
        help_text='Usuarios que ya marcaron el aviso como leído/entendido'
    )
    creado_por = models.ForeignKey(User, on_delete=models.PROTECT,
                                    verbose_name='Creado por')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Aviso / Pendiente'
        verbose_name_plural = 'Avisos y Pendientes'
        ordering = ['-prioridad', '-created_at']

    def __str__(self):
        return self.titulo


class Machote(models.Model):
    """
    Plantillas reutilizables (machotes) para generación de documentos.
    
    Almacena el contenido HTML de plantillas de demanda, carta finiquito,
    convenio, etc. que los asesores pueden usar como base para nuevos casos.
    Se administran desde el panel de admin.
    """

    CATEGORIA_CHOICES = [
        ('demanda', 'Demanda Laboral'),
        ('carta_finiquito', 'Carta Finiquito'),
        ('convenio', 'Convenio'),
        ('solicitud', 'Solicitud'),
        ('citatorio', 'Citatorio'),
        ('otro', 'Otro'),
    ]

    JURISDICCION_CHOICES = [
        ('federal', 'Federal'),
        ('estatal', 'Estatal (Baja California)'),
        ('ambas', 'Ambas'),
    ]

    nombre = models.CharField('Nombre del machote', max_length=200)
    descripcion = models.TextField('Descripción', blank=True,
                                    help_text='Breve descripción de cuándo usar esta plantilla')
    categoria = models.CharField('Categoría', max_length=30, choices=CATEGORIA_CHOICES, default='demanda')
    tipo_despido = models.CharField('Tipo de despido', max_length=20,
                                     choices=Expediente.TIPO_DESPIDO_CHOICES,
                                     null=True, blank=True,
                                     help_text='Solo para demandas: el tipo de despido al que aplica')
    jurisdiccion = models.CharField('Jurisdicción', max_length=20,
                                     choices=JURISDICCION_CHOICES, default='federal')
    contenido_html = models.TextField('Contenido HTML',
                                       help_text='HTML de la plantilla. Usa marcadores como {{ nombre }}, {{ empresa }}, etc.')
    icono = models.CharField('Icono', max_length=10, default='📄',
                              help_text='Emoji o icono para mostrar en la UI')
    activo = models.BooleanField('Activo', default=True)
    favorito = models.BooleanField('Favorito', default=False,
                                    help_text='Los machotes favoritos aparecen primero en el editor')
    orden = models.PositiveIntegerField('Orden', default=0,
                                         help_text='Orden de aparición en el selector')

    # Metadata
    archivo_origen = models.CharField('Archivo de origen', max_length=255, blank=True,
                                       help_text='Nombre del archivo .docx del que se importó')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Machote'
        verbose_name_plural = 'Machotes'
        ordering = ['categoria', 'orden', 'nombre']

    def __str__(self):
        return f'{self.icono} {self.nombre}'

    def get_marcadores_disponibles(self) -> list:
        """
        Retorna la lista de marcadores disponibles para este machote.
        Útil para mostrar al usuario qué datos puede personalizar.
        """
        import re
        return re.findall(r'\{\{\s*(\w+)\s*\}\}', self.contenido_html)


class TareaConciliacion(models.Model):
    """
    Rastrea el estado de las tareas de conciliación automática asíncronas.
    
    Cuando el usuario inicia el envío automático al portal de conciliación,
    se crea un registro aquí y la tarea se ejecuta en un hilo separado
    para evitar timeouts de HTTP/Gunicorn.
    """

    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('ejecutando', 'Ejecutando'),
        ('completado', 'Completado'),
        ('fallido', 'Fallido'),
    ]

    expediente = models.ForeignKey(
        'Expediente', on_delete=models.CASCADE,
        related_name='tareas_conciliacion',
        verbose_name='Expediente'
    )
    usuario = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Iniciada por'
    )
    estado = models.CharField(
        'Estado', max_length=15,
        choices=ESTADO_CHOICES, default='pendiente'
    )
    folio = models.CharField('Folio generado', max_length=50, blank=True)
    pdf_path = models.CharField('Ruta del PDF', max_length=500, blank=True)
    error = models.TextField('Error', blank=True)
    detalle = models.TextField('Detalle', blank=True)
    screenshots_json = models.TextField('Capturas (JSON)', blank=True,
                                         help_text='Lista de rutas de screenshots en formato JSON')
    modo = models.CharField('Modo', max_length=15, default='automatico',
                             choices=[('automatico', 'Automático (Headless)'),
                                      ('debug', 'Visible (Debug)'),
                                      ('extension', 'Extensión de Chrome')])
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField('Completada en', null=True, blank=True)

    class Meta:
        verbose_name = 'Tarea de Conciliación'
        verbose_name_plural = 'Tareas de Conciliación'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['estado']),
            models.Index(fields=['expediente', 'estado']),
        ]

    def __str__(self):
        return f'Tarea {self.pk} - {self.expediente.numero} ({self.get_estado_display()})'

    def tiempo_transcurrido(self):
        """Retorna el tiempo transcurrido desde la creación."""
        if not self.created_at:
            return '—'
        delta = (self.completed_at or timezone.now()) - self.created_at
        total_segundos = int(delta.total_seconds())
        if total_segundos < 60:
            return f'{total_segundos}s'
        return f'{total_segundos // 60}m {total_segundos % 60}s'


class WhatsAppMessage(models.Model):
    TIPO_CHOICES = [
        ('recordatorio_audiencia', 'Recordatorio de Audiencia'),
        ('citatorio', 'Citatorio'),
        ('convenio', 'Seguimiento de Convenio'),
        ('seguimiento', 'Seguimiento'),
        ('documentos', 'Solicitud de Documentos'),
        ('personalizado', 'Mensaje Personalizado'),
    ]

    VIA_CHOICES = [
        ('deep_link', 'Enlace wa.me'),
        ('twilio', 'API Twilio'),
    ]

    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('enviado', 'Enviado'),
        ('fallido', 'Fallido'),
    ]

    expediente = models.ForeignKey(Expediente, on_delete=models.CASCADE,
                                    related_name='whatsapp_mensajes', verbose_name='Expediente')
    destino = models.CharField('Número destino', max_length=20,
                                help_text='Número con código de país, ej: +526641234567')
    mensaje = models.TextField('Mensaje')
    tipo = models.CharField('Tipo', max_length=30, choices=TIPO_CHOICES, default='personalizado')
    via = models.CharField('Enviado vía', max_length=15, choices=VIA_CHOICES, default='deep_link')
    estado = models.CharField('Estado', max_length=15, choices=ESTADO_CHOICES, default='pendiente')
    enviado_por = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='Enviado por')
    link_generado = models.TextField('Link generado', blank=True,
                                      help_text='Link wa.me generado para el mensaje')
    error_log = models.TextField('Registro de error', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Mensaje WhatsApp'
        verbose_name_plural = 'Mensajes WhatsApp'
        ordering = ['-created_at']

    def __str__(self):
        return f"WA {self.expediente.numero} - {self.get_tipo_display()} ({self.get_estado_display()})"

    @property
    def destinatario_nombre(self):
        return self.expediente.cliente.nombre

    @staticmethod
    def generar_deep_link(telefono, mensaje):
        """Genera un link wa.me con mensaje pre-llenado."""
        return _generar_deep_link(telefono, mensaje)
