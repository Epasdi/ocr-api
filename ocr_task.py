# Este archivo permite que RQ haga import del mismo nombre en ambos repos.
# La lógica real vive en el repo del worker. Aquí dejamos un marcador por si
# accidentalmente alguien intenta importarlo localmente.
def process_document(path: str) -> dict:
    raise RuntimeError("Este endpoint debe ser ejecutado por el worker.")
