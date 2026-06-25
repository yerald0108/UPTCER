from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.db.models import Count, Q
from django.utils import timezone


# ─── Login ────────────────────────────────────────────────────────────────────
@never_cache
@require_http_methods(['GET', 'POST'])
def vista_login(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        if not username or not password:
            messages.error(request, 'Por favor complete todos los campos.')
            return render(request, 'accounts/login.html', {'username_valor': username})

        usuario = authenticate(request, username=username, password=password)

        if usuario is not None:
            if usuario.is_active:
                login(request, usuario)
                messages.success(request, f'Bienvenido al sistema, {usuario.get_nombre_completo()}.')
                siguiente = request.GET.get('next', 'accounts:dashboard')
                return redirect(siguiente)
            else:
                messages.error(request, 'Su cuenta está desactivada. Contacte al administrador.')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')

        return render(request, 'accounts/login.html', {'username_valor': username})

    return render(request, 'accounts/login.html')


# ─── Logout ───────────────────────────────────────────────────────────────────
@require_http_methods(['POST'])
def vista_logout(request):
    logout(request)
    messages.success(request, 'Ha cerrado sesión correctamente.')
    return redirect('accounts:login')


# ─── Dashboard ────────────────────────────────────────────────────────────────
@never_cache
@login_required
def vista_dashboard(request):
    usuario = request.user

    if usuario.es_persona_natural:
        return _dashboard_persona_natural(request, usuario)
    if usuario.es_operador:
        return _dashboard_operador(request, usuario)
    if usuario.es_especialista:
        return _dashboard_especialista(request, usuario)
    if usuario.es_aduana:
        return _dashboard_aduana(request, usuario)
    if usuario.es_directivo:
        return _dashboard_directivo(request, usuario)

    return _dashboard_operador(request, usuario)


# ─── Dashboards por rol ───────────────────────────────────────────────────────

def _dashboard_persona_natural(request, usuario):
    from apps.solicitudes.models import Solicitud

    solicitudes = Solicitud.objects.filter(solicitante=usuario)

    contexto = {
        'usuario': usuario,
        'total_solicitudes':   solicitudes.count(),
        'aprobadas':           solicitudes.filter(estado=Solicitud.ESTADO_APROBADA).count(),
        'en_revision':         solicitudes.filter(estado__in=[
                                   Solicitud.ESTADO_ENVIADA,
                                   Solicitud.ESTADO_EN_REVISION
                               ]).count(),
        'denegadas':           solicitudes.filter(estado=Solicitud.ESTADO_DENEGADA).count(),
        'solicitudes_recientes': solicitudes.select_related('equipo')[:5],
    }
    return render(request, 'accounts/dashboard_persona_natural.html', contexto)


def _dashboard_operador(request, usuario):
    from apps.solicitudes.models import Solicitud

    hoy = timezone.now().date()
    solicitudes = Solicitud.objects.select_related('solicitante', 'equipo')

    contexto = {
        'usuario': usuario,
        'nuevas':        solicitudes.filter(estado=Solicitud.ESTADO_ENVIADA).count(),
        'en_proceso':    solicitudes.filter(estado=Solicitud.ESTADO_EN_REVISION).count(),
        'aprobadas_hoy': solicitudes.filter(
                             estado=Solicitud.ESTADO_APROBADA,
                             fecha_resolucion__date=hoy
                         ).count(),
        'denegadas_hoy': solicitudes.filter(
                             estado=Solicitud.ESTADO_DENEGADA,
                             fecha_resolucion__date=hoy
                         ).count(),
        'solicitudes_recientes': solicitudes.filter(
                                     estado__in=[
                                         Solicitud.ESTADO_ENVIADA,
                                         Solicitud.ESTADO_EN_REVISION,
                                     ]
                                 ).order_by('-fecha_creacion')[:8],
    }
    return render(request, 'accounts/dashboard_operador.html', contexto)


def _dashboard_especialista(request, usuario):
    from apps.solicitudes.models import Solicitud

    contexto = {
        'usuario': usuario,
        'por_evaluar':       Solicitud.objects.filter(
                                 equipo_no_listado=True,
                                 estado=Solicitud.ESTADO_EN_REVISION
                             ).count(),
        'evaluadas_mes':     Solicitud.objects.filter(
                                 equipo_no_listado=True,
                                 estado__in=[
                                     Solicitud.ESTADO_APROBADA,
                                     Solicitud.ESTADO_DENEGADA,
                                 ],
                                 fecha_resolucion__month=timezone.now().month,
                                 fecha_resolucion__year=timezone.now().year,
                             ).count(),
        'aprobadas_total':   Solicitud.objects.filter(
                                 equipo_no_listado=True,
                                 estado=Solicitud.ESTADO_APROBADA
                             ).count(),
        'pendientes_recientes': Solicitud.objects.filter(
                                    equipo_no_listado=True,
                                    estado=Solicitud.ESTADO_EN_REVISION
                                ).select_related('solicitante').order_by('-fecha_creacion')[:5],
    }
    return render(request, 'accounts/dashboard_especialista.html', contexto)


def _dashboard_aduana(request, usuario):
    from apps.solicitudes.models import Solicitud

    hoy = timezone.now().date()
    rats = Solicitud.objects.filter(flujo=Solicitud.FLUJO_RATS)

    contexto = {
        'usuario': usuario,
        'retenidos':         rats.filter(estado=Solicitud.ESTADO_ENVIADA).count(),
        'rats_activas':      rats.filter(estado__in=[
                                 Solicitud.ESTADO_ENVIADA,
                                 Solicitud.ESTADO_EN_REVISION,
                             ]).count(),
        'verificados_hoy':   rats.filter(
                                 estado=Solicitud.ESTADO_APROBADA,
                                 fecha_resolucion__date=hoy
                             ).count(),
        'rats_recientes':    rats.select_related('solicitante').order_by('-fecha_creacion')[:5],
    }
    return render(request, 'accounts/dashboard_aduana.html', contexto)


def _dashboard_directivo(request, usuario):
    from apps.solicitudes.models import Solicitud
    from apps.accounts.models import Usuario

    solicitudes = Solicitud.objects.all()
    total       = solicitudes.count()
    aprobadas   = solicitudes.filter(estado=Solicitud.ESTADO_APROBADA).count()

    contexto = {
        'usuario': usuario,
        'total_solicitudes': total,
        'tasa_aprobacion':   round((aprobadas / total * 100), 1) if total > 0 else 0,
        'usuarios_activos':  Usuario.objects.filter(is_active=True).count(),
        'pendientes_firma':  solicitudes.filter(estado=Solicitud.ESTADO_EN_REVISION).count(),
        'por_flujo': {
            'f43':  solicitudes.filter(flujo=Solicitud.FLUJO_F43).count(),
            'rats': solicitudes.filter(flujo=Solicitud.FLUJO_RATS).count(),
        },
        'por_estado': solicitudes.values('estado').annotate(total=Count('estado')),
        'solicitudes_recientes': solicitudes.select_related(
                                     'solicitante', 'equipo'
                                 ).order_by('-fecha_creacion')[:8],
    }
    return render(request, 'accounts/dashboard_directivo.html', contexto)