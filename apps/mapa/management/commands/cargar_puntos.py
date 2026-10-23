import json
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.mapa.models import PuntoMapa

class Command(BaseCommand):
    help = 'Carga puntos desde un archivo JSON (sin problemas con auto_now_add)'

    def handle(self, *args, **options):
        fixture_path = os.path.join(settings.BASE_DIR, 'apps', 'mapa', 'fixtures', 'puntos_iniciales.json')
        if not os.path.exists(fixture_path):
            self.stdout.write(self.style.ERROR(f'Archivo no encontrado: {fixture_path}'))
            return

        with open(fixture_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for item in data:
            fields = item['fields']
            obj = PuntoMapa.objects.create(
                nombre=fields['nombre'],
                tipo=fields['tipo'],
                latitud=fields['latitud'],
                longitud=fields['longitud'],
                estado=fields.get('estado', 'ACTIVO'),
                atributos=fields.get('atributos', {}),
                descripcion=fields.get('descripcion', ''),
                responsable=fields.get('responsable', ''),
                fecha_instalacion=fields.get('fecha_instalacion'),
                ultima_revision=fields.get('ultima_revision'),
            )
            self.stdout.write(self.style.SUCCESS(f'Creado: {obj}'))

        self.stdout.write(self.style.SUCCESS('¡Carga completada!'))