"""One-click desktop launcher.

Starts the FastAPI backend and opens a native window with the UI.

Resolution order for the UI:
  1. built frontend dist (../frontend/dist/index.html) mounted by FastAPI at /ui
  2. dev server at http://127.0.0.1:5173 if it's already running
  3. system browser as a last resort

The window itself is a pywebview (Edge WebView2 / WebKit / GTK) shell.
"""
import os
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
FRONTEND_DIST = ROOT / "frontend" / "dist"

HOST = "127.0.0.1"
PORT = 8765
DEV_PORT = 5173


def wait_port(host: str, port: int, timeout: float = 25.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def start_backend() -> subprocess.Popen:
    env = os.environ.copy()
    env.setdefault("ROWPIC_HOST", HOST)
    env.setdefault("ROWPIC_PORT", str(PORT))
    log_path = ROOT / "logs" / "backend_desktop.log"
    log_path.parent.mkdir(exist_ok=True)
    log_fh = open(log_path, "ab", buffering=0)
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", HOST, "--port", str(PORT), "--log-level", "info"],
        cwd=str(BACKEND),
        env=env,
        stdout=log_fh,
        stderr=log_fh,
    )


def pick_ui_url() -> str:
    """Decide which URL to load in the native window."""
    backend_ui = f"http://{HOST}:{PORT}/ui"
    dev_ui = f"http://{HOST}:{DEV_PORT}"
    if FRONTEND_DIST.is_dir() and (FRONTEND_DIST / "index.html").is_file():
        return backend_ui
    if wait_port(HOST, DEV_PORT, timeout=0.3):
        return dev_ui
    return f"http://{HOST}:{PORT}/"


def open_window(url: str) -> None:
    try:
        import webview  # pywebview
    except ImportError:
        print("[rowpic] pywebview not installed, opening system browser")
        print("[rowpic]   install: pip install pywebview")
        webbrowser.open(url)
        return
    webview.create_window(
        title="rowpic",
        url=url,
        width=1480,
        height=920,
        resizable=True,
        background_color="#0e1014",
    )
    webview.start()


def main() -> int:
    print(f"[rowpic] starting backend on http://{HOST}:{PORT}")
    backend = start_backend()
    try:
        if not wait_port(HOST, PORT, timeout=25.0):
            print("[rowpic] backend failed to start within 25s", file=sys.stderr)
            return 1
        url = pick_ui_url()
        print(f"[rowpic] opening window: {url}")
        open_window(url)
        backend.wait()
    except KeyboardInterrupt:
        print("\n[rowpic] shutting down...")
    finally:
        if backend.poll() is None:
            backend.terminate()
            try:
                backend.wait(timeout=5)
            except subprocess.TimeoutExpired:
                backend.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())