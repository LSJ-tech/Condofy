import re

from django import forms
from django.core.exceptions import ValidationError

from .models import GastoComun

MODO_CHOICES = [
    ("total", "Monto total del condominio (se reparte por alícuota, o parejo si no hay)"),
    ("por_unidad", "Monto fijo por unidad (todas pagan lo mismo)"),
]

PERIODO_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class GastoComunForm(forms.ModelForm):
    modo = forms.ChoiceField(
        choices=MODO_CHOICES, initial="total", widget=forms.RadioSelect, label="¿Cómo quieres ingresar el monto?",
    )

    class Meta:
        model = GastoComun
        fields = ["periodo", "monto_total", "monto_por_unidad"]
        widgets = {
            "periodo": forms.TextInput(attrs={"class": "form-control", "type": "month"}),
            "monto_total": forms.NumberInput(attrs={"class": "form-control", "id": "id_monto_total"}),
            "monto_por_unidad": forms.NumberInput(attrs={"class": "form-control", "id": "id_monto_por_unidad"}),
        }
        labels = {
            "periodo": "Mes",
            "monto_total": "Monto total",
            "monto_por_unidad": "Monto por unidad",
        }
        help_texts = {
            "periodo": "La fecha de vencimiento queda automáticamente en el último día de este mes.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["monto_total"].required = False
        self.fields["monto_por_unidad"].required = False

    def clean_periodo(self):
        periodo = self.cleaned_data["periodo"]
        if not PERIODO_RE.match(periodo):
            raise ValidationError("Elige un mes válido.")
        return periodo

    def clean(self):
        cleaned = super().clean()
        modo = cleaned.get("modo")
        if modo == "total" and not cleaned.get("monto_total"):
            raise ValidationError("Ingresa el monto total del condominio.")
        if modo == "por_unidad" and not cleaned.get("monto_por_unidad"):
            raise ValidationError("Ingresa el monto fijo por unidad.")
        return cleaned
