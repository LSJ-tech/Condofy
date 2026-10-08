# Condofy

SaaS de emergencias y gestión para juntas de vecinos y condominios en Chile — segundo producto de [DevQuad](https://devquad.cl), en la misma línea que [PataAgenda](https://patagenda.devquad.cl).

Botón de pánico con notificación push, comunicación vecinal (avisos), gestión de accesos y gastos comunes, con un panel web (instalable como PWA) para directiva/administración/conserjería/residentes. Una app nativa (React Native + Expo) es el siguiente paso si el volumen de clientes lo justifica.

**Condofy es gratis, sin límite de unidades ni de tiempo** — no hay plan pago ni suscripción. Existe una donación voluntaria opcional (condominio → DevQuad) para apoyar el desarrollo.

## Estado actual

Implementado y probado de punta a punta:

- Registro self-service de un condominio (crea Condominio + cuenta de directiva). Las torres las configura DevQuad al dar de alta al cliente; las unidades las carga la directiva/administración.
- Multi-tenant real: cada condominio solo ve sus propios datos (verificado con tests de aislamiento).
- 4 roles: **directiva** (gobierno: miembros, unidades, avisos, accesos, Mi condominio), **administración** (día a día, incluyendo lo exclusivo de gastos comunes -- generar el cargo del periodo y los datos de transferencia, que ni la directiva puede tocar), **conserjería** (accesos), **residente**.
- Botón de pánico: la app/API crea una `Alerta` con ubicación GPS, se envía push a todo el condominio (vía Expo), y **cualquier miembro** (no solo directiva/conserjería) puede ver el mapa y resolverla o marcarla como falsa alarma. Se auto-cierra sola si nadie responde en 30 minutos. Historial completo filtrable en `/alertas/historial/`.
- Avisos (muro de noticias simple): directiva/administración publican, todos los miembros leen.
- Accesos: registro manual de ingresos por conserjería/directiva/administración desde el panel (sin QR todavía).
- Gastos comunes: **administración** (exclusivo, ni directiva) genera el cargo del periodo (se prorratea automático por alícuota, cuota fija por unidad, o en partes iguales) y define los datos de transferencia; directiva/administración marcan cuotas como pagadas a mano; cada residente solo lee las suyas (sin pago online todavía).
- Panel de directiva/administración con KPIs (unidades, miembros, alertas activas, morosidad) y accesos directos a las secciones principales.
- Donación voluntaria (condominio → DevQuad) vía Mercado Pago Checkout Pro, mismo patrón de seguridad que PataAgenda (el webhook siempre re-consulta el pago por ID, nunca confía en el body; no extiende ningún plan, Condofy ya es gratis).
- Política de Privacidad y Términos de Uso (`/privacidad/`, `/terminos/`), con aceptación obligatoria al registrarse (o en el primer login para cuentas creadas por la directiva), y solicitud de eliminación de cuenta/datos desde "Mi perfil".
- Panel de administración (django-unfold) para el dueño de la plataforma.
- API REST documentada con Swagger en `/api/docs/` (drf-spectacular).
- PWA instalable (manifest + service worker en `/sw.js`, íconos propios): ícono en el escritorio del celular, ventana standalone, página de respaldo sin conexión en `/offline/`. **Con Web Push real**: botón de pánico y avisos llegan como notificación del sistema aunque la PWA esté cerrada (VAPID + `pywebpush`, generar el par de llaves con `manage.py generar_vapid_keys`) -- separado de `DispositivoPush`/Expo, que sigue siendo solo para la futura app nativa.

No implementado a propósito todavía: QR de visitas, encuestas, pago online de gastos comunes, confirmaciones de alerta entre vecinos, reportes, donación recurrente/mensual, app nativa.

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

Tests: `python manage.py test` (cubre permisos por rol, el gate de Términos/Privacidad, y donaciones/webhook de Mercado Pago).

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

- **directiva**: miembros, unidades, avisos, accesos, más lo exclusivo de gobierno (Mi condominio, link/QR de autoregistro, nombrar otra directiva/administración). **No** incluye generar gastos comunes ni editar los datos de transferencia -- eso es exclusivo de administración, a pedido explícito del cliente (es la única área donde administración tiene más permiso que directiva).
- **administracion**: el día a día del condominio (miembros, unidades, avisos, accesos), más lo exclusivo de gastos comunes: generar el cargo del periodo y los datos de transferencia — puede ser un tercero contratado, no necesariamente un vecino elegido.
- **conserje**: registra accesos.
- **residente**: dispara alertas, lee avisos y sus propias cuotas (uso principal: la app móvil).

Cualquier rol puede ver y resolver alertas de pánico, y donar. Las cuentas de conserjería y residentes las puede crear tanto directiva como administración desde `/miembros/nuevo/` (contraseña temporal generada automáticamente, se muestra una sola vez); solo directiva puede nombrar otra directiva o administración.
