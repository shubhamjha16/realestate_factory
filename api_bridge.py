"""
API Bridge — Real Estate Factory

Endpoints:
  POST /generate         — start a real estate document job
  GET  /status/{job_id}  — poll job status
  GET  /health           — health check
"""

import os, uuid, threading, json, requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Real Estate Factory", version="1.0.0")

_cors = os.environ.get("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
app.add_middleware(CORSMiddleware, allow_origins=_cors, allow_methods=["POST", "GET"], allow_headers=["*"])

JOBS_FILE = "jobs.json"
_lock     = threading.Lock()


def _load():
    if os.path.exists(JOBS_FILE):
        try:
            with open(JOBS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save():
    with _lock:
        with open(JOBS_FILE, "w") as f:
            json.dump(jobs, f, indent=2)


jobs = _load()


class GenerateRequest(BaseModel):
    instructions:  str
    property_data: Optional[str] = ""   # CSV of comparables / lease schedule / etc.
    job_type:      Optional[str] = None


class JobStatus(BaseModel):
    job_id:   str
    status:   str
    doc_url:  str = ""
    job_type: str = ""
    error:    str = ""


def _run(job_id, instructions, property_data, job_type):
    with _lock:
        jobs[job_id]["status"] = "processing"

    try:
        from re_graph import app as graph

        final = graph.invoke({
            "raw_instructions":  instructions,
            "raw_property_data": property_data or "",
            "job_type":          job_type,
            "_job_id":           job_id,
            "doc_type":          None, "client_name":      None,
            "property_address":  None, "property_type":    None,
            "purpose":           None, "special_notes":    None,
            "parsed_data":       None, "computed":         None,
            "re_research":       None, "header_image_path": None,
            "structure_plan":    None, "structure_attempt": 0,
            "critic_feedback":   None, "_critic_approved":  False,
            "section_index":     0,    "drafted_sections":  None,
            "clause_plan":       None,
            "render_attempt":    0,    "render_error":      None,
            "doc_path":          None, "doc_url":           None,
            "generation_errors": None,
        })

        url = final.get("doc_url") or ""
        with _lock:
            if url:
                jobs[job_id].update({
                    "status":   "completed",
                    "doc_url":  url,
                    "job_type": final.get("doc_type", ""),
                })
                print(f"✅ Job {job_id} done: {url}")
            else:
                jobs[job_id].update({
                    "status": "failed",
                    "error":  final.get("generation_errors", "No output"),
                })

    except Exception as e:
        with _lock:
            jobs[job_id].update({"status": "failed", "error": str(e)})
        print(f"❌ Job {job_id}: {e}")

    _save()
    webhook = os.environ.get("WEBHOOK_URL")
    if webhook:
        try:
            requests.post(webhook, json=jobs[job_id], timeout=10)
        except Exception:
            pass


@app.post("/generate", response_model=JobStatus)
def generate(req: GenerateRequest):
    if not req.instructions.strip():
        raise HTTPException(400, "instructions required")
    job_id = str(uuid.uuid4())[:12]
    with _lock:
        jobs[job_id] = {
            "job_id":   job_id,
            "status":   "queued",
            "doc_url":  "",
            "job_type": req.job_type or "",
            "error":    "",
        }
    threading.Thread(
        target=_run,
        args=(job_id, req.instructions, req.property_data, req.job_type),
        daemon=True,
    ).start()
    _save()
    print(f"🚀 Job {job_id} queued | type: {req.job_type}")
    with _lock:
        return dict(jobs[job_id])


@app.get("/status/{job_id}", response_model=JobStatus)
def status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")
    return jobs[job_id]


@app.get("/health")
def health():
    return {"status": "ok", "service": "realestate-factory"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8004)))
