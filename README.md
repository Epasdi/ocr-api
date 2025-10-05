# ocr-api (FastAPI + RQ client)

API interna (no pública) que recibe archivos, los envía al worker por Redis/RQ y devuelve el resultado si está listo en <=25 s, si no: `pending=true`.

## Endpoints
- `POST /ingest` (multipart): `file`, `user_slug`, `title`
- `GET /result/{job_id}`
- `GET /health`

## Variables
- `REDIS_URL=redis://redis:6379/0`
- `QUAR_DIR=/srv/quarantine`
- `MAX_UPLOAD_MB=25`

## Despliegue en Coolify
- Build pack: **Dockerfile**
- **Port:** 8088
- **No expongas dominio** (interno).
- **Volume**: host `/srv/quarantine` -> container `/srv/quarantine`.

Desde n8n/evolution-api usa `http://ocr-api:8088/ingest`.
