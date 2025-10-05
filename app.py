import os, time, uuid, shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from redis import Redis
from rq import Queue
from utils import QUAR_DIR, clamp

load_dotenv()
app = FastAPI()

redis = Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))
q = Queue("ocr", connection=redis)

MAX_UPLOAD = int(float(os.getenv("MAX_UPLOAD_MB", "25")) * 1024 * 1024)

@app.get("/health")
def health():
    try:
        redis.ping()
        return {"ok": True}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@app.post("/ingest")
async def ingest(
    file: UploadFile = File(...),
    user_slug: str = Form(...),
    title: str = Form("documento")
):
    # control de tamaño (si Content-Length no viene, igual guardamos y luego chequeamos)
    size = 0
    tmp = QUAR_DIR / f"{uuid.uuid4()}_{file.filename}"
    with tmp.open("wb") as f:
        while True:
            chunk = await file.read(1<<20)
            if not chunk: break
            size += len(chunk)
            if size > MAX_UPLOAD:
                try: tmp.unlink()
                except: pass
                raise HTTPException(413, detail="Archivo demasiado grande")
            f.write(chunk)

    # Encola trabajo
    job = q.enqueue("ocr_task.process_document", str(tmp), job_timeout=600)

    # Espera corta (hasta 25 s) para respuesta síncrona
    deadline = time.time() + 25
    while time.time() < deadline:
        job.refresh()
        if job.is_finished:
            return job.result
        if job.is_failed:
            raise HTTPException(500, detail=f"OCR falló: {job.exc_info}")
        time.sleep(0.6)

    # Timeout corto: devolver job_id para polling
    return {"pending": True, "job_id": job.id}

@app.get("/result/{job_id}")
def result(job_id: str):
    from rq.job import Job
    job = Job.fetch(job_id, connection=redis)
    if job.is_finished:
        return job.result
    if job.is_failed:
        raise HTTPException(500, detail=f"OCR falló: {job.exc_info}")
    return {"pending": True, "job_id": job.id}
