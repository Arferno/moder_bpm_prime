# Деплой на Oracle Cloud Free Tier

Полное руководство по бесплатному хостингу бота на Oracle Cloud (ARM, 4 OCPU, 24 GB RAM).

## 📋 Подготовка

### 1. Аккаунт Oracle Cloud
1. Зарегистрируйся на https://cloud.oracle.com
2. Нужна банковская карта для верификации (списют $1 и вернут)
3. Выбери регион ближе к тебе (лучше пинг)

### 2. Создание VM (Compute Instance)
1. **Compute → Instances → Create Instance**
2. Название: `moder-bpm-prime`
3. **Image**: Ubuntu 22.04 (Canonical)
4. **Shape**: `VM.Standard.A1.Flex` (ARM Ampere)
   - OCPU: **4** (максимум бесплатно)
   - Memory: **24 GB** (максимум бесплатно)
5. **Networking**: Новая VCN с публичным IP
6. **SSH Keys**: Загрузи свой публичный ключ (`~/.ssh/id_ed25519.pub`)
7. **Boot Volume**: 200 GB (бесплатно до 200 GB)
8. **Create**

### 3. Настройка Security List (Firewall)
В VCN → Security Lists → Default Security List → Add Ingress Rules:
| Type | Port | Source | Description |
|------|------|--------|-------------|
| SSH | 22 | 0.0.0.0/0 | SSH доступ |
| TCP | 6379 | 10.0.0.0/16 | Redis (только внутри VCN) |

> **Важно**: Не открывай порт 6379 для 0.0.0.0/0! Redis только для внутренней сети.

## 🐳 Установка Docker на VPS

```bash
# Подключись к VPS
ssh ubuntu@<VPS_IP>

# Обновление и установка Docker
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose git

# Добавь пользователя в группу docker
sudo usermod -aG docker ubuntu
newgrp docker  # или перезайди по SSH

# Проверка
docker --version
docker compose version
```

## 🗄 База данных: Supabase (бесплатно)

1. Зайди на https://supabase.com → New Project
2. Название: `moder-bpm-prime`
3. Пароль БД: **сгенерируй сложный** (сохрани!)
4. Регион: ближе к Oracle VPS
5. Жди создания (~2 мин)

### Connection String
Settings → Connection pooling → Transaction mode → URI:
```
postgresql+asyncpg://postgres:<PASSWORD>@db.<PROJECT>.supabase.co:5432/postgres
```

## 🤖 Создание бота
1. Напиши @BotFather → `/newbot`
2. Имя: `BPM PRIME Moderator`
3. Username: `bpm_prime_moder_bot` (любой свободный)
4. Скопируй **BOT_TOKEN**

## 📥 Деплой бота

### 1. На VPS — клонирование репозитория
```bash
cd /opt
sudo git clone https://github.com/<your-username>/moder_bpm_prime.git
sudo chown -R ubuntu:ubuntu moder_bpm_prime
cd moder_bpm_prime
```

### 2. Настройка .env
```bash
cp .env.example .env
nano .env
```

Заполни:
```env
BOT_TOKEN=8827733006:AAEru_XDRmizJ5x0IZC0ayHEIAqD7eEj98E
DATABASE_URL=postgresql+asyncpg://postgres:PASSWORD@db.xxx.supabase.co:5432/postgres
ADMIN_IDS=5459865698,6766857089,7079908197
SUPER_ADMIN_ID=6766857089
LOG_LEVEL=INFO
```

### 3. Запуск
```bash
# Сборка и запуск
docker compose -f docker-compose.prod.yml up -d --build

# Миграции БД
docker compose -f docker-compose.prod.yml exec bot alembic upgrade head

# Сид данных (работы, преступления, бизнесы, предметы, ЧС)
docker compose -f docker-compose.prod.yml exec bot python scripts/init_db.py

# Проверка логов
docker compose -f docker-compose.prod.yml logs -f bot
```

### 4. Добавь бота в группу
1. Открой группу → Добавить участников → найди бота по юзернейму
2. **Дай права администратора**:
   - ✅ Удаление сообщений
   - ✅ Блокировка пользователей
   - ✅ Приглашение пользователей (для разбана)
   - ✅ Закрепление сообщений (опционально)

## 🔧 Systemd сервис (автозапуск после ребута)

```bash
sudo tee /etc/systemd/system/moder-bpm-prime.service > /dev/null <<'EOF'
[Unit]
Description=Moder_for_BPM_PRIME Bot
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/moder_bpm_prime
ExecStart=/usr/bin/docker compose -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose.prod.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable moder-bpm-prime
sudo systemctl start moder-bpm-prime
```

## 🗄 Бэкап базы данных

### Настройка автоматического бэкапа (cron)
```bash
# На VPS
crontab -e
```

Добавь:
```cron
# Ежедневно в 3:00
0 3 * * * /opt/moder_bpm_prime/scripts/backup_db.sh >> /opt/backups/backup.log 2>&1
```

### Ручной бэкап
```bash
/opt/moder_bpm_prime/scripts/backup_db.sh
```

### Восстановление
```bash
gunzip -c /opt/backups/moder_bpm_prime_20260627_030000.sql.gz | docker exec -i moder_bpm_prime-bot-1 psql $DATABASE_URL
```

## 📊 Мониторинг и логи

```bash
# Логи бота
docker compose -f docker-compose.prod.yml logs -f bot

# Статус контейнеров
docker compose -f docker-compose.prod.yml ps

# Ресурсы
docker stats

# Systemd логи
journalctl -u moder-bpm-prime -f
```

## 🔄 Обновление бота

### Автоматически (Watchtower — уже в docker-compose.prod.yml)
Watchtower проверяет обновления образа каждые 5 минут и пересоздаёт контейнер.

### Вручную
```bash
cd /opt/moder_bpm_prime
git pull origin main
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d --build
docker system prune -f
```

### Через GitHub Actions
Добавь секреты в репозиторий:
- `VPS_HOST` — IP адрес VPS
- `VPS_USER` — `ubuntu`
- `VPS_SSH_KEY` — приватный SSH ключ (без пароля)

Push в `main` → автоматический деплой.

## ⚠️ Частые проблемы

### Бот не отвечает в группе
- Проверь права админа (удалить сообщения, блокировать)
- Проверь логи: `docker compose -f docker-compose.prod.yml logs bot`

### Ошибка подключения к БД
- Проверь `DATABASE_URL` в `.env`
- Убедись, что Supabase не на паузе (free tier засыпает через неделю неактивности)
- Проверь Security List в Oracle VCN (порт 5432 не нужен, Supabase доступен по интернету)

### Миграции не применяются
```bash
docker compose -f docker-compose.prod.yml exec bot alembic upgrade head
```

## 💰 Стоимость
**$0/месяц** на Oracle Cloud Free Tier:
- 4 ARM OCPU (Ampere)
- 24 GB RAM
- 200 GB Block Volume
- 10 TB исходящего трафика

Supabase Free Tier:
- 500 MB БД
- 1 GB файловое хранилище
- 2 млн запросов в месяц

## 🆘 Поддержка
При проблемах проверь:
1. `docker compose -f docker-compose.prod.yml logs bot`
2. `journalctl -u moder-bpm-prime -f`
3. Ресурсы: `htop`, `df -h`, `docker stats`