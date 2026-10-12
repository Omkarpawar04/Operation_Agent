"""Run Freshersworld and Instahyre concurrently in this terminal."""

from datetime import datetime
from pathlib import Path
import subprocess
import sys
import threading
import os


ROOT = Path(__file__).resolve().parent
SCRIPTS = [
    ("Freshersworld", ROOT / "freshersworld_automation" / "main.py"),
    ("Instahyre", ROOT / "instahyre" / "main.py"),
]
PRINT_LOCK = threading.Lock()

# Some scripts print symbols such as ✓ and ✗. Windows may otherwise choose
# cp1252 for child processes and crash before the automation can continue.
CHILD_ENV = os.environ.copy()
CHILD_ENV["PYTHONIOENCODING"] = "utf-8"

# Keep the launcher alive if the active terminal encoding cannot display a
# character emitted by a child. The complete UTF-8 output remains in each log.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")


def relay_output(name: str, process: subprocess.Popen, log_path: Path) -> None:
    """Write each child's output to its own log and tag it in this terminal."""
    with log_path.open("w", encoding="utf-8", errors="replace") as log:
        for line in process.stdout:
            log.write(line)
            log.flush()
            with PRINT_LOCK:
                print(f"[{name}] {line}", end="", flush=True)


def main() -> int:
    missing = [str(script) for _, script in SCRIPTS if not script.is_file()]
    if missing:
        print("Could not find these scripts:", file=sys.stderr)
        print("\n".join(missing), file=sys.stderr)
        return 1

    log_dir = ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    run_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    processes = []
    readers = []

    print("Starting Freshersworld and Instahyre concurrently in this terminal.")
    print(f"Separate logs: {log_dir}\n")

    try:
        for name, script in SCRIPTS:
            process = subprocess.Popen(
                [sys.executable, "-u", script.name],
                cwd=script.parent,
                stdin=None,  # Keep each existing script's Enter-to-close behavior.
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                env=CHILD_ENV,
            )
            processes.append((name, process))
            log_path = log_dir / f"{run_stamp}_{name.lower()}.log"
            reader = threading.Thread(
                target=relay_output,
                args=(name, process, log_path),
                daemon=True,
            )
            reader.start()
            readers.append(reader)
            print(f"[{name}] started (PID {process.pid}); log: {log_path.name}")

        for _, process in processes:
            process.wait()
        for reader in readers:
            reader.join()

    except KeyboardInterrupt:
        print("\nStopping all automation processes...")
        for _, process in processes:
            if process.poll() is None:
                process.terminate()
        for _, process in processes:
            process.wait()
        return 130

    failed = [(name, process.returncode) for name, process in processes if process.returncode]
    if failed:
        for name, code in failed:
            print(f"[{name}] exited with code {code}")
        return 1

    print("\nAll automation scripts have finished.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
