from django.urls import path
from . import views

app_name = 'licencias'

urlpatterns = [
    path('',                    views.lista_licencias,  name='lista'),
    path('<str:numero>/',       views.detalle_licencia, name='detalle'),
    path('<str:numero>/revocar/', views.revocar_licencia, name='revocar'),
]