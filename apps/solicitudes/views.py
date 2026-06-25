import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.cache import never_cache
from django.utils import timezone
from .models import Solicitud
from .forms import FormularioF43


@never_cache
@login_required
def nueva_solicitud_f43(request):
    """Formulario F43 — solo para personas naturales."""
    if not request.user.es_persona_natural:
        messages.error(request, 'No tiene permisos para acceder a esta sección.')
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        form = FormularioF43(request.POST, request.FILES)

        # Leer equipos enviados desde el JS
        equipos_json = request.POST.get('equipos_json', '[]')
        try:
            equipos = json.loads(equipos_json)
        except json.JSONDecodeError:
            equipos = []

        if form.is_valid():
            if not equipos:
                messages.error(request, 'Debe agregar al menos un equipo a la solicitud.')
                return render(request, 'solicitudes/f43.html', {
                    'form': form,
                    'equipos': equipos,
                })

            # Guardar solicitud
            solicitud = Solicitud(
                flujo       = Solicitud.FLUJO_F43,
                estado      = Solicitud.ESTADO_ENVIADA,
                solicitante = request.user,
                observaciones_solicitante = form.cleaned_data.get('observaciones_solicitante', ''),
            )

            # Documento adjunto
            if form.cleaned_data.get('documento_adjunto'):
                solicitud.documento_adjunto = form.cleaned_data['documento_adjunto']

            # Guardar datos del formulario en observaciones técnicas (JSON)
            datos_f43 = {
                'nombre_apellidos':       form.cleaned_data['nombre_apellidos'],
                'numero_pasaporte':       form.cleaned_data['numero_pasaporte'],
                'pais_residencia':        form.cleaned_data['pais_residencia'],
                'direccion_residencia':   form.cleaned_data['direccion_residencia'],
                'correo_electronico':     form.cleaned_data['correo_electronico'],
                'telefono':               form.cleaned_data['telefono'],
                'provincia':              form.cleaned_data['provincia'],
                'modo_importacion':       form.cleaned_data['modo_importacion'],
                'numero_vuelo':           form.cleaned_data.get('numero_vuelo', ''),
                'fecha_arribo':           str(form.cleaned_data.get('fecha_arribo', '')),
                'pais_procedencia':       form.cleaned_data.get('pais_procedencia', ''),
                'aduana_acceso':          form.cleaned_data.get('aduana_acceso', ''),
                'lugar_acceso':           form.cleaned_data.get('lugar_acceso', ''),
                'numero_rad':             form.cleaned_data.get('numero_rad', ''),
                'objetivo_importacion':   form.cleaned_data['objetivo_importacion'],
                'objetivo_otros_detalle': form.cleaned_data.get('objetivo_otros_detalle', ''),
                'periodo_importacion':    form.cleaned_data['periodo_importacion'],
                'tiempo_solicitado':      form.cleaned_data.get('tiempo_solicitado', ''),
                'equipos':                equipos,
            }

            solicitud.equipo_descripcion = json.dumps(datos_f43, ensure_ascii=False)
            solicitud.save()

            messages.success(
                request,
                f'Solicitud {solicitud.numero} enviada correctamente. El operador la revisará en breve.'
            )
            return redirect('solicitudes:mis_solicitudes')

        else:
            messages.error(request, 'Por favor corrija los errores en el formulario.')
            return render(request, 'solicitudes/f43.html', {
                'form': form,
                'equipos': equipos,
            })

    else:
        # Prellenar con datos del usuario autenticado
        form = FormularioF43(initial={
            'nombre_apellidos':  request.user.get_nombre_completo(),
            'correo_electronico': request.user.email,
            'telefono':           request.user.telefono,
        })

    return render(request, 'solicitudes/f43.html', {
        'form': form,
        'equipos': [],
    })


@never_cache
@login_required
def mis_solicitudes(request):
    """Lista de solicitudes del usuario autenticado."""
    solicitudes = Solicitud.objects.filter(
        solicitante=request.user
    ).order_by('-fecha_creacion')

    return render(request, 'solicitudes/mis_solicitudes.html', {
        'solicitudes': solicitudes,
    })