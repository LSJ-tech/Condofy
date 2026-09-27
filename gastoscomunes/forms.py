from django import forms

from .models import GastoComun


class GastoComunForm(forms.ModelForm):
    class Meta:
        model = GastoComun
        fields = ["periodo", "monto_total", "fecha_vencimiento"]
        widgets = {
            "periodo": forms.TextInput(attrs={"class": "form-control", "placeholder": "2026-09"}),
            "monto_total": forms.NumberInput(attrs={"class": "form-control"}),
            "fecha_vencimiento": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }
