"""Valor de UTM/UF vía mindicador.cl (API pública chilena, sin auth, sin
costo, datos del Banco Central) -- evita que alguien tenga que cargar estos
valores a mano cada mes. Las tasas de AFP y los tramos de impuesto único NO
se automatizan acá: no hay una API oficial confiable para eso y cambian muy
rara vez (quedan en Afp/TramoImpuestoUnico, editables a mano cuando cambien)."""

import calendar
import logging
from datetime import date
from decimal import Decimal

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://mindicador.cl/api"
TIMEOUT = 8


class IndicadorNoDisponibleError(Exception):
    pass


def obtener_utm(periodo):
    """periodo: 'YYYY-MM'. Lanza IndicadorNoDisponibleError si todavía no
    está publicada (ej. un mes futuro) o si la API no responde."""
    anio, mes = periodo.split("-")
    try:
        r = requests.get(f"{BASE_URL}/utm/{anio}", timeout=TIMEOUT)
        r.raise_for_status()
        serie = r.json().get("serie", [])
    except (requests.RequestException, ValueError) as exc:
        logger.warning("No se pudo consultar UTM en mindicador.cl: %s", exc)
        raise IndicadorNoDisponibleError("No se pudo consultar el valor de la UTM (sin conexión con mindicador.cl).") from exc

    for punto in serie:
        if punto["fecha"].startswith(f"{anio}-{mes}"):
            return Decimal(str(punto["valor"]))
    raise IndicadorNoDisponibleError(f"La UTM de {periodo} todavía no está publicada.")


def obtener_uf(periodo):
    """UF del último día del periodo -- si el mes todavía no terminó (o la
    fecha es futura), usa el último valor disponible como aproximación."""
    anio, mes = (int(p) for p in periodo.split("-"))
    ultimo_dia = calendar.monthrange(anio, mes)[1]
    fecha_objetivo = date(anio, mes, ultimo_dia)

    try:
        r = requests.get(f"{BASE_URL}/uf/{fecha_objetivo.strftime('%d-%m-%Y')}", timeout=TIMEOUT)
        r.raise_for_status()
        serie = r.json().get("serie", [])
        if serie:
            return Decimal(str(serie[0]["valor"]))

        # fecha futura o todavía no publicada: cae al valor más reciente disponible
        r = requests.get(f"{BASE_URL}/uf", timeout=TIMEOUT)
        r.raise_for_status()
        serie_reciente = r.json().get("serie", [])
        if not serie_reciente:
            raise IndicadorNoDisponibleError("mindicador.cl no devolvió ningún valor de UF reciente.")
        return Decimal(str(serie_reciente[0]["valor"]))
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.warning("No se pudo consultar UF en mindicador.cl: %s", exc)
        raise IndicadorNoDisponibleError("No se pudo consultar el valor de la UF (sin conexión con mindicador.cl).") from exc


def asegurar_parametros_periodo(periodo):
    """Devuelve el ParametrosPeriodo de ese mes, creándolo automáticamente si
    no existe: UTM/UF se consultan solas en mindicador.cl, el resto
    (ingreso mínimo, tope imponible, tasas de cesantía -- cambian muy rara
    vez) se hereda del periodo más reciente que exista. Lanza ValueError si
    es la primera vez que se usa el sistema y no hay ningún periodo previo
    del que heredar esos valores."""
    from .models import ParametrosPeriodo

    existente = ParametrosPeriodo.objects.filter(periodo=periodo).first()
    if existente:
        return existente

    anterior = ParametrosPeriodo.objects.order_by("-periodo").first()
    if anterior is None:
        raise ValueError(
            "Todavía no hay ningún periodo configurado. Crea el primero a mano en "
            "/admin/personal/parametrosperiodo/ (ingreso mínimo, tope imponible, tasas de cesantía) -- "
            "los siguientes meses se generan solos."
        )

    valor_utm = obtener_utm(periodo)
    valor_uf = obtener_uf(periodo)

    return ParametrosPeriodo.objects.create(
        periodo=periodo,
        valor_utm=valor_utm,
        valor_uf=valor_uf,
        ingreso_minimo_mensual=anterior.ingreso_minimo_mensual,
        tope_imponible_uf=anterior.tope_imponible_uf,
        tasa_cesantia_trabajador_indefinido_pct=anterior.tasa_cesantia_trabajador_indefinido_pct,
        tasa_cesantia_trabajador_plazo_fijo_pct=anterior.tasa_cesantia_trabajador_plazo_fijo_pct,
    )
