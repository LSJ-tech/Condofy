from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from personal.models import Afp, ParametrosPeriodo, TramoImpuestoUnico

# Tasa total = 10% de cotización obligatoria + comisión de la AFP. Comisiones
# verificadas en spensiones.cl / comparadores públicos a octubre 2026 --
# cambian con 90 días de aviso previo por ley, así que hay que revisarlas de
# nuevo si ha pasado tiempo desde que se cargó esto.
AFPS = [
    ("Uno", Decimal("10.46")),
    ("Modelo", Decimal("10.58")),
    ("PlanVital", Decimal("11.16")),
    ("Habitat", Decimal("11.27")),
    ("Capital", Decimal("11.44")),
    ("Cuprum", Decimal("11.44")),
    ("Provida", Decimal("11.45")),
]

# Tabla de impuesto único de segunda categoría (SII) -- los tramos y rebajas
# en UTM son estructurales (vienen de la ley) y no cambian mes a mes, solo
# cambia su equivalente en pesos según la UTM vigente (por eso están en UTM
# acá, no en pesos).
TRAMOS_IMPUESTO = [
    (Decimal("0"), Decimal("13.5"), Decimal("0"), Decimal("0")),
    (Decimal("13.5"), Decimal("30"), Decimal("4"), Decimal("0.54")),
    (Decimal("30"), Decimal("50"), Decimal("8"), Decimal("1.74")),
    (Decimal("50"), Decimal("70"), Decimal("13.5"), Decimal("4.49")),
    (Decimal("70"), Decimal("90"), Decimal("23"), Decimal("11.14")),
    (Decimal("90"), Decimal("120"), Decimal("30.4"), Decimal("17.80")),
    (Decimal("120"), Decimal("310"), Decimal("35"), Decimal("23.32")),
    (Decimal("310"), None, Decimal("40"), Decimal("38.82")),
]

# Periodo semilla (bootstrap) -- de acá en adelante, cada mes nuevo se arma
# solo (UTM/UF vía mindicador.cl, ver personal/indicadores.py).
PERIODO_SEMILLA = "2026-10"
VALOR_UTM_SEMILLA = Decimal("72151")  # SII, octubre 2026
VALOR_UF_SEMILLA = Decimal("41130.94")  # mindicador.cl, 09-10-2026
INGRESO_MINIMO_SEMILLA = 553553  # vigente desde mayo 2026 (Ley 21.751, reajuste retroactivo)
TOPE_AFP_SALUD_SEMILLA = Decimal("90")  # UF, vigente desde febrero 2026
TOPE_CESANTIA_SEMILLA = Decimal("135.2")  # UF


class Command(BaseCommand):
    help = "Carga AFP, tabla de impuesto único y el periodo semilla (parámetros previsionales), verificados a la fecha de carga. Idempotente."

    def handle(self, *args, **options):
        with transaction.atomic():
            self._cargar_afps()
            self._cargar_tramos()
            self._cargar_periodo_semilla()

    def _cargar_afps(self):
        for nombre, tasa in AFPS:
            afp, creada = Afp.objects.update_or_create(nombre=nombre, defaults={"tasa_total_pct": tasa})
            self.stdout.write(self.style.SUCCESS(f"AFP {'creada' if creada else 'actualizada'}: {afp}"))

    def _cargar_tramos(self):
        if TramoImpuestoUnico.objects.exists():
            self.stdout.write("Tramos de impuesto único ya existían -- no se tocan (bórralos a mano en el admin si quieres recargarlos).")
            return
        TramoImpuestoUnico.objects.bulk_create([
            TramoImpuestoUnico(desde_utm=desde, hasta_utm=hasta, tasa_pct=tasa, rebaja_utm=rebaja)
            for desde, hasta, tasa, rebaja in TRAMOS_IMPUESTO
        ])
        self.stdout.write(self.style.SUCCESS(f"{len(TRAMOS_IMPUESTO)} tramos de impuesto único cargados."))

    def _cargar_periodo_semilla(self):
        parametros, creado = ParametrosPeriodo.objects.get_or_create(
            periodo=PERIODO_SEMILLA,
            defaults={
                "valor_utm": VALOR_UTM_SEMILLA,
                "valor_uf": VALOR_UF_SEMILLA,
                "ingreso_minimo_mensual": INGRESO_MINIMO_SEMILLA,
                "tope_imponible_afp_salud_uf": TOPE_AFP_SALUD_SEMILLA,
                "tope_imponible_cesantia_uf": TOPE_CESANTIA_SEMILLA,
            },
        )
        if creado:
            self.stdout.write(self.style.SUCCESS(f"Periodo semilla {parametros.periodo} creado -- los meses siguientes se arman solos."))
        else:
            self.stdout.write(f"Periodo {parametros.periodo} ya existía -- no se tocó.")
