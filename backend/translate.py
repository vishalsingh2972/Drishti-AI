"""
translate.py — Sarvam AI Translation (Mayura) API
Translates English text to Indian languages using Sarvam's Mayura model.
Can be integrated into narration pipeline or used standalone.
"""

import os
import json
import requests

# ─────────────────────────────────────────
# Sarvam Translate (Mayura) configuration
# ─────────────────────────────────────────
SARVAM_API_KEY = os.environ.get("SARVAM_API_KEY", "").strip()
SARVAM_TRANSLATE_URL = "https://api.sarvam.ai/v1/translate"

# Supported target languages
# Source is always English (en-IN)
TRANSLATE_LANG_MAP = {
    "hi": "hi-IN",
    "ta": "ta-IN",
    "te": "te-IN",
    "kn": "kn-IN",
    "ml": "ml-IN",
    # English passthrough (no translation needed)
    "en": "en-IN",
}


def translate_text(text: str, target_language: str = "hi") -> str:
    """
    Translate English text to the target Indian language using Sarvam Mayura.
    
    Args:
        text: English text to translate
        target_language: Language code (hi, ta, te, kn, ml, en)
    
    Returns:
        Translated text string. Returns original text if:
        - target is English (passthrough)
        - SARVAM_API_KEY is not set
        - API call fails
    """
    if not text:
        return ""

    # English passthrough — no translation needed
    if target_language == "en":
        return text

    # If no API key, return original text (graceful degradation)
    if not SARVAM_API_KEY:
        print("⚠️ Sarvam Translate: SARVAM_API_KEY not set, returning original text")
        return text

    target_code = TRANSLATE_LANG_MAP.get(target_language)
    if not target_code:
        print(f"⚠️ Sarvam Translate: Unsupported language '{target_language}', returning original")
        return text

    try:
        response = requests.post(
            SARVAM_TRANSLATE_URL,
            headers={
                "api-subscription-key": SARVAM_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "input": text,
                "source_language_code": "en-IN",
                "target_language_code": target_code,
                "mode": "formal",  # formal/casual — formal works better for navigation
            },
            timeout=30,
        )

        if response.status_code == 200:
            data = response.json()
            translated = data.get("translated_text", "")
            if translated:
                return translated.strip()
            else:
                print("⚠️ Sarvam Translate: empty translation in response")
        else:
            print(f"⚠️ Sarvam Translate error {response.status_code}: {response.text[:200]}")

    except Exception as e:
        print(f"⚠️ Sarvam Translate exception: {e}")

    # Fallback: return original text
    return text