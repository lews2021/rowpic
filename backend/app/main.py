"""rowpic backend entrypoint."""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.routes_photos import router as photos_router
from app.api.routes_color import router as color_router
from app.api.routes_classify import router as classify_router
from app.api.routes_info import router as info_router
from app.api.routes_tools import router as tools_router
from app.core.config import settings
from app.core.logging import setup_logging

setup_logging()
log = logging.getLogger("rowpic")

app = FastAPI(
    title="rowpic",
    description="Photo viewer & analyzer (RAW + standard), composition guides, focus/face checks, color grading.",
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(info_router)
app.include_router(photos_router)
app.include_router(color_router)
app.include_router(classify_router)
app.include_router(tools_router)


@app.get("/")
def root():
    return {"name": "rowpic", "version": __version__, "docs": "/docs", "ui": "/ui"}


@app.get("/healthz")
def healthz():
    return {"ok": True}


# Mount built frontend (production) if present
FRONT_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if FRONT_DIST.is_dir():
    @app.get("/ui")
    def ui_index():
        return FileResponse(FRONT_DIST / "index.html")
    app.mount("/ui", StaticFiles(directory=str(FRONT_DIST), html=True), name="ui")
    log.info("mounted frontend at /ui from %s", FRONT_DIST)


@app.exception_handler(Exception)
def generic_handler(_, exc: Exception):
    log.exception("unhandled error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": str(exc)})


def main():
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()