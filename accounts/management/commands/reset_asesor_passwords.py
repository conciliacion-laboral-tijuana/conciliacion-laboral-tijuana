"""
Management command to reset all asesor passwords.

Usage:
    python manage.py reset_asesor_passwords
    python manage.py reset_asesor_passwords --password "CustomPass123!"
    python manage.py reset_asesor_passwords --dry-run
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Reset passwords for all active asesores'

    def add_arguments(self, parser):
        parser.add_argument(
            '--password', type=str, default='Asesor2026!',
            help='Password to set (default: Asesor2026!)'
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Show what would be changed without making changes'
        )

    def handle(self, *args, **options):
        password = options['password']
        dry_run = options['dry_run']

        asesores = User.objects.filter(
            profile__rol='asesor',
            is_active=True
        ).select_related('profile').order_by('username')

        if not asesores.exists():
            self.stdout.write(self.style.WARNING('No active asesores found.'))
            return

        self.stdout.write(f'\nFound {asesores.count()} active asesores:')
        self.stdout.write(f'Password to set: {password}')
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no changes will be made\n'))

        for u in asesores:
            nombre = u.get_full_name() or '(sin nombre)'
            self.stdout.write(f'  - {u.username:<20} {nombre}')

            if not dry_run:
                u.set_password(password)
                u.save()

        if not dry_run:
            self.stdout.write(self.style.SUCCESS(
                f'\n✓ Passwords reset for {asesores.count()} asesores to "{password}"'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                '\nDry run complete. Run without --dry-run to apply changes.'
            ))
