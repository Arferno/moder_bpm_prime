# 🚀 Полное руководство по деплою на Railway (2026)

## 📋 Содержание
1. [Подготовка](#подготовка)
2. [Создание проекта на Railway](#создание-проекта-на-railway)
3. [Настройка PostgreSQL](#настройка-postgresql)
4. [Деплой бота](#деплой-бота)
5. [Переменные окружения](#переменные-окружения)
6. [Миграции базы данных](#миграции-базы-данных)
7. [Проверка работы](#проверка-работы)
8. [Решение проблем](#решение-проблем)
9. [Обновление бота](#обновление-бота)

---

## 🎯 Подготовка

### 1. GitHub репозиторий
```bash
# Локально
cd D:\moder_bpm_prime
git init
git add .
git commit -m "Initial commit"
# Создайте репозиторий на GitHub (Private)
git remote add origin https://github.com/ВАШ_ЛОГИН/moder_bpm_prime.git
git push -u origin main
```

### 2. Токен бота
1. Напишите [@BotFather](https://t.me/BotFather)
2. `/newbot` → имя: `BPM PRIME Moderator` → username: `moder_bpm_primebot`
3. Скопируйте **BOT_TOKEN** (вида `123456:ABC-DEF...`)

### 3. Ваш Telegram ID
1. Напишите [@userinfobot](https://t.me/userinfobot)
2. Скопируйте ваш ID (число, например `5459865698`)

---

## 🚂 Создание проекта на Railway

### 1. Регистрация
1. Зайдите на [railway.app](https://railway.app)
2. **Login with GitHub** (авторизация через GitHub)
3. Никаких карт не нужно — бесплатный тариф $5/мес кредитов

### 2. Новый проект
1. **New Project** → **Empty Project**
2. Название: `moder-bpm-prime`
3. Выберите регион ближе к вам (например, `US East` или `Europe West`)

---

## 🐘 Настройка PostgreSQL

### 1. Добавление базы
1. В проекте: **New** → **Database** → **Add PostgreSQL**
2. Ждите ~1 минуту пока создастся
3. Нажмите на сервис **PostgreSQL** → вкладка **Connect**

### 2. Получение Private URL (ВАЖНО!)
Используйте **Internal/Private Network** URL, а не Public:
```
postgresql+asyncpg://postgres:ПАРОЛЬ@postgres.railway.internal:5432/railway
```
> ❌ НЕ используйте `reseau.proxy.rlwy.net` — это публичный URL, он медленный и может не работать изнутри Railway

### 3. Сохраните пароль
В строке подключения пароль уже встроен — просто скопируйте полную строку.

---

## 🤖 Деплой бота

### 1. Добавление сервиса
1. В проекте: **New** → **GitHub Repo**
2. Выберите репозиторий `moder_bpm_prime`
3. Railway сам определит `Dockerfile` и соберёт образ

### 2. Настройка сборки
Railway автоматически использует `Dockerfile`. Убедитесь, что в репозитории есть:
- `Dockerfile`
- `pyproject.toml` (или `requirements.txt`)
- `bot/main.py` — точка входа

---

## ⚙️ Переменные окружения

Зайдите в сервис **бота** (не базы!) → вкладка **Variables** → **Add Variable**:

| Name | Value | Описание |
|------|-------|----------|
| `BOT_TOKEN` | `8827733006:AAEru_XDRmizJ5x0IZC0ayHEIAqD7eEj98E` | Токен от @BotFather |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:ПАРОЛЬ@postgres.railway.internal:5432/railway` | **Private URL базы + asyncpg** |
| `ADMIN_IDS` | `5459865698,6766857089,7079908197` | Ваши Telegram ID через запятую |
| `SUPER_ADMIN_ID` | `6766857089` | Главный админ (первый ID) |
| `LOG_LEVEL` | `WARNING` | Уровень логов (INFO/DEBUG/WARNING) |

> ⚠️ **DATABASE_URL должен быть с `postgresql+asyncpg://`** — это критично для asyncpg!

---

## 🗄️ Миграции базы данных

После первого деплоя (когда бот запустится, но может упасть с ошибкой BigInteger):

### Через Railway Shell (рекомендуется):
1. В сервисе бота → вкладка **Shell**
2. Выполните по очереди:

```bash
# Создание миграции
python -m alembic revision --autogenerate -m "BigInteger for User.id and FKs"

# Применение миграции
python -m alembic upgrade head
```

### Если нужно вручную (через CLI):
```bash
# Локально (нужен railway CLI)
npm i -g @railway/cli
railway login
railway link
railway run python -m alembic revision --autogenerate -m "BigInteger for User.id and FKs"
railway run python -m alembic upgrade head
```

> После миграции бот перезапустится автоматически.

---

## ✅ Проверка работы

### 1. Логи успешного запуска
В логах бота (вкладка **Logs**) должно быть:
```
=== BOT STARTING ===
=== CONFIG LOADED: 8827733006... ===
=== ENGINE CREATED: postgresql+asyncpg://postgres:... ===
=== INIT_DB: Database initialized successfully ===
=== BOT CREATED ===
=== WEBHOOK DELETED ===
=== SCHEDULER STARTED ===
=== BOT STARTED: @moder_bpm_primebot (8827733006) ===
=== STARTING POLLING ===
```

### 2. Тест в личке
1. Найдите бота по `@moder_bpm_primebot`
2. Напишите `/start` — должен ответить с клавиатурой
3. Нажмите кнопки: **Профиль**, **Баланс**, **Ежедневка** — должны работать

### 3. Тест в группе
1. Добавьте бота в группу
2. Дайте права админа (3 галочки):
   - ✅ Удаление сообщений
   - ✅ Блокировка пользователей
   - ✅ Приглашение пользователей
3. Напишите `/start` в группе — бот должен ответить

---

## 🔧 Решение проблем

### ❌ TelegramConflictError
```
Failed to fetch updates - TelegramConflictError: terminated by other getUpdates request
```
**Причина:** Запущено 2 экземпляра бота.
**Решение:**
- Railway Settings → **Replicas = 1**
- Подождите 30-60 сек после деплоя
- Остановите локальный запуск (`docker compose down`)

### ❌ BigInteger Error
```
OverflowError: value out of int32 range (6766857089)
```
**Причина:** Telegram ID > 2^31, а в БД был `Integer`.
**Решение:** Запустите миграции (см. выше).

### ❌ ModuleNotFoundError: psycopg2
```
ModuleNotFoundError: No module named 'psycopg2'
```
**Причина:** SQLAlchemy пытается использовать psycopg2 вместо asyncpg.
**Решение:** DATABASE_URL должен начинаться с `postgresql+asyncpg://`

### ❌ "Starting Container" и тишина
**Причина:** Процесс падает до логирования.
**Решение:** Проверьте Start Command в Settings:
```
python -m bot.main
```

### ❌ Кнопки не работают
**Причина:** Нет хендлеров для текста кнопок.
**Решение:** Добавлен `text_commands.py` — перезадеплойте.

### ❌ Бот не отвечает в группе
**Причина:** Нет прав админа или бот не добавлен.
**Решение:** Проверьте 3 галочки админа + бот добавлен по @username.

---

## 🔄 Обновление бота

### Автоматически (GitHub → Railway)
```bash
# Локально
git add .
git commit -m "Описание изменений"
git push origin main
```
Railway сам соберёт и задеплоит за ~1-2 минуты.

### Принудительный деплой
В Railway: **Deployments** → **Redeploy** (последний коммит)

---

## 💰 Лимиты и стоимость

| Ресурс | Free Tier |
|--------|-----------|
| Кредиты | $5/мес |
| RAM | 512 MB (до 8 GB за кредиты) |
| CPU | Shared |
| Диск | 1 GB |
| PostgreSQL | Включено в кредиты |
| Запросы | Неограничено |

**Типичный расход:** бот + PostgreSQL ≈ **$1-2/мес** — входит в $5 бесплатно.

---

## 📞 Полезные команды Railway CLI

```bash
# Установка
npm i -g @railway/cli

# Логин
railway login

# Связать проект
railway link

# Запуск команд в контейнере
railway run python -m alembic upgrade head
railway run python scripts/init_db.py

# Логи
railway logs

# Shell в контейнере
railway shell

# Переменные
railway variables
```

---

## 📁 Структура проекта (для понимания)

```
moder_bpm_prime/
├── bot/
│   ├── main.py              # Точка входа
│   ├── config.py            # Настройки (pydantic)
│   ├── database/
│   │   ├── models.py        # SQLAlchemy модели (BigInteger!)
│   │   ├── connection.py    # Async engine + session
│   │   └── crud.py          # Запросы к БД
│   ├── handlers/
│   │   ├── text_commands.py # Хендлеры кнопок Reply keyboard
│   │   ├── farming/         # Daily, Work, Crime, Business, Clan
│   │   ├── moderation.py    # Ban, Mute, Warn, Blacklist
│   │   ├── profile.py       # Profile, Balance, Top
│   │   ├── shop.py          # Shop, Inventory
│   │   └── admin.py         # Admin commands
│   ├── middlewares/
│   │   ├── database.py      # Сессия БД
│   │   ├── registration.py  # Авто-регистрация юзеров
│   │   ├── blacklist.py     # Проверка ЧС
│   │   └── throttle.py      # Антифлуд
│   └── ...
├── alembic/                 # Миграции
├── Dockerfile               # Multi-stage build
├── pyproject.toml           # Зависимости
└── railway.toml             # (опционально) конфиг Railway
```

---

## 🎯 Чек-лист перед запуском

- [ ] Репозиторий на GitHub (Private)
- [ ] Railway проект создан
- [ ] PostgreSQL добавлен (Private URL)
- [ ] Сервис бота подключен к GitHub
- [ ] Variables заполнены (BOT_TOKEN, DATABASE_URL с asyncpg, ADMIN_IDS, SUPER_ADMIN_ID)
- [ ] Деплой прошёл успешно
- [ ] Миграции применены (`alembic upgrade head`)
- [ ] Бот добавлен в группу + права админа (3 галочки)
- [ ] `/start` в личке работает → кнопки работают
- [ ] `/start` в группе работает

---

## 📚 Полезные ссылки

- [Railway Docs](https://docs.railway.app)
- [Railway Discord](https://discord.gg/railway)
- [aiogram 3.x Docs](https://docs.aiogram.dev)
- [SQLAlchemy 2.0 Docs](https://docs.sqlalchemy.org)
- [asyncpg Docs](https://magicstack.github.io/asyncpg)

---

**Удачи с деплоем! 🚀** При ошибках — скидывайте логи из Railway (последние 50 строк).