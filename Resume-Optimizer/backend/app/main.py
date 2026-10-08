import re
import uuid
import logging
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .services.ai_optimizer import optimize_resume
from .services.jd_analyzer import analyze_job
from .services.jobs import get_job_description, list_jobs, JobNotFoundError
from .services.jobs import normalize_job_dict
from .services.matcher import match_resume
from .services.quality_analyzer import analyze_resume_quality
from .services.resume_generator import TEMPLATES, render_docx, render_pdf, preview_text
from .services.resume_parser import extract_text, parse_resume
from .services.resume_validation import validate_optimized_resume, ResumeValidationError

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]
UPLOADS = ROOT / "uploads"; OUTPUTS = ROOT / "outputs"
UPLOADS.mkdir(exist_ok=True); OUTPUTS.mkdir(exist_ok=True)
MAX_BYTES = 8 * 1024 * 1024
app = FastAPI(title="FINXL AI Resume Optimizer", version="0.1.0")


@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.endswith((".js", ".css", ".html")) or request.url.path in {"", "/"}:
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


SESSIONS: dict[str, dict] = {}


def _is_resume_id(value: str) -> bool:
    return bool(re.fullmatch(r"[a-f0-9]{32}", value))


def _safe_upload_name(filename: str | None, suffix: str) -> str:
    # Treat both slash styles as separators, regardless of the host OS.
    basename = (filename or "resume").replace("\\", "/").split("/")[-1]
    stem = Path(basename).stem
    safe_stem = re.sub(r"[^A-Za-z0-9._ -]", "_", stem).strip(" .")[:80] or "resume"
    return f"{safe_stem}{suffix}"


def _safe_output_stem(filename: str) -> str:
    stem = Path(filename).stem
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", stem).strip(" .")[:100] or "resume"


async def _resolve_job(job_id: str | None, jd_text: str | None, jd_file: UploadFile | None) -> dict:
    if jd_text and jd_text.strip():
        return normalize_job_dict({"job_id": "pasted-jd", "title": "Pasted Job Description", "company": "",
                                   "description": jd_text.strip()})
    if jd_file and jd_file.filename:
        filename = jd_file.filename.replace("\\", "/").split("/")[-1]
        suffix = Path(filename).suffix.lower()
        if suffix not in {".pdf", ".docx", ".txt", ".json"}:
            raise HTTPException(400, "Upload a PDF, DOCX, TXT, or JSON job description.")
        content = await jd_file.read(MAX_BYTES + 1)
        if not content:
            raise HTTPException(400, "The uploaded job description is empty.")
        if len(content) > MAX_BYTES:
            raise HTTPException(413, "Job description file is too large. Maximum size is 8 MB.")
        try:
            if suffix == ".json":
                import json
                payload = json.loads(content.decode("utf-8-sig"))
                if not isinstance(payload, dict):
                    raise ValueError("JSON job description must contain an object.")
                payload.setdefault("job_id", "uploaded-jd")
                payload.setdefault("title", Path(filename).stem)
                return normalize_job_dict(payload)
            if suffix in {".pdf", ".docx"}:
                temporary = UPLOADS / f"{uuid.uuid4().hex}_{_safe_upload_name(filename, suffix)}"
                temporary.write_bytes(content)
                try:
                    description = extract_text(temporary)
                finally:
                    temporary.unlink(missing_ok=True)
            else:
                description = content.decode("utf-8-sig").strip()
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(422, f"Could not read job description: {exc}") from exc
        return normalize_job_dict({"job_id": "uploaded-jd", "title": Path(filename).stem,
                                   "company": "", "description": description})
    if not job_id or not job_id.strip():
        raise HTTPException(400, "Provide a job ID, paste a job description, or upload a job description file.")
    try:
        return get_job_description(job_id.strip())
    except (JobNotFoundError, KeyError) as exc:
        raise HTTPException(404, f"Job not found: {job_id}") from exc


@app.exception_handler(JobNotFoundError)
async def job_not_found_handler(request, exc: JobNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"error": "Job not found", "job_id": exc.job_id, "detail": f"Job ID '{exc.job_id}' not found."},
    )


@app.get("/api/health")
def health(): return {"status": "ok"}


@app.get("/api/jobs")
def jobs(): return list_jobs()


@app.get("/api/jobs/{job_id}")
def job(job_id: str):
    try:
        return get_job_description(job_id)
    except (JobNotFoundError, KeyError):
        return JSONResponse(
            status_code=404,
            content={"error": "Job not found", "job_id": job_id, "detail": f"Job ID '{job_id}' not found."},
        )


@app.get("/api/templates")
def templates():
    descriptions = {
        "professional": "Modern, warm accent color, airy spacing, centered name.",
        "corporate": "Formal navy styling, compact spacing, left-aligned name.",
        "finance": "Conservative navy hierarchy with focused section spacing.",
        "fresher": "Education and project-forward layout with centered header.",
        "sidebar": "Light sidebar with a professional two-column layout.",
        "sidebar_corporate": "Dark navy sidebar with a corporate two-column layout.",
    }
    return [{"id": template_id, "name": template["name"], "description": descriptions[template_id]}
            for template_id, template in TEMPLATES.items()]


@app.post("/api/optimize-resume")
async def optimize(file: UploadFile = File(...), job_id: str | None = Form(None), source: str = Form("finxl"),
                   jd_text: str | None = Form(None), jd_file: UploadFile | None = File(None)):
    original_filename = (file.filename or "").replace("\\", "/").split("/")[-1]
    suffix = Path(original_filename).suffix.lower()
    if suffix not in {".pdf", ".docx"}: raise HTTPException(400, "Upload a PDF or DOCX resume.")
    content = await file.read(MAX_BYTES + 1)
    if not content: raise HTTPException(400, "The uploaded file is empty.")
    if len(content) > MAX_BYTES: raise HTTPException(413, "File is too large. Maximum size is 8 MB.")
    sid = uuid.uuid4().hex
    safe_filename = _safe_upload_name(original_filename, suffix)
    source_path = UPLOADS / f"{sid}_{safe_filename}"
    source_path.write_bytes(content)
    logger.info("Temporary resume saved: %s", source_path)
    logger.info("Resume processing started: %s", sid)
    try:
        target_job = await _resolve_job(job_id if source in {"finxl", "external"} else None,
                                        jd_text if source == "paste" else None,
                                        jd_file if source == "upload" else None)
    except (JobNotFoundError, KeyError) as exc:
        logger.exception("Resume processing failed; temporary upload retained: %s", source_path)
        err_id = getattr(exc, "job_id", job_id.strip())
        return JSONResponse(
            status_code=404,
            content={"error": "Job not found", "job_id": err_id, "detail": f"Job ID '{err_id}' not found. The temporary upload was retained for debugging."}
        )
    try:
        original = parse_resume(extract_text(source_path))
    except Exception as exc:
        logger.exception("Resume parsing failed; temporary upload retained: %s", source_path)
        message = str(exc) if isinstance(exc, ValueError) else "The PDF or DOCX may be corrupted or unreadable"
        raise HTTPException(422, f"Could not parse this resume: {message}. The temporary upload was retained for debugging.")
    try:
        analysis = analyze_job(target_job)
        match = match_resume(original, analysis)
        quality = analyze_resume_quality(original, match)
    except Exception:
        logger.exception("Resume processing failed; temporary upload retained: %s", source_path)
        raise HTTPException(500, "Resume analysis failed. The temporary upload was retained for debugging.")
    SESSIONS[sid] = {"job": target_job, "original": original, "resume": None, "analysis": analysis, "match": match,
                     "quality": quality, "source_path": source_path, "optimization_method": None, "template_id": "professional"}
    SESSIONS[sid]["original_filename"] = original_filename
    logger.info("Resume analysis completed: %s", sid)
    return {"id": sid, "job": target_job, "resume_analysis": original,
            "job_analysis": analysis, "match": match, "quality_analysis": quality,
            "templates": templates()}


@app.post("/api/optimize-resumes")
async def optimize_batch(files: list[UploadFile] = File(...), job_id: str | None = Form(None),
                         source: str = Form("finxl"), jd_text: str | None = Form(None),
                         jd_file: UploadFile | None = File(None)):
    """Independently optimize up to five resumes against one shared JD analysis."""
    if not 1 <= len(files) <= 5:
        raise HTTPException(400, "Maximum 5 resumes can be optimized at once.")
    try:
        target_job = await _resolve_job(job_id if source in {"finxl", "external"} else None,
                                        jd_text if source == "paste" else None,
                                        jd_file if source == "upload" else None)
        analysis = analyze_job(target_job)
    except (JobNotFoundError, KeyError) as exc:
        raise HTTPException(404, f"Job not found: {job_id}") from exc
    results = []
    names_in_batch: set[str] = set()
    for uploaded in files:
        original_filename = (uploaded.filename or "resume").replace("\\", "/").split("/")[-1]
        item = {"original_filename": original_filename, "status": "failed"}
        source_path = None
        generated_paths: list[Path] = []
        try:
            suffix = Path(original_filename).suffix.lower()
            if suffix not in {".pdf", ".docx"}:
                raise ValueError("Please upload a PDF or DOCX resume.")
            content = await uploaded.read(MAX_BYTES + 1)
            if not content:
                raise ValueError("The uploaded file is empty.")
            if len(content) > MAX_BYTES:
                raise ValueError("File is too large. Maximum size is 8 MB.")
            sid = uuid.uuid4().hex
            source_path = UPLOADS / f"{sid}_{_safe_upload_name(original_filename, suffix)}"
            source_path.write_bytes(content)
            original = parse_resume(extract_text(source_path))
            match = match_resume(original, analysis)
            quality = analyze_resume_quality(original, match)
            optimized, method = optimize_resume(original, target_job, analysis, match, quality)
            optimized = validate_optimized_resume(original, optimized)
            stem = _safe_output_stem(original_filename)
            candidate = f"{stem}_Optimized"
            index = 2
            while candidate.casefold() in names_in_batch or (OUTPUTS / f"{candidate}.docx").exists() or (OUTPUTS / f"{candidate}.pdf").exists():
                candidate = f"{stem}_Optimized_{index}"; index += 1
            names_in_batch.add(candidate.casefold())
            docx, pdf = OUTPUTS / f"{candidate}.docx", OUTPUTS / f"{candidate}.pdf"
            generated_paths = [docx, pdf]
            render_docx(optimized, docx)
            render_pdf(optimized, pdf)
            if not docx.is_file() or not docx.stat().st_size or not pdf.is_file() or not pdf.stat().st_size:
                raise OSError("DOCX or PDF generation failed.")
            SESSIONS[sid] = {"job": target_job, "original": original, "resume": optimized, "analysis": analysis,
                             "match": match, "quality": quality, "source_path": source_path,
                             "original_filename": original_filename, "output_paths": {"docx": docx, "pdf": pdf},
                             "optimization_method": method, "template_id": "professional"}
            item.update({"id": sid, "status": "completed", "optimization_method": method,
                         "optimized_docx": docx.name, "optimized_pdf": pdf.name,
                         "docx_url": f"/api/generated-resumes/{sid}/docx", "pdf_url": f"/api/generated-resumes/{sid}/pdf"})
        except Exception as exc:
            logger.exception("Batch resume failed: %s", original_filename)
            for output_path in generated_paths:
                output_path.unlink(missing_ok=True)
            item["error"] = str(exc) or "Resume processing failed."
        finally:
            if source_path:
                source_path.unlink(missing_ok=True)
        results.append(item)
    return {"job": target_job, "results": results, "status": "completed"}


@app.post("/api/resumes/{resume_id}/optimize")
def optimize_existing(resume_id: str):
    if not _is_resume_id(resume_id): raise HTTPException(404, "Resume session not found.")
    session = SESSIONS.get(resume_id)
    if not session: raise HTTPException(404, "Resume session expired. Please upload again.")
    try:
        optimized, method = optimize_resume(session["original"], session["job"], session["analysis"], session["match"], session["quality"])
        optimized = validate_optimized_resume(session["original"], optimized)
    except ResumeValidationError as exc:
        logger.exception("Resume validation failed: %s", resume_id)
        raise HTTPException(422, f"Resume validation failed: {exc}")
    except Exception:
        logger.exception("Resume optimization failed; temporary upload retained: %s", session["source_path"])
        raise HTTPException(502, "Resume optimization failed. The temporary upload was retained for debugging.")
    session["resume"] = optimized; session["optimization_method"] = method
    logger.info("Resume optimization completed: %s", resume_id)
    return {"id": resume_id, "optimization_method": method, "optimized_resume": preview_text(optimized)}


@app.post("/api/resumes/{resume_id}/generate")
def generate(resume_id: str, template_id: str = Form("professional")):
    if not _is_resume_id(resume_id): raise HTTPException(404, "Resume session not found.")
    session = SESSIONS.get(resume_id)
    if not session: raise HTTPException(404, "Resume session expired. Please upload again.")
    if not session.get("resume"): raise HTTPException(409, "Optimize the resume before generating documents.")
    if template_id not in TEMPLATES: raise HTTPException(400, "Unknown template.")
    session["template_id"] = template_id
    safe_base = _safe_output_stem(session.get("original_filename", "resume"))
    docx = OUTPUTS / f"{safe_base}_Optimized.docx"; pdf = OUTPUTS / f"{safe_base}_Optimized.pdf"
    collision = 2
    while docx.exists() or pdf.exists():
        docx = OUTPUTS / f"{safe_base}_Optimized_{collision}.docx"; pdf = OUTPUTS / f"{safe_base}_Optimized_{collision}.pdf"
        collision += 1
    try:
        render_docx(session["resume"], docx, template_id)
        render_pdf(session["resume"], pdf, template_id, session.get("job", {}).get("title", ""))
        if not docx.is_file() or docx.stat().st_size == 0 or not pdf.is_file() or pdf.stat().st_size == 0:
            raise OSError("Generated document is missing or empty.")
    except Exception:
        logger.exception("Output generation failed; temporary upload retained: %s", session["source_path"])
        raise HTTPException(500, "Resume generation failed. The temporary upload was retained for debugging.")
    logger.info("Generated output successfully: %s and %s", docx, pdf)
    session["output_paths"] = {"docx": docx, "pdf": pdf}
    source_path: Path = session["source_path"]
    try:
        # The path was created under UPLOADS from a generated ID and sanitized basename.
        if source_path.parent.resolve() == UPLOADS.resolve():
            source_path.unlink(missing_ok=True)
            logger.info("Temporary uploaded resume deleted: %s", source_path)
        else:
            logger.error("Refusing to delete temporary upload outside uploads/: %s", source_path)
    except OSError:
        # Output is complete; leave it available and log a cleanup failure for later inspection.
        logger.exception("Could not delete temporary uploaded resume: %s", source_path)
    logger.info("Resume processing completed: %s", resume_id)
    return {"id": resume_id, "docx_url": f"/api/generated-resumes/{resume_id}/docx", "pdf_url": f"/api/generated-resumes/{resume_id}/pdf", "job_title": session["job"]["title"], "preview": preview_text(session["resume"])}


@app.get("/api/generated-resumes/{resume_id}/{format}")
def download(resume_id: str, format: str):
    if not _is_resume_id(resume_id): raise HTTPException(404, "Generated resume not found.")
    if format not in {"docx", "pdf"}: raise HTTPException(400, "Format must be docx or pdf.")
    session = SESSIONS.get(resume_id, {})
    path = session.get("output_paths", {}).get(format, OUTPUTS / f"{resume_id}_optimized.{format}")
    if not path.is_file(): raise HTTPException(404, "Generate the resume before downloading.")
    filename = path.name
    return FileResponse(path, filename=filename)


FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
