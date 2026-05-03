import logging
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile

from .config import settings
from .postprocessor import clean_transcript
from .transcriber import load_model, transcribe

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_ALLOWED_EXTENSIONS = {".wav", ".m4a", ".aac"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Loading Whisper model...")
    load_model()
    logger.info("Whisper model loaded on %s", settings.whisper_device)
    yield


app = FastAPI(title="OpenDictate", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "model": settings.whisper_model, "device": settings.whisper_device}


@app.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    suffix = Path(audio.filename or "audio").suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Accepted: .wav, .m4a, .aac",
        )

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name

    try:
        raw, duration = await transcribe(tmp_path)
        if duration > settings.max_audio_duration_seconds:
            raise HTTPException(
                status_code=400,
                detail=f"Audio is {duration:.0f}s; limit is {settings.max_audio_duration_seconds}s",
            )
        cleaned = await clean_transcript(raw)
        return {"transcript": cleaned, "raw": raw, "duration_seconds": round(duration, 2)}
    finally:
        Path(tmp_path).unlink(missing_ok=True)
