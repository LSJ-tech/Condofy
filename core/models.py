import uuid

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from .usuarios import generar_codigo_invitacion

REGION_CHOICES = [
    ("arica_parinacota", "Arica y Parinacota"),
    ("tarapaca", "Tarapacá"),
    ("antofagasta", "Antofagasta"),
    ("atacama", "Atacama"),
    ("coquimbo", "Coquimbo"),
    ("valparaiso", "Valparaíso"),
    ("metropolitana", "Metropolitana de Santiago"),
    ("ohiggins", "Libertador General Bernardo O'Higgins"),
    ("maule", "Maule"),
    ("nuble", "Ñuble"),
    ("biobio", "Biobío"),
    ("araucania", "La Araucanía"),
    ("los_rios", "Los Ríos"),
    ("los_lagos", "Los Lagos"),
    ("aysen", "Aysén del General Carlos Ibáñez del Campo"),
    ("magallanes", "Magallanes y de la Antártica Chilena"),
]

PLAN_CHOICES = [
    ("free", "Gratis"),
    ("premium", "Pro"),
]

ROL_CHOICES = [
    ("directiva", "Directiva"),
    ("administracion", "Administración"),
    ("conserje", "Conserjería"),
    ("residente", "Residente"),
]


class Condominio(models.Model):
    """El tenant: una junta de vecinos o condominio cliente de la plataforma.

    A diferencia de PataAgenda (Negocio + Sucursal), acá hay un solo nivel de
    tenant -- alertas, avisos, conserjería y gastos comunes son compartidos
    por todo el condominio, no por torre.
    """

    nombre = models.CharField(max_length=150)
    direccion = models.CharField(max_length=255, blank=True)
    comuna = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)
    activo = models.BooleanField(default=True, help_text="Interruptor manual: desactivarlo bloquea todo (ej. un cliente que dejó de serlo).")
    plan = models.CharField(max_length=10, choices=PLAN_CHOICES, default="premium", help_text="Condofy es gratis para todos -- este campo es solo registro interno de DevQuad, no limita nada.")
    pagado_hasta = models.DateField(null=True, blank=True, help_text="Histórico de cuando Condofy todavía cobraba suscripción. Ya no restringe el acceso.")
    es_fundador = models.BooleanField(default=False, help_text="Uno de los primeros condominios en registrarse.")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    datos_transferencia = models.TextField(
        blank=True,
        help_text="Banco, tipo de cuenta, número, RUT y email de la administración — se muestra a los "
        "residentes para que paguen los gastos comunes por transferencia (no es un pago online).",
    )
    token_registro_residentes = models.UUIDField(
        default=uuid.uuid4, unique=True, editable=False,
        help_text="Identifica el link/QR público de autoregistro de residentes de este condominio.",
    )

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    @property
    def esta_vencido(self):
        return self.pagado_hasta is not None and self.pagado_hasta < timezone.localdate()

    @property
    def puede_operar(self):
        """Condofy es gratis y sin límites -- lo único que puede bloquear el
        acceso es el interruptor manual `activo` (ver su help_text)."""
        return self.activo

    @property
    def total_unidades(self):
        return self.unidades.count()


class Torre(models.Model):
    """Agrupación organizativa opcional dentro de un condominio grande -- NO es un tenant."""

    condominio = models.ForeignKey(Condominio, on_delete=models.CASCADE, related_name="torres")
    nombre = models.CharField(max_length=100)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.condominio})"


class Unidad(models.Model):
    """Un departamento/casa dentro del condominio -- nivel al que se prorratean los gastos comunes."""

    condominio = models.ForeignKey(Condominio, on_delete=models.CASCADE, related_name="unidades")
    torre = models.ForeignKey(Torre, on_delete=models.SET_NULL, null=True, blank=True, related_name="unidades")
    numero = models.CharField(max_length=20, help_text="Número o identificador del departamento/casa, ej. '304' o 'Casa 12'.")
    alicuota = models.DecimalField(max_digits=6, decimal_places=4, default=0, help_text="Coeficiente de copropiedad usado para prorratear gastos comunes (0 si no se usa).")

    class Meta:
        ordering = ["numero"]
        constraints = [
            models.UniqueConstraint(fields=["condominio", "torre", "numero"], name="unidad_numero_unico_por_torre"),
        ]

    def __str__(self):
        if self.torre_id:
            return f"Torre {self.torre.nombre} - Depto {self.numero}"
        return f"{self.numero} - {self.condominio}"


class Membresia(models.Model):
    """Liga un usuario de login a su condominio y le asigna un rol."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="membresia")
    condominio = models.ForeignKey(Condominio, on_delete=models.CASCADE, related_name="membresias")
    unidad = models.ForeignKey(Unidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="membresias", help_text="Solo aplica a residentes.")
    rol = models.CharField(max_length=15, choices=ROL_CHOICES, default="residente")

    def __str__(self):
        return f"{self.user} ({self.get_rol_display()} de {self.condominio})"


class CodigoInvitacion(models.Model):
    """Gate del registro público: sin un código válido y no usado, no se puede crear un condominio."""

    codigo = models.CharField(max_length=20, unique=True, default=generar_codigo_invitacion)
    condominio = models.OneToOneField(Condominio, on_delete=models.CASCADE, null=True, blank=True, related_name="codigo_invitacion")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_uso = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return self.codigo

    @property
    def usado(self):
        return self.condominio_id is not None


class SolicitudAcceso(models.Model):
    """Lead capturado desde el formulario público de la landing -- quien lo pide todavía no tiene código de invitación."""

    nombre = models.CharField(max_length=150)
    condominio = models.CharField(max_length=150, verbose_name="Condominio o junta de vecinos")
    comuna = models.CharField(max_length=100, blank=True)
    telefono = models.CharField(max_length=30)
    email = models.EmailField(blank=True)
    mensaje = models.TextField(blank=True)
    atendido = models.BooleanField(default=False, help_text="Marca cuando ya contactaste a esta persona.")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"{self.condominio} ({self.nombre})"
