from threading import Thread

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags


# ==============================================================================
# ENVÍO ASÍNCRONO
# ==============================================================================

class EmailThread(Thread):
    """
    Envía el correo en segundo plano para no bloquear la petición HTTP.
    """

    def __init__(self, email):
        Thread.__init__(self)
        self.email = email

    def run(self):
        try:
            self.email.send(fail_silently=True)
        except Exception as e:
            print(f"[EMAIL ERROR] {e}")


# ==============================================================================
# ENVÍO GENERAL
# ==============================================================================

def enviar_correo_notificacion(
    usuario,
    titulo,
    mensaje,
    solicitud=None,
    template="notificaciones/emails/usuario.html",
    contexto=None,
    cc=None,
    bcc=None,
    reply_to=None,
    archivos=None,
):
    """
    Envío general de correos del sistema.
    """

    if usuario is None:
        return False

    if not usuario.email:
        return False

    contexto = contexto or {}

    contexto.update(
        {
            "usuario": usuario,
            "titulo": titulo,
            "mensaje": mensaje,
            "solicitud": solicitud,
            "app_nombre": getattr(
                settings,
                "APP_NAME",
                "Sistema de Autorizaciones",
            ),
            "app_url": getattr(
                settings,
                "APP_URL",
                "",
            ),
        }
    )

    html = render_to_string(
        template,
        contexto,
    )

    texto = strip_tags(html)

    email = EmailMultiAlternatives(
        subject=titulo,
        body=texto,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[usuario.email],
        cc=cc or [],
        bcc=bcc or [],
        reply_to=reply_to or [],
    )

    email.attach_alternative(
        html,
        "text/html",
    )

    if archivos:

        for archivo in archivos:

            nombre, contenido, mimetype = archivo

            email.attach(
                nombre,
                contenido,
                mimetype,
            )

    EmailThread(email).start()

    return True