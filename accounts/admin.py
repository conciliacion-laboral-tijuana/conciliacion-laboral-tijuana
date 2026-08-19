from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils import timezone
from .models import UserProfile, PermisoAuditLog


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Perfil'
    fieldsets = [
        ('Información', {'fields': ['rol', 'telefono']}),
        ('Permisos Especiales', {
            'fields': ['puede_generar_documentos'],
            'description': 'Activa esta opción para que el usuario pueda generar demandas, documentos legales y usar machotes, independientemente de su rol.'
        }),
    ]

    def save_model(self, request, obj, form, change):
        """
        Detecta cambios en los permisos y registra en el log de auditoría.
        """
        if change and obj.pk:
            try:
                old = UserProfile.objects.get(pk=obj.pk)
                cambios = []
                acciones = []

                if old.rol != obj.rol:
                    cambios.append(f"Rol: {old.get_rol_display()} → {obj.get_rol_display()}")
                    acciones.append('cambio_rol')
                if old.puede_generar_documentos != obj.puede_generar_documentos:
                    antes = 'Sí' if old.puede_generar_documentos else 'No'
                    despues = 'Sí' if obj.puede_generar_documentos else 'No'
                    cambios.append(f"Docs: {antes} → {despues}")
                    acciones.append('cambio_docs')

                if cambios:
                    accion = 'mixto' if len(cambios) > 1 else acciones[0]
                    PermisoAuditLog.objects.create(
                        usuario_modificado=obj.user,
                        modificado_por=request.user if request.user.is_authenticated else None,
                        accion=accion,
                        detalle='; '.join(cambios),
                    )
            except UserProfile.DoesNotExist:
                pass

        super().save_model(request, obj, form, change)


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ['username', 'email', 'get_rol', 'get_puede_generar', 'is_staff', 'is_active']
    list_filter = ['profile__rol', 'profile__puede_generar_documentos', 'is_staff', 'is_active']
    list_editable = []

    def get_rol(self, obj):
        return obj.profile.get_rol_display() if hasattr(obj, 'profile') else '—'
    get_rol.short_description = 'Rol'
    get_rol.admin_order_field = 'profile__rol'

    def get_puede_generar(self, obj):
        if hasattr(obj, 'profile') and obj.profile.puede_generar_documentos:
            return '✅ Sí'
        return '—'
    get_puede_generar.short_description = 'Docs'
    get_puede_generar.admin_order_field = 'profile__puede_generar_documentos'

    def save_formsets(self, request, form, formsets, change):
        """Guarda el User y los inlines sin duplicar el UserProfile.

        El signal ``crear_perfil_usuario`` ya crea un UserProfile al
        guardar el User. Si el inline también intenta crear uno, se
        produce un IntegrityError (OneToOneField duplicado).

        Este método detecta si el perfil ya existe y, en ese caso,
        actualiza los campos del inline en el perfil existente.
        """
        # 1. Guardar el User (dispara post_save → crea UserProfile)
        form.save()

        # 2. Procesar cada inline formset
        for formset in formsets:
            instances = formset.save(commit=False)
            for instance in instances:
                if isinstance(instance, UserProfile) and not instance.pk:
                    # El perfil fue creado por el signal; actualizarlo
                    existing = UserProfile.objects.filter(user=form.instance).first()
                    if existing:
                        existing.rol = instance.rol
                        existing.telefono = instance.telefono
                        existing.puede_generar_documentos = instance.puede_generar_documentos
                        existing.save()
                    else:
                        instance.save()
                else:
                    instance.save()
            formset.save_m2m()


class PermisoAuditLogAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'usuario_modificado', 'get_quien', 'accion', 'detalle_resumido']
    list_filter = ['accion', 'created_at']
    search_fields = ['usuario_modificado__username', 'usuario_modificado__email', 'detalle']
    readonly_fields = ['usuario_modificado', 'modificado_por', 'accion', 'detalle', 'created_at']
    date_hierarchy = 'created_at'

    def get_quien(self, obj):
        if obj.modificado_por:
            return obj.modificado_por.get_full_name() or obj.modificado_por.username
        return '—'
    get_quien.short_description = 'Modificado por'
    get_quien.admin_order_field = 'modificado_por'

    def detalle_resumido(self, obj):
        return obj.detalle[:80] + '…' if len(obj.detalle) > 80 else obj.detalle
    detalle_resumido.short_description = 'Detalle'

    def has_add_permission(self, request):
        return False  # Solo lectura

    def has_change_permission(self, request):
        return False  # Solo lectura

    def has_delete_permission(self, request):
        return request.user.is_superuser


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(PermisoAuditLog, PermisoAuditLogAdmin)
