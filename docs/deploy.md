# Развёртывание на VPS + CI/CD (GitHub Actions + Docker)

> Пошаговая инструкция: от «голого VPS» до работающего продакшена с автоматическим
> деплоем при каждом пуше в `main`.

---

## 1. Как устроена система (кратко)

```
GitHub (main) ──push──▶ GitHub Actions
                           │  1. build image (docker/prod/Dockerfile)
                           │  2. push → ghcr.io/PxrpGill/alexa-backend:latest
                           ▼
                       appleboy/ssh-action ──SSH──▶ VPS (/opt/alexa-backend)
                                                    │  git pull + docker-compose pull
                                                    │  up -d + migrate + collectstatic
                                                    ▼
                              docker-compose (docker/prod/docker-compose.yml)
                        db(postgres:16) · redis · web(gunicorn) · worker(celery)
                                                   │  nginx:80/443 + certbot (SSL)
                                                   ▼
                                               https://yourdomain.com
```

Продакшн-образ (`docker/prod/Dockerfile`) собирается один раз в CI и раздаётся на
сервер из GHCR — сам сервер код не собирает, только тянет готовый образ.

**Три объекта аутентификации, не путать:**
| Ключ/токен | Кто → Кто | Где хранится |
|---|---|---|
| `SERVER_SSH_KEY` (пара А) | GitHub Actions → VPS | секрет в GitHub |
| SSH-ключ (пара Б) | VPS → GitHub (для `git pull`) | на сервере + Deploy Key в GitHub |
| `GHCR_TOKEN` (PAT) | VPS → ghcr.io (скачать образ) | секрет в GitHub |

---

## 2. Требования

- VPS: Ubuntu 22.04/24.04, от 2 vCPU / 2 GB RAM
- Домен (или subdomain), который вы контролируете (нужен для HTTPS)
- Репозиторий `PxrpGill/alexa-backend` (этот)

---

## 3. Подготовка домена (DNS)

Создайте в панели DNS вашего домена две A-записи, указывающие на **публичный IP VPS**:

| Type | Name | Value |
|---|---|---|
| A | `@` (yourdomain.com) | `<IP_сервера>` |
| A | `www` | `<IP_сервера>` |

Проверка после пропагации (5–30 минут): `dig +short yourdomain.com`.

---

## 4. Первичная настройка VPS

Выполняется один раз по SSH под root.

### 4.1. Создать deploy-пользователя

```bash
adduser deploy
usermod -aG sudo deploy
```

### 4.2. Установить Docker + docker-compose

```bash
# Docker (официальный скрипт)
curl -fsSL https://get.docker.com | sh

# docker-compose v2 (standalone-бинарь — используется в workflow и Makefile)
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
     -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Право запускать docker без sudo
usermod -aG docker deploy
```

Выйти и зайти заново, чтобы группа подхватилась: `exit`, затем `ssh deploy@<IP>`.
Проверка: `docker version && docker-compose version`.

### 4.3. Файрвол (UFW)

```bash
  c
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
ufw status
```

> Никогда не открывайте `5432` (Postgres) наружу — база ходит только по внутренней
> docker-сети.

### 4.4. Директория под проект

```bash
sudo mkdir -p /opt/alexa-backend
sudo chown deploy:deploy /opt/alexa-backend
```

---

## 5. SSH-ключи (две пары)

### 5.1. Пара А — GitHub Actions → VPS

Генерируем **на локальной машине** (там, где GitHub Actions будет «сидеть»):

```bashc
ssh-keygen -t ed25519 -C "gh-actions-deploy" -f ~/.ssh/gh_actions_key
ssh-copy-id -i ~/.ssh/gh_actions_key.pub deploy@<IP_сервера>
```

Приватный ключ (`~/.ssh/gh_actions_key`) понадобится позже для секрета
`SERVER_SSH_KEY`. Публичный теперь разрешает вход на сервер.

### 5.2. Пара Б — VPS → GitHub (для `git pull`)

Генерируем **на самом сервере**:

```bash
ssh-keygen -t ed25519 -C "deploy@vps" -f ~/.ssh/id_ed25519 -N ""
ssh-keyscan github.com >> ~/.ssh/known_hosts
cat ~/.ssh/id_ed25519.pub
```

Полученный публичный ключ добавьте в GitHub:
**Repo → Settings → Deploy keys → Add deploy key** (Read-only, галку
«Allow write access» НЕ ставить).

---

## 6. Размещение репозитория на сервере

```bash
cd /opt/alexa-backend
git clone git@github.com:PxrpGill/alexa-backend.git /opt/alexa-backend
```

> Если репозиторий публичный — можно `git clone https://github.com/PxrpGill/alexa-backend.git`
> и пропустить Deploy key. SSH-способ универсальнее.

---

## 7. Конфигурация продакшена

### 7.1. Файл `.env.prod`

```bash
cp docker/prod/.env.prod.example docker/prod/.env.prod
nano docker/prod/.env.prod
```

Заполните значения:

```ini
SECRET_KEY=                          # сгенерировать: python3 -c "import secrets; print(secrets.token_urlsafe(50))"
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CORS_ALLOWED_ORIGINS=https://yourdomain.com

DB_NAME=alexa
DB_USER=alexa
DB_PASSWORD=<сложный пароль>
DB_HOST=db
DB_PORT=5432

POSTGRES_DB=alexa
POSTGRES_USER=alexa
POSTGRES_PASSWORD=<тот же пароль, что DB_PASSWORD>

DOCKER_IMAGE=ghcr.io/PxrpGill/alexa-backend:latest

CELERY_BROKER_URL=redis://redis:6379/0
```

Файл в `.gitignore` (git pull его не трогает). **Никогда не коммитьте его.**

### 7.2. Домен в nginx + защита от перезаписи при git pull

```bash
cd /opt/alexa-backend
sed -i 's/YOUR_DOMAIN/yourdomain.com/g' docker/prod/nginx/nginx.conf

# Ключевой шаг: git pull при деплоях больше НЕ будет перезаписывать этот файл
git update-index --skip-worktree docker/prod/nginx/nginx.conf
```

> Без `skip-worktree` каждый деплой возвращал бы в nginx.conf заглушку
> `YOUR_DOMAIN` и ломал SSL. Проверить статус: `git ls-files -v docker/prod/nginx/nginx.conf`
> (строчная `S` = защищён). Снять защиту при осознанной правке:
> `git update-index --no-skip-worktree docker/prod/nginx/nginx.conf`.

### 7.3. Первичная выдача SSL (bootstrap)

Проблема: HTTPS-блок в nginx.conf ссылается на ещё не существующие сертификаты,
поэтому nginx не стартует, пока их нет. Решаем за два приёма.

**Шаг 1.** Временно закомментируйте HTTPS-блок (строки `server { listen 443 ssl; ... }`)
в `docker/prod/nginx/nginx.conf` с помощью `nano`. Сохраните.

**Шаг 2.** Поднимите БД и nginx (HTTP-режим), получите сертификат:

```bash
cd /opt/alexa-backend
docker-compose -f docker/prod/docker-compose.yml up -d db nginx

docker-compose -f docker/prod/docker-compose.yml run --rm certbot certonly \
  --webroot --webroot-path=/var/www/certbot \
  --email you@example.com \
  -d yourdomain.com -d www.yourdomain.com \
  --agree-tos --no-eff-email
```

**Шаг 3.** Раскомментируйте HTTPS-блок обратно в `nginx.conf`, затем поднимите весь стек
(nginx пересоздастся уже с настоящими сертификатами):

```bash
docker-compose -f docker/prod/docker-compose.yml up -d
```

> Дальше сертификаты обновляет сам сервис `certbot` (каждые 12 часов). Вручную больше
> ничего делать не нужно.

---

## 8. Первый запуск приложения

```bash
cd /opt/alexa-backend

# Миграции и статика
docker-compose -f docker/prod/docker-compose.yml exec -T web python manage.py migrate --noinput
docker-compose -f docker/prod/docker-compose.yml exec -T web python manage.py collectstatic --noinput

# Суперпользователь для /admin/
docker-compose -f docker/prod/docker-compose.yml exec -T web python manage.py createsuperuser

# Статус и логи
docker-compose -f docker/prod/docker-compose.yml ps
docker-compose -f docker/prod/docker-compose.yml logs -f web
```

Проверка:
- `https://yourdomain.com/api/v1/docs` — API docs
- `https://yourdomain.com/admin/` — админка

---

## 9. Настройка CI/CD в GitHub

### 9.1. Токен для GHCR (PAT)

1. Перейти: **github.com → Settings → Developer settings → Personal access tokens → Tokens (classic)**
2. **Generate new token**, выбрать scope **`read:packages`** (одного достаточно)
3. Скопировать токен.

> `GITHUB_TOKEN` из Actions использовать НЕЛЬЗЯ — он короткоживущий, сервер им
> залогиниться не сможет. Нужен именно персональный PAT.

### 9.2. Секреты репозитория

**Repo → Settings → Secrets and variables → Actions → New repository secret:**

| Секрет | Значение |
|---|---|
| `SERVER_HOST` | IP или домен VPS |
| `SERVER_USER` | `deploy` |
| `SERVER_SSH_KEY` | содержимое `~/.ssh/gh_actions_key` (приватный ключ из шага 5.1) |
| `GHCR_TOKEN` | PAT из шага 9.1 |

### 9.3. Проверка пакета в GHCR

Первое время пакет будет приватным — это нормально, сервер ходит по PAT.
Убедиться, что пакет появился: **Repo → Packages → alexa-backend**.

---

## 10. Как идёт деплой

При каждом **push в `main`** автоматически:
1. Actions собирает образ из `docker/prod/Dockerfile` и пушит в GHCR
   (теги `latest` и `+sha`);
2. По SSH на сервере: `git pull`, login в GHCR, `docker-compose pull web`,
   `up -d`, `migrate`, `collectstatic`.

Следить: **Repo → Actions → «Build and Deploy»**.

> В текущем workflow обновление web-контейнера тянет и worker, т.к. оба используют
> один тег `:latest` (compose пересоздаёт сервис, чей образ изменился).
> Для явности можно заменить `pull web` на `pull web worker`.

**Ручной запуск** (если push в main нежелателен): добавить в `deploy.yml`
триггер `workflow_dispatch:` в блок `on:` — появится кнопка «Run workflow».

---

## 11. Эксплуатация (day-2)

### Логи и статус

```bash
docker-compose -f docker/prod/docker-compose.yml ps
docker-compose -f docker/prod/docker-compose.yml logs -f web        # gunicorn
docker-compose -f docker/prod/docker-compose.yml logs -f worker     # celery
docker-compose -f docker/prod/docker-compose.yml logs -f nginx      # http
```

### Резервное копирование БД

Добавить в crontab на сервере (`crontab -e`):

```cron
0 3 * * * docker exec alexa-backend-db-1 pg_dump -U alexa alexa | gzip > /opt/backups/alexa_$(date +\%F).sql.gz
```

> Имя контейнера посмотреть: `docker ps --format '{{.Names}}'`. Восстановление:
> `gunzip -c backup.sql.gz | docker exec -i <имя> psql -U alexa alexa`.

### Обновление вручную (без CI)

```bash
cd /opt/alexa-backend
git pull origin main
docker-compose -f docker/prod/docker-compose.yml pull web
docker-compose -f docker/prod/docker-compose.yml up -d
docker-compose -f docker/prod/docker-compose.yml exec -T web python manage.py migrate --noinput
docker-compose -f docker/prod/docker-compose.yml exec -T web python manage.py collectstatic --noinput
```

### Откат

```bash
# Откатить на предыдущий образ по SHA коммита
export DOCKER_IMAGE=ghcr.io/PxrpGill/alexa-backend:<sha_предыдущего_коммита>
docker-compose -f docker/prod/docker-compose.yml up -d web worker
```

---

## 12. Частые проблемы

| Симптом | Причина / решение |
|---|---|
| `502 Bad Gateway` | упал gunicorn: `docker-compose logs web`; часто — упал Celery/Redis, проверьте `depends_on` |
| `400 Bad Request` | `ALLOWED_HOSTS` не содержит домен в `.env.prod` |
| SSL не выдаётся | DNS ещё не пропагировался; порт 80 закрыт файрволом; `YOUR_DOMAIN` остался в nginx.conf |
| nginx не стартует после первого запуска | не выполнен bootstrap из шага 7.3 (нет сертификатов) |
| `git pull` сбросил nginx.conf | пропал `skip-worktree` — выполнить команду из шага 7.2 снова |
| `denied: requested access to the resource is denied` на GHCR | `GHCR_TOKEN` без scope `read:packages`, либо пакет приватный и токен не от владельца |
| контейнеры падают с ошибкой БД | база ещё не поднялась на старте — добавьте `restart: always` (уже есть) и подождите |

---

## 13. Рекомендуемые улучшения (не обязательно сразу)

- Добавить в CI **прогон тестов** перед сборкой (`python manage.py test`).
- Добавить `healthcheck` для `web` в compose (curl `/api/v1/docs`).
- Перейти с `docker-compose` (standalone) на плагин `docker compose` v2 и поправить
  workflow/Makefile — единая команда, встроенная в Docker.
- Настроить `SENTRY_DSN` для мониторинга ошибок продакшена.
- Слать уведомления о деплое в Telegram/Slack через `workflow_dispatch` + notify.
