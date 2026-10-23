from django import forms
from django.core.exceptions import ValidationError
from .models import FactorServicio


class CalculoEspectroForm(forms.Form):
    # --- Grupo (oculto, viene de la URL) ---
    grupo = forms.ChoiceField(
        choices=[('1', 'Grupo 1 (CUP)'), ('2', 'Grupo 2 (USD)')],
        widget=forms.HiddenInput()
    )

    # --- Selección de servicio (dinámico según grupo) ---
    servicio = forms.ChoiceField(
        choices=[],
        label='Tipo de servicio',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    # --- Parámetros técnicos comunes ---
    fc = forms.FloatField(
        label='Frecuencia central (MHz)',
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'ej: 900'})
    )
    htx = forms.FloatField(
        label='Altura antena transmisora (m)',
        min_value=0,
        initial=30,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    hrx = forms.FloatField(
        label='Altura antena receptora (m)',
        min_value=0,
        initial=1.5,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    pt = forms.FloatField(
        label='Potencia transmisor (dBm)',
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'ej: 40'})
    )
    gax = forms.FloatField(
        label='Ganancia antena (dBi)',
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'ej: 10'})
    )
    lt_constante = forms.FloatField(
        label='Constante de pérdidas (Lt)',
        initial=65,
        help_text='56 para FM, 65 para TV analógica, 70 para TV digital',
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    diff = forms.FloatField(
        label='Factor diff',
        initial=0,
        help_text='0 para microceldas, 10 para FM/TV',
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    # --- Método de cálculo del ancho de banda B ---
    METODO_B_CHOICES = [
        ('estandar', 'Por rango de frecuencias (fi, ff)'),
        ('satelital', 'Por velocidad y modulación (satelital)'),
    ]
    metodo_b = forms.ChoiceField(
        choices=METODO_B_CHOICES,
        label='Método para calcular B',
        initial='estandar',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'metodo_b'})
    )

    fi = forms.FloatField(
        label='Frecuencia inicial (MHz)',
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'ej: 700'})
    )
    ff = forms.FloatField(
        label='Frecuencia final (MHz)',
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'ej: 800'})
    )

    velocidad_mbps = forms.FloatField(
        label='Velocidad contratada (Mbps)',
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'ej: 2'})
    )
    modulacion = forms.ChoiceField(
        choices=[('MQPSK', 'MQPSK'), ('8PSK', '8PSK'), ('16APSK', '16APSK'), ('32APSK', '32APSK')],
        label='Modulación',
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    # --- Método de cálculo del área A ---
    METODO_A_CHOICES = [
        ('directa', 'Ingresar área directamente'),
        ('d_alfa', 'Calcular con distancia d y apertura α'),
        ('auto', 'Calcular automáticamente (Okumura-Hata)'),
    ]
    metodo_a = forms.ChoiceField(
        choices=METODO_A_CHOICES,
        label='Método para calcular A',
        initial='directa',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'metodo_a'})
    )

    area_directa = forms.FloatField(
        label='Área de servicio (km²)',
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'ej: 500'})
    )

    d = forms.FloatField(
        label='Distancia d (km)',
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'ej: 5'})
    )
    alfa = forms.FloatField(
        label='Apertura α (grados)',
        required=False,
        min_value=0,
        max_value=360,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'ej: 120'})
    )
    es_satelital_area = forms.BooleanField(
        label='¿Es servicio satelital? (área con división por 180°)',
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    # --- Modo de uso y naturaleza ---
    modo_uso = forms.ChoiceField(
        choices=[('EXCLUSIVO', 'Exclusivo'), ('COMPARTIDO', 'Compartido')],
        label='Modo de uso',
        initial='COMPARTIDO',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    naturaleza = forms.ChoiceField(
        choices=[('COMERCIAL', 'Comercial'), ('NO_COMERCIAL', 'No Comercial')],
        label='Naturaleza del servicio',
        initial='COMERCIAL',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    # --- Tiempo de autorización ---
    tiempo_anios = forms.FloatField(
        label='Tiempo de autorización (años)',
        min_value=0.01,
        initial=1.0,
        help_text='0.25 para 3 meses, 0.5 para 6 meses, 1 para un año',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )

    ffactor_correccion = forms.FloatField(
    required=False,
    initial=1.0,
    widget=forms.HiddenInput()
)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Determinar el grupo desde initial o data (POST)
        grupo = (
            self.initial.get('grupo')
            or (self.data.get('grupo') if self.data else None)
            or '1'
        )
        # Si viene como lista (QueryDict), tomar el primer valor
        if isinstance(grupo, list):
            grupo = grupo[0]

        # Filtrar servicios por grupo
        servicios = FactorServicio.objects.filter(
            activo=True, grupo=grupo
        ).order_by('categoria', 'subcategoria')

        choices = [('', '--------- Seleccione un servicio ---------')]
        for s in servicios:
            label = f"{s.categoria} → {s.subcategoria}"
            choices.append((s.subcategoria, label))
        self.fields['servicio'].choices = choices
        self.fields['grupo'].initial = grupo

    def clean(self):
        cleaned_data = super().clean()
        metodo_b = cleaned_data.get('metodo_b')
        metodo_a = cleaned_data.get('metodo_a')

        # Validar método B
        if metodo_b == 'estandar':
            fi = cleaned_data.get('fi')
            ff = cleaned_data.get('ff')
            if fi is None or ff is None:
                raise ValidationError('Para B estándar, debe ingresar frecuencia inicial y final.')
            if fi >= ff:
                raise ValidationError('La frecuencia final debe ser mayor que la inicial.')
        elif metodo_b == 'satelital':
            vel = cleaned_data.get('velocidad_mbps')
            mod = cleaned_data.get('modulacion')
            if vel is None or vel <= 0:
                raise ValidationError('Para B satelital, debe ingresar una velocidad válida (Mbps).')
            if not mod:
                raise ValidationError('Debe seleccionar una modulación.')

        # Validar método A
        if metodo_a == 'directa':
            area = cleaned_data.get('area_directa')
            if area is None or area <= 0:
                raise ValidationError('Para área directa, ingrese un valor positivo en km².')
        elif metodo_a == 'd_alfa':
            d = cleaned_data.get('d')
            alfa = cleaned_data.get('alfa')
            if d is None or d <= 0:
                raise ValidationError('Para área con d y α, ingrese una distancia d positiva.')
            if alfa is None or alfa <= 0 or alfa > 360:
                raise ValidationError('α debe ser un valor entre 1 y 360 grados.')

        # Validar campos comunes obligatorios
        for field in ['fc', 'htx', 'hrx', 'pt', 'gax', 'lt_constante', 'diff']:
            if cleaned_data.get(field) is None:
                raise ValidationError(f'El campo {field} es obligatorio.')

        return cleaned_data