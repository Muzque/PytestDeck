import sys
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

_SRC_DIR = Path(__file__).resolve().parent
for _sub in (_SRC_DIR, _SRC_DIR / "test_deck"):
    _sub_str = str(_sub)
    if _sub_str not in sys.path:
        sys.path.insert(0, _sub_str)

# Load .env file from root or working directory if present
load_dotenv(find_dotenv(usecwd=True))

from api_deck.api.api_routes import router as api_deck_router
from test_deck.api.config import router as config_router
from test_deck.api.discover import router as discover_router
from test_deck.api.health import router as health_router
from test_deck.api.history import router as history_router
from test_deck.api.history import run_options_router
from test_deck.api.runner import router as runner_router

app = FastAPI(title="PytestDeck Core API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Test Deck & API Deck Routers
app.include_router(health_router)
app.include_router(config_router)
app.include_router(discover_router)
app.include_router(runner_router)
app.include_router(history_router)
app.include_router(run_options_router)
app.include_router(api_deck_router)

frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if frontend_dist.exists():
    app.mount(
        "/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="static"
    )

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith(("api", "ws")):
            raise HTTPException(status_code=404)
        resolved_dist = frontend_dist.resolve()
        try:
            file_path = (resolved_dist / full_path).resolve()
            is_within = file_path.is_relative_to(resolved_dist)
        except (ValueError, OSError):
            is_within = False
            file_path = resolved_dist / "index.html"
        if not is_within:
            raise HTTPException(status_code=404)
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(resolved_dist / "index.html")
