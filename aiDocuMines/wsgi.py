"""
WSGI config for mind_factory_data_science_rest_apis_v1 project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os
from whitenoise import WhiteNoise
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aiDocuMines.settings')

application = get_wsgi_application()
application = WhiteNoise(application)
# application = WhiteNoise(application, root='/app/static/')