from django import forms

from core.models import Unidad

from .models import RegistroIngreso


class RegistroIngresoForm(forms.ModelForm):
    class Meta:
        model = RegistroIngreso
        fields = ["unidad", "nombre_visitante", "motivo"]
        widgets = {
            "unidad": forms.Select(attrs={"class": "form-select"}),
            "nombre_visitante": forms.TextInput(attrs={"class": "form-control"}),
            "motivo": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, condominio=None, **kwargs):
        super().__init__(*args, **kwargs)
        if condominio is not None:
            self.fields["unidad"].queryset = Unidad.objects.filter(condominio=condominio)
