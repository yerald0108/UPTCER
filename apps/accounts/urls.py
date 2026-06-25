from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('',          views.vista_login,     name='login'),
    path('logout/',   views.vista_logout,    name='logout'),
    path('dashboard/', views.vista_dashboard, name='dashboard'),
]