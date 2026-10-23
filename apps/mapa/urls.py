from django.urls import path
from . import views

app_name = 'mapa'
urlpatterns = [
    path('', views.mapa_view, name='mapa'),
    path('seleccionar-ubicacion/', views.seleccionar_ubicacion_view, name='seleccionar_ubicacion'),
    path('crear/', views.crear_punto_view, name='crear_punto'),
    path('importar/', views.importar_view, name='importar'),
    path('api/crear/', views.api_crear_punto, name='api_crear_punto'),
    path('api/puntos.geojson', views.api_puntos_geojson, name='api_puntos'),
]