"""
Start Django dev server locally without SSL redirect.
Run: uv run python run_local.py
"""
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ['FORCE_HEADLESS'] = 'true'

import django
from django.conf import settings

# Force SECURE_SSL_REDIRECT to False for local dev
settings.SECURE_SSL_REDIRECT = False
settings.SESSION_COOKIE_SECURE = False
settings.CSRF_COOKIE_SECURE = False

django.setup()

from django.core.management import execute_from_command_line
execute_from_command_line([sys.argv[0], 'runserver', '127.0.0.1:8080', '--noreload'])
