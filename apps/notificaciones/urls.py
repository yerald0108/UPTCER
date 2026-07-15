from django.urls import path
from . import views

app_name = 'notificaciones'

urlpatterns = [
    path('',              views.lista_notificaciones, name='lista'),
    path('<int:pk>/leer/', views.marcar_leida,        name='marcar_leida'),
    path('contador/',     views.contador_no_leidas,   name='contador'),
    path('marcar-todas-leidas/', views.marcar_todas_leidas, name='marcar_todas_leidas'),
]