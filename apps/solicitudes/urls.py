from django.urls import path
from . import views

app_name = 'solicitudes'

urlpatterns = [
    path('nueva/f43/',  views.nueva_solicitud_f43, name='nueva_f43'),
    path('mis/',        views.mis_solicitudes,      name='mis_solicitudes'),
]