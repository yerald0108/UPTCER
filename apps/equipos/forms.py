from django import forms
from .models import Equipo, CategoriaEquipo


class FormularioEquipo(forms.ModelForm):

    class Meta:
        model  = Equipo
        fields = [
            'categoria', 'nombre', 'marca', 'modelo',
            'descripcion', 'banda_frecuencia', 'requiere_permiso', 'activo'
        ]
        labels = {
            'categoria':        'Categoría',
            'nombre':           'Nombre del equipo',
            'marca':            'Marca',
            'modelo':           'Modelo',
            'descripcion':      'Descripción técnica',
            'banda_frecuencia': 'Banda de frecuencia',
            'requiere_permiso': 'Requiere permiso de importación',
            'activo':           'Activo en el catálogo',
        }
        widgets = {
            'categoria':        forms.Select(attrs={'class': 'campo-select'}),
            'nombre':           forms.TextInput(attrs={'class': 'campo-input', 'placeholder': 'Nombre descriptivo del equipo'}),
            'marca':            forms.TextInput(attrs={'class': 'campo-input', 'placeholder': 'Ej: Samsung, Huawei, Cisco'}),
            'modelo':           forms.TextInput(attrs={'class': 'campo-input', 'placeholder': 'Ej: Galaxy S24, RV340'}),
            'descripcion':      forms.Textarea(attrs={'class': 'campo-textarea', 'rows': 3, 'placeholder': 'Descripción técnica del equipo'}),
            'banda_frecuencia': forms.Select(attrs={'class': 'campo-select'}),
            'requiere_permiso': forms.CheckboxInput(),
            'activo':           forms.CheckboxInput(),
        }

    def clean(self):
        cleaned = super().clean()
        marca  = cleaned.get('marca', '').strip()
        modelo = cleaned.get('modelo', '').strip()

        if marca and modelo:
            qs = Equipo.objects.filter(marca__iexact=marca, modelo__iexact=modelo)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    f'Ya existe un equipo con la marca "{marca}" y modelo "{modelo}" en el catálogo.'
                )
        return cleaned


class FormularioCategoria(forms.ModelForm):

    class Meta:
        model  = CategoriaEquipo
        fields = ['nombre', 'descripcion']
        labels = {
            'nombre':      'Nombre de la categoría',
            'descripcion': 'Descripción',
        }
        widgets = {
            'nombre':      forms.TextInput(attrs={'class': 'campo-input', 'placeholder': 'Ej: Teléfonos móviles, Routers, Tablets'}),
            'descripcion': forms.Textarea(attrs={'class': 'campo-textarea', 'rows': 2, 'placeholder': 'Descripción breve de la categoría'}),
        }