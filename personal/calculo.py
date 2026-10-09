"""Cálculo de liquidación de sueldo (Chile) -- función pura, sin tocar la base
de datos, para poder testearla con casos verificados a mano.

IMPORTANTE: esto es una estimación según las reglas generales vigentes para un
contrato de trabajo dependiente común (sin asignación familiar, sin horas
extra, sin finiquito). No reemplaza la revisión de un contador antes de pagar
sueldos reales -- ver el descargo en el PDF generado."""

GRATIFICACION_PORCENTAJE = 25
GRATIFICACION_TOPE_INGRESOS_MINIMOS = 4.75
PORCENTAJE_SALUD_FONASA = 7


def _tasa_cesantia_trabajador(empleado, parametros):
    if empleado.tipo_contrato == "indefinido":
        return parametros.tasa_cesantia_trabajador_indefinido_pct
    return parametros.tasa_cesantia_trabajador_plazo_fijo_pct


def _buscar_tramo_impuesto(base_utm, tramos):
    for tramo in tramos:
        if base_utm < tramo.desde_utm:
            continue
        if tramo.hasta_utm is None or base_utm <= tramo.hasta_utm:
            return tramo
    return None


def calcular_liquidacion(empleado, parametros, tramos_impuesto):
    """`tramos_impuesto` es un iterable de TramoImpuestoUnico ordenado por
    desde_utm (ya viene así por el Meta.ordering del modelo)."""
    sueldo_base = empleado.sueldo_base

    gratificacion = 0
    if empleado.aplica_gratificacion:
        tope_gratificacion = round(GRATIFICACION_TOPE_INGRESOS_MINIMOS * parametros.ingreso_minimo_mensual / 12)
        gratificacion = min(round(sueldo_base * GRATIFICACION_PORCENTAJE / 100), tope_gratificacion)

    total_imponible = sueldo_base + gratificacion
    total_haberes = total_imponible + empleado.asignacion_colacion + empleado.asignacion_movilizacion

    tope_imponible_pesos = round(parametros.tope_imponible_uf * parametros.valor_uf)
    base_descuentos = min(total_imponible, tope_imponible_pesos)

    descuento_afp = round(base_descuentos * empleado.afp.tasa_total_pct / 100)

    if empleado.sistema_salud == "isapre" and empleado.plan_isapre_uf:
        descuento_salud = round(empleado.plan_isapre_uf * parametros.valor_uf)
    else:
        descuento_salud = round(base_descuentos * PORCENTAJE_SALUD_FONASA / 100)

    tasa_cesantia = _tasa_cesantia_trabajador(empleado, parametros)
    descuento_cesantia = round(base_descuentos * tasa_cesantia / 100)

    base_tributable = total_imponible - descuento_afp - descuento_salud - descuento_cesantia
    base_tributable_utm = base_tributable / parametros.valor_utm
    tramo = _buscar_tramo_impuesto(base_tributable_utm, tramos_impuesto)
    if tramo is None or tramo.tasa_pct == 0:
        impuesto_unico = 0
    else:
        impuesto_unico = max(0, round((base_tributable_utm * tramo.tasa_pct / 100 - tramo.rebaja_utm) * parametros.valor_utm))

    total_descuentos = descuento_afp + descuento_salud + descuento_cesantia + impuesto_unico
    liquido_a_pagar = total_haberes - total_descuentos

    return {
        "sueldo_base": sueldo_base,
        "gratificacion": gratificacion,
        "asignacion_colacion": empleado.asignacion_colacion,
        "asignacion_movilizacion": empleado.asignacion_movilizacion,
        "total_imponible": total_imponible,
        "total_haberes": total_haberes,
        "descuento_afp": descuento_afp,
        "descuento_salud": descuento_salud,
        "descuento_cesantia": descuento_cesantia,
        "impuesto_unico": impuesto_unico,
        "total_descuentos": total_descuentos,
        "liquido_a_pagar": liquido_a_pagar,
        "utm_usada": parametros.valor_utm,
        "afp_nombre_usada": empleado.afp.nombre,
        "afp_tasa_usada": empleado.afp.tasa_total_pct,
    }
