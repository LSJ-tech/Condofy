from django import forms

from .models import Empleado


class EmpleadoForm(forms.ModelForm):
    class Meta:
        model = Empleado
        fields = [
            "nombre", "rut", "cargo", "tipo_contrato", "fecha_ingreso", "fecha_termino",
            "afp", "sistema_salud", "plan_isapre_uf", "sueldo_base", "asignacion_colacion",
            "asignacion_movilizacion", "aplica_gratificacion", "email", "activo",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "rut": forms.TextInput(attrs={"class": "form-control", "placeholder": "11.111.111-1"}),
            "cargo": forms.TextInput(attrs={"class": "form-control"}),
            "tipo_contrato": forms.Select(attrs={"class": "form-select"}),
            "fecha_ingreso": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "fecha_termino": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "afp": forms.Select(attrs={"class": "form-select"}),
            "sistema_salud": forms.Select(attrs={"class": "form-select"}),
            "plan_isapre_uf": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "sueldo_base": forms.NumberInput(attrs={"class": "form-control", "step": "1"}),
            "asignacion_colacion": forms.NumberInput(attrs={"class": "form-control", "step": "1"}),
            "asignacion_movilizacion": forms.NumberInput(attrs={"class": "form-control", "step": "1"}),
            "aplica_gratificacion": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "rut": "RUT",
            "plan_isapre_uf": "Plan Isapre (UF)",
            "aplica_gratificacion": "Aplica gratificación legal",
        }
        help_texts = {
            "aplica_gratificacion": "Activar solo si un contador confirmó que el condominio está obligado a pagarla.",
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("sistema_salud") == "isapre" and not cleaned.get("plan_isapre_uf"):
            self.add_error("plan_isapre_uf", "Ingresa el valor del plan Isapre en UF.")
        return cleaned
