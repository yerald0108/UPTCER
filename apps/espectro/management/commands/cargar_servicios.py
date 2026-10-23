from django.core.management.base import BaseCommand
from apps.espectro.models import FactorServicio


# ============================================================
# TODOS LOS SERVICIOS DE LOS ANEXOS I Y II DE LA RESOLUCIÓN 20/2025
# ============================================================
# Estructura: (categoria, subcategoria, valor_c)
# El grupo se asigna por separado.

SERVICIOS_GRUPO_1 = [
    # 1. SERVICIO FIJO
    # a) Servicio fijo punto a punto
    ("Servicio fijo", "Fijo punto a punto - Monocanales", 8),
    ("Servicio fijo", "Fijo punto a punto - Radioenlaces < 800 MHz", 3.5),
    ("Servicio fijo", "Fijo punto a punto - Radioenlaces de 800 MHz a 3 GHz", 70),
    ("Servicio fijo", "Fijo punto a punto - Radioenlaces de 3 GHz a 10 GHz y más de 24 GHz", 700),
    ("Servicio fijo", "Fijo punto a punto - Radioenlaces de 10 GHz a 24 GHz", 5000),
    ("Servicio fijo", "Control remoto de audio de alta calidad", 10),
    ("Servicio fijo", "Control remoto de audio y video o televisión", 100),
    ("Servicio fijo", "Telemando, telecontrol, telemedida no considerados corto alcance", 1500),
    # b) Servicio fijo punto a multipunto
    ("Servicio fijo", "Fijo punto a multipunto - Transmisores de HF", 10),
    ("Servicio fijo", "Fijo punto a multipunto - Acceso fijo inalámbrico FWA", 10),
    ("Servicio fijo", "Fijo punto a multipunto - WiMax fijo", 2),

    # 2. SERVICIO FIJO POR SATÉLITE
    ("Servicio fijo por satélite", "Estaciones terrenas fijas", 0.4),
    ("Servicio fijo por satélite", "VSAT", 8),
    ("Servicio fijo por satélite", "Terminal fijo por satélite con voz y datos", 20),

    # 3. SERVICIO MÓVIL
    # a) Móvil terrestre
    ("Servicio móvil", "Móvil terrestre en 7 m", 3),
    ("Servicio móvil", "Móvil terrestre en 2 m", 55),
    ("Servicio móvil", "Móvil terrestre en 70 cm", 55),
    ("Servicio móvil", "Móvil terrestre (onda corta)", 10),
    ("Servicio móvil", "GSM-R", 5),
    ("Servicio móvil", "Radiobase Celular 2G/GSM, 3G/UMTS, 4G/LTE", 2),
    ("Servicio móvil", "Radiobase Celular 5G - 700 MHz", 2),
    ("Servicio móvil", "Radiobase Celular 5G - 3,5 GHz", 2),
    ("Servicio móvil", "Radiobase Celular 5G - 28 GHz", 15),
    ("Servicio móvil", "Radiobase sistema público troncalizadas analógicas", 2),
    ("Servicio móvil", "Radiobase sistema privado troncalizadas analógicas", 2),
    ("Servicio móvil", "Radiobase sistema troncalizadas digitales LTE", 1),
    ("Servicio móvil", "WiMax móvil", 4),
    # b) Móvil marítimo
    ("Servicio móvil", "Marítimo - Estaciones fijas SMM", 150),
    ("Servicio móvil", "Marítimo - Estaciones fijas SMM de HF", 3),
    ("Servicio móvil", "Marítimo - Estaciones móviles personales", 150),
    # c) Móvil aeronáutico
    ("Servicio móvil", "Aeronáutico - Estaciones fijas SMA", 10),
    ("Servicio móvil", "Aeronáutico - Estaciones fijas SMA de HF", 100),
    ("Servicio móvil", "Aeronáutico - Estaciones móviles personales", 200),
    ("Servicio móvil", "Aeronáutico - Drones", 1),
    ("Servicio móvil", "Aeronáutico - Cetrería robótica", 1),

    # 4. SERVICIO MÓVIL POR SATÉLITE
    ("Servicio móvil por satélite", "Móvil terrestre por satélite con voz y datos", 0.4),
    ("Servicio móvil por satélite", "Móvil terrestre por satélite con voz", 0.4),
    ("Servicio móvil por satélite", "Móvil marítimo por satélite con voz", 0.4),
    ("Servicio móvil por satélite", "Móvil marítimo por satélite con voz y datos", 0.07),
    ("Servicio móvil por satélite", "Móvil aeronáutico por satélite con voz y datos", 0.07),

    # 5. SERVICIO DE RADIODIFUSIÓN TERRENAL
    ("Radiodifusión terrenal", "Emisión sonora - Radiodifusión de onda media", 60),
    ("Radiodifusión terrenal", "Emisión sonora - Radiodifusión de frecuencia modulada", 3),
    ("Radiodifusión terrenal", "Emisión sonora - Radiodifusión de HF", 0.2),
    ("Radiodifusión terrenal", "Televisión analógica", 0.13),
    ("Radiodifusión terrenal", "Televisión digital", 0.13),

    # 6. SERVICIO DE RADIODETERMINACIÓN
    ("Radiodeterminación", "Radiolocalización - Radares", 0.5),
    ("Radiodeterminación", "Radiolocalización - Radares marinos de HF", 0.01),
    ("Radiodeterminación", "Radiolocalización - Radiobaliza marítima VHF y UHF", 150),
    ("Radiodeterminación", "Radiolocalización - Radiomodem incluye GPS diferencial", 5000),
    ("Radiodeterminación", "Radiolocalización - Estación radiobúsqueda (BIPER)", 20),
    ("Radiodeterminación", "Radionavegación - Radiofaros aeronáuticos", 200),
    ("Radiodeterminación", "Radionavegación - Estación fija SMA VOR, ILS y DME", 30),
    ("Radiodeterminación", "Radionavegación - Radiofaros marítimos", 100),
    ("Radiodeterminación", "Radionavegación - Estación fija costera NAVTEX", 250),

    # 7. SERVICIO DE RADIODETERMINACIÓN POR SATÉLITE
    ("Radiodeterminación por satélite", "Radiobaliza marítima por satélite", 3),
    ("Radiodeterminación por satélite", "Radiobaliza marítima por satélite y en VHF o UHF", 0.3),
]


SERVICIOS_GRUPO_2 = [
    # 1. SERVICIO FIJO
    # a) Servicio fijo punto a punto
    ("Servicio fijo", "Fijo punto a punto - Radioenlaces < 800 MHz", 0.146),
    ("Servicio fijo", "Fijo punto a punto - Radioenlaces de 800 MHz a 3 GHz", 2.917),
    ("Servicio fijo", "Fijo punto a punto - Radioenlaces de 3 GHz a 10 GHz y más de 24 GHz", 29.167),
    ("Servicio fijo", "Fijo punto a punto - Radioenlaces de 10 GHz a 24 GHz", 208.333),
    ("Servicio fijo", "Control remoto de audio de alta calidad", 0.417),
    ("Servicio fijo", "Control remoto de audio y video o televisión", 4.167),
    ("Servicio fijo", "Telemando, telecontrol, telemedida no considerados corto alcance", 62.5),
    # b) Servicio fijo punto a multipunto
    ("Servicio fijo", "Fijo punto a multipunto - Transmisores de HF", 0.417),
    ("Servicio fijo", "Fijo punto a multipunto - WiMax fijo", 0.083),

    # 2. SERVICIO FIJO POR SATÉLITE
    ("Servicio fijo por satélite", "VSAT", 0.333),
    ("Servicio fijo por satélite", "Terminal fijo por satélite con voz y datos", 0.833),

    # 3. SERVICIO MÓVIL
    # a) Móvil terrestre
    ("Servicio móvil", "Móvil terrestre en 7 m", 0.125),
    ("Servicio móvil", "Móvil terrestre en 2 m", 2.292),
    ("Servicio móvil", "Móvil terrestre en 70 cm", 2.292),
    # b) Móvil marítimo
    ("Servicio móvil", "Marítimo - Estaciones fijas SMM", 6.25),
    ("Servicio móvil", "Marítimo - Estaciones fijas SMM de HF", 0.125),
    ("Servicio móvil", "Marítimo - Estaciones móviles personales", 6.25),
    # c) Móvil aeronáutico
    ("Servicio móvil", "Aeronáutico - Estaciones fijas SMA", 0.417),
    ("Servicio móvil", "Aeronáutico - Estaciones fijas SMA de HF", 0.417),
    ("Servicio móvil", "Aeronáutico - Estaciones móviles personales", 8.333),

    # 4. SERVICIO MÓVIL POR SATÉLITE
    ("Servicio móvil por satélite", "Móvil terrestre por satélite con voz y datos", 0.017),
    ("Servicio móvil por satélite", "Móvil terrestre por satélite con voz", 0.017),
    ("Servicio móvil por satélite", "Móvil marítimo por satélite con voz", 0.017),
    ("Servicio móvil por satélite", "Móvil marítimo por satélite con voz y datos", 0.003),
    ("Servicio móvil por satélite", "Móvil aeronáutico por satélite con voz y datos", 0.003),

    # 5. SERVICIO DE RADIODETERMINACIÓN
    ("Radiodeterminación", "Radiolocalización - Radiobaliza marítima VHF y UHF", 6.25),
    ("Radiodeterminación", "Radiolocalización - Radiomodem incluye GPS diferencial", 208.333),

    # 6. SERVICIO DE RADIODETERMINACIÓN POR SATÉLITE
    ("Radiodeterminación por satélite", "Radiobaliza marítima por satélite", 0.125),
    ("Radiodeterminación por satélite", "Radiobaliza marítima por satélite y en VHF o UHF", 0.125),
]


class Command(BaseCommand):
    help = 'Carga todos los servicios de los Anexos I y II diferenciados por grupo'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limpiar',
            action='store_true',
            help='Elimina todos los servicios existentes antes de cargar',
        )

    def handle(self, *args, **options):
        if options['limpiar']:
            eliminados = FactorServicio.objects.all().delete()
            self.stdout.write(self.style.WARNING(
                f'Eliminados {eliminados[0]} registros previos'
            ))

        creados = 0
        actualizados = 0

        # --- Grupo 1 (CUP) ---
        for categoria, subcategoria, valor in SERVICIOS_GRUPO_1:
            obj, created = FactorServicio.objects.update_or_create(
                grupo='1',
                subcategoria=subcategoria,
                defaults={
                    'categoria': categoria,
                    'valor_c': valor,
                    'activo': True,
                }
            )
            if created:
                creados += 1
            else:
                actualizados += 1

        # --- Grupo 2 (USD) ---
        for categoria, subcategoria, valor in SERVICIOS_GRUPO_2:
            obj, created = FactorServicio.objects.update_or_create(
                grupo='2',
                subcategoria=subcategoria,
                defaults={
                    'categoria': categoria,
                    'valor_c': valor,
                    'activo': True,
                }
            )
            if created:
                creados += 1
            else:
                actualizados += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nCarga completada:'
            f'\n   - Creados: {creados}'
            f'\n   - Actualizados: {actualizados}'
            f'\n   - Total Grupo 1 (CUP): {FactorServicio.objects.filter(grupo="1").count()}'
            f'\n   - Total Grupo 2 (USD): {FactorServicio.objects.filter(grupo="2").count()}'
        ))