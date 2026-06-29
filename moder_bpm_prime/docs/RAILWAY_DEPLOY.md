# Деплой на Railway.app — полный гайд (бесплатно, без карты)

## 🎯 Что получится
- Бот на Railway (хостинг)
- PostgreSQL на Railway (база)
- Авто-деплой при `git push`
- **$0/месяц** (входит в $5 бесплатных кредитов)

---

## 1. Подготовка репозитория

### Залей код на GitHub
```bash
cd D:\moder_bpm_prime
git init
git add .
git commit -m "Initial commit: Moder_for_BPM_PRIME"
# Создай репозиторий на github.com (приватный)
git remote add origin https://github.com/<ТВОЙ_ЮЗЕРНЕЙМ>/moder_bpm_prime.git
git push -u origin main
```

---

## 2. Создание проекта на Railway

1. Зайди на **railway.app** → **Login with GitHub**
2. **New Project** → **Empty Project**
3. Название: `moder-bpm-prime`

---

## 3. Добавление PostgreSQL

1. В проекте нажми **New** → **Database** → **Add PostgreSQL**
2. Жди ~1 минуту — база создастся
3. Нажми на сервис **PostgreSQL** → вкладка **Connect**
4. Скопируй **DATABASE_URL** (вида `postgresql://...`)
   - **Важно**: он уже в формате для asyncpg, ничего менять не нужно

---

## 4. Добавление бота (Web Service)

1. **New** → **GitHub Repo** → выбери `moder_bpm_prime`
2. Railway сам определит `Dockerfile` и соберёт образ
3. Жди сборку (2-3 минуты)

---

## 5. Переменные окружения

Зайди в сервис бота → **Variables** → **Add Variable**:

| Name | Value |
|------|-------|
| `BOT_TOKEN` | `8827733006:AAEru_XDRmizJ5x0IZC0ayHEIAqD7eEj98E` |
| `ADMIN_IDS` | `5459865698,6766857089,7079908197` |
| `SUPER_ADMIN_ID` | `6766857089` |
| `LOG_LEVEL` | `INFO` |
| `DAILY_BASE_REWARD` | `100` |
| `DAILY_STREAK_BONUS` | `50` |
| `MAX_STREAK_DAYS` | `30` |

**`DATABASE_URL` добавлять НЕ НАДО** — Railway сам подставит его из PostgreSQL сервиса (reference).

---

## 6. Настройка автодеплоя

Уже работает! При каждом `git push origin main`:
1. Railway видит изменения
2. Собирает новый образ
3. Перезапускает контейнер с нулевым даунтаймом

---

## 7. Миграции и сиды (один раз)

После первого успешного деплоя:

### Через Railway Shell:
1. В сервисе бота → вкладка **Shell**
2. Выполни:
```bash
alembic upgrade head
python scripts/init_db.py
```

### Или локально (подключившись к удалённой БД):
```bash
# Установи Railway CLI
npm i -g @railway/cli
railway login
railway link <project-id>
railway run alembic upgrade head
railway run python scripts/init_db.py
```

---

## 8. Добавление бота в группу

1. Открой группу → **Добавить участников** → найди бота по @username
2. **Дай права админа** (3 галочки):
   - ✅ **Удаление сообщений**
   - ✅ **Блокировка пользователей**
   - ✅ **Приглашение пользователей**
3. Напиши в группе `/start` — бот ответит и зарегистрирует чат

---

## 9. Проверка

### Логи:
- В сервисе бота → **Logs** — смотри вывод в реальном времени

### Команды для теста в группе:
```
/start           # Регистрация
/profile         # Профиль
/daily           # Ежедневка
/work            # Работа
/blacklist add мат warn  # Тест ЧС (админом)
```

---

## 10. Полезные команды Railway CLI

```bash
# Установка
npm i -g @railway/cli

# Логин
railway login

# Связать проект
railway link

# Запустить команду в контейнере бота
railway run alembic upgrade head
railway run python scripts/init_db.py

# Посмотреть логи
railway logs

# Открыть shell в контейнере
railway shell

# Переменные окружения
railway variables
```

---

## 💰 Лимиты бесплатного тарифа

| Ресурс | Лимит |
|--------|-------|
| Кредиты | $5/мес |
| RAM | 512 MB (до 8 GB с кредитами) |
| CPU | Shared |
| Диск | 1 GB |
| PostgreSQL | Включено в кредиты |
| Запросы | Неограничено |

**Типичный расход**: бот + PostgreSQL ≈ **$1-2/мес** — входит в $5 бесплатно.

---

## ⚠️ Частые проблемы

### Бот не отвечает
- Проверь **Logs** — есть ошибки?
- Проверь права админа в группе (3 галочки)
- Убедись, что `BOT_TOKEN` правильный

### Ошибка БД
- `DATABASE_URL` должен подставиться автоматически
- Проверь в Variables: `DATABASE_URL` = `${{Postgres.DATABASE_URL}}` (reference)

### Миграции не применяются
```bash
railway run alembic upgrade head
```

### Сборка падает
- Проверь `Dockerfile` — Railway использует его
- Убедись, что `pyproject.toml` корректный

---

## 🔄 Обновление бота

```bash
git add .
git commit -m "Фича: ..."
git push origin main
# Railway сам соберёт и задеплоит
```

---

## 🗑 Удаление (если нужно)

Settings → **Delete Project** — всё удалится, денег не спишут.

---

## 📞 Поддержка

- Railway Docs: https://docs.railway.app
- Discord: https://discord.gg/railway
- Логи бота: в Railway UI → сервис бота → Logs