from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.cache import never_cache
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from .models import CategoriaEquipo, Equipo
from .forms import FormularioEquipo, FormularioCategoria


# ─── Lista de equipos ─────────────────────────────────────────────────────────
@never_cache
@login_required
def lista_equipos(request):
    equipos_qs = Equipo.objects.select_related('categoria').filter(activo=True)

    busqueda  = request.GET.get('q', '').strip()
    categoria = request.GET.get('categoria', '')
    banda     = request.GET.get('banda', '')

    if busqueda:
        equipos_qs = equipos_qs.filter(
            Q(nombre__icontains=busqueda) |
            Q(marca__icontains=busqueda)  |
            Q(modelo__icontains=busqueda)
        )
    if categoria:
        equipos_qs = equipos_qs.filter(categoria__id=categoria)
    if banda:
        equipos_qs = equipos_qs.filter(banda_frecuencia=banda)

    categorias = CategoriaEquipo.objects.all()

    paginator = Paginator(equipos_qs, 15)
    pagina    = request.GET.get('pagina', 1)

    try:
        equipos = paginator.page(pagina)
    except PageNotAnInteger:
        equipos = paginator.page(1)
    except EmptyPage:
        equipos = paginator.page(paginator.num_pages)

    return render(request, 'equipos/lista.html', {
        'equipos':       equipos,
        'categorias':    categorias,
        'busqueda':      busqueda,
        'categoria_sel': categoria,
        'banda_sel':     banda,
        'BANDAS':        Equipo.BANDAS,
        'total':         equipos_qs.count(),
        'paginator':     paginator,
    })


# ─── Detalle de equipo ────────────────────────────────────────────────────────
@never_cache
@login_required
def detalle_equipo(request, pk):
    equipo = get_object_or_404(Equipo, pk=pk)
    return render(request, 'equipos/detalle.html', {
        'equipo': equipo,
    })


# ─── Nuevo equipo ─────────────────────────────────────────────────────────────
@never_cache
@login_required
def nuevo_equipo(request):
    if not (request.user.es_operador or request.user.es_especialista or request.user.es_directivo):
        messages.error(request, 'No tiene permisos para agregar equipos.')
        return redirect('equipos:lista')

    if request.method == 'POST':
        form = FormularioEquipo(request.POST)
        if form.is_valid():
            equipo = form.save()
            messages.success(request, f'Equipo "{equipo.nombre}" agregado correctamente al catálogo.')
            return redirect('equipos:detalle', pk=equipo.pk)
        else:
            messages.error(request, 'Por favor corrija los errores en el formulario.')
    else:
        form = FormularioEquipo()

    return render(request, 'equipos/form_equipo.html', {
        'form':   form,
        'titulo': 'Nuevo equipo',
        'accion': 'Agregar al catálogo',
    })


# ─── Editar equipo ────────────────────────────────────────────────────────────
@never_cache
@login_required
def editar_equipo(request, pk):
    if not (request.user.es_operador or request.user.es_especialista or request.user.es_directivo):
        messages.error(request, 'No tiene permisos para editar equipos.')
        return redirect('equipos:lista')

    equipo = get_object_or_404(Equipo, pk=pk)

    if request.method == 'POST':
        form = FormularioEquipo(request.POST, instance=equipo)
        if form.is_valid():
            equipo = form.save()
            messages.success(request, f'Equipo "{equipo.nombre}" actualizado correctamente.')
            return redirect('equipos:detalle', pk=equipo.pk)
        else:
            messages.error(request, 'Por favor corrija los errores en el formulario.')
    else:
        form = FormularioEquipo(instance=equipo)

    return render(request, 'equipos/form_equipo.html', {
        'form':   form,
        'equipo': equipo,
        'titulo': f'Editar — {equipo.nombre}',
        'accion': 'Guardar cambios',
    })


# ─── Desactivar equipo ────────────────────────────────────────────────────────
@never_cache
@login_required
def desactivar_equipo(request, pk):
    if not (request.user.es_operador or request.user.es_directivo):
        messages.error(request, 'No tiene permisos para realizar esta acción.')
        return redirect('equipos:lista')

    equipo = get_object_or_404(Equipo, pk=pk)

    if request.method == 'POST':
        equipo.activo = not equipo.activo
        equipo.save()
        estado = 'activado' if equipo.activo else 'desactivado'
        messages.success(request, f'Equipo "{equipo.nombre}" {estado} correctamente.')
        return redirect('equipos:detalle', pk=equipo.pk)

    return redirect('equipos:detalle', pk=equipo.pk)


# ─── Categorías ───────────────────────────────────────────────────────────────
@never_cache
@login_required
def lista_categorias(request):
    if not (request.user.es_operador or request.user.es_especialista or request.user.es_directivo):
        messages.error(request, 'No tiene permisos para acceder a esta sección.')
        return redirect('equipos:lista')

    if request.method == 'POST':
        form = FormularioCategoria(request.POST)
        if form.is_valid():
            cat = form.save()
            messages.success(request, f'Categoría "{cat.nombre}" creada correctamente.')
            return redirect('equipos:categorias')
        else:
            messages.error(request, 'Por favor corrija los errores.')
    else:
        form = FormularioCategoria()

    categorias = CategoriaEquipo.objects.all()
    return render(request, 'equipos/categorias.html', {
        'categorias': categorias,
        'form':       form,
    })


# ─── Búsqueda AJAX para el formulario F43 ────────────────────────────────────
@login_required
def buscar_equipos_ajax(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'equipos': []})

    equipos = Equipo.objects.filter(
        Q(nombre__icontains=q) |
        Q(marca__icontains=q)  |
        Q(modelo__icontains=q),
        activo=True
    )[:10]

    data = [{
        'id':          e.pk,
        'nombre':      e.nombre,
        'marca':       e.marca,
        'modelo':      e.modelo,
        'banda':       e.get_banda_frecuencia_display(),
        'restringido': e.es_restringido,
        'libre':       e.es_banda_libre,
    } for e in equipos]

    return JsonResponse({'equipos': data})