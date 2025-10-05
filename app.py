import os, time, uuid, shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from redis import Redis
from rq import Queue

# ---- Carga variables de entorno ----
load_dotenv()

# ---- Configuración base ----
APP_PORT = int(os.getenv("PORT", "8088"))
QUAR_DIR = Path(os.getenv("QUAR_DIR", "/srv/quarantine"))
QUAR_DIR.mkdir(parents=True, exist_ok=True)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis = Redis.from_url(REDIS_URL)
q = Queue("ocr", connection=redis)

MAX_UPLOAD = int(float(os.getenv("MAX_UPLOAD_MB", "25")) * 1024 * 1024)

app = FastAPI()

# ---------- Healthcheck: SIEMPRE 200 ----------
@app.get("/health")
def health():
    status = {"ok": True}
    try:
        redis.ping()
        status["redis"] = "ok"
    except Exception as e:
        # No devolvemos 500 para que Coolify no haga rollback
        status["redis"] = f"error:{e.__class__.__name__}"
    return JSONResponse(status, status_code=200)

# ---------- Ingesta ----------
@app.post("/ingest")
async def ingest(
    file: UploadFile = File(...),
    user_slug: str = Form(...),
    title: str = Form("documento")
):
    # Guarda a disco controlando tamaño
    size = 0
    tmp = QUAR_DIR / f"{uuid.uuid4()}_{file.filename}"
    with tmp.open("wb") as f:
        while True:
            chunk = await file.read(1 << 20)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_UPLOAD:
                try:
                    tmp.unlink()
                except:
                    pass
                raise HTTPException(413, detail="Archivo demasiado grande")
            f.write(chunk)

    # Encola trabajo en RQ
    job = q.enqueue("ocr_worker.ocr_task.process_document", str(tmp), job_timeout=600)

    # Espera corta (hasta 25s) para respuesta directa
    deadline = time.time() + 25
    while time.time() < deadline:
        job.refresh()
        if job.is_finished:
            return job.result
        if job.is_failed:
            raise HTTPException(500, detail=f"OCR falló: {job.exc_info}")
        time.sleep(0.6)

    # Si tarda, devolvemos job_id para polling
    return {"pending": True, "job_id": job.id}

# ---------- Polling del resultado ----------
@app.get("/result/{job_id}")
def result(job_id: str):
    from rq.job import Job
    job = Job.fetch(job_id, connection=redis)
    if job.is_finished:
        return job.result
    if job.is_failed:
        raise HTTPException(500, detail=f"OCR falló: {job.exc_info}")
    return {"pending": True, "job_id": job.id}
