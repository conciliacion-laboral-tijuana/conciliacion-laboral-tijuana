from django.contrib import admin
from django.utils import timezone

from .models import Cliente, Expediente, Documento, Movimiento, Nota, SolicitudConciliacion, WhatsAppMessage, LegalConfig, CalculoLaboral, Machote, Aviso, SolicitudTransferencia, Notificacion, TareaConciliacion, Empresa


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'domicilio_colonia', 'tipo_persona', 'abogado', 'telefono', 'created_at']
    list_filter = ['tipo_persona', 'created_at']
    search_fields = ['nombre', 'domicilio', 'abogado', 'telefono', 'domicilio_colonia']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = [
        ('Empresa', {'fields': ['nombre', 'domicilio', 'abogado', 'telefono', 'tipo_persona']}),
        ('Domicilio desglosado', {'fields': ['domicilio_calle', 'domicilio_numero', 'domicilio_colonia', 'domicilio_cp']}),
        ('Metadatos', {'fields': ['created_at', 'updated_at']}),
    ]


@admin.register(SolicitudTransferencia)
class SolicitudTransferenciaAdmin(admin.ModelAdmin):
    list_display = ['expediente', 'solicitante', 'estado', 'asesor_destino', 'asesor_asignado', 'created_at', 'fecha_resolucion']
    list_filter = ['estado', 'created_at']
    search_fields = ['expediente__numero', 'expediente__cliente__nombre', 'solicitante__username', 'motivo']
    list_editable = ['estado']
    date_hierarchy = 'created_at'
    autocomplete_fields = ['expediente', 'solicitante', 'asesor_destino', 'asesor_asignado', 'resuelto_por']
    readonly_fields = ['created_at', 'updated_at', 'fecha_resolucion']
    fieldsets = [
        ('Solicitud', {'fields': ['expediente', 'solicitante', 'motivo', 'asesor_destino', 'estado']}),
        ('Resolución', {'fields': ['resuelto_por', 'asesor_asignado', 'comentario_admin', 'fecha_resolucion']}),
        ('Metadatos', {'fields': ['created_at', 'updated_at']}),
    ]

    def save_model(self, request, obj, form, change):
        if change and obj.estado in ['aprobada', 'rechazada', 'cancelada'] and not obj.fecha_resolucion:
            obj.fecha_resolucion = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'curp', 'telefono', 'email', 'empresa', 'como_supo', 'oficina', 'created_at']
    search_fields = ['nombre', 'curp', 'rfc', 'telefono', 'email', 'como_supo', 'oficina']
    list_filter = ['empresa', 'como_supo', 'oficina', 'created_at']
    date_hierarchy = 'created_at'


@admin.register(Expediente)
class ExpedienteAdmin(admin.ModelAdmin):
    list_display = ['numero', 'cliente', 'asesor', 'estado', 'monto_reclamado',
                    'fecha_audiencia', 'prioridad', 'notificar_whatsapp_auto', 'created_at']
    list_filter = ['estado', 'prioridad', 'asesor', 'notificar_whatsapp_auto', 'created_at']
    search_fields = ['numero', 'cliente__nombre', 'cliente__curp']
    date_hierarchy = 'created_at'
    readonly_fields = ['numero', 'created_at', 'updated_at']
    autocomplete_fields = ['cliente', 'asesor']
    list_select_related = ['cliente', 'asesor']
    list_editable = ['notificar_whatsapp_auto']


@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    list_display = ['expediente', 'descripcion', 'tipo', 'subido_por', 'created_at']
    list_filter = ['tipo', 'created_at']
    search_fields = ['descripcion', 'expediente__numero']
    date_hierarchy = 'created_at'


@admin.register(Movimiento)
class MovimientoAdmin(admin.ModelAdmin):
    list_display = ['expediente', 'usuario', 'accion', 'created_at']
    list_filter = ['accion', 'created_at']
    search_fields = ['expediente__numero', 'usuario__username']
    readonly_fields = ['expediente', 'usuario', 'accion', 'detalle', 'created_at']
    date_hierarchy = 'created_at'


@admin.register(Nota)
class NotaAdmin(admin.ModelAdmin):
    list_display = ['expediente', 'usuario', 'created_at']
    list_filter = ['created_at']
    search_fields = ['expediente__numero', 'contenido']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'


@admin.register(SolicitudConciliacion)
class SolicitudConciliacionAdmin(admin.ModelAdmin):
    list_display = ['expediente', 'fecha_solicitud', 'unidad_sede', 'created_at']
    list_filter = ['unidad_sede', 'fecha_solicitud']
    search_fields = ['expediente__numero', 'expediente__cliente__nombre']
    date_hierarchy = 'fecha_solicitud'
    readonly_fields = ['created_at', 'updated_at']
    autocomplete_fields = ['expediente']


@admin.register(LegalConfig)
class LegalConfigAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'activo', 'uma_diaria', 'salario_minimo_frontera',
                    'aguinaldo_dias', 'created_at']
    list_filter = ['activo']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = [
        ('General', {'fields': ['nombre', 'activo']}),
        ('UMA y Salario Mínimo', {
            'description': 'Valores oficiales CONASAMI/INEGI. El tope de la prima de '
                           'antigüedad se mide con el salario mínimo del ÁREA, no con la UMA.',
            'fields': ['uma_diaria', 'salario_minimo', 'salario_minimo_frontera'],
        }),
        ('Aguinaldo (art. 87 LFT)', {'fields': ['aguinaldo_dias']}),
        ('Prima Vacacional (art. 80 LFT)', {'fields': ['prima_vacacional_porcentaje']}),
        ('Prima de Antigüedad (arts. 162, 485 y 486 LFT)', {
            'description': 'El tope legal es el DOBLE del salario mínimo del área '
                           'geográfica donde se prestó el trabajo (Tijuana = Zona Libre de '
                           'la Frontera Norte).',
            'fields': ['prima_antiguedad_dias_por_ano',
                       'prima_antiguedad_anios_voluntaria',
                       'tope_prima_tipo', 'tope_prima_multiplo'],
        }),
        ('Vacaciones (art. 76 LFT)', {'fields': ['vacaciones_antes_de_un_ano']}),
        ('Indemnizaciones (art. 50 LFT)', {
            'fields': ['indemnizacion_dias', 'indemnizacion_20dias_dias_por_ano'],
        }),
        ('Salario integrado (arts. 84 y 89 LFT)', {
            'description': 'Base de las indemnizaciones: cuota diaria y parte proporcional '
                           'de las prestaciones que integran el salario.',
            'fields': ['salario_integrado_modo', 'salario_integrado_porcentaje'],
        }),
        ('Metadatos', {'fields': ['created_at', 'updated_at']}),
    ]


@admin.register(CalculoLaboral)
class CalculoLaboralAdmin(admin.ModelAdmin):
    list_display = ['expediente', 'total', 'salario_diario', 'salario_diario_integrado',
                    'dias_trabajados', 'años_trabajados', 'recalculado_en']
    list_filter = ['tope_salarial_aplicado', 'zona_salarial', 'created_at']
    search_fields = ['expediente__numero', 'expediente__cliente__nombre']
    readonly_fields = ['salario_diario', 'salario_diario_integrado', 'zona_salarial',
                        'dias_trabajados', 'años_trabajados',
                        'aguinaldo', 'vacaciones', 'prima_vacacional', 'prima_antiguedad',
                        'indemnizacion', 'total', 'recalculado_en', 'created_at', 'updated_at']
    autocomplete_fields = ['expediente']
    fieldsets = [
        ('Expediente', {'fields': ['expediente']}),
        ('Datos del Cálculo', {'fields': ['salario_mensual', 'salario_diario',
                                           'salario_diario_integrado', 'periodo_pago',
                                           'zona_salarial',
                                           'fecha_ingreso', 'fecha_salida',
                                           'dias_trabajados', 'años_trabajados']}),
        ('Salario integrado (arts. 84 y 89 LFT)', {
            'description': 'Desglose de lo que integra el salario para el cálculo de las '
                           'indemnizaciones. Si capturas un porcentaje, manda sobre el desglose.',
            'fields': ['salario_integrado_cuota_diaria',
                       'salario_integrado_gratificaciones',
                       'salario_integrado_ayudas',
                       'salario_integrado_porcentaje'],
        }),
        ('Resultados', {'fields': ['aguinaldo', 'vacaciones', 'dias_vacaciones',
                                    'prima_vacacional', 'prima_antiguedad',
                                    'tope_salarial_aplicado', 'indemnizacion', 'total']}),
        ('Metadatos', {'fields': ['notas', 'recalculado_en', 'created_at', 'updated_at']}),
    ]


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'titulo', 'tipo', 'leida', 'created_at']
    list_filter = ['tipo', 'leida', 'created_at']
    search_fields = ['usuario__username', 'titulo', 'mensaje']
    list_editable = ['leida']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']
    autocomplete_fields = ['usuario']
    fieldsets = [
        ('Información', {'fields': ['usuario', 'titulo', 'mensaje', 'tipo', 'link']}),
        ('Estado', {'fields': ['leida']}),
        ('Metadatos', {'fields': ['created_at']}),
    ]


@admin.register(Aviso)
class AvisoAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'prioridad', 'activo', 'fecha_vencimiento', 'creado_por', 'created_at']
    list_filter = ['prioridad', 'activo', 'created_at', 'fecha_vencimiento']
    search_fields = ['titulo', 'contenido']
    list_editable = ['activo']
    date_hierarchy = 'created_at'
    fieldsets = [
        ('Información', {
            'fields': ['titulo', 'contenido', 'prioridad', 'activo', 'fecha_vencimiento']
        }),
        ('Metadatos', {
            'fields': ['creado_por', 'created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(Machote)
class MachoteAdmin(admin.ModelAdmin):
    list_display = ['icono', 'nombre', 'categoria', 'tipo_despido', 'jurisdiccion', 'activo', 'orden']
    list_filter = ['categoria', 'tipo_despido', 'jurisdiccion', 'activo']
    search_fields = ['nombre', 'descripcion']
    list_editable = ['activo', 'orden']
    readonly_fields = ['created_at', 'updated_at', 'archivo_origen']
    fieldsets = [
        ('Información General', {
            'fields': ['nombre', 'descripcion', 'icono', 'categoria', 'tipo_despido', 'jurisdiccion']
        }),
        ('Contenido', {
            'fields': ['contenido_html'],
            'description': 'Usa marcadores como {{ nombre_cliente }}, {{ empresa }}, {{ salario }}, etc. para datos dinámicos.'
        }),
        ('Configuración', {
            'fields': ['activo', 'orden']
        }),
        ('Metadatos', {
            'fields': ['archivo_origen', 'created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]


@admin.register(TareaConciliacion)
class TareaConciliacionAdmin(admin.ModelAdmin):
    list_display = ['pk', 'expediente', 'usuario', 'estado', 'folio', 'modo', 'created_at', 'completed_at']
    list_filter = ['estado', 'modo', 'created_at']
    search_fields = ['expediente__numero', 'folio', 'error', 'detalle']
    readonly_fields = ['created_at', 'completed_at']
    date_hierarchy = 'created_at'
    autocomplete_fields = ['expediente', 'usuario']
    fieldsets = [
        ('Expediente y Usuario', {'fields': ['expediente', 'usuario', 'modo']}),
        ('Estado', {'fields': ['estado', 'created_at', 'completed_at', 'tiempo_transcurrido']}),
        ('Resultado', {'fields': ['folio', 'pdf_path', 'detalle', 'error']}),
        ('Screenshots', {'fields': ['screenshots_json'], 'classes': ['collapse']}),
    ]


@admin.register(WhatsAppMessage)
class WhatsAppMessageAdmin(admin.ModelAdmin):
    list_display = ['expediente', 'destino', 'tipo', 'via', 'estado', 'enviado_por', 'created_at']
    list_filter = ['tipo', 'via', 'estado', 'created_at']
    search_fields = ['expediente__numero', 'destino', 'mensaje']
    readonly_fields = ['link_generado', 'error_log', 'created_at']
    date_hierarchy = 'created_at'
    autocomplete_fields = ['expediente', 'enviado_por']
