import secrets

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    ROL_CHOICES = [
        ('superadmin', 'Superadmin'),
        ('admin', 'Administrativo'),
        ('asesor', 'Asesor'),
        ('abogada', 'Abogada'),
        ('finanzas', 'Finanzas'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    rol = models.CharField('Rol', max_length=20, choices=ROL_CHOICES, default='asesor')
    telefono = models.CharField('Teléfono', max_length=15, blank=True)
    puede_generar_documentos = models.BooleanField(
        '¿Puede generar documentos legales?', default=False,
        help_text='Permite al usuario acceder al generador de demandas, machotes y documentos legales'
    )
    api_token = models.CharField(
        'Token API (extensión Chrome)', max_length=64, blank=True, unique=True,
        help_text='Token personal para que la extensión de Chrome se comunique con la app'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Perfil de Usuario'
        verbose_name_plural = 'Perfiles de Usuarios'

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.get_rol_display()}"

    def es_admin(self):
        return self.rol in ['superadmin', 'admin', 'finanzas']

    def es_finanzas(self):
        return self.rol == 'finanzas'

    def es_superadmin(self):
        return self.rol == 'superadmin'

    def regenerar_token(self):
        """Genera un token nuevo (invalida el anterior)."""
        self.api_token = secrets.token_urlsafe(32)
        self.save(update_fields=['api_token'])
        return self.api_token

    def save(self, *args, **kwargs):
        # Auto-generar token al crear el perfil si no tiene uno
        if not self.api_token:
            self.api_token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)


class PermisoAuditLog(models.Model):
    """
    Registro de auditoría de cambios en permisos de usuarios.
    Se crea una entrada cada vez que un superadmin/admin modifica
    el rol, el flag 'puede_generar_documentos' u otros permisos de un usuario.
    """
    ACCION_CHOICES = [
        ('cambio_rol', 'Cambio de Rol'),
        ('cambio_docs', 'Permiso de Documentos'),
        ('mixto', 'Cambio Múltiple'),
    ]

    usuario_modificado = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='audit_logs_recibidos',
        verbose_name='Usuario modificado'
    )
    modificado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='audit_logs_realizados',
        verbose_name='Modificado por'
    )
    accion = models.CharField('Acción', max_length=20, choices=ACCION_CHOICES)
    detalle = models.TextField('Detalle del cambio', blank=True,
        help_text='Descripción de lo que cambió (ej: "Rol: asesor → admin")')
    created_at = models.DateTimeField('Fecha', auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Auditoría de Permiso'
        verbose_name_plural = 'Auditoría de Permisos'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_accion_display()} - {self.usuario_modificado.username} ({self.created_at.strftime('%d/%m/%Y %H:%M')})"


@receiver(post_save, sender=User)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    """Crea automáticamente un UserProfile al crear un User.

    Usa get_or_create para evitar IntegrityError cuando el admin
    con inline ya creó el perfil antes de que el signal se ejecute.
    """
    if created:
        UserProfile.objects.get_or_create(user=instance)
