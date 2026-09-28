DEV  = docker-compose -f docker/dev/docker-compose.yml
PROD = docker-compose -f docker/prod/docker-compose.yml

# Прод-цели читают DOCKER_IMAGE и DOMAIN из .env.prod: compose требует их
# на этапе интерполяции, env_file на этом этапе ещё не применён.
PROD_ENV = set -a; . docker/prod/.env.prod; set +a;

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
	$(PROD_ENV) $(PROD) up -d

prod-down:
	$(PROD_ENV) $(PROD) down

prod-logs:
	$(PROD_ENV) $(PROD) logs -f web

prod-migrate:
	$(PROD_ENV) $(PROD) exec -T web python manage.py migrate --noinput
