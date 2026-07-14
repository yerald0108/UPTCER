from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.http import JsonResponse
from django.utils import timezone
from .models import Notificacion


@never_cache
@login_required
def lista_notificaciones(request):
    notificaciones = Notificacion.objects.filter(
        destinatario=request.user
    ).select_related('solicitud')

    # Marcar todas como leídas con una sola consulta
    notificaciones.filter(leida=False).update(
        leida=True,
        fecha_lectura=timezone.now()
    )

    return render(request, 'notificaciones/lista.html', {
        'notificaciones': notificaciones,
    })


@never_cache
@login_required
def marcar_leida(request, pk):
    notificacion = get_object_or_404(Notificacion, pk=pk, destinatario=request.user)
    notificacion.marcar_leida()
    if notificacion.solicitud:
        return redirect('solicitudes:detalle', pk=notificacion.solicitud.pk)
    return redirect('notificaciones:lista')


@login_required
def contador_no_leidas(request):
    """Endpoint AJAX para el contador del navbar."""
    count = Notificacion.objects.filter(
        destinatario=request.user,
        leida=False
    ).count()
    return JsonResponse({'count': count})