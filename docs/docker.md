# Docker — Dev и Prod окружения

## Структура

```
docker/
  dev/   — локальная разработка (hot-reload, runserver)
  prod/  — продакшн (gunicorn + nginx + certbot)
```

---

## Dev-окружение

### Первый запуск

```bash
# Скопировать env-файл (уже содержит дефолтные значения для локальной разработки)
cp docker/dev/.env.dev docker/dev/.env.dev   # уже существует, редактировать не нужно

# Поднять окружение
make dev-up

# Применить миграции
make dev-migrate

# Создать суперпользователя
docker-compose -f docker/dev/docker-compose.yml exec web python manage.py createsuperuser
```

### Доступные адреса

| Сервис | URL |
|--------|-----|
| API docs | http://localhost:8000/api/v1/docs |
| Admin    | http://localhost:8000/admin/ |

### Часто используемые команды

```bash
make dev-up              # запустить все сервисы
make dev-down            # остановить
make dev-logs            # логи web-контейнера
make dev-shell           # Django shell
make dev-test            # запустить все тесты
make dev-test-app APP=doctors   # тесты одного приложения
make dev-migrate APP=services   # создать и применить миграции
make dev-check           # django system check
```

### Hot-reload

Код монтируется как volume — изменения в `.py`-файлах применяются без перезапуска контейнера.

---

## Prod-окружение

### Первичная настройка сервера

**1. Клонировать репозиторий**

```bash
git clone https://github.com/YOUR_USERNAME/alexa-backend.git /opt/alexa-backend
cd /opt/alexa-backend
```

**2. Создать `.env.prod`**

```bash
cp docker/prod/.env.prod.example docker/prod/.env.prod
nano docker/prod/.env.prod   # заполнить все значения
```

Обязательно заполнить:
- `SECRET_KEY` — сгенерировать: `python -c "import secrets; print(secrets.token_urlsafe(50))"`
- `ALLOWED_HOSTS` — домен сервера
- `DB_PASSWORD` и `POSTGRES_PASSWORD` — одинаковые, сложный пароль
- `DOCKER_IMAGE` — `ghcr.io/your-github-username/alexa-backend:latest`

**3. Первичная выдача SSL-сертификата**

Certbot требует, чтобы домен уже указывал на сервер.

*Шаг 3.1:* Временно настроить nginx только для HTTP (закомментировать HTTPS-блок в `nginx.conf`, заменить `YOUR_DOMAIN` на реальный домен).

```bash
# Заменить YOUR_DOMAIN в nginx.conf
sed -i 's/YOUR_DOMAIN/yourdomain.com/g' docker/prod/nginx/nginx.conf
```

*Шаг 3.2:* Поднять только nginx и db:

```bash
docker-compose -f docker/prod/docker-compose.yml up -d db nginx
```

*Шаг 3.3:* Получить сертификат:

```bash
docker-compose -f docker/prod/docker-compose.yml run --rm certbot \
  certonly --webroot --webroot-path=/var/www/certbot \
  --email your@email.com \
  -d yourdomain.com -d www.yourdomain.com \
  --agree-tos --no-eff-email
```

*Шаг 3.4:* Раскомментировать HTTPS-блок в `nginx.conf` (он уже присутствует в файле).

**4. Поднять все сервисы**

```bash
make prod-up
make prod-migrate
docker-compose -f docker/prod/docker-compose.yml exec -T web python manage.py collectstatic --noinput
docker-compose -f docker/prod/docker-compose.yml exec web python manage.py createsuperuser
```

### Обновление вручную (без CI/CD)

```bash
cd /opt/alexa-backend
git pull origin main
docker-compose -f docker/prod/docker-compose.yml pull web
make prod-up
make prod-migrate
docker-compose -f docker/prod/docker-compose.yml exec -T web python manage.py collectstatic --noinput
```

---

## CI/CD — GitHub Actions

При каждом пуше в ветку `main`:
1. GitHub Actions собирает образ из `docker/prod/Dockerfile`
2. Пушит на `ghcr.io/your-username/alexa-backend:latest`
3. Подключается к серверу по SSH и обновляет контейнеры

### Настройка секретов в GitHub репозитории

Перейти в **Settings → Secrets and variables → Actions** и добавить:

| Секрет | Описание |
|--------|----------|
| `SERVER_HOST` | IP-адрес или домен сервера |
| `SERVER_USER` | Пользователь SSH (например `ubuntu`) |
| `SERVER_SSH_KEY` | Приватный ключ SSH (содержимое `~/.ssh/id_rsa`) |
| `GHCR_TOKEN` | GitHub Personal Access Token с правом `read:packages` (создать на github.com/settings/tokens) |

### Генерация SSH-ключа для деплоя (если нет)

```bash
# Локально
ssh-keygen -t ed25519 -C "deploy-key" -f ~/.ssh/deploy_key

# Публичный ключ добавить на сервер
ssh-copy-id -i ~/.ssh/deploy_key.pub user@server

# Приватный ключ (содержимое ~/.ssh/deploy_key) добавить в секрет SERVER_SSH_KEY
```

---

## SSL-авторенewal

Certbot настроен как отдельный сервис в `docker-compose.yml` и автоматически обновляет сертификаты каждые 12 часов. Дополнительных действий не требуется.

Проверить статус:

```bash
docker-compose -f docker/prod/docker-compose.yml exec certbot certbot certificates
```
