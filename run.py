"""
Unified Process Runner for malloc().

Runs FastAPI backend on an internal port (default 8000) and Streamlit frontend
on the public PORT (environment variable PORT, or 8501, or 7860 for Hugging Face Spaces).
Allows 1-click single-service deployments on Render, Railway, Hugging Face Spaces, Koyeb, Fly.io, and Docker.
"""
import os
import sys
import time
import signal
import subprocess
import urllib.request
import urllib.error

BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = int(os.environ.get("BACKEND_PORT", "8000"))
BACKEND_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"

FRONTEND_PORT = int(os.environ.get("PORT", os.environ.get("STREAMLIT_SERVER_PORT", "8501")))
FRONTEND_ADDRESS = os.environ.get("STREAMLIT_SERVER_ADDRESS", "0.0.0.0")


def wait_for_backend(url: str, timeout: int = 25) -> bool:
    start_time = time.time()
    health_endpoint = f"{url}/health"
    print(f"[*] Waiting for FastAPI backend to become ready at {health_endpoint}...")
    while time.time() - start_time < timeout:
        try:
            req = urllib.request.urlopen(health_endpoint, timeout=2)
            if req.getcode() == 200:
                print(f"[+] Backend is ready and healthy at {health_endpoint}!")
                return True
        except (urllib.error.URLError, urllib.error.HTTPError, OSError):
            time.sleep(0.5)
    print("[-] Warning: Backend did not respond within timeout, starting frontend anyway...")
    return False


def main():
    print("=" * 60)
    print("  Starting malloc() Unified Application Server")
    print(f"  Backend: {BACKEND_URL}")
    print(f"  Frontend: http://{FRONTEND_ADDRESS}:{FRONTEND_PORT}")
    print("=" * 60)

    # 1. Start FastAPI backend
    backend_env = os.environ.copy()
    backend_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        BACKEND_HOST,
        "--port",
        str(BACKEND_PORT),
    ]

    backend_proc = subprocess.Popen(backend_cmd, env=backend_env)

    # 2. Wait for backend to be ready
    wait_for_backend(BACKEND_URL)

    # 3. Start Streamlit frontend
    frontend_env = os.environ.copy()
    frontend_env["API_URL"] = BACKEND_URL
    frontend_cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "streamlit_app.py",
        "--server.port",
        str(FRONTEND_PORT),
        "--server.address",
        FRONTEND_ADDRESS,
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
    ]

    frontend_proc = subprocess.Popen(frontend_cmd, env=frontend_env)

    def signal_handler(sig, frame):
        print("\n[*] Shutting down malloc() services...")
        frontend_proc.terminate()
        backend_proc.terminate()
        try:
            frontend_proc.wait(timeout=5)
            backend_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            frontend_proc.kill()
            backend_proc.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Monitor processes
    while True:
        if backend_proc.poll() is not None:
            print("[-] FastAPI backend process exited unexpectedly.")
            frontend_proc.terminate()
            sys.exit(backend_proc.returncode)
        if frontend_proc.poll() is not None:
            print("[-] Streamlit frontend process exited.")
            backend_proc.terminate()
            sys.exit(frontend_proc.returncode)
        time.sleep(1)


if __name__ == "__main__":
    main()
