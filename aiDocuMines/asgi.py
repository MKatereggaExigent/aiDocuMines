"""
ASGI config for aidocumine project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
from whitenoise import WhiteNoise
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import path


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aiDocuMines.settings')


application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    # Uncomment the lines below if you are using WebSockets
    # "websocket": AuthMiddlewareStack(
    #     URLRouter([
    #         path("ws/some-path/", YourWebSocketConsumer.as_asgi()),
    #     ])
    # ),
})


#application = get_asgi_application()
application = WhiteNoise(application, root='/app/static/')
