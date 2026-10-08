from django import forms
from django.core.exceptions import ValidationError

from .models import GastoComun

MODO_CHOICES = [
    ("total", "Monto total del condominio (se reparte por alícuota, o parejo si no hay)"),
    ("por_unidad", "Monto fijo por unidad (todas pagan lo mismo)"),
]


class GastoComunForm(forms.ModelForm):
    modo = forms.ChoiceField(
        choices=MODO_CHOICES, initial="total", widget=forms.RadioSelect, label="¿Cómo quieres ingresar el monto?",
    )

    class Meta:
        model = GastoComun
        fields = ["periodo", "monto_total", "monto_por_unidad", "fecha_vencimiento"]
        widgets = {
            "periodo": forms.TextInput(attrs={"class": "form-control", "placeholder": "2026-09"}),
            "monto_total": forms.NumberInput(attrs={"class": "form-control", "id": "id_monto_total"}),
            "monto_por_unidad": forms.NumberInput(attrs={"class": "form-control", "id": "id_monto_por_unidad"}),
            "fecha_vencimiento": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }
        labels = {
            "monto_total": "Monto total",
            "monto_por_unidad": "Monto por unidad",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["monto_total"].required = False
        self.fields["monto_por_unidad"].required = False

    def clean(self):
        cleaned = super().clean()
        modo = cleaned.get("modo")
        if modo == "total" and not cleaned.get("monto_total"):
            raise ValidationError("Ingresa el monto total del condominio.")
        if modo == "por_unidad" and not cleaned.get("monto_por_unidad"):
            raise ValidationError("Ingresa el monto fijo por unidad.")
        return cleaned
