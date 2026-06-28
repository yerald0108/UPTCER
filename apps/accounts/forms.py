from django import forms
from django.contrib.auth.password_validation import validate_password
from .models import Usuario


class FormularioCrearUsuario(forms.ModelForm):

    password1 = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'campo-input',
            'placeholder': 'Contraseña del usuario'
        })
    )
    password2 = forms.CharField(
        label='Confirmar contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'campo-input',
            'placeholder': 'Repita la contraseña'
        })
    )

    class Meta:
        model  = Usuario
        fields = ['username', 'nombre', 'apellidos', 'email', 'telefono', 'rol']
        labels = {
            'username':  'Nombre de usuario',
            'nombre':    'Nombre',
            'apellidos': 'Apellidos',
            'email':     'Correo electrónico',
            'telefono':  'Teléfono',
            'rol':       'Rol en el sistema',
        }
        widgets = {
            'username':  forms.TextInput(attrs={'class': 'campo-input', 'placeholder': 'Ej: jperez'}),
            'nombre':    forms.TextInput(attrs={'class': 'campo-input', 'placeholder': 'Nombre del usuario'}),
            'apellidos': forms.TextInput(attrs={'class': 'campo-input', 'placeholder': 'Apellidos del usuario'}),
            'email':     forms.EmailInput(attrs={'class': 'campo-input', 'placeholder': 'correo@ejemplo.cu'}),
            'telefono':  forms.TextInput(attrs={'class': 'campo-input', 'placeholder': '+53 5 000 0000'}),
            'rol':       forms.Select(attrs={'class': 'campo-select'}),
        }

    def clean(self):
        cleaned  = super().clean()
        password1 = cleaned.get('password1')
        password2 = cleaned.get('password2')
        if password1 and password2 and password1 != password2:
            self.add_error('password2', 'Las contraseñas no coinciden.')
        return cleaned

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.set_password(self.cleaned_data['password1'])
        if commit:
            usuario.save()
        return usuario


class FormularioEditarUsuario(forms.ModelForm):

    class Meta:
        model  = Usuario
        fields = ['username', 'nombre', 'apellidos', 'email', 'telefono', 'rol', 'is_active']
        labels = {
            'username':  'Nombre de usuario',
            'nombre':    'Nombre',
            'apellidos': 'Apellidos',
            'email':     'Correo electrónico',
            'telefono':  'Teléfono',
            'rol':       'Rol en el sistema',
            'is_active': 'Usuario activo',
        }
        widgets = {
            'username':  forms.TextInput(attrs={'class': 'campo-input'}),
            'nombre':    forms.TextInput(attrs={'class': 'campo-input'}),
            'apellidos': forms.TextInput(attrs={'class': 'campo-input'}),
            'email':     forms.EmailInput(attrs={'class': 'campo-input'}),
            'telefono':  forms.TextInput(attrs={'class': 'campo-input'}),
            'rol':       forms.Select(attrs={'class': 'campo-select'}),
            'is_active': forms.CheckboxInput(),
        }


class FormularioCambiarPassword(forms.Form):

    password1 = forms.CharField(
        label='Nueva contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'campo-input',
            'placeholder': 'Nueva contraseña'
        })
    )
    password2 = forms.CharField(
        label='Confirmar nueva contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'campo-input',
            'placeholder': 'Repita la nueva contraseña'
        })
    )

    def clean(self):
        cleaned   = super().clean()
        password1 = cleaned.get('password1')
        password2 = cleaned.get('password2')
        if password1 and password2 and password1 != password2:
            self.add_error('password2', 'Las contraseñas no coinciden.')
        return cleaned
    
class FormularioEditarPerfil(forms.ModelForm):

    class Meta:
        model  = Usuario
        fields = ['nombre', 'apellidos', 'email', 'telefono']
        labels = {
            'nombre':    'Nombre',
            'apellidos': 'Apellidos',
            'email':     'Correo electrónico',
            'telefono':  'Teléfono',
        }
        widgets = {
            'nombre':    forms.TextInput(attrs={'class': 'campo-input'}),
            'apellidos': forms.TextInput(attrs={'class': 'campo-input'}),
            'email':     forms.EmailInput(attrs={'class': 'campo-input'}),
            'telefono':  forms.TextInput(attrs={'class': 'campo-input', 'placeholder': '+53 5 000 0000'}),
        }


class FormularioCambiarMiPassword(forms.Form):

    password_actual = forms.CharField(
        label='Contraseña actual',
        widget=forms.PasswordInput(attrs={
            'class': 'campo-input',
            'placeholder': 'Su contraseña actual'
        })
    )
    password_nueva1 = forms.CharField(
        label='Nueva contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'campo-input',
            'placeholder': 'Nueva contraseña'
        })
    )
    password_nueva2 = forms.CharField(
        label='Confirmar nueva contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'campo-input',
            'placeholder': 'Repita la nueva contraseña'
        })
    )

    def clean(self):
        cleaned  = super().clean()
        nueva1   = cleaned.get('password_nueva1')
        nueva2   = cleaned.get('password_nueva2')
        if nueva1 and nueva2 and nueva1 != nueva2:
            self.add_error('password_nueva2', 'Las contraseñas nuevas no coinciden.')
        return cleaned