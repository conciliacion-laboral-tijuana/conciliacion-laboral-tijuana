"""
Comando para migrar datos de SQLite a PostgreSQL.

FLUJO:
    1. Railway provisiona PostgreSQL → variables PGHOST, PGUSER etc. se inyectan
    2. Entrypoint corre `migrate` → tablas creadas en PostgreSQL
    3. Este comando detecta SQLite con datos y PostgreSQL como DB actual
    4. Exporta de SQLite → archivo JSON temporal
    5. Importa JSON → PostgreSQL

Uso:
    python manage.py migrate_sqlite_to_pg
    python manage.py migrate_sqlite_to_pg --sqlite-path ruta/a/db.sqlite3
    python manage.py migrate_sqlite_to_pg --skip-contenttypes  # Omite contenttypes (recomendado)
"""
import os
import subprocess
import sys
import tempfile

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Migra datos de SQLite a PostgreSQL cuando se detecta un cambio de base de datos'

    def add_arguments(self, parser):
        parser.add_argument('--sqlite-path', default=None,
                            help='Ruta al archivo SQLite (default: db.sqlite3 en BASE_DIR)')
        parser.add_argument('--skip-contenttypes', action='store_true', default=True,
                            help='Omite django.contrib.contenttypes (recomendado)')
        parser.add_argument('--force', action='store_true', default=False,
                            help='Fuerza la migración aunque no se detecte SQLite')

    def handle(self, *args, **options):
        # ── 1. Determinar ruta del SQLite ─────────────────────────────
        sqlite_path = options['sqlite_path']
        if not sqlite_path:
            sqlite_path = str(settings.BASE_DIR / 'db.sqlite3')

        # ── 2. Verificar que SQLite existe ────────────────────────────
        if not os.path.exists(sqlite_path):
            self.stdout.write(self.style.WARNING(
                'ℹ️  No se encontró archivo SQLite. Nada que migrar.'
            ))
            return

        # Verificar que tenga datos (no esté vacío)
        if os.path.getsize(sqlite_path) < 4096 and not options['force']:
            self.stdout.write(self.style.WARNING(
                'ℹ️  El archivo SQLite parece estar vacío. Nada que migrar.'
            ))
            return

        # ── 3. Verificar que la DB actual es PostgreSQL ───────────────
        db_url = os.environ.get('DATABASE_URL', '')
        is_postgres = 'postgres' in db_url.lower()

        # ── 3b. Saltar si PostgreSQL YA tiene datos (producción) ─────
        # Evita re-importar datos viejos de SQLite en cada deploy.
        if is_postgres and not options['force']:
            from expedientes.models import Expediente
            pg_count = Expediente.objects.count()
            if pg_count > 0:
                self.stdout.write(self.style.WARNING(
                    f'ℹ️  PostgreSQL ya tiene {pg_count} expedientes. '
                    f'Omitiendo migración desde SQLite (usa --force para forzar).'
                ))
                return

        if not is_postgres and not options['force']:
            # Revisar variables de Railway
            has_pg_vars = all(os.environ.get(v) for v in ['PGHOST', 'PGUSER', 'PGDATABASE'])
            if not has_pg_vars:
                self.stdout.write(self.style.ERROR(
                    '❌ La base de datos actual NO es PostgreSQL.\n'
                    '   Agrega PostgreSQL desde el dashboard de Railway y vuelve a intentar.'
                ))
                return
            is_postgres = True

        if not is_postgres:
            self.stdout.write(self.style.WARNING(
                'ℹ️  La base de datos sigue siendo SQLite. No se requiere migración.'
            ))
            return

        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('🚀 Migrando datos de SQLite → PostgreSQL'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'   SQLite:    {sqlite_path}')
        self.stdout.write(f'   Tamaño:    {os.path.getsize(sqlite_path) / 1024:.1f} KB')

        # ── 4. Apps a incluir ─────────────────────────────────────────
        sistemas_excluidos = {
            'contenttypes',  # Se regenera con migrate
            'sessions',      # Sesiones temporales
            'admin',         # Admin log es regenerable
            'auth',          # Usuarios del sistema pueden tratarse aparte
        }
        # ContentTypes ya se excluye si la opción se activó; evita duplicar
        if options['skip_contenttypes']:
            sistemas_excluidos.add('contenttypes')

        include_apps = [
            'accounts',
            'expedientes',
            'finanzas',
        ]

        # ── 5. Dump desde SQLite (subprocess con DATABASE_URL temporal) ──
        self.stdout.write('\n📤 Exportando datos desde SQLite...')

        with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w') as tmp:
            fixture_path = tmp.name

        env = os.environ.copy()
        env['DATABASE_URL'] = f'sqlite:///{os.path.abspath(sqlite_path)}'

        dump_cmd = [
            sys.executable, 'manage.py', 'dumpdata',
            '--natural-foreign',
            '--natural-primary',
            '--indent', '2',
            '-o', fixture_path,
        ]

        # Excluir apps del sistema
        for app in sistemas_excluidos:
            dump_cmd.extend(['--exclude', app])

        # Incluir explícitamente las apps del proyecto
        dump_cmd.extend(include_apps)

        self.stdout.write(f'   Comando: {" ".join(dump_cmd[:6])} ... -o {fixture_path}')
        self.stdout.flush()

        try:
            result = subprocess.run(
                dump_cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                self.stdout.write(self.style.ERROR(
                    f'❌ Error exportando desde SQLite:\n{result.stderr[:1000]}'
                ))
                self._cleanup(fixture_path)
                return

            # Verificar que el fixture no esté vacío
            fixture_size = os.path.getsize(fixture_path)
            self.stdout.write(self.style.SUCCESS(f'   ✅ Exportado: {fixture_size / 1024:.1f} KB'))

            if fixture_size < 100:  # Muy pequeño, probablemente vacío
                self.stdout.write(self.style.WARNING(
                    '   ⚠️  El archivo exportado está casi vacío. Puede que no haya datos.'
                ))
                if not options['force']:
                    self._cleanup(fixture_path)
                    return

        except subprocess.TimeoutExpired:
            self.stdout.write(self.style.ERROR('❌ Timeout exportando datos.'))
            self._cleanup(fixture_path)
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))
            self._cleanup(fixture_path)
            return

        # ── 6. Load a PostgreSQL ──────────────────────────────────────
        self.stdout.write('\n📥 Importando datos a PostgreSQL...')

        load_cmd = [
            sys.executable, 'manage.py', 'loaddata',
            fixture_path,
        ]

        self.stdout.write(f'   Comando: {" ".join(load_cmd)}')

        try:
            result = subprocess.run(
                load_cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                self.stdout.write(self.style.ERROR(
                    f'❌ Error importando a PostgreSQL:\n{result.stderr[:2000]}'
                ))
                self._cleanup(fixture_path)
                return

            self.stdout.write(self.style.SUCCESS(
                f'   ✅ Datos importados exitosamente a PostgreSQL'
            ))

            # Mostrar resumen de lo importado
            for line in result.stdout.split('\n'):
                if line.strip():
                    self.stdout.write(f'      {line.strip()}')

        except subprocess.TimeoutExpired:
            self.stdout.write(self.style.ERROR('❌ Timeout importando datos.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error importando: {e}'))
        finally:
            self._cleanup(fixture_path)

        # ── 7. Resumen ────────────────────────────────────────────────
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('✅ Migración completada'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(
            '   Los datos han sido migrados de SQLite a PostgreSQL.\n'
            '   Ya puedes respaldar o eliminar el archivo SQLite.\n'
        )

    def _cleanup(self, fixture_path):
        """Elimina el archivo temporal."""
        try:
            if os.path.exists(fixture_path):
                os.unlink(fixture_path)
        except Exception:
            pass
