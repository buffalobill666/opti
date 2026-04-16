"""
Основное FastAPI приложение для Web-GUI OptionsRunner.

Запускает Web-интерфейс с парольным доступом,
управлением API ключами, просмотром балансов, позиций, ордеров.
"""

import os
from pathlib import Path

from fastapi import FastAPI, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from jinja2 import Environment, FileSystemLoader

from utils.logger import logger, log_gui_access
from ui.auth import verify_password
from ui.api import (
    auth_routes,
    api_keys_routes,
    balances_routes,
    positions_routes,
    orders_routes,
    market_data_routes,
    strategies_routes,
)

# ─── Инициализация приложения ───────────────────────────────────────

app = FastAPI(
    title="OptionsRunner",
    description="Web-GUI для торговли опционами на Bybit и Deribit",
    version="1.0.0",
)

# Сессии
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("APP_SECRET_KEY", "change_me_to_random_string"),
)

# Статические файлы
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Шаблоны — ручная инициализация Jinja2 для обхода бага Starlette 1.0 + Jinja2 3.1
templates_dir = Path(__file__).parent / "templates"
jinja_env = Environment(
    loader=FileSystemLoader(str(templates_dir)),
    autoescape=True,
)


def _get_network_status() -> dict:
    """Получить текущий статус сетей — ЧИТАЕТ НАПРЯМУЮ ИЗ .env ФАЙЛА каждый раз."""
    env_vars = {}
    # Абсолютный путь к .env в корне проекта
    env_path = Path(__file__).parent.parent / ".env"

    try:
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, value = line.split("=", 1)
                        env_vars[key.strip()] = value.strip()
        else:
            logger.warning(f".env файл не найден по пути: {env_path}")
    except Exception as e:
        logger.warning(f"Ошибка чтения .env: {e}")

    # Fallback на os.getenv если файл не прочитан
    bybit_demo = env_vars.get("BYBIT_DEMO") or os.getenv("BYBIT_DEMO", "false")
    bybit_testnet = env_vars.get("BYBIT_TESTNET") or os.getenv("BYBIT_TESTNET", "false")
    deribit_testnet = env_vars.get("DERIBIT_TESTNET") or os.getenv("DERIBIT_TESTNET", "false")

    bybit_demo = bybit_demo.lower() == "true"
    bybit_testnet = bybit_testnet.lower() == "true"
    deribit_testnet = deribit_testnet.lower() == "true"

    if bybit_demo:
        bybit_network = "demo"
    elif bybit_testnet:
        bybit_network = "testnet"
    else:
        bybit_network = "mainnet"

    deribit_network = "testnet" if deribit_testnet else "mainnet"

    logger.debug(f"Сети: bybit={bybit_network}, deribit={deribit_network} (env_vars={env_vars})")

    return {
        "bybit_network": bybit_network,
        "deribit_network": deribit_network,
    }


def render(name: str, context: dict, status_code: int = 200) -> HTMLResponse:
    """Рендер HTML шаблона."""
    template = jinja_env.get_template(name)
    html = template.render(**context)
    return HTMLResponse(content=html, status_code=status_code)


def render_page(template_name: str, context: dict, status_code: int = 200) -> HTMLResponse:
    """Рендер страницы с общим layout (навбар + сети)."""
    networks = _get_network_status()
    # Добавляем сети в контекст если их нет
    for key, value in networks.items():
        context.setdefault(key, value)
    return render(template_name, context, status_code)


# ─── Middleware для логирования доступа ─────────────────────────────

@app.middleware("http")
async def log_access(request: Request, call_next):
    """Логирование доступа к Web-GUI."""
    if request.url.path.startswith("/static") or request.url.path.startswith("/api"):
        return await call_next(request)

    try:
        user = request.session.get("user", "anonymous")
    except (AssertionError, KeyError):
        user = "anonymous"

    client_ip = request.client.host if request.client else "unknown"

    log_gui_access(
        user=user,
        ip=client_ip,
        path=request.url.path,
    )

    response = await call_next(request)
    return response

# ─── Зависимость аутентификации ─────────────────────────────────────

async def require_auth(request: Request):
    """Проверка аутентификации для защищённых роутов."""
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=307, detail="Требуется аутентификация")
    return request

# ─── Страницы ───────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Главная страница — редирект на dashboard или login."""
    if not request.session.get("authenticated"):
        return RedirectResponse("/login")
    return RedirectResponse("/dashboard")


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Страница входа."""
    return render("login.html", {"request": request})


@app.post("/login")
async def login(request: Request, password: str = Form(...)):
    """Обработка входа."""
    if verify_password(password):
        request.session["authenticated"] = True
        request.session["user"] = "admin"
        logger.info("Вход выполнен успешно")
        return RedirectResponse("/dashboard", status_code=303)

    logger.warning("Неверная попытка входа")
    return render(
        "login.html",
        {"request": request, "error": "Неверный пароль"},
        status_code=401,
    )


@app.get("/logout")
async def logout(request: Request):
    """Выход."""
    request.session.clear()
    logger.info("Пользователь вышел")
    return RedirectResponse("/login")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, _=Depends(require_auth)):
    """Главная панель."""
    return render_page("dashboard.html", {
        "request": request,
        "page_title": "Панель",
        "active_page": "dashboard",
    })


@app.get("/api-keys", response_class=HTMLResponse)
async def api_keys_page(request: Request, _=Depends(require_auth)):
    """Страница управления API ключами."""
    return render_page("api_keys.html", {
        "request": request,
        "page_title": "API Ключи",
        "active_page": "api-keys",
    })


@app.get("/balances", response_class=HTMLResponse)
async def balances_page(request: Request, _=Depends(require_auth)):
    """Страница балансов."""
    return render_page("balances.html", {
        "request": request,
        "page_title": "Балансы",
        "active_page": "balances",
    })


@app.get("/positions", response_class=HTMLResponse)
async def positions_page(request: Request, _=Depends(require_auth)):
    """Страница позиций."""
    return render_page("positions.html", {
        "request": request,
        "page_title": "Позиции",
        "active_page": "positions",
    })


@app.get("/orders", response_class=HTMLResponse)
async def orders_page(request: Request, _=Depends(require_auth)):
    """Страница ордеров."""
    return render_page("orders.html", {
        "request": request,
        "page_title": "Ордера",
        "active_page": "orders",
    })


@app.get("/market-data", response_class=HTMLResponse)
async def market_data_page(request: Request, _=Depends(require_auth)):
    """Страница рыночных данных."""
    return render_page("market_data.html", {
        "request": request,
        "page_title": "Рынок",
        "active_page": "market-data",
    })


@app.get("/strategies", response_class=HTMLResponse)
async def strategies_page(request: Request, _=Depends(require_auth)):
    """Страница списка стратегий."""
    return render_page("strategies.html", {
        "request": request,
        "page_title": "Стратегии",
        "active_page": "strategies",
    })


@app.get("/strategies/new", response_class=HTMLResponse)
async def strategy_new_page(request: Request, _=Depends(require_auth)):
    """Страница создания новой стратегии."""
    return render_page("strategy_form.html", {
        "request": request,
        "page_title": "Новая стратегия",
        "active_page": "strategies",
        "mode": "create",
    })


@app.get("/strategies/{strategy_id}", response_class=HTMLResponse)
async def strategy_detail_page(request: Request, strategy_id: str, _=Depends(require_auth)):
    """Страница обзора отдельной стратегии."""
    return render_page("strategy_detail.html", {
        "request": request,
        "page_title": f"Стратегия #{strategy_id}",
        "active_page": "strategies",
        "strategy_id": strategy_id,
    })


@app.get("/strategies/{strategy_id}/edit", response_class=HTMLResponse)
async def strategy_edit_page(request: Request, strategy_id: str, _=Depends(require_auth)):
    """Страница редактирования стратегии."""
    return render_page("strategy_form.html", {
        "request": request,
        "page_title": f"Редактирование #{strategy_id}",
        "active_page": "strategies",
        "mode": "edit",
        "strategy_id": strategy_id,
    })


# ─── Подключение API роутов ─────────────────────────────────────────

app.include_router(auth_routes.router, prefix="/api/auth", tags=["auth"])
app.include_router(api_keys_routes.router, prefix="/api/keys", tags=["keys"])
app.include_router(balances_routes.router, prefix="/api/balances", tags=["balances"])
app.include_router(positions_routes.router, prefix="/api/positions", tags=["positions"])
app.include_router(orders_routes.router, prefix="/api/orders", tags=["orders"])
app.include_router(market_data_routes.router, prefix="/api/market", tags=["market"])
app.include_router(strategies_routes.router, prefix="/api/strategies", tags=["strategies"])


# ─── Обработка ошибок ───────────────────────────────────────────────

@app.exception_handler(401)
async def unauthorized_handler(request: Request, exc):
    return JSONResponse(
        status_code=401,
        content={"success": False, "error": "Требуется аутентификация"},
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": "Ресурс не найден"},
        )
    return render("404.html", {"request": request}, status_code=404)
