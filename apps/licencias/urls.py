from django.urls import path
from . import views

app_name = 'licencias'

urlpatterns = [
    # Facturas — DEBEN ir antes que <str:numero>/ para no ser capturadas
    path('facturas/',                     views.lista_facturas,         name='lista_facturas'),
    path('facturas/<str:numero>/',        views.detalle_factura,        name='detalle_factura'),
    path('facturas/<str:numero>/pagar/',  views.registrar_pago_factura, name='registrar_pago'),

    # Licencias
    path('',                              views.lista_licencias,        name='lista'),
    path('<str:numero>/',                 views.detalle_licencia,       name='detalle'),
    path('<str:numero>/revocar/',         views.revocar_licencia,       name='revocar'),
]