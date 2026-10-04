from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Load .env file from root or working directory if present
load_dotenv(find_dotenv(usecwd=True))

from api.config import router as config_router
from api.discover import router as discover_router
from api.health import router as health_router
from api.runner import router as runner_router

app = FastAPI(title="PytestDeck Core API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(health_router)
app.include_router(config_router)
app.include_router(discover_router)
app.include_router(runner_router)

frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="static")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith(("api", "ws")):
            raise HTTPException(status_code=404)
        file_path = frontend_dist / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")
