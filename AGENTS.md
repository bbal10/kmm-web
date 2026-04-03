# AGENTS.md

## Start here
- Read `README.md` and `kmm_web_backend/settings/README.md` first; they describe the repo’s canonical workflows and the settings split.
- Settings are selected in `kmm_web_backend/settings/__init__.py`: `DJANGO_ENV=production` loads `production.py`, otherwise `local.py` is used.

## Architecture map
- `data_management/` is the domain core: user registration/login, student profile CRUD, staff dashboard, exports, password reset, middleware, signals, and audit/security logging.
- `vite/` is the frontend bridge. The Vite app lives under `vite/src/` and builds into `static/dist` via `vite/src/vite.config.js`.
- Project routing starts in `kmm_web_backend/urls.py`, which includes `data_management.urls` at `/` and health checks from `data_management/health_checks.py`.
- `handler404` points to `vite.views.custom_404_view`.

## Request flow and access rules
- `data_management.middleware.AuthRedirectMiddleware` redirects authenticated users away from `/`, `/staff/`, and `/register/`.
- Staff is defined as either `user.is_staff` or membership in the `data_management_staff` group.
- Regular users are sent to `data_management:profile`; staff users go to `data_management:dashboard`.
- HTMX-aware views return partials and `HX-Redirect` headers on success, especially in `user_login` and `staff_login`.

## Data model conventions
- `Student` is one-to-one with Django `User`; profile creation is automated in `data_management/signals.py`.
- The app uses explicit choice fields and custom `*_custom` fallback fields for “other” values.
- Interests are stored through `StudentInterest`; view code syncs them manually instead of relying on a standard M2M form.

## Logging and audit trail
- Use `data_management.utils.logging_utils` for request/user context, audit logs, and security logs.
- Loggers are intentionally split: `data_management`, `data_management.security`, and `data_management.audit`.
- File logging is configured in `kmm_web_backend/settings/logging.py`; production settings switch logs to stdout/stderr.

## Frontend conventions
- Vite entrypoint: `vite/src/src/index.ts`; it wires SortableJS reorder updates and NotifyX toasts.
- Tailwind source scanning is configured in `vite/src/src/style.css` with `@source` covering Django HTML/Python/JS files.
- Frontend build command: `npm --prefix vite/src run build`; development command: `python manage.py vite dev`.

## Developer workflows
- Local setup: `uv sync`, copy an env file, run `python manage.py migrate`, then start Django + Vite separately.
- Docker workflow is preferred for production-like runs: `./validate-deployment.sh` then `./docker-deploy.sh`.
- `Makefile` is the shortcut layer for container tasks: use `make up`, `make down`, `make logs`, `make migrate`, `make collectstatic`, `make backup`, and `make check`.
- Run tests with `docker-compose exec web python manage.py test`.

## Deployment expectations
- Production requires a valid `SECRET_KEY` (50+ chars), `DATABASE_URL`, and `ALLOWED_HOSTS`.
- `docker-entrypoint.sh` waits for PostgreSQL/Redis, runs migrations, collects static files, and executes `python manage.py check --deploy` before starting the server.
- Health endpoints are `/health/`, `/ready/`, and `/alive/`.

## When editing
- Keep settings changes in the matching settings module (`apps.py`, `database.py`, `security.py`, `static.py`, `logging.py`, `local.py`, or `production.py`).
- Preserve the HTMX partial-rendering pattern and the existing staff/regular user split in `data_management/views.py`.
- Check `data_management/tests.py` if you touch student creation or staff flows; it already guards against duplicate profile creation.

