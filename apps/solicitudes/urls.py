from django.urls import path
from . import views

app_name = 'solicitudes'

urlpatterns = [
    path('nueva/f43/',          views.nueva_solicitud_f43,  name='nueva_f43'),
    path('mis/',                views.mis_solicitudes,       name='mis_solicitudes'),
    path('lista/',              views.lista_solicitudes,     name='lista'),
    path('<int:pk>/',           views.detalle_solicitud,     name='detalle'),
    path('<int:pk>/estado/',    views.cambiar_estado,        name='cambiar_estado'),
]