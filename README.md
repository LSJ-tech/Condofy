# BarrioSeguro

SaaS de emergencias y gestión para juntas de vecinos y condominios en Chile — segundo producto de [DevQuad](https://devquad.cl), en la misma línea que [PataAgenda](https://patagenda.devquad.cl).

Botón de pánico con notificación push, comunicación vecinal (avisos), gestión de accesos y gastos comunes, con un panel web para directiva/conserjería y una app móvil (React Native + Expo, repo separado `barrioseguro-app`) para residentes.

## Estado actual (Fase 1 — MVP)

Implementado y probado de punta a punta:

- Registro self-service de un condominio (crea Condominio + primera Unidad + cuenta de directiva).
- Multi-tenant real: cada condominio solo ve sus propios datos (verificado con tests de aislamiento).
- Botón de pánico: la app/API crea una `Alerta`, se envía push a todos los dispositivos registrados del condominio (vía el servicio de push de Expo), y directiva/conserjería la ve y resuelve desde el panel (con polling, sin sockets).
- Avisos (muro de noticias simple): solo directiva publica, todos los miembros leen.
- Accesos: registro manual de ingresos por conserjería desde el panel (sin QR todavía, ver Fase 2).
- Gastos comunes: directiva genera el cargo del periodo (se prorratea automático por alícuota o en partes iguales) y marca cuotas como pagadas a mano; la app solo lee sus cuotas (sin pago online todavía, ver Fase 2).
- Suscripción SaaS (condominio → DevQuad) vía Mercado Pago Checkout Pro, mismo patrón de seguridad que PataAgenda (el webhook siempre re-consulta el pago por ID, nunca confía en el body).
- Panel de administración (django-unfold) para el dueño de la plataforma.
- API REST documentada con Swagger en `/api/docs/` (drf-spectacular).

No implementado a propósito todavía (ver el plan completo del proyecto para las fases siguientes): QR de visitas, encuestas, pago online de gastos comunes, confirmaciones de alerta entre vecinos, reportes.

## Stack

Django 6 + Django REST Framework + JWT (`djangorestframework-simplejwt`) + PostgreSQL (SQLite en desarrollo) + Bootstrap (panel web) + django-unfold (admin) + Mercado Pago (suscripción) + Expo push notifications.

## Desarrollo local

```bash
python -m venv venv
source venv/Scripts/activate   # Windows (git bash)
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Panel web: `http://127.0.0.1:8000/`. Documentación de la API: `http://127.0.0.1:8000/api/docs/`.

## Estructura

```
config/            # settings.py, urls.py (equivalente a "peluqueria/" en PataAgenda)
core/               # Condominio, Torre, Unidad, Membresia, auth JWT, mixins de tenant
alertas/            # botón de pánico
comunicacion/       # avisos
accesos/            # registro de ingresos (conserjería)
gastoscomunes/      # cuotas del condominio
notificaciones/     # dispositivos push y envío vía Expo
pagos/              # suscripción SaaS (Mercado Pago)
```

Cada app de dominio (excepto `core`) sigue el mismo patrón: `models.py`, `serializers.py` + `api_views.py` + `api_urls.py` (API para la app móvil, bajo `/api/v1/`), y `views.py`/`forms.py`/`urls.py` cuando además tiene panel web.

## Despliegue

Mismo patrón que PataAgenda: `build.sh` + `render.yaml` para Render (Blueprint con web service + Postgres). Variables de entorno en `.env.example`.

## Roles

- **directiva**: administra el condominio completo (miembros, unidades, avisos, gastos comunes, suscripción).
- **conserje**: ve y resuelve alertas, registra accesos.
- **residente**: dispara alertas, lee avisos y sus propias cuotas (uso principal: la app móvil).

Las cuentas de conserjería y residentes las crea la directiva desde `/miembros/nuevo/` (contraseña temporal generada automáticamente, se muestra una sola vez).
