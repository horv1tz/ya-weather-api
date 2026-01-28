# Yandex Weather API

FastAPI сервис для парсинга данных о погоде с сайта Yandex Погода.

## Описание

Сервис предоставляет REST API для получения актуальной информации о погоде и месячного прогноза на основе координат (широта и долгота). Данные парсятся с сайта yandex.ru/pogoda и кешируются на 15 минут для оптимизации запросов.

## Возможности

- Получение текущей погоды по координатам
- Получение месячного прогноза погоды
- Кеширование данных (TTL: 15 минут)
- Автоматическая обработка ошибок с fallback на кеш

## API Endpoints

### GET `/api/weather/total`

Получение текущей погоды для указанных координат.

**Параметры:**
- `lat` (float) - широта
- `lon` (float) - долгота

**Пример запроса:**
```bash
curl "http://localhost:8000/api/weather/total?lat=55.7558&lon=37.6173"
```

**Пример ответа:**
```json
{
  "lat": 55.7558,
  "lon": 37.6173,
  "source": "https://yandex.ru/pogoda/ru?lat=55.7558&lon=37.6173",
  "cached": false,
  "data": {
    "temperature": "+5°",
    "condition": "cloudy",
    "condition_text": "Облачно",
    "feels_like": "+3°",
    "yesterday_full": "+2°",
    "yesterday_short": null,
    "wind": "СЗ 3 м/с",
    "pressure": "758",
    "humidity": "65",
    "water_temperature": null
  }
}
```

**Коды условий погоды (condition):**
- `clear` - Ясно
- `partly-cloudy` - Малооблачно, переменная облачность
- `cloudy-and-clear` - Облачно с прояснениями
- `cloudy` - Облачно
- `overcast` - Пасмурно
- `light-rain` - Небольшой/слабый дождь
- `rain` - Дождь
- `heavy-rain` - Ливень, сильный дождь
- `thunderstorm` - Гроза
- `light-snow` - Небольшой/слабый снег
- `snow` - Снег
- `heavy-snow` - Метель, сильный снег
- `fog` - Туман
- `haze` - Мгла, дымка
- `drizzle` - Морось
- `hail` - Град
- `unknown` - Неизвестное условие

### GET `/api/weather/month`

Получение месячного прогноза погоды для указанных координат.

**Параметры:**
- `lat` (float) - широта
- `lon` (float) - долгота

**Пример запроса:**
```bash
curl "http://localhost:8000/api/weather/month?lat=55.7558&lon=37.6173"
```

**Пример ответа:**
```json
{
  "lat": 55.7558,
  "lon": 37.6173,
  "source": "https://yandex.ru/pogoda/ru/month?lat=55.7558&lon=37.6173",
  "cached": false,
  "data": [
    {
      "title": "Сегодня, 15 марта",
      "label": "15 марта",
      "day_temp": "+5",
      "night_temp": "-2",
      "feels_like": "+3°",
      "pressure": "758",
      "humidity": "65",
      "wind": "СЗ 3 м/с",
      "water_temperature": null
    }
  ]
}
```

### GET `/docs`

Интерактивная документация API (Swagger UI).

### GET `/redoc`

Альтернативная документация API (ReDoc).

## Установка и запуск

### С помощью Docker Compose (рекомендуется)

1. Клонируйте репозиторий или перейдите в директорию проекта:
```bash
cd yaweather
```

2. Запустите сервис:
```bash
docker-compose up -d
```

3. Сервис будет доступен по адресу: `http://localhost:8000`

4. Остановка сервиса:
```bash
docker-compose down
```

### С помощью Docker

1. Соберите образ:
```bash
docker build -t yaweather .
```

2. Запустите контейнер:
```bash
docker run -d -p 8000:8000 --name yaweather-api yaweather
```

### Локальная установка

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Запустите сервис:
```bash
python main.py
```

или с помощью uvicorn:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Зависимости

- Python 3.11+
- FastAPI 0.115.5
- Uvicorn 0.23.2
- Requests 2.31.0
- BeautifulSoup4 4.12.3

## Особенности

- **Кеширование**: Данные кешируются в памяти на 15 минут для снижения нагрузки на внешний источник
- **Обработка ошибок**: При ошибках парсинга или сетевых проблемах сервис пытается вернуть данные из кеша
- **User-Agent ротация**: Используется случайный User-Agent из пула для снижения вероятности блокировки

## Структура проекта

```
yaweather/
├── main.py              # Основной файл приложения
├── requirements.txt     # Зависимости Python
├── Dockerfile           # Конфигурация Docker образа
├── docker-compose.yml   # Конфигурация Docker Compose
└── README.md           # Документация
```

## Лицензия

Проект предназначен для образовательных целей. Использование данных с сайта Yandex должно соответствовать их условиям использования.
