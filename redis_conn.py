# redis_conn.py
import os
from urllib.parse import urlparse, urlunparse
from redis import Redis
from redis.exceptions import AuthenticationError, ConnectionError

def _mk_url(scheme, username, password, host, port, db):
    netloc = ""
    if username is not None:
        # username puede ser "", lo tratamos como sin usuario
        if username == "":
            netloc = f":{password}@{host}:{port}"
        else:
            netloc = f"{username}:{password}@{host}:{port}"
    else:
        # sin credenciales en netloc
        netloc = f"{host}:{port}"
    return urlunparse((scheme, netloc, f"/{db}", "", "", ""))

def build_redis():
    """
    Prioriza REDIS_URL si está definida.
    Si da AuthenticationError, prueba variaciones comunes:
      - sin usuario (":password@")
      - con usuario 'default'
    Alternativamente, permite usar REDIS_HOST/PORT/DB/USERNAME/PASSWORD.
    """
    url = os.getenv("REDIS_URL", "").strip()
    if url:
        # primer intento: tal cual
        try:
            r = Redis.from_url(url)
            r.ping()
            return r
        except AuthenticationError:
            # probamos variantes solo si hay password
            parsed = urlparse(url)
            scheme = parsed.scheme or "redis"
            host = parsed.hostname
            port = parsed.port or 6379
            db = parsed.path.lstrip("/") or "0"
            password = parsed.password
            # si no hay password no podemos variar credenciales
            if not password:
                raise

            # variante 1: sin usuario (":password@")
            try:
                url_no_user = _mk_url(scheme, "", password, host, port, db)
                r = Redis.from_url(url_no_user)
                r.ping()
                return r
            except AuthenticationError:
                pass

            # variante 2: usuario 'default'
            try:
                url_def_user = _mk_url(scheme, "default", password, host, port, db)
                r = Redis.from_url(url_def_user)
                r.ping()
                return r
            except AuthenticationError as e2:
                raise e2
        except ConnectionError as e:
            # re-lanza para que el /health lo muestre
            raise e
    else:
        # construir desde piezas
        scheme  = os.getenv("REDIS_SCHEME", "redis")
        host    = os.getenv("REDIS_HOST", "redis")
        port    = int(os.getenv("REDIS_PORT", "6379"))
        db      = int(os.getenv("REDIS_DB", "0"))
        user    = os.getenv("REDIS_USERNAME", None)  # None = sin user en URL
        pwd     = os.getenv("REDIS_PASSWORD", None)

        # intentos según user/pwd
        variants = []
        if pwd:
            # si tenemos password, probamos: user explícito -> sin user -> default
            if user is not None:
                variants.append(_mk_url(scheme, user, pwd, host, port, db))
            variants.append(_mk_url(scheme, "", pwd, host, port, db))
            variants.append(_mk_url(scheme, "default", pwd, host, port, db))
        else:
            # sin credenciales
            variants.append(_mk_url(scheme, None, None, host, port, db))

        last_exc = None
        for u in variants:
            try:
                r = Redis.from_url(u)
                r.ping()
                return r
            except (AuthenticationError, ConnectionError) as e:
                last_exc = e
                continue
        if last_exc:
            raise last_exc

def redis_connection():
    return build_redis()
