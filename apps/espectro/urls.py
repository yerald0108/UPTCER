from django.urls import path
from django.views.generic import RedirectView
from .views import seleccion_anexo_view, calcular_view

app_name = 'espectro'

urlpatterns = [
    # Pantalla de bienvenida con las dos cards
    path('', seleccion_anexo_view, name='seleccion_anexo'),

    # Formulario de cálculo con el grupo preestablecido
    path('calcular/<str:grupo>/', calcular_view, name='calcular'),

    # Compatibilidad con ruta antigua
    path('calcular/', RedirectView.as_view(
        pattern_name='espectro:seleccion_anexo', permanent=False
    )),
]