"""启动本地 API 与 Worker；Ctrl+C 会清理本脚本启动的子进程。"""

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"


def main():
    with socket.socket() as sock:
        if sock.connect_ex(("127.0.0.1", 39800)) == 0:
            raise SystemExit("Port 39800 is occupied. Stop the previous instance first.")
    if not (ROOT / "frontend/dist/index.html").exists():
        raise SystemExit("Build frontend first: cd frontend && npm run build")
    log_dir = BACKEND / "var/logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    commands = {
        "api": [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "39800"],
        "worker": [sys.executable, str(BACKEND / "scripts/run_worker.py")],
    }
    processes = []
    logs = []
    try:
        for name, command in commands.items():
            log = (log_dir / f"{name}.log").open("a", encoding="utf-8")
            logs.append(log)
            processes.append(subprocess.Popen(
                command, cwd=BACKEND, stdout=log, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            ))
        print("AI PPT: http://127.0.0.1:39800 | Ctrl+C to stop", flush=True)
        while all(process.poll() is None for process in processes):
            time.sleep(1)
        raise RuntimeError(f"A service stopped; see {log_dir}")
    except KeyboardInterrupt:
        pass
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        for log in logs:
            log.close()


if __name__ == "__main__":
    main()
