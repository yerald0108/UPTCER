from .models import Notificacion
from apps.accounts.models import Usuario
from .emails import enviar_correo_notificacion


# ==============================================================================
# FUNCIÓN PRINCIPAL
# ==============================================================================

def notificar(
    destinatario,
    tipo,
    titulo,
    mensaje,
    solicitud=None,
    enviar_email=True,
    template=None,
    contexto_extra=None,
):
    """
    Crea una notificación en la base de datos y opcionalmente envía un correo.

    Parámetros
    ----------
    destinatario : Usuario
    tipo : str
    titulo : str
    mensaje : str
    solicitud : Solicitud | None
    enviar_email : bool
    template : str | None
        Template HTML a utilizar.
    contexto_extra : dict | None
        Información adicional para el template.
    """

    notificacion = Notificacion.objects.create(
        destinatario=destinatario,
        tipo=tipo,
        titulo=titulo,
        mensaje=mensaje,
        solicitud=solicitud,
    )

    # Si el usuario no posee correo simplemente termina.
    if (
        enviar_email
        and destinatario
        and getattr(destinatario, "email", None)
    ):

        contexto = {
            "titulo": titulo,
            "mensaje": mensaje,
            "usuario": destinatario,
            "solicitud": solicitud,
            "notificacion": notificacion,
        }

        if contexto_extra:
            contexto.update(contexto_extra)

        # Selección automática del template según el rol
        if template is None:

            if destinatario.es_especialista_superior:
                template = "notificaciones/emails/especialista.html"

            elif destinatario.es_especialista_base:
                template = "notificaciones/emails/especialista.html"

            elif destinatario.es_directivo:
                template = "notificaciones/emails/administrador.html"

            else:
                template = "notificaciones/emails/usuario.html"

        enviar_correo_notificacion(
            usuario=destinatario,
            titulo=titulo,
            mensaje=mensaje,
            solicitud=solicitud,
            template=template,
            contexto=contexto,
        )

    return notificacion


# Mapa de categoría de solicitud → rol de especialista
CATEGORIA_A_ROL = {
    'radiofaro': Usuario.ROL_ESPECIALISTA_RADIOFARO,
    'movil':     Usuario.ROL_ESPECIALISTA_MOVIL,
    'maritimo':  Usuario.ROL_ESPECIALISTA_MARITIMO,
    'internet':  Usuario.ROL_ESPECIALISTA_INTERNET,
}


def notificar_especialistas_por_categoria(
    categoria,
    tipo,
    titulo,
    mensaje,
    solicitud=None,
    enviar_email=True,
):
    """Notifica a los especialistas del rol correspondiente a la categoría."""
    rol = CATEGORIA_A_ROL.get(categoria)
    if not rol:
        return

    especialistas = Usuario.objects.filter(
        rol=rol,
        is_active=True,
    )

    for especialista in especialistas:
        notificar(
            destinatario=especialista,
            tipo=tipo,
            titulo=titulo,
            mensaje=mensaje,
            solicitud=solicitud,
            enviar_email=enviar_email,
        )


def notificar_especialistas_superiores(
    tipo,
    titulo,
    mensaje,
    solicitud=None,
    enviar_email=True,
):
    """Notifica a todos los especialistas superiores."""
    superiores = Usuario.objects.filter(
        rol=Usuario.ROL_ESPECIALISTA_SUPERIOR,
        is_active=True,
    )

    for superior in superiores:
        notificar(
            destinatario=superior,
            tipo=tipo,
            titulo=titulo,
            mensaje=mensaje,
            solicitud=solicitud,
            enviar_email=enviar_email,
        )


def notificar_directivos(
    tipo,
    titulo,
    mensaje,
    solicitud=None,
    enviar_email=True,
):
    """Notifica a todos los directivos."""
    directivos = Usuario.objects.filter(
        rol=Usuario.ROL_DIRECTIVO,
        is_active=True,
    )

    for directivo in directivos:
        notificar(
            destinatario=directivo,
            tipo=tipo,
            titulo=titulo,
            mensaje=mensaje,
            solicitud=solicitud,
            enviar_email=enviar_email,
        )


# ==============================================================================
# ESPECIALISTAS
# ==============================================================================

def notificar_especialistas(
    tipo,
    titulo,
    mensaje,
    solicitud=None,
    enviar_email=True,
):

    especialistas = Usuario.objects.filter(
        rol=Usuario.ROL_ESPECIALISTA,
        is_active=True,
    )

    for especialista in especialistas:

        notificar(
            destinatario=especialista,
            tipo=tipo,
            titulo=titulo,
            mensaje=mensaje,
            solicitud=solicitud,
            enviar_email=enviar_email,
        )


# ==============================================================================
# NUEVA SOLICITUD
# ==============================================================================

def notificar_solicitud_nueva(solicitud):
    """Notifica al especialista del área correspondiente a la categoría."""
    titulo = f"Nueva solicitud {solicitud.numero}"

    mensaje = (
        f"El solicitante "
        f"{solicitud.solicitante.get_nombre_completo()} "
        f"ha registrado una nueva solicitud "
        f"({solicitud.get_flujo_display()}) "
        f"de categoría {solicitud.get_categoria_display()}."
    )

    notificar_especialistas_por_categoria(
        categoria=solicitud.categoria,
        tipo=Notificacion.TIPO_SOLICITUD_NUEVA,
        titulo=titulo,
        mensaje=mensaje,
        solicitud=solicitud,
    )


# ==============================================================================
# DERIVACIÓN A ESPECIALISTA
# ==============================================================================

def notificar_derivacion_superior(solicitud):
    """Notifica al especialista superior cuando el equipo no está listado."""
    titulo = f"Equipo no listado — {solicitud.numero}"

    mensaje = (
        f"La solicitud {solicitud.numero} "
        f"requiere evaluación de equipo no listado.\n\n"
        f"Categoría: {solicitud.get_categoria_display()}\n"
        f"Solicitante: {solicitud.solicitante.get_nombre_completo()}"
    )

    notificar_especialistas_superiores(
        tipo=Notificacion.TIPO_DERIVADA_ESPECIALISTA,
        titulo=titulo,
        mensaje=mensaje,
        solicitud=solicitud,
    )


def notificar_pendiente_aprobacion(solicitud):
    """Notifica al directivo que una solicitud está lista para aprobación."""
    titulo = f"Solicitud lista para aprobación — {solicitud.numero}"

    mensaje = (
        f"La solicitud {solicitud.numero} "
        f"ha sido revisada y está pendiente de aprobación.\n\n"
        f"Categoría: {solicitud.get_categoria_display()}\n"
        f"Solicitante: {solicitud.solicitante.get_nombre_completo()}"
    )

    notificar_directivos(
        tipo=Notificacion.TIPO_CAMBIO_ESTADO,
        titulo=titulo,
        mensaje=mensaje,
        solicitud=solicitud,
    )


# ==============================================================================
# CAMBIO DE ESTADO
# ==============================================================================

def notificar_cambio_estado(
    solicitud,
    estado_anterior,
    usuario_responsable,
):

    estado_viejo = dict(
        solicitud.ESTADOS
    ).get(
        estado_anterior,
        estado_anterior,
    )

    estado_nuevo = solicitud.get_estado_display()

    titulo = f"Solicitud {solicitud.numero} actualizada"

    mensaje = (
        f"Su solicitud "
        f"{solicitud.numero} "
        f"ha cambiado de estado.\n\n"
        f"Estado anterior: {estado_viejo}\n"
        f"Nuevo estado: {estado_nuevo}\n\n"
        f"Responsable:\n"
        f"{usuario_responsable.get_nombre_completo()}"
    )

    notificar(
        destinatario=solicitud.solicitante,
        tipo=Notificacion.TIPO_CAMBIO_ESTADO,
        titulo=titulo,
        mensaje=mensaje,
        solicitud=solicitud,
        contexto_extra={
            "estado_anterior": estado_viejo,
            "estado_actual": estado_nuevo,
            "responsable": usuario_responsable,
        },
    )


# ==============================================================================
# CRITERIO TÉCNICO
# ==============================================================================

def notificar_criterio_tecnico(solicitud):
    """Notifica al directivo que el especialista superior emitió criterio técnico."""
    titulo = (
        f"Criterio técnico emitido — "
        f"{solicitud.numero}"
    )

    mensaje = (
        f"El especialista superior ha emitido "
        f"su criterio para la solicitud "
        f"{solicitud.numero}.\n\n"
        f"Ya puede continuar con la resolución."
    )

    notificar_directivos(
        tipo=Notificacion.TIPO_CRITERIO_TECNICO,
        titulo=titulo,
        mensaje=mensaje,
        solicitud=solicitud,
    )