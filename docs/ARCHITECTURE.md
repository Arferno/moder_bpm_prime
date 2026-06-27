# Архитектура проекта

## Общая схема

```
┌─────────────────────────────────────────────────────────────────┐
│                        Telegram API                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        aiogram 3.x                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Dispatcher │  │    Router    │  │   Middleware │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  Middlewares  │    │    Filters    │    │   Handlers    │
│               │    │               │    │               │
│ • Registration│    │ • IsAdmin     │    │ • Moderation  │
│ • Throttling  │    │ • IsSuperAdmin│    │ • Farming     │
│ • Blacklist   │    │ • ChatType    │    │ • Profile     │
└───────────────┘    └───────────────┘    │ • Shop        │
                                           │ • Admin       │
                                           └───────────────┘
                                                   │
                                                   ▼
                                           ┌───────────────┐
                                           │   Services    │
                                           │               │
                                           │ • Farming     │
                                           │ • Moderation  │
                                           │ • Clan        │
                                           └───────────────┘
                                                   │
                                                   ▼
                                           ┌───────────────┐
                                           │   Database    │
                                           │  (PostgreSQL) │
                                           │               │
                                           │ • SQLAlchemy  │
                                           │ • AsyncPG     │
                                           │ • Alembic     │
                                           └───────────────┘
                                                   │
                                                   ▼
                                           ┌───────────────┐
                                           │     Redis     │
                                           │   (Cache)     │
                                           │               │
                                           │ • Blacklist   │
                                           │ • Throttling  │
                                           └───────────────┘
```

## Потоки данных

### 1. Входящее сообщение (группа)
```
Message → RegistrationMiddleware (create/get user)
       → ThrottlingMiddleware (rate limit)
       → BlacklistMiddleware (check forbidden words)
          ├─ Matched → Delete message + apply action (warn/mute/ban)
          └─ Not matched → Handler (command processing)
```

### 2. Команда пользователя
```
Command → Filters (admin check, chat type)
       → Handler (business logic)
          → Service (calculations, DB operations)
             → CRUD (database queries)
                → Database
          → Response (formatted message + keyboard)
```

### 3. Периодические задачи (APScheduler)
```
Scheduler (every 1 min)
    → check_and_unmute_expired() — снимает истекшие муты
    → collect_business_income_job() — начисляет доход бизнесов
    → distribute_clan_income_job() — пополняет казны кланов
```

## Компоненты

### Middlewares (порядок важен!)
1. **RegistrationMiddleware** — авто-регистрация пользователя в БД
2. **ThrottlingMiddleware** — токен-бакет rate limiting (0.5 сек между сообщениями, burst 10)
3. **BlacklistMiddleware** — проверка каждого сообщения на запрещённые слова

### Filters
- **IsAdminFilter** — проверка по `settings.admin_ids`
- **IsSuperAdminFilter** — проверка `settings.super_admin_id`
- **ChatTypeFilter** — `group`/`supergroup` или `private`

### Handlers (по роутерам)
| Роутер | Команды | Описание |
|--------|---------|----------|
| `moderation` | ban, mute, warn, blacklist | Модерация чата |
| `daily` | daily, streak | Ежедневные бонусы |
| `work` | work, jobinfo | Работы |
| `crime` | crime, crimeinfo | Преступления |
| `business` | business, businessinfo | Бизнесы |
| `clan` | clan (create/join/leave/info/top/members/treasury) | Кланы |
| `profile` | profile, balance, top, mystats | Профиль и топы |
| `shop` | shop, buy, inventory | Магазин и инвентарь |
| `admin` | stats, broadcast, give, setlevel, reload_blacklist, userinfo, logs | Супер-админка |

### Services (бизнес-логика)
- **FarmingService** — расчёты наград, лвл-апы, формулы
- **ModerationService** — бан/мут/варн, применение действий ЧС
- **ClanService** — клановая логика, доходы, повышения

### Database
- **SQLAlchemy 2.0 async** + **asyncpg**
- **Alembic** для миграций
- **Models** — все таблицы с relationships
- **CRUD** — все запросы к БД с кэшированием ЧС в Redis

### Redis
- Кэш чёрного списка (TTL 5 мин)
- In-memory токен-бакет для троттлинга (в middleware)

## Конфигурация
- **pydantic-settings** — загрузка из `.env`
- Валидация типов, значения по умолчанию
- Алиасы для переменных окружения

## Деплой
- **Docker multi-stage build** (builder → runtime)
- **docker-compose.yml** (dev) + **docker-compose.prod.yml** (prod + watchtower)
- **systemd** сервис для автозапуска
- **GitHub Actions** → SSH → docker deploy на VPS → git pull + rebuild

## Масштабируемость
- Stateless бот — можно запускать несколько реплик
- Redis для shared кэша и троттлинга
- PostgreSQL connection pooling (Supabase/Neon)
- APScheduler — только на одной реплике (или использовать distributed lock)

## Безопасность
- Токен бота только в `.env` (не в коде)
- Админ-ID в конфиге
- Параметризованные запросы (SQLAlchemy ORM)
- Rate limiting на уровне middleware
- Проверка прав перед действиями модерации