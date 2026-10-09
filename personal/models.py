from django.db import models

from core.models import Condominio, Membresia

TIPO_CONTRATO_CHOICES = [
    ("indefinido", "Indefinido"),
    ("plazo_fijo", "Plazo fijo"),
]

SISTEMA_SALUD_CHOICES = [
    ("fonasa", "Fonasa"),
    ("isapre", "Isapre"),
]


class Afp(models.Model):
    """Tabla de referencia -- solo editable vía Django admin por DevQuad. Las
    tasas cambian (rara vez, pero cambian), así que no van hardcodeadas en
    el código, mismo criterio que Condominio.etiqueta_torre."""

    nombre = models.CharField(max_length=50, unique=True)
    tasa_total_pct = models.DecimalField(
        max_digits=5, decimal_places=2,
        help_text="Cotización obligatoria (10%) + comisión de la AFP, ej. 11.44 para 11,44%.",
    )

    class Meta:
        ordering = ["nombre"]
        verbose_name = "AFP"
        verbose_name_plural = "AFPs"

    def __str__(self):
        return f"{self.nombre} ({self.tasa_total_pct}%)"


class TramoImpuestoUnico(models.Model):
    """Tabla de referencia -- tramos de la tabla de impuesto único de segunda
    categoría, expresados en UTM. Solo editable vía Django admin por DevQuad;
    hay que mantenerla al día contra la tabla vigente del SII."""

    desde_utm = models.DecimalField(max_digits=8, decimal_places=2)
    hasta_utm = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="Vacío = tramo superior, sin techo.",
    )
    tasa_pct = models.DecimalField(max_digits=5, decimal_places=2)
    rebaja_utm = models.DecimalField(max_digits=8, decimal_places=4)

    class Meta:
        ordering = ["desde_utm"]
        verbose_name = "Tramo de impuesto único"
        verbose_name_plural = "Tramos de impuesto único"

    def __str__(self):
        hasta = self.hasta_utm if self.hasta_utm is not None else "∞"
        return f"{self.desde_utm} a {hasta} UTM -- {self.tasa_pct}%"


class ParametrosPeriodo(models.Model):
    """Un registro por mes -- liga cada liquidación a los valores legales
    vigentes ESE mes (UTM, UF, ingreso mínimo, tope imponible), para que no
    cambien retroactivamente si se actualizan después. Solo editable vía
    Django admin por DevQuad, igual que Afp/TramoImpuestoUnico."""

    periodo = models.CharField(max_length=20, unique=True, help_text="Ej. '2026-10'.")
    valor_utm = models.DecimalField(max_digits=10, decimal_places=2)
    valor_uf = models.DecimalField(max_digits=10, decimal_places=2)
    ingreso_minimo_mensual = models.PositiveIntegerField(help_text="En pesos chilenos -- sin centavos.")
    tope_imponible_uf = models.DecimalField(max_digits=6, decimal_places=2, help_text="Tope imponible para AFP/salud/cesantía, en UF.")
    tasa_cesantia_trabajador_indefinido_pct = models.DecimalField(max_digits=4, decimal_places=2, default=0.6)
    tasa_cesantia_trabajador_plazo_fijo_pct = models.DecimalField(max_digits=4, decimal_places=2, default=0)

    class Meta:
        ordering = ["-periodo"]
        verbose_name = "Parámetros del periodo"
        verbose_name_plural = "Parámetros por periodo"

    def __str__(self):
        return self.periodo


class Empleado(models.Model):
    """Personal del condominio (conserjería, aseo, mantención...). No requiere
    cuenta de login -- membresia es opcional, solo si además tiene acceso al
    sistema como conserje."""

    condominio = models.ForeignKey(Condominio, on_delete=models.CASCADE, related_name="empleados")
    membresia = models.OneToOneField(
        Membresia, null=True, blank=True, on_delete=models.SET_NULL, related_name="empleado",
        help_text="Si además tiene cuenta de conserjería en el sistema.",
    )
    nombre = models.CharField(max_length=150)
    rut = models.CharField(max_length=12)
    cargo = models.CharField(max_length=100, help_text="Ej. 'Conserje', 'Aseo', 'Mantención'.")
    tipo_contrato = models.CharField(max_length=12, choices=TIPO_CONTRATO_CHOICES, default="indefinido")
    fecha_ingreso = models.DateField()
    fecha_termino = models.DateField(null=True, blank=True)
    afp = models.ForeignKey(Afp, on_delete=models.PROTECT, related_name="empleados")
    sistema_salud = models.CharField(max_length=10, choices=SISTEMA_SALUD_CHOICES, default="fonasa")
    plan_isapre_uf = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        help_text="Solo si el sistema de salud es Isapre -- valor del plan en UF.",
    )
    sueldo_base = models.PositiveIntegerField(help_text="En pesos chilenos -- sin centavos.")
    asignacion_colacion = models.PositiveIntegerField(default=0, help_text="No imponible. En pesos chilenos -- sin centavos.")
    asignacion_movilizacion = models.PositiveIntegerField(default=0, help_text="No imponible. En pesos chilenos -- sin centavos.")
    aplica_gratificacion = models.BooleanField(
        default=False,
        help_text="Activar solo si un contador confirmó que el condominio está obligado a pagar gratificación legal.",
    )
    email = models.EmailField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.cargo})"


class Liquidacion(models.Model):
    """Liquidación de sueldo de un empleado para un periodo -- guarda el
    resultado ya calculado (snapshot), no se recalcula sola si después
    cambian los parámetros/tasas."""

    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name="liquidaciones")
    periodo = models.CharField(max_length=20, help_text="Ej. '2026-10'.")
    fecha_generacion = models.DateTimeField(auto_now_add=True)

    sueldo_base = models.PositiveIntegerField()
    gratificacion = models.PositiveIntegerField(default=0)
    asignacion_colacion = models.PositiveIntegerField(default=0)
    asignacion_movilizacion = models.PositiveIntegerField(default=0)
    total_imponible = models.PositiveIntegerField()
    total_haberes = models.PositiveIntegerField()

    descuento_afp = models.PositiveIntegerField()
    descuento_salud = models.PositiveIntegerField()
    descuento_cesantia = models.PositiveIntegerField()
    impuesto_unico = models.PositiveIntegerField()
    total_descuentos = models.PositiveIntegerField()

    liquido_a_pagar = models.PositiveIntegerField()

    utm_usada = models.DecimalField(max_digits=10, decimal_places=2)
    afp_nombre_usada = models.CharField(max_length=50)
    afp_tasa_usada = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        ordering = ["-periodo"]
        constraints = [
            models.UniqueConstraint(fields=["empleado", "periodo"], name="liquidacion_unica_por_empleado_y_periodo"),
        ]

    def __str__(self):
        return f"{self.empleado} - {self.periodo}"
