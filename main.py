import logging

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles

import config
import db
import levels
import routes_auth
import routes_game
import routes_misc


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("mipt_prompts")

db.init_db()
levels.load_all()
log.info("loaded %d tracks", len(levels.all_tracks()))


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(routes_game.router)
app.include_router(routes_auth.router, prefix="/auth")
app.include_router(routes_misc.router)


@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt():
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /auth/\n"
        "Disallow: /level/\n"
        "Disallow: /profile\n"
        "\n"
        f"Sitemap: {config.SITE_URL}/sitemap.xml\n"
    )


@app.get("/sitemap.xml")
async def sitemap_xml():
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        "  <url>\n"
        f"    <loc>{config.SITE_URL}/</loc>\n"
        "    <changefreq>weekly</changefreq>\n"
        "    <priority>1.0</priority>\n"
        "  </url>\n"
        "  <url>\n"
        f"    <loc>{config.SITE_URL}/leaderboard</loc>\n"
        "    <changefreq>daily</changefreq>\n"
        "    <priority>0.5</priority>\n"
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
