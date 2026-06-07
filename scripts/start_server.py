"""Server-only launcher: starts FastAPI backend (for remote / Docker use).

The frontend should be built (`npm run build` in /frontend) and mounted as
static files. For dev, use scripts/start_web.py instead.
"""
import os
import sys
import uvicorn

if __name__ == "__main__":
    host = os.environ.get("ROWPIC_HOST", "0.0.0.0")
    port = int(os.environ.get("ROWPIC_PORT", "8765"))
    reload = os.environ.get("ROWPIC_RELOAD", "0") == "1"
    print(f"[rowpic] server mode — http://{host}:{port}")
    uvicorn.run("app.main:app", host=host, port=port, reload=reload, log_level="info")
