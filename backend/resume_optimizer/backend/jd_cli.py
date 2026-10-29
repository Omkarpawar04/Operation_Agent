"""Read a job as JSON on stdin, print the analysed requirements as JSON on stdout.

Used by the Node API (backend/drives/jdParser.js) so drives can reuse the
resume optimizer's JD analyzer without running the FastAPI service.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.services.jd_analyzer import analyze_job  # noqa: E402

job = json.load(sys.stdin)
json.dump(analyze_job(job), sys.stdout)
