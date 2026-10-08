# Condofy

SaaS de emergencias y gestión para juntas de vecinos y condominios en Chile — segundo producto de [DevQuad](https://devquad.cl), en la misma línea que [PataAgenda](https://patagenda.devquad.cl).

Botón de pánico con notificación push, comunicación vecinal (avisos), gestión de accesos y gastos comunes, con un panel web para directiva/administración/conserjería y una app móvil (React Native + Expo) para residentes.

**Condofy es gratis, sin límite de unidades ni de tiempo** — no hay plan pago ni suscripción. Existe una donación voluntaria opcional (condominio → DevQuad) para apoyar el desarrollo.

## Estado actual

Implementado y probado de punta a punta:

- Registro self-service de un condominio (crea Condominio + cuenta de directiva). Las torres las configura DevQuad al dar de alta al cliente; las unidades las carga la directiva/administración.
- Multi-tenant real: cada condominio solo ve sus propios datos (verificado con tests de aislamiento).
- 4 roles: **directiva** (gobierno, supervisa todo), **administración** (día a día: miembros, gastos comunes, avisos, accesos), **conserjería** (accesos), **residente**.
- Botón de pánico: la app/API crea una `Alerta` con ubicación GPS, se envía push a todo el condominio (vía Expo), y **cualquier miembro** (no solo directiva/conserjería) puede ver el mapa y resolverla o marcarla como falsa alarma. Se auto-cierra sola si nadie responde en 30 minutos. Historial completo filtrable en `/alertas/historial/`.
- Avisos (muro de noticias simple): directiva/administración publican, todos los miembros leen.
- Accesos: registro manual de ingresos por conserjería/directiva/administración desde el panel (sin QR todavía).
- Gastos comunes: directiva/administración genera el cargo del periodo (se prorratea automático por alícuota, cuota fija por unidad, o en partes iguales) y marca cuotas como pagadas a mano; cada residente solo lee las suyas (sin pago online todavía).
- Panel de directiva/administración con KPIs (unidades, miembros, alertas activas, morosidad) y accesos directos a las secciones principales.
- Donación voluntaria (condominio → DevQuad) vía Mercado Pago Checkout Pro, mismo patrón de seguridad que PataAgenda (el webhook siempre re-consulta el pago por ID, nunca confía en el body; no extiende ningún plan, Condofy ya es gratis).
- Política de Privacidad y Términos de Uso (`/privacidad/`, `/terminos/`), con aceptación obligatoria al registrarse (o en el primer login para cuentas creadas por la directiva), y solicitud de eliminación de cuenta/datos desde "Mi perfil".
- Panel de administración (django-unfold) para el dueño de la plataforma.
- API REST documentada con Swagger en `/api/docs/` (drf-spectacular).

No implementado a propósito todavía: QR de visitas, encuestas, pago online de gastos comunes, confirmaciones de alerta entre vecinos, reportes, donación recurrente/mensual.

## Stack

Django 6 + Django REST Framework + JWT (`djangorestframework-simplejwt`) + PostgreSQL (SQLite en desarrollo) + Bootstrap (panel web) + django-unfold (admin) + Mercado Pago (donaciones) + Expo push notifications.

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
pagos/              # donaciones voluntarias (Mercado Pago)
```

Cada app de dominio (excepto `core`) sigue el mismo patrón: `models.py`, `serializers.py` + `api_views.py` + `api_urls.py` (API para la app móvil, bajo `/api/v1/`), y `views.py`/`forms.py`/`urls.py` cuando además tiene panel web.

## Despliegue

Mismo patrón que PataAgenda: `build.sh` + `render.yaml` para Render (Blueprint con web service + Postgres). Variables de entorno en `.env.example`.

## Roles

- **directiva**: todo lo de administración, más lo exclusivo de gobierno (Mi condominio, link/QR de autoregistro, nombrar otra directiva/administración).
- **administracion**: el día a día del condominio (miembros, unidades, gastos comunes, avisos, accesos) — puede ser un tercero contratado, no necesariamente un vecino elegido.
- **conserje**: registra accesos.
- **residente**: dispara alertas, lee avisos y sus propias cuotas (uso principal: la app móvil).

Cualquier rol puede ver y resolver alertas de pánico, y donar. Las cuentas de conserjería y residentes las puede crear tanto directiva como administración desde `/miembros/nuevo/` (contraseña temporal generada automáticamente, se muestra una sola vez); solo directiva puede nombrar otra directiva o administración.
