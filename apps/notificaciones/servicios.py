from .models import Notificacion
from apps.accounts.models import Usuario


def notificar(destinatario, tipo, titulo, mensaje, solicitud=None):
    """Crea una notificación para un usuario."""
    return Notificacion.objects.create(
        destinatario = destinatario,
        tipo         = tipo,
        titulo       = titulo,
        mensaje      = mensaje,
        solicitud    = solicitud,
    )


def notificar_operadores(tipo, titulo, mensaje, solicitud=None):
    """Notifica a todos los operadores activos."""
    operadores = Usuario.objects.filter(
        rol=Usuario.ROL_OPERADOR,
        is_active=True
    )
    for operador in operadores:
        notificar(operador, tipo, titulo, mensaje, solicitud)


def notificar_especialistas(tipo, titulo, mensaje, solicitud=None):
    """Notifica a todos los especialistas técnicos activos."""
    especialistas = Usuario.objects.filter(
        rol=Usuario.ROL_ESPECIALISTA,
        is_active=True
    )
    for especialista in especialistas:
        notificar(especialista, tipo, titulo, mensaje, solicitud)


def notificar_solicitud_nueva(solicitud):
    """Notifica a operadores cuando llega una nueva solicitud F43."""
    notificar_operadores(
        tipo      = Notificacion.TIPO_SOLICITUD_NUEVA,
        titulo    = f'Nueva solicitud {solicitud.numero}',
        mensaje   = (
            f'El solicitante {solicitud.solicitante.get_nombre_completo()} '
            f'ha enviado una nueva solicitud de autorización técnica ({solicitud.get_flujo_display()}).'
        ),
        solicitud = solicitud,
    )


def notificar_derivacion_especialista(solicitud):
    """Notifica a especialistas cuando una solicitud tiene equipo no listado."""
    # Construir descripción del equipo de forma segura
    marca  = solicitud.equipo_marca_manual or ''
    modelo = solicitud.equipo_modelo_manual or ''
    descripcion_equipo = f'{marca} {modelo}'.strip()
    
    if not descripcion_equipo:
        descripcion_equipo = 'equipo no identificado'
    
    notificar_especialistas(
        tipo      = Notificacion.TIPO_DERIVADA_ESPECIALISTA,
        titulo    = f'Equipo no listado — {solicitud.numero}',
        mensaje   = (
            f'La solicitud {solicitud.numero} contiene un equipo no registrado en el catálogo '
            f'({descripcion_equipo}). '
            f'Se requiere evaluación técnica.'
        ),
        solicitud = solicitud,
    )


def notificar_cambio_estado(solicitud, estado_anterior, usuario_responsable):
    """Notifica al solicitante cuando cambia el estado de su solicitud."""
    notificar(
        destinatario = solicitud.solicitante,
        tipo         = Notificacion.TIPO_CAMBIO_ESTADO,
        titulo       = f'Solicitud {solicitud.numero} actualizada',
        mensaje      = (
            f'Su solicitud {solicitud.numero} ha cambiado de estado: '
            f'"{dict(solicitud.ESTADOS).get(estado_anterior, estado_anterior)}" → '
            f'"{solicitud.get_estado_display()}". '
            f'Realizado por: {usuario_responsable.get_nombre_completo()}.'
        ),
        solicitud    = solicitud,
    )


def notificar_criterio_tecnico(solicitud):
    """Notifica a operadores cuando el especialista emite criterio técnico."""
    notificar_operadores(
        tipo      = Notificacion.TIPO_CRITERIO_TECNICO,
        titulo    = f'Criterio técnico emitido — {solicitud.numero}',
        mensaje   = (
            f'El especialista técnico ha emitido su criterio sobre la solicitud {solicitud.numero}. '
            f'Puede proceder con la resolución final.'
        ),
        solicitud = solicitud,
    )