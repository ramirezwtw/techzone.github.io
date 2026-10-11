# TechZone

Plataforma de asesoría y catálogo de hardware para PC: catálogo de componentes,
builds recomendadas, solicitudes de "ayúdame a armar mi PC", foro de comunidad y
panel de administración.

**Stack:** FastAPI + arquitectura en capas · Astro para el sitio público ·
Jinja2 para los formularios y el panel · SQLAlchemy 2.0 · Alembic ·
PostgreSQL en producción / SQLite en desarrollo · despliegue en Vercel.

## Arquitectura

El backend está separado en capas y cada una solo habla con la de abajo:

| Capa | Responsabilidad |
|---|---|
| `routers/` (HTML) y `api/` (JSON) | HTTP: leer el formulario, validar CSRF, elegir status, renderizar o redirigir |
| `services/` | reglas de negocio: validaciones, estados, CSV de usos, contadores |
| `repositories/` | todas las consultas SQLAlchemy |
| `models.py` | mapeo ORM |
| `core/` | infraestructura: conexión, sesión, plantillas, correo |
| `schemas/` | DTOs Pydantic de la API (no exponen columnas internas) |

El frontend tiene dos mitades que conviven:

* **Astro** (`frontend/`) para el sitio público —home, detalle de build, legales
  y foro— consumiendo `/api/v1/*`.
* **Jinja2** (`templates/`) para todo lo que lleva formulario con sesión:
  login, registro, perfil, armado de PC y el panel de administración.

## Estructura

```
.
├── app.py                  # entrypoint ASGI (uvicorn app:app y @vercel/python)
├── techzone/
│   ├── app.py              # create_app(): middleware, static, routers, errores
│   ├── models.py           # modelos SQLAlchemy
│   ├── seed_data.py        # catálogo y builds iniciales
│   ├── seed.py             # comando: python -m techzone.seed
│   ├── core/               # database, security, templating, mailer
│   ├── repositories/       # products, builds, users, posts, build_requests, tokens
│   ├── services/           # catalog, accounts, build_requests, community, stats, pages
│   ├── schemas/            # DTOs de la API
│   ├── api/v1/             # endpoints JSON
│   └── routers/            # vistas HTML (Jinja)
├── frontend/               # Astro: sitio público
│   ├── astro.config.mjs    # adaptador Node + proxy al backend en desarrollo
│   └── src/
│       ├── lib/api.ts      # cliente de la API (tipado, reenvía cookies)
│       ├── layouts/        # Base (home) y Minimal (páginas internas)
│       ├── components/     # Nav, Footer, Flash, Chatbot, SiteScripts
│       └── pages/          # index, builds/[id], legal/[slug], comunidad/
├── templates/              # plantillas Jinja2 (formularios y panel)
├── static/                 # CSS e imágenes (las sirve FastAPI)
├── migrations/             # revisiones de Alembic
├── tests/                  # 135 pruebas de pytest
├── alembic.ini
├── pytest.ini
├── requirements.txt        # dependencias de producción
├── requirements-dev.txt    # + pytest y httpx
└── vercel.json
```

Las rutas Jinja se registran con nombre (`name="auth.login"`) y las plantillas
las resuelven con `url_for('auth.login')`, igual que en Flask.

## La API

| Endpoint | Para qué |
|---|---|
| `GET /api/v1/home` | todo lo que necesita el home en una llamada |
| `GET /api/v1/catalog/products` · `/builds` · `/builds/{id}` | catálogo público |
| `GET /api/v1/community/posts` · `/posts/{id}` · `/stats` | foro |
| `GET /api/v1/legal/{slug}` | páginas legales |
| `GET /api/v1/me` | quién está conectado + avisos pendientes |
| `GET /api/v1/csrf` | token para los formularios que procesa el backend |

Documentación interactiva en `/docs`.

Dos detalles importantes de `/me` y `/csrf`: **consumen y modifican la sesión**
(los avisos se entregan una sola vez y el token se guarda en la cookie), así
que el frontend tiene que reenviar al navegador el `Set-Cookie` de la
respuesta. Eso lo hacen `loadSession()` y `loadCsrf()` en `frontend/src/lib`.

## Puesta en marcha (local)

Backend:

```bash
pip install -r requirements-dev.txt
python -m techzone.seed --create-tables    # solo la primera vez
uvicorn app:app --reload                   # http://127.0.0.1:8000
```

El sitio completo ya funciona en ese puerto con las plantillas Jinja. Para
trabajar con el frontend Astro, en otra terminal y con el backend arriba:

```bash
cd frontend
npm install                                # solo la primera vez
npm run dev                                # http://localhost:4321
```

En `localhost:4321` el servidor de Astro sirve el sitio público y hace de proxy
hacia FastAPI para `/api`, `/static`, el panel y los formularios. Así todo
queda en el mismo origen y la cookie de sesión funciona igual que en
producción: si inicias sesión en `/login`, el menú de Astro ya te reconoce.

**Hoy en producción manda Jinja.** El frontend Astro está completo y verificado
en local, pero el despliegue sigue sirviendo las plantillas: cambiar eso es una
decisión de infraestructura (hay que meter un runtime Node junto al de Python
en Vercel, o separar el frontend en su propio proyecto).

Sin `DATABASE_URL` definida se usa el SQLite local `database.db`. El usuario
administrador que crea el seed es `admin@techzone.app` / `TechZone2026!`
(configurable con `ADMIN_EMAIL` y `ADMIN_PASSWORD`).

## Pruebas

```bash
pytest                      # las 135 pruebas, cada una con un SQLite temporal
pytest tests/test_auth.py   # un solo archivo
pytest -k admin             # por nombre
```

## Base de datos

```bash
alembic upgrade head                        # aplicar migraciones
alembic revision --autogenerate -m "..."    # crear una nueva
```

Alembic y la aplicación leen la misma `DATABASE_URL`. En PostgreSQL remoto se
fuerza `sslmode=require`, y en Vercel se usa `NullPool` (una conexión por
request, sin pool propio); si el proveedor ofrece un endpoint con pooler
—como el host `-pooler` de Neon— conviene apuntar `DATABASE_URL` ahí.

## Variables de entorno

| Variable | Para qué | Obligatoria |
|---|---|---|
| `DATABASE_URL` | PostgreSQL de producción | Sí en Vercel |
| `SECRET_KEY` | firma de la cookie de sesión | Sí en producción |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | credenciales que crea el seed | No |
| `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_USE_TLS`, `MAIL_DEFAULT_SENDER` | envío real de correos; sin `MAIL_SERVER` se imprimen en consola | No |

## Despliegue

`vercel.json` publica `app.py` como función serverless ASGI y enruta todo el
tráfico ahí. El esquema y los datos iniciales **no** se crean en el arranque:
se ejecutan a mano una vez por entorno con `alembic upgrade head` y
`python -m techzone.seed`.
