from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.db.models import Count, Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models.functions import TruncMonth
from django.utils import timezone
from dateutil.relativedelta import relativedelta
import json

from apps.solicitudes.models import Solicitud
from apps.licencias.models import Licencia
from .forms import FormularioCrearUsuario
from .forms import FormularioCambiarPassword
from .forms import FormularioEditarUsuario
from .forms import FormularioEditarPerfil
from .forms import FormularioCambiarMiPassword
from .models import Usuario

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

    solicitudes = Solicitud.objects.all()
    total       = solicitudes.count()
    aprobadas   = solicitudes.filter(estado=Solicitud.ESTADO_APROBADA).count()
    denegadas   = solicitudes.filter(estado=Solicitud.ESTADO_DENEGADA).count()
    pendientes  = solicitudes.filter(estado__in=[
                      Solicitud.ESTADO_ENVIADA,
                      Solicitud.ESTADO_EN_REVISION
                  ]).count()

    # Solicitudes por mes (últimos 6 meses)
    hoy        = timezone.now()
    hace_6m    = hoy - relativedelta(months=5)

    por_mes_qs = (
        solicitudes
        .filter(fecha_creacion__gte=hace_6m)
        .annotate(mes=TruncMonth('fecha_creacion'))
        .values('mes')
        .annotate(total=Count('id'))
        .order_by('mes')
    )

    # Construir labels y datos para los últimos 6 meses
    meses_labels = []
    meses_data   = []
    meses_map    = {item['mes'].strftime('%Y-%m'): item['total'] for item in por_mes_qs}

    MESES_ES = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']

    for i in range(6):
        fecha = hace_6m + relativedelta(months=i)
        clave = fecha.strftime('%Y-%m')
        meses_labels.append(MESES_ES[fecha.month - 1])
        meses_data.append(meses_map.get(clave, 0))

    # Solicitudes por estado
    estados_qs = (
        solicitudes
        .values('estado')
        .annotate(total=Count('id'))
        .order_by('estado')
    )
    estados_labels = [dict(Solicitud.ESTADOS).get(e['estado'], e['estado']) for e in estados_qs]
    estados_data   = [e['total'] for e in estados_qs]

    # Solicitudes por flujo
    por_flujo = {
        'f43':  solicitudes.filter(flujo=Solicitud.FLUJO_F43).count(),
        'rats': solicitudes.filter(flujo=Solicitud.FLUJO_RATS).count(),
    }

    # Usuarios por rol
    usuarios_por_rol = (
        Usuario.objects
        .values('rol')
        .annotate(total=Count('id'))
        .order_by('rol')
    )
    roles_labels = [dict(Usuario.ROLES).get(r['rol'], r['rol']) for r in usuarios_por_rol]
    roles_data   = [r['total'] for r in usuarios_por_rol]

    contexto = {
        'usuario':           usuario,
        'total_solicitudes': total,
        'tasa_aprobacion':   round((aprobadas / total * 100), 1) if total > 0 else 0,
        'usuarios_activos':  Usuario.objects.filter(is_active=True).count(),
        'pendientes_firma':  pendientes,
        'aprobadas':         aprobadas,
        'denegadas':         denegadas,
        'licencias_vigentes': Licencia.objects.filter(estado=Licencia.ESTADO_VIGENTE).count(),
        'por_flujo':         por_flujo,
        'solicitudes_recientes': solicitudes.select_related(
                                     'solicitante', 'equipo'
                                 ).order_by('-fecha_creacion')[:8],

        # Datos para Chart.js (JSON)
        'chart_meses_labels':  json.dumps(meses_labels),
        'chart_meses_data':    json.dumps(meses_data),
        'chart_estados_labels': json.dumps(estados_labels),
        'chart_estados_data':   json.dumps(estados_data),
        'chart_roles_labels':   json.dumps(roles_labels),
        'chart_roles_data':     json.dumps(roles_data),
    }

    return render(request, 'accounts/dashboard_directivo.html', contexto)

# ─── Gestión de usuarios (directivo) ─────────────────────────────────────────
@never_cache
@login_required
def lista_usuarios(request):
    if not (request.user.es_directivo or request.user.es_operador):
        messages.error(request, 'No tiene permisos para acceder a esta sección.')
        return redirect('accounts:dashboard')

    usuarios_qs = Usuario.objects.all().order_by('apellidos', 'nombre')

    rol    = request.GET.get('rol', '')
    activo = request.GET.get('activo', '')
    q      = request.GET.get('q', '').strip()

    if rol:
        usuarios_qs = usuarios_qs.filter(rol=rol)
    if activo != '':
        usuarios_qs = usuarios_qs.filter(is_active=activo == '1')
    if q:
        usuarios_qs = usuarios_qs.filter(
            Q(nombre__icontains=q) |
            Q(apellidos__icontains=q) |
            Q(username__icontains=q) |
            Q(email__icontains=q)
        )

    paginator = Paginator(usuarios_qs, 15)
    pagina    = request.GET.get('pagina', 1)

    try:
        usuarios = paginator.page(pagina)
    except PageNotAnInteger:
        usuarios = paginator.page(1)
    except EmptyPage:
        usuarios = paginator.page(paginator.num_pages)

    return render(request, 'accounts/usuarios/lista.html', {
        'usuarios':      usuarios,
        'paginator':     paginator,
        'rol_actual':    rol,
        'activo_actual': activo,
        'busqueda':      q,
        'ROLES':         Usuario.ROLES,
        'total':         usuarios_qs.count(),
    })


@never_cache
@login_required
def nuevo_usuario(request):
    if not request.user.es_directivo:
        messages.error(request, 'No tiene permisos para crear usuarios.')
        return redirect('accounts:lista_usuarios')

    if request.method == 'POST':
        form = FormularioCrearUsuario(request.POST)
        if form.is_valid():
            usuario = form.save()
            messages.success(
                request,
                f'Usuario "{usuario.get_nombre_completo()}" creado correctamente.'
            )
            return redirect('accounts:detalle_usuario', pk=usuario.pk)
        else:
            messages.error(request, 'Por favor corrija los errores en el formulario.')
    else:
        form = FormularioCrearUsuario()

    return render(request, 'accounts/usuarios/form_usuario.html', {
        'form':   form,
        'titulo': 'Nuevo usuario',
        'accion': 'Crear usuario',
    })


@never_cache
@login_required
def detalle_usuario(request, pk):
    if not (request.user.es_directivo or request.user.es_operador):
        messages.error(request, 'No tiene permisos para acceder a esta sección.')
        return redirect('accounts:dashboard')

    usuario_obj = get_object_or_404(Usuario, pk=pk)

    # Estadísticas del usuario
    solicitudes = Solicitud.objects.filter(solicitante=usuario_obj)

    estadisticas = {
        'total':       solicitudes.count(),
        'aprobadas':   solicitudes.filter(estado=Solicitud.ESTADO_APROBADA).count(),
        'denegadas':   solicitudes.filter(estado=Solicitud.ESTADO_DENEGADA).count(),
        'pendientes':  solicitudes.filter(estado__in=[
                           Solicitud.ESTADO_ENVIADA,
                           Solicitud.ESTADO_EN_REVISION
                       ]).count(),
    }

    return render(request, 'accounts/usuarios/detalle.html', {
        'usuario_obj':   usuario_obj,
        'estadisticas':  estadisticas,
        'solicitudes_recientes': solicitudes.order_by('-fecha_creacion')[:5],
    })


@never_cache
@login_required
def editar_usuario(request, pk):
    if not request.user.es_directivo:
        messages.error(request, 'No tiene permisos para editar usuarios.')
        return redirect('accounts:lista_usuarios')

    usuario_obj = get_object_or_404(Usuario, pk=pk)

    if request.method == 'POST':
        form = FormularioEditarUsuario(request.POST, instance=usuario_obj)
        if form.is_valid():
            usuario_obj = form.save()
            messages.success(
                request,
                f'Usuario "{usuario_obj.get_nombre_completo()}" actualizado correctamente.'
            )
            return redirect('accounts:detalle_usuario', pk=usuario_obj.pk)
        else:
            messages.error(request, 'Por favor corrija los errores en el formulario.')
    else:
        form = FormularioEditarUsuario(instance=usuario_obj)

    return render(request, 'accounts/usuarios/form_usuario.html', {
        'form':        form,
        'usuario_obj': usuario_obj,
        'titulo':      f'Editar — {usuario_obj.get_nombre_completo()}',
        'accion':      'Guardar cambios',
    })


@never_cache
@login_required
def cambiar_password_usuario(request, pk):
    if not request.user.es_directivo:
        messages.error(request, 'No tiene permisos para cambiar contraseñas.')
        return redirect('accounts:lista_usuarios')

    usuario_obj = get_object_or_404(Usuario, pk=pk)

    if request.method == 'POST':
        form = FormularioCambiarPassword(request.POST)
        if form.is_valid():
            usuario_obj.set_password(form.cleaned_data['password1'])
            usuario_obj.save()
            messages.success(
                request,
                f'Contraseña de "{usuario_obj.get_nombre_completo()}" actualizada correctamente.'
            )
            return redirect('accounts:detalle_usuario', pk=usuario_obj.pk)
        else:
            messages.error(request, 'Por favor corrija los errores.')
    else:
        form = FormularioCambiarPassword()

    return render(request, 'accounts/usuarios/cambiar_password.html', {
        'form':        form,
        'usuario_obj': usuario_obj,
    })


@never_cache
@login_required
@require_http_methods(['POST'])
def togglear_usuario(request, pk):
    if not request.user.es_directivo:
        messages.error(request, 'No tiene permisos para realizar esta acción.')
        return redirect('accounts:lista_usuarios')

    usuario_obj = get_object_or_404(Usuario, pk=pk)

    # No permitir desactivarse a sí mismo
    if usuario_obj.pk == request.user.pk:
        messages.error(request, 'No puede desactivar su propia cuenta.')
        return redirect('accounts:detalle_usuario', pk=pk)

    usuario_obj.is_active = not usuario_obj.is_active
    usuario_obj.save()
    estado = 'activado' if usuario_obj.is_active else 'desactivado'
    messages.success(
        request,
        f'Usuario "{usuario_obj.get_nombre_completo()}" {estado} correctamente.'
    )

    return redirect('accounts:detalle_usuario', pk=pk)

# ─── Perfil del usuario autenticado ──────────────────────────────────────────
@never_cache
@login_required
def perfil(request):
    usuario = request.user

    if request.method == 'POST':
        form = FormularioEditarPerfil(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            messages.success(request, 'Su perfil ha sido actualizado correctamente.')
            return redirect('accounts:perfil')
        else:
            messages.error(request, 'Por favor corrija los errores en el formulario.')
    else:
        form = FormularioEditarPerfil(instance=usuario)

    solicitudes = Solicitud.objects.filter(solicitante=usuario)

    return render(request, 'accounts/perfil.html', {
        'form':    form,
        'usuario': usuario,
        'estadisticas': {
            'total':      solicitudes.count(),
            'aprobadas':  solicitudes.filter(estado=Solicitud.ESTADO_APROBADA).count(),
            'pendientes': solicitudes.filter(estado__in=[
                              Solicitud.ESTADO_ENVIADA,
                              Solicitud.ESTADO_EN_REVISION
                          ]).count(),
        }
    })


@never_cache
@login_required
def cambiar_mi_password(request):

    if request.method == 'POST':
        form = FormularioCambiarMiPassword(request.POST)
        if form.is_valid():
            usuario = request.user
            # Verificar contraseña actual
            if not usuario.check_password(form.cleaned_data['password_actual']):
                form.add_error('password_actual', 'La contraseña actual es incorrecta.')
                return render(request, 'accounts/cambiar_password.html', {'form': form})

            usuario.set_password(form.cleaned_data['password_nueva1'])
            usuario.save()

            # Mantener sesión activa tras cambio de contraseña
            update_session_auth_hash(request, usuario)

            messages.success(request, 'Su contraseña ha sido actualizada correctamente.')
            return redirect('accounts:perfil')
        else:
            messages.error(request, 'Por favor corrija los errores en el formulario.')
    else:
        form = FormularioCambiarMiPassword()

    return render(request, 'accounts/cambiar_password.html', {'form': form})