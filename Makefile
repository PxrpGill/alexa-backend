.PHONY: up down logs shell test test-app migrate check

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f web

shell:
	docker-compose exec web python manage.py shell_plus

test:
	docker-compose exec web python manage.py test -v 2 --keepdb

test-app:
	docker-compose exec web python manage.py test apps.$(APP) -v 2 --keepdb

migrate:
	docker-compose exec web python manage.py makemigrations $(APP)
	docker-compose exec web python manage.py migrate

check:
	docker-compose exec web python manage.py check
