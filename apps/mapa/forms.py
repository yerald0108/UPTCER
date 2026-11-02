from django import forms
from .models import PuntoMapa


class ImportarArchivoForm(forms.Form):
    archivo = forms.FileField(
        label='Archivo Excel (.xlsx, .xls) o CSV',
        help_text='Formatos permitidos: .xlsx, .xls, .csv',
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': '.xlsx,.xls,.csv',
        })
    )
    actualizar_existentes = forms.BooleanField(
        label='Actualizar puntos existentes (si coincide el nombre)',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def clean_archivo(self):
        archivo = self.cleaned_data['archivo']
        nombre = archivo.name.lower()
        if not (nombre.endswith('.xlsx') or nombre.endswith('.xls') or nombre.endswith('.csv')):
            raise forms.ValidationError('Formato no permitido. Usa .xlsx, .xls o .csv')
        if archivo.size > 20 * 1024 * 1024:  # 20 MB
            raise forms.ValidationError('El archivo es demasiado grande (máx. 20 MB)')
        return archivo


class PuntoMapaAdminForm(forms.ModelForm):
    frecuencia_mhz = forms.FloatField(
        label='Frecuencia (MHz)',
        required=False,
        min_value=0.0001,
    )
    radio_km = forms.FloatField(
        label='Radio de cobertura estimado (km)',
        required=False,
        min_value=0.01,
        max_value=1000,
        help_text='Radio manual para visualizar cobertura aproximada y solapamientos.',
    )

    class Meta:
        model = PuntoMapa
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            atributos = self.instance.atributos or {}
            self.fields['frecuencia_mhz'].initial = atributos.get('frecuencia_mhz')
            self.fields['radio_km'].initial = atributos.get('radio_km')

    def save(self, commit=True):
        punto = super().save(commit=False)
        atributos = dict(punto.atributos or {})
        for campo in ('frecuencia_mhz', 'radio_km'):
            valor = self.cleaned_data[campo]
            if valor is None:
                atributos.pop(campo, None)
            else:
                atributos[campo] = valor
        punto.atributos = atributos
        if commit:
            punto.save()
            self.save_m2m()
        return punto