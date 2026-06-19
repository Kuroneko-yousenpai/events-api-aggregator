# Events Aggregator

Асинхронный REST API-сервис, который служит промежуточным слоем между клиентами и внешним Events Provider API.

Сервис позволяет:
- автоматически синхронизировать события из внешнего API раз в день и хранить их локально;
- получать список событий с фильтрацией по дате и постраничной пагинацией;
- просматривать детали события и актуальный список свободных мест;
- регистрироваться на мероприятие и отменять регистрацию.

## Запуск

```bash
cp .env.example .env
docker compose up --build
```

Сервис доступен на `http://localhost:8000`.  
Документация API: `http://localhost:8000/docs`.

Для полного сброса окружения (включая данные БД):

```bash
docker compose down -v
docker compose up --build
```

## API

### Проверка доступности

```
GET /api/health
```

### Ручной запуск синхронизации

```
POST /api/sync/trigger
```

### Получение списка событий

```
GET /api/events?date_from=2026-01-01&page=1&page_size=20
```

`date_from` — фильтр по дате начала события (формат `YYYY-MM-DD`, опционально).  
`page` и `page_size` — параметры пагинации (по умолчанию `1` и `20`).

### Получение детали события

```
GET /api/events/{event_id}
```

### Получение свободных мест

```
GET /api/events/{event_id}/seats
```

Возвращает актуальный список свободных мест из внешнего API. Результат кэшируется на 30 секунд.

### Регистрация на событие

```
POST /api/tickets
```

```json
{
  "event_id": "uuid",
  "first_name": "Иван",
  "last_name": "Иванов",
  "email": "ivan@example.com",
  "seat": "A15"
}
```

Возвращает `ticket_id` созданной регистрации.

### Отмена регистрации

```
DELETE /api/tickets/{ticket_id}
```

## Запуск тестов

```bash
docker compose exec api uv run pytest tests/ -v
```

## Стек

- Python 3.12
- FastAPI
- SQLAlchemy 2 (async)
- asyncpg
- PostgreSQL 16
- Alembic
- httpx
- uv
- ruff
- Docker Compose
