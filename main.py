"""
main.py — Multi-Portal Job Automation Launcher
================================================

Launches multiple portal-specific automation scripts (each in its own
subprocess) and streams their output back to the console while also
writing a per-portal log file.

Each portal script is expected to live in ./automation/ and to be a
standalone Python program. Every configured portal runs sequentially
for each valid Excel student before the runner advances to the next row.

Design notes
------------
* Uses asyncio subprocesses (no shell) so Ctrl+C propagates cleanly.
* Each child runs with -u (unbuffered) so we see progress in real time.
* Per-student, per-portal logs are written under ./logs/.
* On Ctrl+C or exception, children get SIGTERM, then SIGKILL after 5s.
* No external dependencies — only the Python standard library.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from automation.excel_users import load_users, select_valid_students

# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
AUTOMATION_DIR = BASE_DIR / "automation"
LOG_DIR = BASE_DIR / "logs"
PROFILE_DIR = BASE_DIR / "chrome_profiles"

# Grace period (seconds) for a child to exit after SIGTERM before SIGKILL.
TERMINATE_GRACE_SECONDS = 5

# How long to wait for the child's output reader to drain after exit.
OUTPUT_DRAIN_SECONDS = 5

# Portals to launch. Format: (DisplayName, filename_in_automation_dir)
PORTAL_SCRIPTS: list[tuple[str, str]] = [
    ("IIMJobs",         "iimjobs.py"),
    ("JobGrin",         "jobgrin.py"),
    ("Wellfound",       "wellfound_login.py"),
    ("PlacementIndia",  "placementindia.py"),
]


# ============================================================
# RESULT TRACKING
# ============================================================

@dataclass
class PortalResult:
    student_id: str
    portal: str
    script: str
    status: str
    exit_code: int | None
    duration: float
    log_path: Path | None


# ============================================================
# HELPERS
# ============================================================

def print_banner(title: str, char: str = "=", width: int = 70) -> None:
    print()
    print(char * width)
    print(title)
    print(char * width)
    sys.stdout.flush()


def ensure_environment() -> None:
    """Create required directories and verify the automation folder exists."""
    if not AUTOMATION_DIR.is_dir():
        raise RuntimeError(
            f"Automation directory not found: {AUTOMATION_DIR}\n"
            f"Create it and place your portal scripts inside."
        )

    LOG_DIR.mkdir(parents=True, exist_ok=True)


def student_profile_path(
    student_id: str,
    portal_name: str,
    account_id: str = "",
) -> Path:
    identity = hashlib.sha256(
        (
            f"{student_id.casefold()}:{portal_name.casefold()}:"
            f"{account_id.strip().casefold()}"
        ).encode("utf-8")
    ).hexdigest()
    return PROFILE_DIR / identity


def portal_account_identifier(student: dict[str, object], portal_name: str) -> str:
    normalized_student = {
        str(key).strip().casefold(): value
        for key, value in student.items()
    }
    account_column = {
        "iimjobs": "iimjobs_email",
        "jobgrin": "jobgrin_email",
        "wellfound": "wellfound_email",
        "placementindia": "placementindia_email",
    }.get(portal_name.casefold())

    if not account_column:
        raise ValueError(f"No account identity mapping for portal: {portal_name}")

    account_id = str(normalized_student.get(account_column) or "").strip()
    if not account_id and portal_name.casefold() == "placementindia":
        account_id = str(normalized_student.get("email") or "").strip()

    return account_id


def discover_scripts(
    portals: Iterable[tuple[str, str]],
) -> tuple[list[tuple[str, str, Path]], list[tuple[str, str]]]:
    """
    Split the configured portals into (available, missing).

    Returns
    -------
    available : list of (portal_name, script_name, script_path)
    missing   : list of (portal_name, script_name)
    """
    available: list[tuple[str, str, Path]] = []
    missing: list[tuple[str, str]] = []

    for portal_name, script_name in portals:
        script_path = AUTOMATION_DIR / script_name
        if script_path.is_file():
            available.append((portal_name, script_name, script_path))
        else:
            missing.append((portal_name, script_name))

    return available, missing


async def stop_process(process: asyncio.subprocess.Process | None) -> None:
    """
    Terminate a subprocess, escalating to SIGKILL if it refuses to exit.
    Safe to call multiple times.
    """
    if process is None or process.returncode is not None:
        return

    try:
        process.terminate()
    except ProcessLookupError:
        return
    except Exception:
        pass

    try:
        await asyncio.wait_for(process.wait(), timeout=TERMINATE_GRACE_SECONDS)
        return
    except asyncio.TimeoutError:
        pass

    try:
        process.kill()
    except ProcessLookupError:
        return
    except Exception:
        pass

    try:
        await process.wait()
    except Exception:
        pass


# ============================================================
# PER-PORTAL RUNNER
# ============================================================

async def run_portal(
    portal_name: str,
    script_name: str,
    script_path: Path,
    log_path: Path,
    student_id: str,
    account_id: str,
) -> PortalResult:
    """
    Launch one portal script as a subprocess.

    Streams stdout/stderr (combined) to both the console and a per-portal
    log file. Returns a PortalResult with status, exit code, and duration.
    """
    started_at = time.time()

    print(
        f"\n[Student {student_id} | {portal_name}] Starting: {script_name}",
        flush=True,
    )
    print(f"[{portal_name}] Log file: {log_path}", flush=True)

    process: asyncio.subprocess.Process | None = None
    output_task: asyncio.Task[None] | None = None
    log_file = None

    async def cleanup() -> None:
        """Stop the child and drain its output pipe cleanly."""
        nonlocal output_task, log_file

        await stop_process(process)

        if output_task is not None:
            try:
                await asyncio.wait_for(
                    asyncio.shield(output_task),
                    timeout=OUTPUT_DRAIN_SECONDS,
                )
            except asyncio.TimeoutError:
                output_task.cancel()
                await asyncio.gather(output_task, return_exceptions=True)
            except Exception:
                pass

        if log_file is not None:
            try:
                log_file.close()
            except Exception:
                pass
            log_file = None

    try:
        # ----------------------------------------------------
        # Prepare child environment
        # ----------------------------------------------------
        child_env = os.environ.copy()
        child_env["PYTHONIOENCODING"] = "utf-8"
        child_env["PYTHONUTF8"] = "1"
        # Prevent Python from writing .pyc files inside automation dir
        child_env["PYTHONDONTWRITEBYTECODE"] = "1"
        child_env["JOB_AUTOMATION_STUDENT_ID"] = student_id
        profile_path = student_profile_path(
            student_id,
            portal_name,
            account_id,
        )
        profile_path.mkdir(parents=True, exist_ok=True)
        child_env["JOB_AUTOMATION_PROFILE_DIR"] = str(profile_path)

        # ----------------------------------------------------
        # Spawn child
        # ----------------------------------------------------
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-u",
            str(script_path),
            cwd=str(BASE_DIR),
            env=child_env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        # ----------------------------------------------------
        # Open log file
        # ----------------------------------------------------
        try:
            log_file = open(log_path, "w", encoding="utf-8", buffering=1)
        except Exception as e:
            print(f"[{portal_name}] WARNING: cannot open log file: {e}", flush=True)
            log_file = None

        # ----------------------------------------------------
        # Output reader
        # ----------------------------------------------------
        async def show_output() -> None:
            assert process is not None
            assert process.stdout is not None

            while True:
                try:
                    line = await process.stdout.readline()
                except Exception:
                    break

                if not line:
                    break

                text = line.decode("utf-8", errors="replace").rstrip()

                try:
                    print(f"[{portal_name}] {text}", flush=True)
                except Exception:
                    # Console may be closed; keep going for the log file
                    pass

                if log_file is not None:
                    try:
                        log_file.write(text + "\n")
                    except Exception:
                        pass

        output_task = asyncio.create_task(show_output())

        # ----------------------------------------------------
        # Wait for child + output reader
        # ----------------------------------------------------
        await asyncio.gather(output_task, process.wait())

        # ----------------------------------------------------
        # Determine status
        # ----------------------------------------------------
        exit_code = process.returncode

        if exit_code == 0:
            status = "FINISHED"
        elif exit_code is None:
            status = "UNKNOWN"
        else:
            status = f"FAILED (exit {exit_code})"

        duration = time.time() - started_at

        print(
            f"[{portal_name}] {status} in {duration:.1f}s",
            flush=True,
        )

        return PortalResult(
            student_id=student_id,
            portal=portal_name,
            script=script_name,
            status=status,
            exit_code=exit_code,
            duration=duration,
            log_path=log_path,
        )

    except asyncio.CancelledError:
        print(
            f"[{portal_name}] Cancellation received. Cleaning up...",
            flush=True,
        )
        await cleanup()
        raise

    except Exception as error:
        duration = time.time() - started_at
        print(f"[{portal_name}] ERROR: {error}", flush=True)
        await cleanup()

        return PortalResult(
            student_id=student_id,
            portal=portal_name,
            script=script_name,
            status=f"ERROR: {error}",
            exit_code=None,
            duration=duration,
            log_path=log_path,
        )

    finally:
        # Make sure we don't leak the child on any code path.
        if process is not None and process.returncode is None:
            await stop_process(process)

        if log_file is not None:
            try:
                log_file.close()
            except Exception:
                pass


# ============================================================
# MAIN ORCHESTRATION
# ============================================================

def print_preflight(
    available: list[tuple[str, str, Path]],
    missing: list[tuple[str, str]],
) -> None:
    print_banner("MULTI-PORTAL JOB AUTOMATION")

    print(f"Base dir       : {BASE_DIR}")
    print(f"Automation dir : {AUTOMATION_DIR}")
    print(f"Log dir        : {LOG_DIR}")
    print("Mode           : sequential by student and portal")
    print()

    print(f"Scripts found  : {len(available)}")
    for name, script, _ in available:
        print(f"  [OK]      {name:<18} -> {script}")

    if missing:
        print(f"\nScripts missing: {len(missing)}")
        for name, script in missing:
            print(f"  [MISSING] {name:<18} -> {script}")

    print()


async def run_all_portals(
    available: list[tuple[str, str, Path]],
    student: dict[str, object],
) -> list[PortalResult]:
    """Run every configured portal in order for one selected student."""

    if not available:
        return []

    results: list[PortalResult] = []
    student_id = str(student["student_id"]).strip()

    for portal_name, script_name, script_path in available:
        student_log_id = hashlib.sha256(
            student_id.casefold().encode("utf-8")
        ).hexdigest()[:12]
        log_path = LOG_DIR / (
            f"{student_log_id}_{portal_name.lower()}.log"
        )

        started_at = time.time()
        try:
            result = await run_portal(
                portal_name=portal_name,
                script_name=script_name,
                script_path=script_path,
                log_path=log_path,
                student_id=student_id,
                account_id=portal_account_identifier(
                    student,
                    portal_name,
                ),
            )
        except asyncio.CancelledError:
            raise
        except Exception as error:
            result = PortalResult(
                student_id=student_id,
                portal=portal_name,
                script=script_name,
                status=f"ERROR: {error}",
                exit_code=None,
                duration=time.time() - started_at,
                log_path=log_path,
            )
        results.append(result)

    return results


async def process_student_queue(students, process_student):
    """Process each validated student sequentially; continue after portal failures."""
    results = []
    for student in students:
        student_results = await process_student(student)
        results.extend(student_results)
    return results


def print_summary(results: list[PortalResult]) -> None:
    print_banner("LAUNCHER SUMMARY")

    if not results:
        print("No portals were executed.")
        return

    successes = sum(1 for r in results if r.exit_code == 0)
    failures = len(results) - successes

    print(f"{'Student ID':<24} {'Portal':<20} {'Status':<28} {'Time':>8}")
    print("-" * 60)

    for r in results:
        print(
            f"{r.student_id:<24} {r.portal:<20} "
            f"{r.status:<28} {r.duration:>6.1f}s"
        )

    print("-" * 60)
    print(f"Total: {len(results)}  |  OK: {successes}  |  Failed: {failures}")

    print("\nPer-portal logs:")
    for r in results:
        if r.log_path is not None:
            print(f"  {r.portal:<20} -> {r.log_path}")

    print()


async def main() -> int:
    ensure_environment()

    available, missing = discover_scripts(PORTAL_SCRIPTS)

    print_preflight(available, missing)

    if not available:
        print("No portal scripts to run. Exiting.", flush=True)
        return 1

    workbook_rows = load_users()
    students = select_valid_students(workbook_rows)
    skipped_rows = len(workbook_rows) - len(students)
    if skipped_rows:
        print(
            f"Rows skipped because student_id is missing: {skipped_rows}",
            flush=True,
        )
    print(f"Students queued: {len(students)}", flush=True)

    async def run_student(student):
        student_id = str(student["student_id"]).strip()
        print_banner(f"PROCESSING STUDENT {student_id}")
        return await run_all_portals(available, student)

    started_at = time.time()

    try:
        results = await process_student_queue(students, run_student)

    except asyncio.CancelledError:
        print(
            "\nCtrl+C detected. Portal automation stopped safely.",
            flush=True,
        )
        # Child cleanup already ran inside each run_portal().
        return 130

    total_duration = time.time() - started_at

    print_summary(results)

    print(f"Total wall-clock time: {total_duration:.1f}s")
    print("All portal processes have exited.", flush=True)

    # Exit non-zero if any portal failed (useful for CI / task schedulers).
    any_failed = any(r.exit_code != 0 for r in results)
    return 1 if any_failed else 0


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
    except KeyboardInterrupt:
        # Second Ctrl+C during shutdown — bail out immediately.
        print("\nShutdown interrupted. Exiting.", flush=True)
        exit_code = 130

    sys.exit(exit_code)