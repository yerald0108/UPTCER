from django.urls import path
from . import views

app_name = 'equipos'

urlpatterns = [
    path('',                views.lista_equipos,       name='lista'),
    path('nuevo/',          views.nuevo_equipo,        name='nuevo'),
    path('categorias/',     views.lista_categorias,    name='categorias'),
    path('buscar/',         views.buscar_equipos_ajax, name='buscar_ajax'),
    path('<int:pk>/',       views.detalle_equipo,      name='detalle'),
    path('<int:pk>/editar/',views.editar_equipo,       name='editar'),
    path('<int:pk>/estado/',views.desactivar_equipo,   name='desactivar'),
]