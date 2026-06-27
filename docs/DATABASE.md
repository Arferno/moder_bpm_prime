# Схема базы данных

## Таблицы

### users — Пользователи
| Поле | Тип | Описание |
|------|-----|----------|
| id | SERIAL PK | Внутренний ID |
| tg_id | BIGINT UNIQUE | Telegram ID |
| username | VARCHAR(64) | @username |
| full_name | VARCHAR(128) | Имя в TG |
| balance | INT | Деньги ($) |
| exp | INT | Опыт (XP) |
| level | INT | Уровень |
| job_id | INT FK → jobs.id | Текущая работа |
| clan_id | INT FK → clans.id | Клан |
| last_daily | TIMESTAMP | Последняя ежедневка |
| last_work | TIMESTAMP | Последняя работа |
| last_crime | TIMESTAMP | Последнее преступление |
| last_business_collect | TIMESTAMP | Последний сбор бизнеса |
| warns | INT | Количество варнов |
| is_banned | BOOL | Забанен |
| is_muted | BOOL | В муте |
| mute_until | TIMESTAMP | До когда мут |
| jail_until | TIMESTAMP | До когда тюрьма |
| created_at | TIMESTAMP | Регистрация |
| updated_at | TIMESTAMP | Обновление |

### blacklist_words — Чёрный список
| Поле | Тип | Описание |
|------|-----|----------|
| id | SERIAL PK | |
| word | VARCHAR(256) UNIQUE | Исходное слово |
| normalized_word | VARCHAR(256) | Нормализованное (для поиска) |
| regex_pattern | VARCHAR(512) | Опциональный regex |
| action | ENUM | delete/warn/mute/ban |
| duration_sec | INT | Длительность (для mute/ban) |
| is_active | BOOL | Активно |
| created_by | BIGINT | Кто добавил |
| created_at | TIMESTAMP | |

### moderation_logs — Логи модерации
| Поле | Тип | Описание |
|------|-----|----------|
| id | SERIAL PK | |
| user_id | INT FK → users.id | Нарушитель |
| admin_id | INT FK → users.id | Админ (NULL = система) |
| action | ENUM | ban/unban/mute/unmute/warn/unwarn/blacklist_trigger |
| reason | TEXT | Причина |
| duration_sec | INT | Длительность |
| created_at | TIMESTAMP | |

### jobs — Работы
| Поле | Тип | Описание |
|------|-----|----------|
| id | SERIAL PK | |
| name | VARCHAR(64) UNIQUE | Название |
| min_level | INT | Мин. уровень |
| base_pay | INT | Базовая зарплата |
| exp_reward | INT | Опыт |
| cooldown_sec | INT | Кулдаун (сек) |
| description | TEXT | Описание |

### crimes — Преступления
| Поле | Тип | Описание |
|------|-----|----------|
| id | SERIAL PK | |
| name | VARCHAR(64) UNIQUE | Название |
| min_level | INT | Мин. уровень |
| min_money | INT | Мин. награда |
| max_money | INT | Макс. награда |
| success_rate | FLOAT | Шанс успеха (0.0-1.0) |
| jail_time_min | INT | Мин. тюрьма (сек) |
| jail_time_max | INT | Макс. тюрьма (сек) |
| exp_reward | INT | Опыт за успех |
| cooldown_sec | INT | Кулдаун (сек) |
| description | TEXT | Описание |

### businesses — Бизнесы
| Поле | Тип | Описание |
|------|-----|----------|
| id | SERIAL PK | |
| name | VARCHAR(64) UNIQUE | Название |
| price | INT | Цена покупки |
| income_per_hour | INT | Доход в час |
| min_level | INT | Мин. уровень |
| max_owned | INT | Макс. на руки |
| description | TEXT | Описание |

### user_businesses — Бизнесы пользователей
| Поле | Тип | Описание |
|------|-----|----------|
| id | SERIAL PK | |
| user_id | INT FK → users.id | Владелец |
| business_id | INT FK → businesses.id | Бизнес |
| level | INT | Уровень бизнеса |
| bought_at | TIMESTAMP | Куплен |
| last_collected | TIMESTAMP | Последний сбор |

### clans — Кланы
| Поле | Тип | Описание |
|------|-----|----------|
| id | SERIAL PK | |
| name | VARCHAR(64) UNIQUE | Название |
| tag | VARCHAR(16) UNIQUE | Тег (например: BPM) |
| owner_id | INT FK → users.id | Владелец |
| level | INT | Уровень клана |
| exp | INT | Опыт клана |
| balance | INT | Казна ($) |
| created_at | TIMESTAMP | Создан |

### clan_members — Участники кланов
| Поле | Тип | Описание |
|------|-----|----------|
| id | SERIAL PK | |
| clan_id | INT FK → clans.id | Клан |
| user_id | INT FK → users.id | Участник |
| role | ENUM | member/officer/owner |
| joined_at | TIMESTAMP | Вступил |

### items — Предметы магазина
| Поле | Тип | Описание |
|------|-----|----------|
| id | SERIAL PK | |
| name | VARCHAR(64) UNIQUE | Название |
| type | ENUM | boost/protection/consumable/clan/special |
| price | INT | Цена |
| effect_json | JSONB | Эффект (см. ниже) |
| description | TEXT | Описание |
| is_active | BOOL | В продаже |

### user_items — Инвентарь
| Поле | Тип | Описание |
|------|-----|----------|
| id | SERIAL PK | |
| user_id | INT FK → users.id | Владелец |
| item_id | INT FK → items.id | Предмет |
| quantity | INT | Количество |
| acquired_at | TIMESTAMP | Получен |

## Эффекты предметов (effect_json)

```json
// Бусты
{"money": 1000}
{"exp": 500}
{"work_multiplier": 2, "duration_hours": 24}

// Защита
{"unmute": true}
{"blacklist_immunity_hours": 24}
{"unban": true}

// Расходники
{"unwarn": 1}
{"unjail": true}
{"lottery": true}

// Клановые
{"clan_exp": 1000}
{"clan_money": 50000}

// Спец
{"premium_days": 30}
{"rename": true}
```

## Индексы
- `users.tg_id` (UNIQUE) — быстрый поиск по TG ID
- `blacklist_words.normalized_word` + `is_active` — быстрая проверка ЧС
- `moderation_logs.user_id` + `created_at` — логи пользователя
- `clans.tag` (UNIQUE) — поиск клана по тегу

## Миграции
```bash
# Создать миграцию
alembic revision --autogenerate -m "описание"

# Применить
alembic upgrade head

# Откатить
alembic downgrade -1
```