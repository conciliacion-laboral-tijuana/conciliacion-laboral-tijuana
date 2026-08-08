from datetime import timedelta

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from expedientes.models import Cliente, Expediente


class Office(models.Model):
    """
    Catálogo de oficinas / sucursales del despacho.
    
    Cada oficina tiene su propia operación y puede tener
    su propio registro de ingresos, gastos y caja diaria.
    """

    nombre = models.CharField('Nombre de la oficina', max_length=200, unique=True)
    direccion = models.TextField('Dirección', blank=True,
                                  help_text='Dirección completa de la oficina')
    telefono = models.CharField('Teléfono', max_length=15, blank=True)
    responsable = models.CharField('Responsable', max_length=200, blank=True,
                                    help_text='Nombre del encargado de la oficina')
    activa = models.BooleanField('¿Oficina activa?', default=True,
                                  help_text='Desmarca para desactivar la oficina sin eliminarla')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Oficina'
        verbose_name_plural = 'Oficinas'
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['activa']),
        ]

    def __str__(self):
        return self.nombre


class SettlementPayment(models.Model):
    """
    Registro de pagos recibidos por convenios.
    
    Cada vez que un cliente paga un acuerdo (convenio), se registra aquí
    el ingreso con su forma de pago y oficina correspondiente.
    """

    FORMA_PAGO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia bancaria'),
        ('cheque', 'Cheque'),
        ('tarjeta_credito', 'Tarjeta de crédito'),
        ('tarjeta_debito', 'Tarjeta de débito'),
        ('deposito', 'Depósito'),
        ('otro', 'Otro'),
    ]

    fecha = models.DateField('Fecha de pago')
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT,
                                 verbose_name='Cliente')
    expediente = models.ForeignKey(Expediente, on_delete=models.PROTECT,
                                    verbose_name='Expediente',
                                    help_text='Expediente relacionado al pago')
    monto = models.DecimalField('Monto', max_digits=12, decimal_places=2)
    forma_pago = models.CharField('Forma de pago', max_length=20,
                                   choices=FORMA_PAGO_CHOICES, default='efectivo')
    oficina = models.ForeignKey('Office', on_delete=models.PROTECT,
                                 verbose_name='Oficina',
                                 help_text='Oficina que recibe el pago')
    notas = models.TextField('Notas', blank=True,
                              help_text='Notas adicionales sobre el pago')

    # Auditoría
    registrado_por = models.ForeignKey(User, on_delete=models.PROTECT,
                                       verbose_name='Registrado por',
                                       related_name='pagos_registrados')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Pago de Convenio'
        verbose_name_plural = 'Pagos de Convenios'
        ordering = ['-fecha', '-created_at']
        indexes = [
            models.Index(fields=['fecha']),
            models.Index(fields=['forma_pago']),
            models.Index(fields=['oficina', 'fecha']),
        ]

    def __str__(self):
        return f"${self.monto:,.2f} - {self.cliente.nombre} ({self.fecha})"


class Expense(models.Model):
    """
    Registro de gastos operativos por oficina.
    
    Cada gasto se clasifica por categoría y se asocia a una oficina
    para poder calcular la utilidad real por sucursal.
    """

    CATEGORIA_CHOICES = [
        ('renta', 'Renta'),
        ('luz', 'Luz'),
        ('agua', 'Agua'),
        ('internet', 'Internet'),
        ('telefono', 'Teléfono'),
        ('papeleria', 'Papelería'),
        ('publicidad', 'Publicidad'),
        ('sueldos', 'Sueldos'),
        ('gasolina', 'Gasolina'),
        ('mantenimiento', 'Mantenimiento'),
        ('impuestos', 'Impuestos'),
        ('equipo', 'Equipo/Cómputo'),
        ('muebles', 'Muebles'),
        ('seguros', 'Seguros'),
        ('honorarios', 'Honorarios profesionales'),
        ('otro', 'Otro'),
    ]

    fecha = models.DateField('Fecha del gasto')
    categoria = models.CharField('Categoría', max_length=20,
                                  choices=CATEGORIA_CHOICES, default='otro')
    monto = models.DecimalField('Monto', max_digits=12, decimal_places=2)
    descripcion = models.TextField('Descripción', blank=True,
                                    help_text='Descripción o detalle del gasto')
    proveedor = models.CharField('Proveedor', max_length=200, blank=True,
                                  help_text='Nombre del proveedor o beneficiario')
    folio_fiscal = models.CharField('Folio fiscal / Factura', max_length=100, blank=True,
                                     help_text='Número de factura o comprobante')
    oficina = models.ForeignKey('Office', on_delete=models.PROTECT,
                                 verbose_name='Oficina',
                                 help_text='Oficina a la que pertenece el gasto')

    # Auditoría
    registrado_por = models.ForeignKey(User, on_delete=models.PROTECT,
                                       verbose_name='Registrado por',
                                       related_name='gastos_registrados')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Gasto Operativo'
        verbose_name_plural = 'Gastos Operativos'
        ordering = ['-fecha', '-created_at']
        indexes = [
            models.Index(fields=['fecha']),
            models.Index(fields=['categoria']),
            models.Index(fields=['oficina', 'fecha']),
        ]

    def __str__(self):
        return f"{self.get_categoria_display()} - ${self.monto:,.2f} ({self.fecha})"


class Commission(models.Model):
    """
    Comisiones de asesores sobre convenios cerrados.
    
    Cuando un asesor cierra un convenio, se le asigna un porcentaje
    como comisión. Este modelo registra cada comisión generada,
    su estado de pago y el cálculo automático del monto.
    """

    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('pagada', 'Pagada'),
        ('cancelada', 'Cancelada'),
    ]

    expediente = models.ForeignKey(Expediente, on_delete=models.PROTECT,
                                    verbose_name='Expediente',
                                    help_text='Expediente del convenio que generó la comisión')
    asesor = models.ForeignKey(User, on_delete=models.PROTECT,
                                verbose_name='Asesor',
                                limit_choices_to={'profile__rol': 'asesor'},
                                related_name='comisiones',
                                help_text='Asesor que recibe la comisión')
    fecha = models.DateField('Fecha')
    monto_convenio = models.DecimalField('Monto del convenio', max_digits=12, decimal_places=2,
                                          help_text='Monto total del convenio cerrado')
    porcentaje = models.DecimalField('Porcentaje de comisión', max_digits=5, decimal_places=2,
                                      help_text='Ej: 5.00 = 5%', default=5.00)
    monto_comision = models.DecimalField('Monto de comisión', max_digits=12, decimal_places=2,
                                          help_text='Calculado automáticamente')
    estado = models.CharField('Estado', max_length=15, choices=ESTADO_CHOICES, default='pendiente')
    fecha_pago = models.DateField('Fecha de pago', null=True, blank=True)
    oficina = models.ForeignKey('Office', on_delete=models.PROTECT,
                                 verbose_name='Oficina',
                                 help_text='Oficina del asesor')
    notas = models.TextField('Notas', blank=True)

    # Auditoría
    registrado_por = models.ForeignKey(User, on_delete=models.PROTECT,
                                       verbose_name='Registrado por',
                                       related_name='comisiones_registradas')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Comisión'
        verbose_name_plural = 'Comisiones'
        ordering = ['-fecha', '-created_at']
        indexes = [
            models.Index(fields=['fecha']),
            models.Index(fields=['estado']),
            models.Index(fields=['asesor', 'estado']),
            models.Index(fields=['oficina', 'fecha']),
        ]

    def __str__(self):
        return f"{self.asesor.get_full_name() or self.asesor.username} - ${self.monto_comision:,.2f} ({self.get_estado_display()})"

    def save(self, *args, **kwargs):
        # Calcular automáticamente el monto de comisión
        self.monto_comision = self.monto_convenio * self.porcentaje / 100
        super().save(*args, **kwargs)


class Agreement(models.Model):
    """
    Convenio del despacho con un cliente.
    
    Registra los acuerdos (convenios) cerrados con clientes,
    incluyendo el monto, honorarios generados y seguimiento de pago.
    """

    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente de firma'),
        ('firmado', 'Firmado'),
        ('pagado', 'Pagado'),
        ('parcial', 'Pagado parcialmente'),
        ('cancelado', 'Cancelado'),
    ]

    cliente = models.ForeignKey(
        'expedientes.Cliente', on_delete=models.PROTECT,
        verbose_name='Cliente',
        help_text='Cliente con quien se firma el convenio'
    )
    empresa = models.CharField(
        'Empresa o contraparte', max_length=200, blank=True,
        help_text='Nombre de la empresa o persona con quien se firma el convenio'
    )
    oficina = models.ForeignKey(
        'Office', on_delete=models.PROTECT,
        verbose_name='Oficina',
        help_text='Oficina responsable del convenio'
    )
    fecha = models.DateField('Fecha del convenio')
    monto_convenio = models.DecimalField(
        'Monto del convenio', max_digits=12, decimal_places=2,
        help_text='Monto total acordado en el convenio'
    )
    honorarios = models.DecimalField(
        'Honorarios totales', max_digits=12, decimal_places=2,
        default=0,
        help_text='Suma total de honorarios generados (se calcula automáticamente al guardar)'
    )
    estado = models.CharField(
        'Estado', max_length=15,
        choices=ESTADO_CHOICES, default='pendiente'
    )
    responsable = models.ForeignKey(
        User, on_delete=models.PROTECT,
        verbose_name='Responsable',
        related_name='convenios_responsable',
        help_text='Abogado o asesor responsable del convenio'
    )
    notas = models.TextField('Notas / Observaciones', blank=True)

    # Auditoría
    creado_por = models.ForeignKey(
        User, on_delete=models.PROTECT,
        verbose_name='Creado por',
        related_name='convenios_creados'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Convenio'
        verbose_name_plural = 'Convenios'
        ordering = ['-fecha', '-created_at']
        indexes = [
            models.Index(fields=['fecha']),
            models.Index(fields=['estado']),
            models.Index(fields=['oficina', 'fecha']),
            models.Index(fields=['responsable', 'estado']),
        ]

    def __str__(self):
        return f'Convenio {self.cliente.nombre} - ${self.monto_convenio:,.2f} ({self.get_estado_display()})'

    def save(self, *args, **kwargs):
        # Recalcular honorarios totales a partir de los honorarios relacionados
        is_new = not self.pk
        super().save(*args, **kwargs)  # Guardar primero para tener PK
        if not is_new:
            # Actualizar la suma de honorarios
            total = self.honorario_set.aggregate(t=models.Sum('monto_calculado'))['t'] or 0
            if self.honorarios != total:
                Agreement.objects.filter(pk=self.pk).update(honorarios=total)

    @property
    def honorarios_pendientes(self):
        """Honorarios aún no pagados."""
        total = self.honorario_set.filter(estado='pendiente').aggregate(
            t=models.Sum('monto_calculado')
        )['t'] or 0
        return total

    @property
    def honorarios_pagados(self):
        """Honorarios ya pagados."""
        total = self.honorario_set.filter(estado='pagado').aggregate(
            t=models.Sum('monto_calculado')
        )['t'] or 0
        return total


class Honorario(models.Model):
    """
    Honorario generado por un convenio.
    
    Cada convenio puede generar uno o varios honorarios con diferentes
    porcentajes. El sistema calcula automáticamente el monto basado
    en el porcentaje configurado y el monto del convenio.
    """

    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('pagado', 'Pagado'),
        ('cancelado', 'Cancelado'),
    ]

    PORCENTAJE_CHOICES = [
        (30.00, '30% (Tarifa general)'),
        (35.00, '35% (Tarifa especial)'),
        (40.00, '40% (Tarifa preferente)'),
        (25.00, '25% (Tarifa reducida)'),
        (50.00, '50% (Tarifa alta)'),
    ]

    convenio = models.ForeignKey(
        'Agreement', on_delete=models.CASCADE,
        verbose_name='Convenio',
        related_name='honorario_set'
    )
    porcentaje = models.DecimalField(
        'Porcentaje', max_digits=5, decimal_places=2,
        choices=PORCENTAJE_CHOICES, default=30.00,
        help_text='Porcentaje de honorarios sobre el monto del convenio'
    )
    monto_calculado = models.DecimalField(
        'Monto calculado', max_digits=12, decimal_places=2,
        editable=False,
        help_text='Calculado automáticamente: monto_del_convenio × porcentaje ÷ 100'
    )
    fecha_estimada = models.DateField(
        'Fecha estimada de pago', null=True, blank=True
    )
    fecha_pagado = models.DateField(
        'Fecha de pago', null=True, blank=True
    )
    estado = models.CharField(
        'Estado', max_length=15,
        choices=ESTADO_CHOICES, default='pendiente'
    )
    notas = models.TextField('Notas', blank=True)

    # Auditoría
    registrado_por = models.ForeignKey(
        User, on_delete=models.PROTECT,
        verbose_name='Registrado por',
        related_name='honorarios_registrados'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Honorario'
        verbose_name_plural = 'Honorarios'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['estado']),
            models.Index(fields=['convenio', 'estado']),
        ]

    def __str__(self):
        return f'{self.convenio.cliente.nombre} - {self.porcentaje}% = ${self.monto_calculado:,.2f}'

    def save(self, *args, **kwargs):
        # Calcular automáticamente el monto
        self.monto_calculado = self.convenio.monto_convenio * self.porcentaje / 100
        super().save(*args, **kwargs)
        # Actualizar el total de honorarios en el convenio
        total = self.convenio.honorario_set.aggregate(t=models.Sum('monto_calculado'))['t'] or 0
        Agreement.objects.filter(pk=self.convenio.pk).update(honorarios=total)


class Employee(models.Model):
    """
    Catálogo de empleados del despacho.
    
    Incluye tanto al personal administrativo como a los asesores
    que reciben un salario base (nómina).
    """

    PUESTO_CHOICES = [
        ('administrativo', 'Administrativo'),
        ('asesor', 'Asesor jurídico'),
        ('supervisor', 'Supervisor jurídico'),
        ('contador', 'Contador'),
        ('recepcionista', 'Recepcionista'),
        ('auxiliar', 'Auxiliar'),
        ('director', 'Director'),
        ('otro', 'Otro'),
    ]

    PERIODO_PAGO_CHOICES = [
        ('semanal', 'Semanal'),
        ('quincenal', 'Quincenal'),
        ('mensual', 'Mensual'),
    ]

    nombre = models.CharField('Nombre completo', max_length=200)
    puesto = models.CharField('Puesto', max_length=30, choices=PUESTO_CHOICES, default='administrativo')
    periodo_pago = models.CharField('Periodo de pago', max_length=15,
                                     choices=PERIODO_PAGO_CHOICES, default='quincenal')
    salario = models.DecimalField('Salario', max_digits=10, decimal_places=2,
                                   help_text='Salario base del empleado')
    telefono = models.CharField('Teléfono', max_length=15, blank=True)
    email = models.EmailField('Email', blank=True)
    oficina = models.ForeignKey('Office', on_delete=models.PROTECT,
                                 verbose_name='Oficina',
                                 help_text='Oficina a la que está asignado')
    activo = models.BooleanField('¿Activo?', default=True,
                                  help_text='Desmarca cuando el empleado ya no trabaje aquí')
    notas = models.TextField('Notas', blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Empleado'
        verbose_name_plural = 'Empleados'
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['activo']),
            models.Index(fields=['oficina', 'activo']),
        ]

    def __str__(self):
        return f"{self.nombre} - {self.get_puesto_display()}"


class Payroll(models.Model):
    """
    Registro de pagos de nómina por período.
    
    Cada vez que se le paga a un empleado, se registra aquí
    el detalle del pago: período, monto pagado y oficina.
    """

    PERIODO_CHOICES = [
        ('semanal', 'Semanal'),
        ('quincenal', 'Quincenal'),
        ('mensual', 'Mensual'),
        ('extraordinario', 'Extraordinario'),
        ('aguinaldo', 'Aguinaldo'),
        ('prima_vacacional', 'Prima vacacional'),
        ('bono', 'Bono'),
    ]

    empleado = models.ForeignKey('Employee', on_delete=models.PROTECT,
                                  verbose_name='Empleado',
                                  related_name='pagos_nomina')
    fecha_pago = models.DateField('Fecha de pago')
    periodo = models.CharField('Período', max_length=20,
                                choices=PERIODO_CHOICES, default='quincenal')
    periodo_inicio = models.DateField('Inicio del período', null=True, blank=True,
                                       help_text='Inicio del período que cubre este pago')
    periodo_fin = models.DateField('Fin del período', null=True, blank=True,
                                    help_text='Fin del período que cubre este pago')
    salario_pagado = models.DecimalField('Salario pagado', max_digits=10, decimal_places=2,
                                          help_text='Monto pagado en este período')
    descuentos = models.DecimalField('Descuentos', max_digits=10, decimal_places=2,
                                      default=0, help_text='Descuentos aplicados (ISR, IMSS, etc.)')
    total_pagado = models.DecimalField('Total pagado', max_digits=10, decimal_places=2,
                                        help_text='Salario pagado - descuentos. Calculado automáticamente')
    oficina = models.ForeignKey('Office', on_delete=models.PROTECT,
                                 verbose_name='Oficina',
                                 help_text='Oficina que realiza el pago')
    notas = models.TextField('Notas', blank=True)

    # Auditoría
    registrado_por = models.ForeignKey(User, on_delete=models.PROTECT,
                                       verbose_name='Registrado por',
                                       related_name='nominas_registradas')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Pago de Nómina'
        verbose_name_plural = 'Pagos de Nómina'
        ordering = ['-fecha_pago', '-created_at']
        indexes = [
            models.Index(fields=['fecha_pago']),
            models.Index(fields=['empleado', 'fecha_pago']),
            models.Index(fields=['oficina', 'fecha_pago']),
            models.Index(fields=['periodo']),
        ]

    def __str__(self):
        return f"{self.empleado.nombre} - ${self.total_pagado:,.2f} ({self.fecha_pago})"

    def save(self, *args, **kwargs):
        # Calcular total automáticamente
        self.total_pagado = self.salario_pagado - self.descuentos
        super().save(*args, **kwargs)


class CashMovement(models.Model):
    """
    Registro de caja diaria por oficina.
    
    Controla las entradas y salidas de efectivo del día a día.
    El saldo se calcula dinámicamente sumando ingresos y restando egresos
    agrupados por oficina y fecha.
    """

    TIPO_CHOICES = [
        ('ingreso', 'Ingreso'),
        ('egreso', 'Egreso'),
    ]

    CATEGORIA_INGRESO_CHOICES = [
        ('convenio', 'Pago de convenio'),
        ('cliente', 'Pago de cliente'),
        ('anticipo', 'Anticipo'),
        ('devolucion', 'Devolución'),
        ('otro_ingreso', 'Otro ingreso'),
    ]

    CATEGORIA_EGRESO_CHOICES = [
        ('papeleria', 'Papelería'),
        ('gasolina', 'Gasolina'),
        ('renta', 'Renta'),
        ('luz', 'Luz'),
        ('agua', 'Agua'),
        ('internet', 'Internet'),
        ('telefono', 'Teléfono'),
        ('viaticos', 'Viáticos'),
        ('comisiones', 'Comisiones'),
        ('honorarios', 'Honorarios'),
        ('otro_egreso', 'Otro egreso'),
    ]

    CATEGORIA_CHOICES = CATEGORIA_INGRESO_CHOICES + CATEGORIA_EGRESO_CHOICES

    oficina = models.ForeignKey('Office', on_delete=models.PROTECT,
                                 verbose_name='Oficina',
                                 help_text='Oficina donde se registra el movimiento')
    fecha = models.DateField('Fecha')
    tipo = models.CharField('Tipo', max_length=10, choices=TIPO_CHOICES)
    categoria = models.CharField('Categoría', max_length=20, choices=CATEGORIA_CHOICES)
    monto = models.DecimalField('Monto', max_digits=12, decimal_places=2)
    descripcion = models.TextField('Descripción', blank=True,
                                    help_text='Detalle del movimiento')
    referencia = models.CharField('Referencia', max_length=200, blank=True,
                                   help_text='Número de expediente, factura o nota relacionada')

    # Auditoría
    registrado_por = models.ForeignKey(User, on_delete=models.PROTECT,
                                       verbose_name='Registrado por',
                                       related_name='caja_registrada')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Movimiento de Caja'
        verbose_name_plural = 'Movimientos de Caja'
        ordering = ['-fecha', '-created_at']
        indexes = [
            models.Index(fields=['fecha']),
            models.Index(fields=['tipo']),
            models.Index(fields=['categoria']),
            models.Index(fields=['oficina', 'fecha', 'tipo']),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} {self.get_categoria_display()} - ${self.monto:,.2f} ({self.oficina.nombre})"

    def clean(self):
        """
        Valida que la categoría sea coherente con el tipo (ingreso/egreso).
        """
        from django.core.exceptions import ValidationError
        super().clean()
        cat_ingreso_keys = [c[0] for c in self.CATEGORIA_INGRESO_CHOICES]
        if self.tipo == 'ingreso' and self.categoria not in cat_ingreso_keys:
            raise ValidationError({
                'categoria': 'La categoría seleccionada no corresponde a un ingreso.'
            })
        if self.tipo == 'egreso' and self.categoria in cat_ingreso_keys:
            raise ValidationError({
                'categoria': 'La categoría seleccionada no corresponde a un egreso.'
            })


class Partner(models.Model):
    """
    Socios del despacho con participación en utilidades.
    
    Cada socio tiene un porcentaje de participación configurable
    que se usa para distribuir automáticamente las utilidades.
    """

    nombre = models.CharField('Nombre completo', max_length=200)
    porcentaje_participacion = models.DecimalField(
        '% de participación', max_digits=5, decimal_places=2,
        default=25.00,
        help_text='Porcentaje de utilidades que le corresponde (ej: 25.00 = 25%%)'
    )
    telefono = models.CharField('Teléfono', max_length=15, blank=True)
    email = models.EmailField('Email', blank=True)
    activo = models.BooleanField('¿Activo?', default=True,
                                  help_text='Desmarca para desactivar sin eliminar')
    notas = models.TextField('Notas', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Socio'
        verbose_name_plural = 'Socios'
        ordering = ['nombre']

    def __str__(self):
        return f'{self.nombre} ({self.porcentaje_participacion}%)'

    @property
    def prestamos_como_origen(self):
        """Préstamos que este socio ha otorgado."""
        return self.prestamos_origen.filter(estado='pendiente')

    @property
    def prestamos_como_destino(self):
        """Préstamos que este socio ha recibido."""
        return self.prestamos_destino.filter(estado='pendiente')

    @property
    def saldo_prestamos_otorgados(self):
        """Total de préstamos otorgados (pendientes)."""
        total = self.prestamos_origen.filter(estado='pendiente').aggregate(
            t=models.Sum('monto')
        )['t'] or 0
        return total

    @property
    def saldo_prestamos_recibidos(self):
        """Total de préstamos recibidos (pendientes)."""
        total = self.prestamos_destino.filter(estado='pendiente').aggregate(
            t=models.Sum('monto')
        )['t'] or 0
        return total

    @property
    def saldo_neto(self):
        """Saldo neto: otorgados - recibidos."""
        return self.saldo_prestamos_otorgados - self.saldo_prestamos_recibidos


class WorkWeek(models.Model):
    """
    Semana de trabajo del despacho.
    
    El sistema gira alrededor de semanas. Cada movimiento (gasto, ingreso,
    nómina, etc.) pertenece a una semana para facilitar reportes semanales.
    """

    ESTADO_CHOICES = [
        ('abierta', 'Abierta'),
        ('cerrada', 'Cerrada'),
    ]

    numero = models.PositiveIntegerField('Número de semana',
                                          help_text='Número de semana del año (1-52)')
    fecha_inicio = models.DateField('Fecha de inicio')
    fecha_fin = models.DateField('Fecha de fin')
    estado = models.CharField('Estado', max_length=10,
                               choices=ESTADO_CHOICES, default='abierta')
    notas = models.TextField('Notas', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Semana de Trabajo'
        verbose_name_plural = 'Semanas de Trabajo'
        ordering = ['-fecha_inicio']
        unique_together = ['numero', 'fecha_inicio']
        indexes = [
            models.Index(fields=['fecha_inicio', 'fecha_fin']),
            models.Index(fields=['estado']),
        ]

    def __str__(self):
        inicio = self.fecha_inicio.strftime('%d %b')
        fin = self.fecha_fin.strftime('%d %b')
        return f'Semana {self.numero} ({inicio} - {fin})'

    @classmethod
    def semana_actual(cls):
        """Retorna la semana activa más reciente, o crea una nueva."""
        hoy = timezone.now().date()
        semana = cls.objects.filter(
            fecha_inicio__lte=hoy, fecha_fin__gte=hoy
        ).first()
        if not semana:
            # Calcular inicio y fin de la semana actual (lunes a domingo)
            inicio = hoy - timedelta(days=hoy.weekday())
            fin = inicio + timedelta(days=6)
            numero = hoy.isocalendar()[1]
            semana, _ = cls.objects.get_or_create(
                numero=numero,
                fecha_inicio=inicio,
                defaults={'fecha_fin': fin, 'estado': 'abierta'}
            )
        return semana

    @property
    def total_ingresos(self):
        from django.db.models import Sum
        from .models import CashMovement, SettlementPayment
        caja = CashMovement.objects.filter(
            fecha__gte=self.fecha_inicio, fecha__lte=self.fecha_fin, tipo='ingreso'
        ).aggregate(t=Sum('monto'))['t'] or 0
        pagos = SettlementPayment.objects.filter(
            fecha__gte=self.fecha_inicio, fecha__lte=self.fecha_fin
        ).aggregate(t=Sum('monto'))['t'] or 0
        return caja + pagos

    @property
    def total_gastos(self):
        from django.db.models import Sum
        from .models import CashMovement, Expense, Payroll
        caja = CashMovement.objects.filter(
            fecha__gte=self.fecha_inicio, fecha__lte=self.fecha_fin, tipo='egreso'
        ).aggregate(t=Sum('monto'))['t'] or 0
        gastos = Expense.objects.filter(
            fecha__gte=self.fecha_inicio, fecha__lte=self.fecha_fin
        ).aggregate(t=Sum('monto'))['t'] or 0
        nomina = Payroll.objects.filter(
            fecha_pago__gte=self.fecha_inicio, fecha_pago__lte=self.fecha_fin
        ).aggregate(t=Sum('total_pagado'))['t'] or 0
        return caja + gastos + nomina

    @property
    def balance(self):
        return self.total_ingresos - self.total_gastos


class PartnerLoan(models.Model):
    """
    Préstamos entre socios del despacho.
    
    Reemplaza las notas manuales como "Le debo a Hans..."
    por un registro formal con saldo pendiente.
    """

    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('pagado', 'Pagado'),
        ('cancelado', 'Cancelado'),
    ]

    socio_origen = models.ForeignKey(
        'Partner', on_delete=models.PROTECT,
        related_name='prestamos_origen',
        verbose_name='Socio que presta (origen)'
    )
    socio_destino = models.ForeignKey(
        'Partner', on_delete=models.PROTECT,
        related_name='prestamos_destino',
        verbose_name='Socio que recibe (destino)'
    )
    monto = models.DecimalField('Monto', max_digits=12, decimal_places=2)
    fecha = models.DateField('Fecha')
    concepto = models.CharField('Concepto', max_length=200,
                                 help_text='Breve descripción del préstamo')
    estado = models.CharField('Estado', max_length=15,
                               choices=ESTADO_CHOICES, default='pendiente')
    fecha_pago = models.DateField('Fecha de pago', null=True, blank=True)
    notas = models.TextField('Notas', blank=True)

    # Auditoría
    registrado_por = models.ForeignKey(
        User, on_delete=models.PROTECT,
        verbose_name='Registrado por',
        related_name='prestamos_registrados'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Préstamo entre Socios'
        verbose_name_plural = 'Préstamos entre Socios'
        ordering = ['-fecha', '-created_at']
        indexes = [
            models.Index(fields=['estado']),
            models.Index(fields=['socio_origen', 'estado']),
            models.Index(fields=['socio_destino', 'estado']),
        ]

    def __str__(self):
        return f'{self.socio_origen.nombre} → {self.socio_destino.nombre}: ${self.monto:,.2f}'

    @property
    def saldo_pendiente(self):
        if self.estado == 'pendiente':
            return self.monto
        return 0


class ProfitDistribution(models.Model):
    """
    Distribución de utilidades generada a partir de un convenio.

    Calcula automáticamente: Ingresos - Honorarios - Comisiones - Retenciones - Gastos = Utilidad Neta
    Luego distribuye la utilidad neta entre los socios según su porcentaje de participación.
    """

    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('distribuida', 'Distribuida'),
        ('confirmada', 'Confirmada'),
        ('cancelada', 'Cancelada'),
    ]

    convenio = models.ForeignKey(
        'Agreement', on_delete=models.PROTECT,
        verbose_name='Convenio',
        related_name='distribuciones',
        help_text='Convenio que genera la distribución'
    )
    fecha = models.DateField('Fecha de distribución')
    descripcion = models.CharField('Descripción', max_length=300, blank=True,
                                    help_text='Breve descripción de la distribución')

    # Cálculos automáticos (se llenan al crear la distribución)
    monto_convenio = models.DecimalField('Monto del convenio', max_digits=12, decimal_places=2, editable=False)
    honorarios = models.DecimalField('Honorarios', max_digits=12, decimal_places=2, editable=False, default=0)
    comisiones = models.DecimalField('Comisiones', max_digits=12, decimal_places=2, editable=False, default=0)
    retenciones = models.DecimalField('Retenciones / ISR', max_digits=12, decimal_places=2, default=0,
                                       help_text='Retenciones fiscales aplicables')
    gastos_relacionados = models.DecimalField('Gastos relacionados', max_digits=12, decimal_places=2, default=0,
                                               help_text='Gastos operativos relacionados al convenio')
    utilidad_neta = models.DecimalField('Utilidad Neta', max_digits=12, decimal_places=2, editable=False, default=0)

    estado = models.CharField('Estado', max_length=15, choices=ESTADO_CHOICES, default='borrador')
    notas = models.TextField('Notas', blank=True)

    # Auditoría
    creado_por = models.ForeignKey(
        User, on_delete=models.PROTECT,
        verbose_name='Creado por',
        related_name='distribuciones_creadas'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Distribución de Utilidad'
        verbose_name_plural = 'Distribuciones de Utilidades'
        ordering = ['-fecha', '-created_at']
        indexes = [
            models.Index(fields=['fecha']),
            models.Index(fields=['estado']),
            models.Index(fields=['convenio', 'estado']),
        ]

    def __str__(self):
        return f'Distribución #{self.pk} - {self.convenio.cliente.nombre} - ${self.utilidad_neta:,.2f}'

    def calcular(self):
        """
        Calcula la utilidad neta basada en el convenio y datos relacionados.
        No guarda en BD, solo actualiza los campos en memoria.
        """
        self.monto_convenio = self.convenio.monto_convenio

        # Honorarios del convenio
        self.honorarios = self.convenio.honorarios or 0

        # Comisiones: buscar comisiones relacionadas al expediente del convenio
        from django.db.models import Sum
        com = Commission.objects.filter(
            expediente__cliente=self.convenio.cliente
        ).aggregate(t=Sum('monto_comision'))['t'] or 0
        self.comisiones = com

        # Utilidad neta
        self.utilidad_neta = self.monto_convenio - self.honorarios - self.comisiones - self.retenciones - self.gastos_relacionados

    def save(self, *args, **kwargs):
        self.calcular()
        super().save(*args, **kwargs)

    @property
    def distribucion_partners(self):
        """Retorna el queryset de las participaciones de socios."""
        return self.partner_profits.select_related('partner').order_by('partner__nombre')

    @property
    def total_distribuido(self):
        """Suma de lo distribudo a todos los socios."""
        return self.partner_profits.aggregate(t=models.Sum('monto'))['t'] or 0


class PartnerProfit(models.Model):
    """
    Participación individual de un socio en una distribución de utilidades.

    Se genera automáticamente al crear una distribución.
    """

    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente de pago'),
        ('pagado', 'Pagado'),
        ('cancelado', 'Cancelado'),
    ]

    distribucion = models.ForeignKey(
        'ProfitDistribution', on_delete=models.CASCADE,
        verbose_name='Distribución',
        related_name='partner_profits'
    )
    partner = models.ForeignKey(
        'Partner', on_delete=models.PROTECT,
        verbose_name='Socio',
        related_name='utilidades'
    )
    porcentaje = models.DecimalField(
        '% aplicado', max_digits=5, decimal_places=2,
        help_text='Porcentaje de participación del socio en esta distribución'
    )
    monto = models.DecimalField(
        'Monto', max_digits=12, decimal_places=2,
        help_text='Monto calculado: utilidad_neta × porcentaje ÷ 100'
    )
    estado = models.CharField(
        'Estado', max_length=15,
        choices=ESTADO_CHOICES, default='pendiente'
    )
    fecha_pago = models.DateField('Fecha de pago', null=True, blank=True)
    notas = models.TextField('Notas', blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Participación de Socio'
        verbose_name_plural = 'Participaciones de Socios'
        ordering = ['partner__nombre']
        unique_together = ['distribucion', 'partner']
        indexes = [
            models.Index(fields=['estado']),
            models.Index(fields=['partner', 'estado']),
        ]

    def __str__(self):
        return f'{self.partner.nombre}: ${self.monto:,.2f} ({self.porcentaje}%)'

    def save(self, *args, **kwargs):
        # Si es nuevo y no tiene monto, calcularlo automáticamente
        if not self.pk or not self.monto:
            self.monto = self.distribucion.utilidad_neta * self.porcentaje / 100
        super().save(*args, **kwargs)


class PartnerUtilitySummary(models.Model):
    """
    Resumen de utilidades acumuladas por socio.
    Se actualiza automáticamente cuando se confirma una distribución.
    """

    partner = models.OneToOneField(
        'Partner', on_delete=models.PROTECT,
        verbose_name='Socio',
        related_name='resumen_utilidades'
    )
    utilidad_generada = models.DecimalField(
        'Utilidad generada', max_digits=14, decimal_places=2, default=0,
        help_text='Total de utilidad generada en distribuciones'
    )
    utilidad_pagada = models.DecimalField(
        'Utilidad pagada', max_digits=14, decimal_places=2, default=0,
        help_text='Total de utilidad que ya se le ha pagado al socio'
    )
    utilidad_pendiente = models.DecimalField(
        'Utilidad pendiente', max_digits=14, decimal_places=2, default=0,
        help_text='Utilidad generada pendiente de pago'
    )
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Resumen de Utilidades del Socio'
        verbose_name_plural = 'Resúmenes de Utilidades de Socios'
        ordering = ['partner__nombre']

    def __str__(self):
        return f'{self.partner.nombre} - G: ${self.utilidad_generada:,.2f} / P: ${self.utilidad_pagada:,.2f}'

    def actualizar(self):
        """Actualiza los totales desde las distribuciones confirmadas."""
        from django.db.models import Sum
        profits = PartnerProfit.objects.filter(
            partner=self.partner,
            distribucion__estado__in=['distribuida', 'confirmada']
        )
        self.utilidad_generada = profits.aggregate(t=Sum('monto'))['t'] or 0
        self.utilidad_pagada = profits.filter(estado='pagado').aggregate(t=Sum('monto'))['t'] or 0
        self.utilidad_pendiente = self.utilidad_generada - self.utilidad_pagada
        self.save()
