"""
voice.py — Text-to-Speech (Sarvam TTS + gTTS fallback) + Speech-to-Text (Whisper)

FIXES vs original:
  1. Browser records audio as audio/webm (Opus, 48kHz stereo).
     Whisper needs 16kHz mono WAV. Added ffmpeg conversion step before
     passing audio to Whisper — this is why transcription was returning
     empty strings or garbled text.
  2. Temp files now cleaned up properly even when transcription fails
     (moved os.unlink into a finally block).
  3. Added fallback: if webm→wav conversion fails, try passing raw file
     directly (some browsers send audio/ogg which Whisper can handle).
  4. Replaced gTTS with Sarvam TTS (Bulbul v1) for better Indian language
     voice quality. Falls back to gTTS if Sarvam API fails.
"""

import base64
import io
import json
import tempfile
import os
import subprocess
import requests
from gtts import gTTS

# ─────────────────────────────────────────
# Sarvam TTS (Bulbul v1) — primary TTS engine
# ─────────────────────────────────────────
SARVAM_API_KEY = os.environ.get("SARVAM_API_KEY", "").strip()
SARVAM_TTS_URL = "https://api.sarvam.ai/v1/tts"

# Sarvam TTS language codes (ISO → Sarvam format)
SARVAM_LANG_MAP = {
    "en": "en-IN",
    "hi": "hi-IN",
    "ta": "ta-IN",
    "te": "te-IN",
    "kn": "kn-IN",
    "ml": "ml-IN",
}

# gTTS language codes (fallback)
GTTS_LANG_MAP = {
    "en": "en",
    "ta": "ta",
    "hi": "hi",
    "ml": "ml",
    "kn": "kn",
    "te": "te",
}

# Whisper is optional: if it's not installed (or fails to load) the rest of
# the backend — detection, depth, narration, TTS, chat — must still start.
# transcribe_audio() checks whisper_model below and returns "" if it's None.
try:
    import whisper
    print("⏳ Loading Whisper model...")
    whisper_model = whisper.load_model("small")
    print("✅ Whisper model loaded")
except Exception as e:
    print(f"⚠️ Whisper unavailable, voice transcription disabled: {e}")
    whisper_model = None

WHISPER_LANG_MAP = {
    "en": "english",
    "ta": "tamil",
    "hi": "hindi",
    "ml": "malayalam",
    "kn": "kannada",
    "te": "telugu",
}


def text_to_speech(text: str, language: str = "en") -> str:
    """
    Convert text to speech using Sarvam TTS (Bulbul v1).
    Falls back to gTTS if Sarvam API is unavailable or fails.
    Returns base64-encoded audio string.
    """
    if not text:
        return ""

    # ── Try Sarvam TTS first ──────────────────────────────
    if SARVAM_API_KEY:
        lang_code = SARVAM_LANG_MAP.get(language, "en-IN")
        try:
            response = requests.post(
                SARVAM_TTS_URL,
                headers={
                    "api-subscription-key": SARVAM_API_KEY,
                    "Content-Type": "application/json",
                },
                json={
                    "inputs": [text],
                    "target_language_code": lang_code,
                    "speaker": "meera",
                    "pitch": 0,
                    "pace": 1,
                    "loudness": 1,
                },
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                # Sarvam returns base64-encoded WAV audio in the response
                audio_b64 = data.get("audios", [None])[0]
                if audio_b64:
                    return "data:audio/wav;base64," + audio_b64
                else:
                    print("⚠️ Sarvam TTS: no audio in response")
            else:
                print(f"⚠️ Sarvam TTS error {response.status_code}: {response.text[:200]}")

        except Exception as e:
            print(f"⚠️ Sarvam TTS exception: {e}")

    # ── Fallback to gTTS ──────────────────────────────────
    print("ℹ️ Falling back to gTTS")
    lang_code = GTTS_LANG_MAP.get(language, "en")

    try:
        tts = gTTS(text=text, lang=lang_code, slow=False)
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        return "data:audio/mp3;base64," + base64.b64encode(audio_buffer.read()).decode("utf-8")
    except Exception as e:
        print(f"gTTS error: {e}")
        try:
            tts = gTTS(text=text, lang="en", slow=False)
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            return "data:audio/mp3;base64," + base64.b64encode(audio_buffer.read()).decode()
        except Exception:
            return ""


def _convert_to_wav(input_path: str, output_path: str) -> bool:
    """
    Use ffmpeg to convert browser audio (webm/ogg/opus) to 16kHz mono WAV.
    Returns True on success.
    This is the KEY FIX for Whisper — browsers record at 48kHz stereo Opus,
    Whisper internally expects 16kHz mono (it calls ffmpeg itself, but only
    when the file extension is recognised; .webm is sometimes mishandled).
    By pre-converting we guarantee the right format every time.
    """
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y",          # overwrite output
                "-i", input_path,        # input file (any format)
                "-ar", "16000",          # resample to 16kHz
                "-ac", "1",              # mono
                "-f", "wav",             # output format
                output_path,
            ],
            capture_output=True,
            timeout=15,
        )
        return result.returncode == 0
    except Exception as e:
        print(f"ffmpeg conversion error: {e}")
        return False


def transcribe_audio(audio_bytes: bytes, language: str = None) -> str:
    """
    Transcribe audio bytes using Whisper.
    Auto-detects language if not specified.
    Returns transcribed text string.

    FIX: converts webm→wav at 16kHz before calling Whisper so that
    transcription works correctly regardless of browser/device.
    """
    if not audio_bytes:
        return ""

    if whisper_model is None:
        # Whisper isn't installed/loaded — voice transcription is disabled,
        # but the rest of the app (typed chat, detection, TTS) keeps working.
        return ""

    tmp_input  = None
    tmp_wav    = None

    try:
        # Write raw browser audio to a temp file
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
            f.write(audio_bytes)
            tmp_input = f.name

        # Create a temp path for the converted WAV
        tmp_wav = tmp_input.replace(".webm", "_converted.wav")

        # FIX: convert to 16kHz mono WAV
        converted = _convert_to_wav(tmp_input, tmp_wav)
        transcribe_path = tmp_wav if converted else tmp_input

        options = {}
        if language and language in WHISPER_LANG_MAP:
            options["language"] = WHISPER_LANG_MAP[language]

        result = whisper_model.transcribe(transcribe_path, **options)
        return result.get("text", "").strip()

    except Exception as e:
        print(f"Transcription error: {e}")
        return ""

    finally:
        # FIX: always clean up temp files, even on error
        for path in [tmp_input, tmp_wav]:
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except Exception:
                    pass