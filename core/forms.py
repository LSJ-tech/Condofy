from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models.functions import Length

from .models import REGION_CHOICES, ROL_CHOICES, CodigoInvitacion, Condominio, SolicitudAcceso, Torre, Unidad


class ConfirmacionContrasenaMixin(forms.Form):
    password1 = forms.CharField(label="Contraseña", widget=forms.PasswordInput(attrs={"class": "form-control"}))
    password2 = forms.CharField(label="Confirmar contraseña", widget=forms.PasswordInput(attrs={"class": "form-control"}))

    def clean_password1(self):
        password = self.cleaned_data["password1"]
        validate_password(password)
        return password

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") and cleaned.get("password2") and cleaned["password1"] != cleaned["password2"]:
            raise ValidationError("Las contraseñas no coinciden.")
        return cleaned


class RegistroCondominioForm(ConfirmacionContrasenaMixin):
    """Alta de un condominio nuevo y de su primer usuario (directiva), sin intervención manual."""

    field_order = [
        "codigo_invitacion", "nombre_condominio", "direccion_condominio", "comuna_condominio", "region_condominio",
        "nombre", "apellido", "password1", "password2",
    ]

    codigo_invitacion = forms.CharField(
        max_length=20, label="Código de invitación",
        widget=forms.TextInput(attrs={"class": "form-control"}),
        help_text="Pídeselo a quien te invitó a usar la plataforma.",
    )
    nombre_condominio = forms.CharField(
        max_length=150, label="Nombre del condominio o junta de vecinos",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    direccion_condominio = forms.CharField(
        max_length=255, required=False, label="Dirección",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    comuna_condominio = forms.CharField(
        max_length=100, required=False, label="Comuna",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    region_condominio = forms.ChoiceField(
        choices=[("", "---------")] + REGION_CHOICES, required=False, label="Región",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    nombre = forms.CharField(
        max_length=150, label="Tu nombre",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    apellido = forms.CharField(
        max_length=150, label="Tu apellido",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    def clean_codigo_invitacion(self):
        codigo = self.cleaned_data["codigo_invitacion"].strip().upper()
        try:
            self.codigo_obj = CodigoInvitacion.objects.get(codigo=codigo, condominio__isnull=True)
        except CodigoInvitacion.DoesNotExist:
            raise ValidationError("Código inválido o ya usado.")
        return codigo


class CrearMiembroForm(forms.Form):
    """Directiva/conserjería crea la cuenta de otro miembro del condominio (residente o conserje)."""

    nombre = forms.CharField(max_length=150, label="Nombre", widget=forms.TextInput(attrs={"class": "form-control"}))
    apellido = forms.CharField(max_length=150, label="Apellido", widget=forms.TextInput(attrs={"class": "form-control"}))
    email = forms.EmailField(required=False, label="Email (opcional)", widget=forms.EmailInput(attrs={"class": "form-control"}))
    rol = forms.ChoiceField(choices=[c for c in ROL_CHOICES if c[0] != "directiva"], widget=forms.Select(attrs={"class": "form-select"}))
    unidad = forms.ModelChoiceField(queryset=Unidad.objects.none(), required=False, label="Unidad (obligatorio para residentes)", widget=forms.Select(attrs={"class": "form-select"}))

    def __init__(self, *args, condominio=None, **kwargs):
        super().__init__(*args, **kwargs)
        if condominio is not None:
            self.fields["unidad"].queryset = Unidad.objects.filter(condominio=condominio)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("rol") == "residente" and not cleaned.get("unidad"):
            raise ValidationError("Selecciona la unidad del residente.")
        return cleaned


class CondominioForm(forms.ModelForm):
    class Meta:
        model = Condominio
        fields = ["datos_transferencia"]
        widgets = {
            "datos_transferencia": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
        }
        labels = {
            "datos_transferencia": "Datos para transferencia de gastos comunes",
        }
        help_texts = {
            "datos_transferencia": "Banco, tipo de cuenta, número, RUT y email — se muestra a los residentes al pagar.",
        }


class SolicitudAccesoForm(forms.ModelForm):
    """Formulario público de la landing -- captura el interés de quien todavía no tiene código de invitación."""

    class Meta:
        model = SolicitudAcceso
        fields = ["nombre", "condominio", "comuna", "telefono", "email", "mensaje"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Tu nombre"}),
            "condominio": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre del condominio o junta de vecinos"}),
            "comuna": forms.TextInput(attrs={"class": "form-control", "placeholder": "Comuna"}),
            "telefono": forms.TextInput(attrs={"class": "form-control", "placeholder": "+56 9 ..."}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email (opcional)"}),
            "mensaje": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Cuéntanos un poco de tu comunidad (opcional)"}),
        }
        labels = {
            "nombre": "Nombre", "condominio": "Condominio o junta de vecinos", "comuna": "Comuna",
            "telefono": "Teléfono", "email": "Email", "mensaje": "Mensaje",
        }


class TorreForm(forms.ModelForm):
    class Meta:
        model = Torre
        fields = ["nombre"]
        widgets = {"nombre": forms.TextInput(attrs={"class": "form-control"})}


class UnidadForm(forms.ModelForm):
    class Meta:
        model = Unidad
        fields = ["numero", "torre", "alicuota"]
        widgets = {
            "numero": forms.TextInput(attrs={"class": "form-control"}),
            "torre": forms.Select(attrs={"class": "form-select"}),
            "alicuota": forms.NumberInput(attrs={"class": "form-control", "step": "0.0001"}),
        }

    def __init__(self, *args, condominio=None, **kwargs):
        super().__init__(*args, **kwargs)
        if condominio is not None:
            self.fields["torre"].queryset = Torre.objects.filter(condominio=condominio).annotate(_len=Length("nombre")).order_by("_len", "nombre")
