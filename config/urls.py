from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/',       admin.site.urls),
    path('',             include('apps.accounts.urls', namespace='accounts')),
    path('solicitudes/', include('apps.solicitudes.urls', namespace='solicitudes')),
    path('equipos/',     include('apps.equipos.urls',    namespace='equipos')),
    path('licencias/',   include('apps.licencias.urls',  namespace='licencias')),
    path('notificaciones/', include('apps.notificaciones.urls', namespace='notificaciones')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)