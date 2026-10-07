"""ARQ 的 Unix 信号监听在 Windows 上不可用；两平台共用同一任务配置。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from arq.worker import create_worker  # noqa: E402

from app.worker.settings import WorkerSettings  # noqa: E402

if __name__ == "__main__":
    worker = create_worker(WorkerSettings, handle_signals=sys.platform != "win32")
    worker.run()
