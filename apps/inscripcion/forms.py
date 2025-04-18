from django import forms  
from .models import  Inscripcion


class InscripcionForm(forms.ModelForm):

    class Meta:
        model = Inscripcion
        fields = ['idPersona', 'idCohorte', 'idTF', 'idFormacion']
