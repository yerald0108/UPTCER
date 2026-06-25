from django import forms
from .models import Solicitud


class FormularioF43(forms.ModelForm):

    # ─── Campos adicionales no en el modelo directamente ─────────────────────
    MODO_EQUIPAJE   = 'equipaje'
    MODO_RAD        = 'rad'
    MODO_CARGA      = 'carga'

    MODOS = [
        (MODO_EQUIPAJE, 'Equipaje acompañante'),
        (MODO_RAD,      'Documento de Retención Aduanal (RAD)'),
        (MODO_CARGA,    'Carga acompañante'),
    ]

    OBJETIVO_EMPLEO  = 'empleo_directo'
    OBJETIVO_MUESTRA = 'muestra_expositiva'
    OBJETIVO_OTROS   = 'otros'

    OBJETIVOS = [
        (OBJETIVO_EMPLEO,  'Empleo directo'),
        (OBJETIVO_MUESTRA, 'Muestra expositiva'),
        (OBJETIVO_OTROS,   'Otros'),
    ]

    PERIODO_DEFINITIVA = 'definitiva'
    PERIODO_TEMPORAL   = 'temporal'

    PERIODOS = [
        (PERIODO_DEFINITIVA, 'Definitiva'),
        (PERIODO_TEMPORAL,   'Temporal'),
    ]

    PROVINCIAS = [
        ('', 'Seleccione una provincia'),
        ('pinar_del_rio',    'Pinar del Río'),
        ('artemisa',         'Artemisa'),
        ('la_habana',        'La Habana'),
        ('mayabeque',        'Mayabeque'),
        ('matanzas',         'Matanzas'),
        ('cienfuegos',       'Cienfuegos'),
        ('villa_clara',      'Villa Clara'),
        ('sancti_spiritus',  'Sancti Spíritus'),
        ('ciego_de_avila',   'Ciego de Ávila'),
        ('camaguey',         'Camagüey'),
        ('las_tunas',        'Las Tunas'),
        ('granma',           'Granma'),
        ('holguin',          'Holguín'),
        ('santiago_de_cuba', 'Santiago de Cuba'),
        ('guantanamo',       'Guantánamo'),
        ('isla_de_la_juventud', 'Isla de la Juventud'),
    ]

    # Datos del solicitante
    nombre_apellidos    = forms.CharField(
                            label='Nombre y apellidos del solicitante',
                            max_length=200,
                            widget=forms.TextInput(attrs={'placeholder': 'Nombre completo del solicitante'})
                          )
    numero_pasaporte    = forms.CharField(
                            label='Número de pasaporte o carné de identidad',
                            max_length=50,
                            widget=forms.TextInput(attrs={'placeholder': 'Ej: A12345678'})
                          )
    pais_residencia     = forms.CharField(
                            label='País de residencia',
                            max_length=100,
                            initial='Cuba',
                            widget=forms.TextInput(attrs={'placeholder': 'País de residencia'})
                          )
    direccion_residencia= forms.CharField(
                            label='Dirección de residencia',
                            widget=forms.TextInput(attrs={'placeholder': 'Calle, número, municipio'})
                          )
    correo_electronico  = forms.EmailField(
                            label='Correo electrónico',
                            widget=forms.EmailInput(attrs={'placeholder': 'correo@ejemplo.cu'})
                          )
    telefono            = forms.CharField(
                            label='Teléfono',
                            max_length=20,
                            widget=forms.TextInput(attrs={'placeholder': '+53 5 000 0000'})
                          )

    # Datos de importación
    provincia           = forms.ChoiceField(
                            label='Provincia donde será realizada la solicitud',
                            choices=PROVINCIAS,
                          )
    modo_importacion    = forms.ChoiceField(
                            label='Modo de la importación',
                            choices=MODOS,
                            widget=forms.RadioSelect,
                          )
    numero_vuelo        = forms.CharField(
                            label='No. de vuelo',
                            max_length=20,
                            required=False,
                            widget=forms.TextInput(attrs={'placeholder': 'Ej: CU123'})
                          )
    fecha_arribo        = forms.DateField(
                            label='Fecha de arribo',
                            required=False,
                            widget=forms.DateInput(attrs={'type': 'date'})
                          )
    pais_procedencia    = forms.CharField(
                            label='País de procedencia',
                            max_length=100,
                            required=False,
                            widget=forms.TextInput(attrs={'placeholder': 'País de origen del viaje'})
                          )
    aduana_acceso       = forms.CharField(
                            label='Aduana de acceso',
                            max_length=100,
                            required=False,
                            widget=forms.TextInput(attrs={'placeholder': 'Ej: Aeropuerto, Puerto, Aduana Postal'})
                          )
    lugar_acceso        = forms.CharField(
                            label='Lugar de acceso',
                            max_length=100,
                            required=False,
                            widget=forms.TextInput(attrs={'placeholder': 'Ej: Aeropuerto José Martí'})
                          )
    numero_rad          = forms.CharField(
                            label='No. del RAD',
                            max_length=50,
                            required=False,
                            widget=forms.TextInput(attrs={'placeholder': 'Número del documento de retención aduanal'})
                          )
    objetivo_importacion= forms.ChoiceField(
                            label='Objetivo de la importación',
                            choices=OBJETIVOS,
                            widget=forms.RadioSelect,
                          )
    objetivo_otros_detalle = forms.CharField(
                            label='Especifique el objetivo',
                            max_length=200,
                            required=False,
                            widget=forms.TextInput(attrs={'placeholder': 'Describa el objetivo de la importación'})
                          )
    periodo_importacion = forms.ChoiceField(
                            label='Período de la importación',
                            choices=PERIODOS,
                            widget=forms.RadioSelect,
                          )
    tiempo_solicitado   = forms.IntegerField(
                            label='Tiempo solicitado (meses)',
                            required=False,
                            min_value=1,
                            max_value=60,
                            widget=forms.NumberInput(attrs={'placeholder': 'Cantidad de meses', 'min': 1, 'max': 60})
                          )

    # Documento adjunto
    documento_adjunto   = forms.FileField(
                            label='Documento adjunto (opcional)',
                            required=False,
                            help_text='Adjunte el modelo F43 firmado si lo tiene disponible (PDF, JPG, PNG)'
                          )

    class Meta:
        model  = Solicitud
        fields = ['observaciones_solicitante']
        labels = {
            'observaciones_solicitante': 'Observaciones adicionales',
        }
        widgets = {
            'observaciones_solicitante': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Información adicional que desee agregar a la solicitud'
            }),
        }

    def clean(self):
        cleaned = super().clean()
        modo    = cleaned.get('modo_importacion')
        periodo = cleaned.get('periodo_importacion')
        objetivo= cleaned.get('objetivo_importacion')

        # Si el modo es RAD, el número de RAD es obligatorio
        if modo == self.MODO_RAD and not cleaned.get('numero_rad'):
            self.add_error('numero_rad', 'El número de RAD es obligatorio para este modo de importación.')

        # Si el período es temporal, el tiempo es obligatorio
        if periodo == self.PERIODO_TEMPORAL and not cleaned.get('tiempo_solicitado'):
            self.add_error('tiempo_solicitado', 'Debe especificar el tiempo solicitado para importación temporal.')

        # Si el objetivo es "Otros", debe especificar
        if objetivo == self.OBJETIVO_OTROS and not cleaned.get('objetivo_otros_detalle'):
            self.add_error('objetivo_otros_detalle', 'Debe especificar el objetivo de la importación.')

        return cleaned