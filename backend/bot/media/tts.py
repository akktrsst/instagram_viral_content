import logging
import wave
from pathlib import Path

from app.config import settings
from bot.media.ai_images import MediaError
from bot.settings import Voiceover

SAMPLE_RATE = 44100
logger = logging.getLogger(__name__)


def synthesize(text: str, out_path: Path, voiceover: Voiceover) -> float:
    """Write `text` as a WAV voiceover with Google Cloud Text-to-Speech; return its length in seconds."""
    from google.cloud import texttospeech as tts

    client = tts.TextToSpeechClient(
        client_options={"quota_project_id": settings.google_cloud_project}
    )
    language = "-".join(voiceover.voice.split("-")[:2])
    audio_config = {"audio_encoding": tts.AudioEncoding.LINEAR16, "sample_rate_hertz": SAMPLE_RATE}
    if voiceover.speaking_rate != 1.0:
        audio_config["speaking_rate"] = voiceover.speaking_rate
    try:
        response = client.synthesize_speech(
            input=tts.SynthesisInput(text=text),
            voice=tts.VoiceSelectionParams(language_code=language, name=voiceover.voice),
            audio_config=tts.AudioConfig(**audio_config),
        )
    except Exception as exc:
        logger.exception("Voiceover synthesis failed")
        raise MediaError("We couldn't record the voiceover. Please try again.") from exc

    # LINEAR16 responses already carry a WAV header.
    out_path.write_bytes(response.audio_content)
    with wave.open(str(out_path)) as audio:
        return audio.getnframes() / audio.getframerate()
