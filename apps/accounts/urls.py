from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Auth
    path('',            views.vista_login,     name='login'),
    path('logout/',     views.vista_logout,    name='logout'),
    path('dashboard/',  views.vista_dashboard, name='dashboard'),

    # Gestión de usuarios
    path('usuarios/',                       views.lista_usuarios,           name='lista_usuarios'),
    path('usuarios/nuevo/',                 views.nuevo_usuario,            name='nuevo_usuario'),
    path('usuarios/<int:pk>/',              views.detalle_usuario,          name='detalle_usuario'),
    path('usuarios/<int:pk>/editar/',       views.editar_usuario,           name='editar_usuario'),
    path('usuarios/<int:pk>/password/',     views.cambiar_password_usuario, name='cambiar_password'),
    path('usuarios/<int:pk>/toggle/',       views.togglear_usuario,         name='toggle_usuario'),
]