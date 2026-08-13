"""FastAPI backend exposing the existing redaction pipeline over HTTP.

Reuses main.process_image (the same single-image pipeline the CLI uses) so
there's one source of truth for OCR + regex + faces + Gemini wiring.
"""

import mimetypes
import os
import tempfile

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.background import BackgroundTask

from main import process_image
from redactly.redact import DEFAULT_BLUR_RADIUS

app = FastAPI(title="Redactly API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# mode -> (use_faces, use_gemini), mirrors main.py's --no-vision / default / --smart tiers
_MODES = {
    "text": (False, False),
    "free": (True, False),
    "smart": (True, True),
}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/redact")
async def redact(file: UploadFile = File(...), mode: str = Form("free"), blur: int = Form(None)):
    """Redact an uploaded image and return the result as an image file."""
    if mode not in _MODES:
        return JSONResponse(status_code=400, content={"error": f"invalid mode {mode!r}, must be one of {list(_MODES)}"})
    if not file.filename or not (file.content_type or "").startswith("image/"):
        return JSONResponse(status_code=400, content={"error": "no valid image file uploaded"})

    use_faces, use_gemini = _MODES[mode]
    suffix = os.path.splitext(file.filename)[1] or ".png"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_in:
        tmp_in.write(await file.read())
        input_path = tmp_in.name
    output_path = tempfile.NamedTemporaryFile(suffix=suffix, delete=False).name

    ok = process_image(input_path, output_path, blur or DEFAULT_BLUR_RADIUS, use_faces, use_gemini, dry_run=False)

    if not ok:
        os.remove(input_path)
        os.remove(output_path)
        return JSONResponse(status_code=500, content={"error": "failed to process image"})

    def cleanup():
        os.remove(input_path)
        os.remove(output_path)

    media_type = mimetypes.guess_type(file.filename)[0] or "image/png"
    return FileResponse(output_path, media_type=media_type, background=BackgroundTask(cleanup))
