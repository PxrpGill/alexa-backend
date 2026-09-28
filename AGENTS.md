# AGENTS.md

Django 5.1.4 + django-ninja backend for the "Alexa" dental clinic (multi-branch, public REST API for a Next.js frontend).

## Commands (Docker-based; all Django commands run inside the `web` container)

```bash
make dev-up              # start db + redis + web + worker (docker-compose, standalone v2 binary)
make dev-migrate APP=<app>   # makemigrations <app> && migrate  (use short name: doctors, NOT apps.doctors)
make dev-test            # python manage.py test -v 2 --keepdb
make dev-test-app APP=doctors
make dev-shell           # django shell
make dev-check           # python manage.py check
```

- No lint/typecheck tooling. Verify with `make dev-check` + tests.
- Tests need `--keepdb` (test DB lives in a Docker volume). Add new apps/tests without worrying about DB reset.
- Dev compose: `docker/dev/docker-compose.yml`. Default settings module is `config.settings.dev` (set in `manage.py` and `config/celery.py`).

## Structure / conventions

- Settings: `config/settings/{base,dev,prod}.py`. New app ⇒ add to `LOCAL_APPS` in `base.py` (`jazzmin` must stay first in `INSTALLED_APPS`).
- New API router ⇒ import + `api.add_router("/name", ...)` in `config/api.py`. Base URL `/api/v1/`; docs at `/api/v1/docs`; OpenAPI at `/api/v1/openapi.json`.
- `APPEND_SLASH = False` — endpoint paths have no trailing slash (`@router.get("")`, `@router.get("/{slug}")`, `@router.post("")`). Tests hit exact paths.
- Every app ships: `models.py`, `admin.py`, `api.py`, `schemas.py` (`*CreateSchema` for POST bodies), optional `tests.py`. Models use Russian `verbose_name` on all fields and in `Meta`.
- `AUTH_USER_MODEL = "users.User"` (roles only — there is **no** `branch` FK on User).

## Cross-app FKs: use the branch app

There is **no `apps/branches` and no `services` app anymore** (both are gone from the current tree). Cross-app FKs use direct imports, not string refs:

```python
from apps.branch.models import BranchModel  # model class is BranchModel, not Branch
```

- `BranchModel`: **UUID primary key** (`id` is a uuid, not int), `unique=True` name, auto-generated transliterated `slug` (via `pytils`) computed in `save()`.
- Other apps' forms select a branch by **`branch_slug` string** (`get_object_or_404(BranchModel, slug=...)`), never by id.

## Image handling (auto webp/avif variants)

Models that store images inherit `ImageVariantsMixin` (`apps/common/mixins.py`) and declare `IMAGE_VARIANT_FIELDS = ['photo', 'photo_mobile']`. On `save()`, a Celery task (`apps/common/tasks.py`) generates `.webp`/`.avif` next to the original (needs `pillow_avif`). Celery runs eager under tests (`CELERY_TASK_ALWAYS_EAGER = "test" in sys.argv`).

In API schemas, expose images via `build_picture_format(obj.photo, obj.photo_mobile)` from `apps/common/schemas.py` → `PictureFormatSchema` (`{original, webp, avif}`, each `{src, mobile}`). Don't return raw URLs.

## Lead-form POST endpoints (appointments, dms, consultation, promotions/request)

All four copy the same pattern from `apps/appointments/api.py`:
- Require `payload.is_privacy_agreement`, else `400` + `ErrorResponseMessageSchema`.
- Resolve `BranchModel` by slug, create record (store `is_ad_agreement` / `is_privacy_agreement`).
- Return `{201: SuccessResponseMessageSchema, 400: ErrorResponseMessageSchema}`.

- Add `@throttle_lead_form` (below the `@router.post` decorator) and declare
  `429: ErrorResponseMessageSchema` — `tests/test_api_smoke.py` enforces this.

When adding a new lead-type endpoint, replicate this exact shape.

## Reverse-proxy assumptions

- Client IP comes from `apps.common.throttling.get_client_ip` (`X-Real-IP`, then the
  LAST `X-Forwarded-For` hop), gated by `TRUST_PROXY_HEADERS` (default `not DEBUG`).
  Never use `REMOTE_ADDR` directly — behind nginx it is the proxy's own address.
- Private uploads (CV files) are served by `apps/vacancies/views.download_resume`
  (staff-only, X-Accel-Redirect); `/media/vacancies/resumes/` is `internal` in nginx.
- `docker/prod/nginx/nginx.conf` is `skip-worktree` on the server — repo edits must be
  copied over by hand (`docs/deploy.md` §7.2 and §14).

## Gotchas

- `BlogPost.save()` auto-applies typography (`apps/common/typography.py`: typograph_text / typograph_html strips `style` attrs). Preserve that behavior when overriding `save()`.
- Blog list endpoint uses custom pagination: query params `page`, `perPage`, `allPages`; response is `PaginatedBlogPostSchema` (`items` + `pagination`), not a plain list.
- Promotions date filtering uses `timezone.localdate()`; `ends_at__isnull=True` means "ongoing".
- Git workflow: feature branches `feat/*` → PR → merge to `main` triggers CI deploy (GHCR image + SSH to VPS). Commit messages in Russian.
- `apps/vacancies/` is fully implemented (vacancy tree + applications with resume upload, own `validators.py` and IP throttling); `apps/dms/tests.py` and `apps/consultation/tests.py` are still empty scaffolds.

## Stale references (do NOT trust)

- `.claude/PROJECT_MEMORY.md` and `docs/superpowers/` (plans + specs) describe the original 9-task plan, back when `apps/branches`, `apps/services` and `BranchFilterMixin` existed. They are historical, not a status of the current tree.
- `CLAUDE.md` is up to date (rewritten 2026-09-28) and covers the same conventions in more detail — keep both in sync when a convention changes.
- Real deploy docs: `docs/deploy.md`, `docs/docker.md`.
