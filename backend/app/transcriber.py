import asyncio
import subprocess
from pathlib import Path

from faster_whisper import WhisperModel

from .config import settings

_model: WhisperModel | None = None


def load_model() -> None:
    global _model
    _model = WhisperModel(
        settings.whisper_model,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
    )


def _transcribe_sync(file_path: str) -> tuple[str, float]:
    converted_path: str | None = None

    if file_path.lower().endswith((".m4a", ".aac")):
        converted_path = file_path + ".wav"
        subprocess.run(
            ["ffmpeg", "-y", "-i", file_path, converted_path],
            check=True,
            capture_output=True,
        )

    transcribe_path = converted_path or file_path
    try:
        segments, info = _model.transcribe(transcribe_path, beam_size=5)
        text = " ".join(seg.text.strip() for seg in segments)
        return text, info.duration
    finally:
        if converted_path:
            Path(converted_path).unlink(missing_ok=True)


async def transcribe(file_path: str) -> tuple[str, float]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _transcribe_sync, file_path)
