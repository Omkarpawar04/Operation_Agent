
import asyncio
import os
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
AUTOMATION_DIR = BASE_DIR / "automation"

# jobgrin_login.py is a helper module, not a separate workflow.
PORTAL_SCRIPTS = [
    ("IIMJobs", "iimjobs.py"),
    ("JobGrin", "jobgrin.py"),
    ("Wellfound", "wellfound_login.py"),
    ("PlacementIndia", "placementindia.py"),
]


async def run_portal(portal_name, script_name):
    script_path = AUTOMATION_DIR / script_name

    if not script_path.is_file():
        print(f"[{portal_name}] FILE NOT FOUND: {script_path}", flush=True)
        return portal_name, "FILE NOT FOUND"

    print(f"\n[{portal_name}] Starting: {script_name}", flush=True)

    try:
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-u",
            str(script_path),
            cwd=str(BASE_DIR),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        async def show_output():
            while True:
                line = await process.stdout.readline()
                if not line:
                    break

                print(
                    f"[{portal_name}] {line.decode(errors='replace').rstrip()}",
                    flush=True,
                )

        await asyncio.gather(show_output(), process.wait())

        if process.returncode == 0:
            status = "FINISHED"
        else:
            status = f"FAILED (exit code {process.returncode})"

        print(f"[{portal_name}] {status}", flush=True)
        return portal_name, status

    except Exception as error:
        print(f"[{portal_name}] ERROR: {error}", flush=True)
        return portal_name, "ERROR"

    except Exception as error:
        print(
            f"[{portal_name}] ERROR: {error}",
            flush=True,
        )
        return portal_name, "ERROR"


async def main():
    print("=" * 65)
    print("MULTI-PORTAL JOB AUTOMATION")
    print("=" * 65)

    results = await asyncio.gather(
        *[
            run_portal(portal_name, script_name)
            for portal_name, script_name in PORTAL_SCRIPTS
        ]
    )

    print("\n" + "=" * 65)
    print("LAUNCHER SUMMARY")
    print("=" * 65)

    for portal_name, status in results:
        print(f"{portal_name:<18} : {status}")

    print("\nAll portal processes have exited.")


if __name__ == "__main__":
    asyncio.run(main())