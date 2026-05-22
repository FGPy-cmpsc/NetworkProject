# MIPT Prompts

Минимальный веб-чат с большой языковой моделью Google Gemini, написанный на FastAPI.

## Что внутри

- FastAPI + Jinja2 - бэкенд и рендеринг главной страницы.
- google-genai SDK в режиме Vertex AI - обращение к Gemini через Google Cloud.
- httpx-socks - отправка трафика через локальный SOCKS5-прокси для обхода геоблока Gemini в России.
- Глобальный rate limiter (один запрос в минуту со всего сайта) для защиты кредитов GCP-аккаунта от анонимного абуза.

## Требования

- Python 3.10+
- GCP-проект с включённым Vertex AI API
- Application Default Credentials (`gcloud auth application-default login`)
- Локальный SOCKS5-прокси с не-российским выходом
- nginx + сертификат Let's Encrypt для прода с HTTPS

## Запуск

    git clone git@github.com:FGPy-cmpsc/NetworkProject.git
    cd NetworkProject
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt

Создайте `.env`:

    GCP_PROJECT=your-gcp-project
    GCP_LOCATION=global
    SOCKS_PROXY_URL=socks5://127.0.0.1:1080
    GEMINI_MODEL=gemini-2.5-flash
    GLOBAL_RATE_LIMIT_SECONDS=60
    HTTP_TIMEOUT_SECONDS=60.0
    DOMAIN=example.com
    YANDEX_VERIFICATION_CODE=

Dev-запуск:

    uvicorn main:app --host 127.0.0.1 --port 9090

Prod - через systemd, который читает `.env` и запускает uvicorn. nginx проксирует на `127.0.0.1:9090`, certbot выдаёт HTTPS-сертификат для домена из `.env`.

## Структура

    .
    ├── main.py            FastAPI-приложение, роуты
    ├── config.py          Загрузка настроек из .env
    ├── gemini_client.py   Vertex AI клиент с SOCKS5-прокси
    ├── rate_limit.py      Async-безопасный глобальный rate limiter
    ├── templates/
    │   └── index.html     Главная страница с формой
    └── requirements.txt
