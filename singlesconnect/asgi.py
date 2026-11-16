import os
from django.core.asgi import get_asgi_application

# 1. Set the settings module FIRST
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'singlesconnect.settings')

# 2. Initialize Django ASGI application EARLY
# This populates the AppRegistry and loads all models
django_asgi_app = get_asgi_application()

# 3. NOW it is safe to import your routing/consumers (which import models)
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from core.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})