"""
Конфігурація WSGI для проєкту СТО.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sto.settings')

application = get_wsgi_application()

