DEV  = docker-compose -f docker/dev/docker-compose.yml
PROD = docker-compose -f docker/prod/docker-compose.yml

.PHONY: dev-up dev-down dev-logs dev-shell dev-test dev-test-app dev-migrate dev-check \
        prod-up prod-down prod-logs prod-migrate

# --- Dev ---

dev-up:
	$(DEV) up -d

dev-down:
	$(DEV) down

dev-logs:
	$(DEV) logs -f web

dev-shell:
	$(DEV) exec web python manage.py shell

dev-test:
	$(DEV) exec web python manage.py test -v 2 --keepdb

dev-test-app:
	$(DEV) exec web python manage.py test apps.$(APP) -v 2 --keepdb

dev-migrate:
	$(DEV) exec web python manage.py makemigrations $(APP)
	$(DEV) exec web python manage.py migrate

dev-check:
	$(DEV) exec web python manage.py check

# --- Prod ---

prod-up:
	$(PROD) up -d

prod-down:
	$(PROD) down

prod-logs:
	$(PROD) logs -f web

prod-migrate:
	$(PROD) exec -T web python manage.py migrate --noinput
