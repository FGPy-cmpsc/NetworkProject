import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse, PlainTextResponse, Response
from fastapi.templating import Jinja2Templates

import config
import rate_limit
from gemini_client import client

logger = logging.getLogger("mipt_prompts")

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
templates = Jinja2Templates(directory="templates")


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    message = (data.get("message") or "").strip()
    if not message:
        return JSONResponse({"error": "Пустое сообщение."}, status_code=400)

    allowed, wait = await rate_limit.acquire(config.GLOBAL_RATE_LIMIT_SECONDS)
    if not allowed:
        return JSONResponse(
            {"error": f"Лимит запросов превышен. Попробуйте через {wait} сек."},
            status_code=429,
        )

    try:
        resp = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=message,
        )
        return {"reply": resp.text}
    except Exception:
        logger.exception("gemini call failed")
        return JSONResponse({"error": "Внутренняя ошибка."}, status_code=500)


@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt():
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /chat\n"
        "\n"
        f"Sitemap: https://{config.DOMAIN}/sitemap.xml\n"
    )


@app.get("/sitemap.xml")
async def sitemap_xml():
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        "  <url>\n"
        f"    <loc>https://{config.DOMAIN}/</loc>\n"
        "    <changefreq>weekly</changefreq>\n"
        "    <priority>1.0</priority>\n"
        "  </url>\n"
        "</urlset>\n"
    )
    return Response(content=body, media_type="application/xml")


if config.YANDEX_VERIFICATION_CODE:
    _code = config.YANDEX_VERIFICATION_CODE
    _yandex_html = (
        "<html>\n"
        '    <head><meta http-equiv="Content-Type" content="text/html; charset=UTF-8"></head>\n'
        f"    <body>Verification: {_code}</body>\n"
        "</html>"
    )

    @app.get(f"/yandex_{_code}.html", response_class=HTMLResponse)
    async def yandex_verification():
        return _yandex_html
