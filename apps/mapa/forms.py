from django import forms


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