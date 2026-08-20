"""Run the FastAPI and React development servers together."""
from __future__ import annotations

import signal
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    commands = [
        ([str(ROOT / ".venv/bin/python"), "-m", "uvicorn", "api.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"], ROOT),
        (["npm", "run", "dev"], ROOT / "frontend"),
    ]
    processes = [subprocess.Popen(command, cwd=cwd) for command, cwd in commands]

    def stop(*_: object) -> None:
        for process in processes:
            if process.poll() is None:
                process.terminate()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        while all(process.poll() is None for process in processes):
            processes[0].wait(timeout=0.5)
    except subprocess.TimeoutExpired:
        return main_loop(processes, stop)
    finally:
        stop()
        for process in processes:
            process.wait()
    return next((process.returncode or 0 for process in processes if process.returncode), 0)


def main_loop(processes: list[subprocess.Popen], stop) -> int:
    try:
        while all(process.poll() is None for process in processes):
            for process in processes:
                try:
                    returncode = process.wait(timeout=0.5)
                    if returncode is not None:
                        return returncode
                except subprocess.TimeoutExpired:
                    pass
    except KeyboardInterrupt:
        stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
