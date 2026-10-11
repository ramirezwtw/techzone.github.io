# TechZone

Plataforma de asesoría y catálogo de hardware para PC: catálogo de componentes,
builds recomendadas, solicitudes de "ayúdame a armar mi PC", foro de comunidad y
panel de administración.

**Stack:** FastAPI · Jinja2 (renderizado en el servidor) · SQLAlchemy 2.0 ·
Alembic · PostgreSQL en producción / SQLite en desarrollo · despliegue en Vercel.

## Estructura

```
.
├── app.py                  # entrypoint ASGI (uvicorn app:app y @vercel/python)
├── techzone/               # la aplicación
│   ├── app.py              # create_app(): middleware, static, routers, errores
│   ├── database.py         # URL de conexión, engine, sesión, dependencia get_db
│   ├── models.py           # modelos SQLAlchemy
│   ├── security.py         # sesión, CSRF y dependencias de acceso
│   ├── templating.py       # Jinja2 + url_for, csrf_token, flash, session
│   ├── mailer.py           # correos de verificación y recuperación
│   ├── seed_data.py        # catálogo y builds iniciales
│   ├── seed.py             # comando: python -m techzone.seed
│   └── routers/
│       ├── main.py         # home y páginas legales
│       ├── auth.py         # registro, login, verificación, recuperación
│       ├── admin.py        # panel: productos, builds, usuarios, solicitudes
│       ├── profile.py      # perfil y formulario de armado de PC
│       ├── community.py    # foro: publicaciones, comentarios, likes
│       └── builds.py       # detalle de una build
├── templates/              # plantillas Jinja2
├── static/                 # CSS e imágenes
├── migrations/             # revisiones de Alembic
├── tests/                  # suite de pytest
├── alembic.ini
├── pytest.ini
├── requirements.txt        # dependencias de producción
├── requirements-dev.txt    # + pytest y httpx
└── vercel.json
```

Las rutas se registran con nombre (`name="auth.login"`), y las plantillas las
resuelven con `url_for('auth.login')` igual que en Flask.

## Puesta en marcha (local)

```bash
pip install -r requirements-dev.txt
python -m techzone.seed --create-tables    # solo la primera vez
uvicorn app:app --reload                   # http://127.0.0.1:8000
```

Sin `DATABASE_URL` definida se usa el SQLite local `database.db`. El usuario
administrador que crea el seed es `admin@techzone.app` / `TechZone2026!`
(configurable con `ADMIN_EMAIL` y `ADMIN_PASSWORD`).

## Pruebas

```bash
pytest                      # las 109 pruebas, cada una con un SQLite temporal
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
