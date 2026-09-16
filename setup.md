# Установка и конфигурация окружения (.env)

---

## Оглавление

1. [Переменные окружения (.env)](#переменные-окружения-env)  
   - [1. Основные настройки Django](#1-основные-настройки-django)  
   - [2. Автоматическое создание суперпользователя (для Docker)](#2-автоматическое-создание-суперпользователя-для-docker)  
   - [3. Режимы работы базы данных (DB_MODE)](#3-режимы-работы-базы-данных-db_mode)  
   - [4. Хранилище медиа-файлов (USE_S3_MEDIA)](#4-хранилище-медиа-файлов-use_s3_media)  
   - [5. Email-уведомления (Resend)](#5-email-уведомления-resend)  
   - [6. Интеграция с OAuth2-провайдерами](#6-интеграция-с-oauth2-провайдерами)  
2. [Инструкции по запуску](#инструкции-по-запуску)  
   - [💻 Сценарий 1: Локальная разработка (SQLite, без Docker)](#сценарий-1-локальная-разработка-sqlite-без-docker)  
   - [🐳 Сценарий 2: Локальный запуск в Docker (PostgreSQL)](#сценарий-2-локальный-запуск-в-docker-postgresql)  
   - [☁️ Сценарий 3: Деплой на Render (внешняя БД и Yandex S3)](#сценарий-3-деплой-на-render-внешняя-бд-и-yandex-s3)  
3. [Дополнительные замечания](#дополнительные-замечания)

---

## Переменные окружения (.env)

Создайте файл `.env` в корневой директории проекта. Ниже приведено полное описание всех доступных переменных.

### 1. Основные настройки Django

| Переменная             | Тип      | По умолчанию | Описание                                                                              |
|:-----------------------|:---------|:-------------|:--------------------------------------------------------------------------------------|
| `DJANGO_SECRET_KEY`    | `string` | `no_key`     | Секретный ключ приложения Django.                                                     |
| `DJANGO_DEBUG`         | `bool`   | `True`       | Включение режима отладки (в продакшене ставить `False`).                              |
| `DJANGO_ALLOWED_HOSTS` | `string` | `*`          | Список разрешённых хостов через запятую (например, `127.0.0.1,localhost,domain.com`). |
| `ON_RENDER`            | `bool`   | `False`      | Флаг развертывания на Render. Включает раздачу статики через WhiteNoise.              |

[🔝 Наверх](#установка-и-конфигурация-окружения-env)

### 2. Автоматическое создание суперпользователя (для Docker)

| Переменная | Тип | По умолчанию | Описание |
| :--- | :--- | :--- | :--- |
| `DJANGO_SUPERUSER_USERNAME` | `string` | `admin` | Имя пользователя суперпользователя. |
| `DJANGO_SUPERUSER_EMAIL` | `string` | `admin@example.com` | Email суперпользователя. |
| `DJANGO_SUPERUSER_PASSWORD` | `string` | `admin123` | Пароль суперпользователя. |

[🔝 Наверх](#установка-и-конфигурация-окружения-env)

### 3. Режимы работы базы данных (`DB_MODE`)

Переменная `DB_MODE` определяет, какую базу данных использовать:

- `sqlite` — локальная SQLite (для разработки)
- `postgres` — самостоятельный PostgreSQL (для Docker-контейнера)
- `url` — внешняя БД по строке подключения (Supabase, Neon, Render Postgres и т.п.)

#### Общие настройки для всех режимов

| Переменная    | Тип        | По умолчанию        | Описание                                                 |
|:--------------|:-----------|:--------------------|:---------------------------------------------------------|
| `DB_NAME`     | `string`   | `web_db`            | Имя базы данных.                                         |
| `DB_USER`     | `string`   | `postgres`          | Пользователь базы данных.                                |
| `DB_PASSWORD` | `string`   | `postgres_password` | Пароль базы данных.                                      |
| `DB_HOST`     | `string`   | `db`                | Хост БД (`db` для docker-compose, `localhost` локально). |
| `DB_PORT`     | `string`   | `5432`              | Порт базы данных.                                        |

#### Настройки для `DB_MODE=url`

| Переменная       | Тип        | По умолчанию | Описание                                                                                                                                                                |
|:-----------------|:-----------|:-------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `DATABASE_URL`   | `string`   | —            | Полная строка подключения к БД (например: `postgres://user:pass@ep-cool-site.us-east-1.aws.neon.tech/neondb`). SSL включается автоматически при отсутствии `?sslmode=`. |

[🔝 Наверх](#установка-и-конфигурация-окружения-env)

### 4. Хранилище медиа-файлов (`USE_S3_MEDIA`)

Разделение статики и медиа позволяет сохранять пользовательские файлы при перезапусках контейнеров.

| Переменная                | Тип       | По умолчанию                       | Описание                                                                                           |
|:--------------------------|:----------|:-----------------------------------|:---------------------------------------------------------------------------------------------------|
| `USE_S3_MEDIA`            | `bool`    | `False`                            | Если `True`, загружаемые файлы сохраняются в Yandex Cloud S3; если `False` – локально в `/media/`. |
| `AWS_STORAGE_BUCKET_NAME` | `string`  | —                                  | Имя бакета в Yandex Cloud Object Storage.                                                          |
| `AWS_ACCESS_KEY_ID`       | `string`  | —                                  | Идентификатор ключа доступа (Key ID).                                                              |
| `AWS_SECRET_ACCESS_KEY`   | `string`  | —                                  | Секретный ключ (Secret Key).                                                                       |
| `AWS_S3_ENDPOINT_URL`     | `string`  | `https://storage.yandexcloud.net`  | Эндпоинт Yandex Cloud S3.                                                                          |

[🔝 Наверх](#установка-и-конфигурация-окружения-env)

### 5. Email-уведомления (Resend)

| Переменная           | Тип       | По умолчанию | Описание                                                    |
|:---------------------|:----------|:-------------|:------------------------------------------------------------|
| `RESEND_API_KEY`     | `string`  | —            | API-ключ сервиса Resend для отправки писем.                 |
| `DEFAULT_FROM_EMAIL` | `string`  | —            | Email-адрес отправителя (должен быть подтверждён в Resend). |

[🔝 Наверх](#установка-и-конфигурация-окружения-env)

### 6. Интеграция с OAuth2-провайдерами

| Переменная               | Тип       | По умолчанию | Описание                                 |
|:-------------------------|:----------|:-------------|:-----------------------------------------|
| `YANDEX_OAUTH2_KEY`      | `string`  | —            | ID приложения Яндекс OAuth.              |
| `YANDEX_OAUTH2_SECRET`   | `string`  | —            | Секретный ключ приложения Яндекс OAuth.  |
| `GITHUB_OAUTH2_KEY`      | `string`  | —            | ID приложения GitHub OAuth.              |
| `GITHUB_OAUTH2_SECRET`   | `string`  | —            | Секретный ключ приложения GitHub OAuth.  |
| `GOOGLE_OAUTH2_KEY`      | `string`  | —            | ID приложения Google OAuth.              |
| `GOOGLE_OAUTH2_SECRET`   | `string`  | —            | Секретный ключ приложения Google OAuth.  |

[🔝 Наверх](#установка-и-конфигурация-окружения-env)

---

## Инструкции по запуску

### Сценарий 1: Локальная разработка (SQLite, без Docker)

<details>
<summary><span style="font-size: 1.2em; font-weight: bold;">Развернуть инструкцию</span></summary>

Быстрый запуск для повседневной разработки.

1. **Создайте и активируйте виртуальное окружение:**
   ```bash
   python -m venv venv
   source venv/bin/activate      # Linux/macOS
   venv\Scripts\activate         # Windows
   ```

2. **Установите зависимости:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Создайте `.env` файл** со следующим содержимым (подставьте свои ключи):
   ```ini
   DJANGO_SECRET_KEY=your_secret_key_here
   DJANGO_DEBUG=True
   DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
   ON_RENDER=False

   DJANGO_SUPERUSER_USERNAME=admin
   DJANGO_SUPERUSER_EMAIL=admin@example.com
   DJANGO_SUPERUSER_PASSWORD=admin123

   DB_MODE=sqlite
   DB_NAME=web_db
   DB_USER=postgres
   DB_PASSWORD=postgres_password
   DB_HOST=db
   DB_PORT=5432

   USE_S3_MEDIA=False
   AWS_STORAGE_BUCKET_NAME=your-bucket-name
   AWS_ACCESS_KEY_ID=your_access_key
   AWS_SECRET_ACCESS_KEY=your_secret_key
   AWS_S3_ENDPOINT_URL=https://storage.yandexcloud.net

   RESEND_API_KEY=your-resend-api-key
   DEFAULT_FROM_EMAIL=noreply@notifications.it-lyceist.ru

   YANDEX_OAUTH2_KEY=your_yandex_key
   YANDEX_OAUTH2_SECRET=your_yandex_secret

   GITHUB_OAUTH2_KEY=your_github_key
   GITHUB_OAUTH2_SECRET=your_github_secret

   GOOGLE_OAUTH2_KEY=your_google_key
   GOOGLE_OAUTH2_SECRET=your_google_secret
   ```

4. **Выполните миграции и запустите сервер:**
   ```bash
   python web/manage.py migrate
   python web/manage.py createsuperuser
   python web/manage.py runserver
   ```
   Сайт будет доступен по адресу `http://127.0.0.1:8000/`.

</details>

[🔝 Наверх](#установка-и-конфигурация-окружения-env)

---

### Сценарий 2: Локальный запуск в Docker (PostgreSQL)

<details>
<summary><span style="font-size: 1.2em; font-weight: bold;">Развернуть инструкцию</span></summary>

Запуск в изолированной среде с готовой БД PostgreSQL и автосозданием администратора.

1. **Скопируйте конфигурацию** (используйте тот же `.env`, но установите `DB_MODE=postgres`):
   ```ini
   DB_MODE=postgres
   DB_NAME=web_db
   DB_USER=postgres
   DB_PASSWORD=postgres_password
   DB_HOST=db
   DB_PORT=5432
   ```
   Остальные переменные – по желанию.

2. **Соберите и запустите контейнеры:**
   ```bash
   docker-compose up --build
   ```

3. **Что произойдет автоматически:**
   - Поднимется PostgreSQL и дождется его готовности.
   - Автоматически выполнятся `collectstatic` и `migrate`.
   - Загрузятся фикстуры (если есть в `web/fixtures/`).
   - Создастся суперпользователь с данными из переменных окружения.

4. **Доступ к приложению:**
   - URL: `http://localhost:8000/`
   - Админка: `http://localhost:8000/admin/`
   - Логин/пароль: `admin` / `admin123` (из `.env`)

</details>

[🔝 Наверх](#установка-и-конфигурация-окружения-env)

---

### Сценарий 3: Деплой на Render (внешняя БД и Yandex S3)

<details>
<summary><span style="font-size: 1.2em; font-weight: bold;">Развернуть инструкцию</span></summary>

Развертывание на бесплатном хостинге Render с использованием удаленной базы данных и S3-бакета для медиа.

1. **Настройка сервиса на Render:**
   - Создайте **Web Service** и подключите GitHub-репозиторий.
   - Укажите **Environment** → `Docker`.

2. **Задайте Environment Variables в панели Render:**
   ```ini
   ON_RENDER=True
   DJANGO_SECRET_KEY=your_secret_key_here
   DJANGO_DEBUG=False
   DJANGO_ALLOWED_HOSTS=your-domain.onrender.com

   DB_MODE=url
   DATABASE_URL=postgres://user:password@ep-cool-site.us-east-1.aws.neon.tech/neondb

   USE_S3_MEDIA=True
   AWS_STORAGE_BUCKET_NAME=my-yandex-bucket
   AWS_ACCESS_KEY_ID=YCAJE...
   AWS_SECRET_ACCESS_KEY=YCMybh...
   AWS_S3_ENDPOINT_URL=https://storage.yandexcloud.net

   RESEND_API_KEY=your-resend-api-key
   DEFAULT_FROM_EMAIL=noreply@notifications.it-lyceist.ru

   YANDEX_OAUTH2_KEY=your_yandex_key
   YANDEX_OAUTH2_SECRET=your_yandex_secret
   GITHUB_OAUTH2_KEY=your_github_key
   GITHUB_OAUTH2_SECRET=your_github_secret
   GOOGLE_OAUTH2_KEY=your_google_key
   GOOGLE_OAUTH2_SECRET=your_google_secret
   ```

3. **Готово!**
   После деплоя Render скомпилирует Dockerfile, подключит бакет и внешнюю БД, а статика будет отдаваться через WhiteNoise.

</details>

[🔝 Наверх](#установка-и-конфигурация-окружения-env)

---

## Дополнительные замечания

- Для работы с S3 необходимы корректные права доступа к бакету.
- При использовании внешней БД убедитесь, что она доступна из сети Render.
- Для production-окружения всегда устанавливайте `DJANGO_DEBUG=False` и задавайте корректные `DJANGO_ALLOWED_HOSTS`.
- Почтовые уведомления через Resend требуют подтверждённого домена отправителя.

[🔝 Наверх](#установка-и-конфигурация-окружения-env)

---

Если возникли вопросы, обратитесь к разделу Issues в репозитории или свяжитесь с разработчиками.