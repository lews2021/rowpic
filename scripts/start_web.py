"""Web launcher: starts FastAPI backend + (Vite dev server | built dist),
opens the browser.

If `npm` is on PATH and frontend deps are installed, prefer the Vite dev
server (HMR).  Otherwise fall back to the built `frontend/dist` served by a
small static server, which the FastAPI app also serves at /ui when present.
"""
import os
import shutil
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
FRONTEND_DIST = FRONTEND / "dist"

BACKEND_HOST, BACKEND_PORT = "127.0.0.1", 8765
FRONTEND_HOST, FRONTEND_PORT = "127.0.0.1", 5173


def wait_port(host: str, port: int, timeout: float = 25.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def resolve_npm() -> str | None:
    """Find the absolute path of `npm` (or `npm.cmd` on Windows)."""
    # 1) shutil.which respects PATHEXT (.cmd / .bat on Windows)
    p = shutil.which("npm")
    if p:
        return p
    # 2) Common Windows install locations
    candidates = [
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "nodejs" / "npm.cmd",
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "nodejs" / "npm.cmd",
        Path.home() / "AppData" / "Roaming" / "nvm" / "current" / "npm.cmd",
    ]
    for c in candidates:
        if c.is_file():
            return str(c)
    return None


def has_frontend_deps() -> bool:
    return (FRONTEND / "node_modules").is_dir() and (FRONTEND / "package.json").is_file()


def has_frontend_dist() -> bool:
    return (FRONTEND_DIST / "index.html").is_file()


def start_frontend_dev(backend_log) -> subprocess.Popen:
    npm = resolve_npm()
    if not npm:
        raise RuntimeError("npm not found on PATH")
    if not has_frontend_deps():
        raise RuntimeError(
            f"frontend deps not installed: {FRONTEND}\\node_modules missing.\n"
            f"Run: cd {FRONTEND} && npm install"
        )
    return subprocess.Popen(
        [npm, "run", "dev", "--", "--host", FRONTEND_HOST, "--port", str(FRONTEND_PORT)],
        cwd=str(FRONTEND),
        shell=False,
        stdout=backend_log,
        stderr=backend_log,
    )


def start_frontend_dist(backend_log) -> subprocess.Popen:
    """Serve the built dist via http.server as a fallback when npm is missing."""
    if not has_frontend_dist():
        raise RuntimeError(
            "no built frontend found.  Either:\n"
            f"  1) install Node.js + run `cd {FRONTEND} && npm install && npm run build`\n"
            "  2) or simply point your browser at http://127.0.0.1:8765/ui (FastAPI will serve it once you build)\n"
            f"  3) or place a built dist at {FRONTEND_DIST}"
        )
    # http.server picks up the dist dir; the SPA index.html is served at /
    return subprocess.Popen(
        [sys.executable, "-m", "http.server", str(FRONTEND_PORT), "--bind", FRONTEND_HOST],
        cwd=str(FRONTEND_DIST),
        shell=False,
        stdout=backend_log,
        stderr=backend_log,
    )


def open_browser(url: str) -> None:
    try:
        webbrowser.open(url)
    except Exception as exc:
        print(f"[rowpic] could not open browser: {exc}")


def main() -> int:
    procs = []
    logs_dir = ROOT / "logs"
    logs_dir.mkdir(exist_ok=True)
    log_path = logs_dir / "start_web.log"
    log_fh = open(log_path, "ab", buffering=0)

    try:
        print(f"[rowpic] starting backend on {BACKEND_HOST}:{BACKEND_PORT}")
        backend = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app",
             "--host", BACKEND_HOST, "--port", str(BACKEND_PORT), "--log-level", "info"],
            cwd=str(BACKEND),
            shell=False,
            stdout=log_fh,
            stderr=log_fh,
        )
        procs.append(backend)

        # Decide how to serve the UI
        mode = None
        try:
            if has_frontend_deps() and resolve_npm():
                mode = "dev (vite)"
                frontend = start_frontend_dev(log_fh)
            elif has_frontend_dist():
                mode = "dist (http.server)"
                frontend = start_frontend_dist(log_fh)
            else:
                mode = "backend-only"
                frontend = None
        except Exception as exc:
            print(f"[rowpic] frontend not started: {exc}")
            frontend = None
            mode = "backend-only"

        if mode == "dev (vite)":
            print(f"[rowpic] starting vite dev server on {FRONTEND_HOST}:{FRONTEND_PORT}")
            procs.append(frontend)
            if not wait_port(FRONTEND_HOST, FRONTEND_PORT, timeout=45):
                print(f"[rowpic] vite failed to start within 45s; see {log_path}")
                # fall back to dist if available
                if has_frontend_dist():
                    print("[rowpic] falling back to dist")
                    try:
                        frontend = start_frontend_dist(log_fh)
                        procs.append(frontend)
                        if not wait_port(FRONTEND_HOST, FRONTEND_PORT, timeout=10):
                            print("[rowpic] dist fallback also failed")
                    except Exception as exc:
                        print(f"[rowpic] dist fallback error: {exc}")
        elif mode == "dist (http.server)":
            print(f"[rowpic] serving built dist on http://{FRONTEND_HOST}:{FRONTEND_PORT}")
            procs.append(frontend)
            if not wait_port(FRONTEND_HOST, FRONTEND_PORT, timeout=10):
                print(f"[rowpic] http.server failed to start; see {log_path}")
        else:
            print(f"[rowpic] no UI launcher available; using backend /ui instead")
            print(f"[rowpic] (if 404 on /ui: run `cd {FRONTEND} && npm run build` first)")

        if not wait_port(BACKEND_HOST, BACKEND_PORT, timeout=30):
            print(f"[rowpic] backend failed to start within 30s; see {log_path}")
            return 1

        # Pick the best URL
        if mode in ("dev (vite)", "dist (http.server)"):
            url = f"http://{FRONTEND_HOST}:{FRONTEND_PORT}"
        else:
            url = f"http://{BACKEND_HOST}:{BACKEND_PORT}/ui"
        print(f"[rowpic] ready ({mode}): {url}")
        open_browser(url)

        # Wait for the backend to exit (Ctrl-C)
        backend.wait()
    except KeyboardInterrupt:
        print("\n[rowpic] shutting down...")
    finally:
        for p in procs:
            if p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    p.kill()
        try:
            log_fh.close()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())