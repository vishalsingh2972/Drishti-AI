"""
chat.py — Conversational AI using Groq (free) + LLaMA 3
User asks questions about their live scene → AI answers in chosen language

BUGS FIXED vs original:
  1. _fallback_answer() looked up translations using language codes like "ta"/"hi",
     but the original detect.py stored them under "tamil"/"hindi". Now that detect.py
     is fixed to use "ta"/"hi" keys, this file's lookup is correct.
  2. near_str join separator was Arabic "، " — harmless for Arabic but looks odd in
     Tamil/Hindi. Changed to ", " (comma-space) which reads correctly in all supported
     languages.
  3. Added guard: if GROQ_API_KEY is an empty string (not just missing), still use
     fallback instead of crashing on Groq's auth check.
"""

import os
import json
from groq import Groq

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# System prompt — Indian road context
SYSTEM_PROMPT = """You are Drishti AI, a helpful navigation assistant for visually impaired people in India.
You receive the current scene context (detected objects and their positions/distances) and the user's question.
You must:
1. Answer in the SAME language the user asked in (Tamil/Hindi/English/Malayalam/Kannada/Telugu)
2. Be concise — max 2 sentences
3. Focus on safety and navigation
4. Use the scene context to give specific, accurate answers
5. If asked about safety, always prioritize caution
6. You understand Indian roads — auto-rickshaws, stray animals, potholes, crowds

Scene context will be provided as JSON with: objects detected, their directions (left/center/right), and distance zones (near/medium/far).
"""


def build_scene_summary(scene_context: dict) -> str:
    """Convert scene JSON to readable text for the AI prompt"""
    if not scene_context:
        return "No objects detected currently."

    detections  = scene_context.get("detections", [])
    depth_zones = scene_context.get("depth_zones", [])

    if not detections:
        return "The path appears clear with no detected obstacles."

    lines = []
    for det in detections[:8]:
        label     = det.get("label", "unknown")
        direction = det.get("direction", "center")
        danger    = det.get("danger_level", 1)

        zone_info = next(
            (z for z in depth_zones if z.get("label") == label),
            {"depth_zone": "unknown"},
        )
        zone = zone_info.get("depth_zone", "unknown")
        lines.append(f"- {label}: {direction} side, {zone} distance, danger level {danger}/3")

    person_count = sum(1 for d in detections if d.get("label") == "person")
    if person_count >= 5:
        lines.append(f"- CROWD: {person_count} people detected ahead")

    return "Current scene:\n" + "\n".join(lines)


def ask_groq(question: str, scene_context: dict, language: str = "en") -> str:
    """
    Send user question + scene context to Groq LLaMA 3.
    Returns answer text in the user's language.
    Falls back to rule-based answer if no Groq key is configured.
    """
    if not client:
        return _fallback_answer(question, scene_context, language)

    scene_summary = build_scene_summary(scene_context)

    user_message = (
        f"Current scene information:\n{scene_summary}\n\n"
        f"User question: {question}\n\n"
        "Please answer in the same language as the question. Be brief and focused on safety."
    )

    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_message},
            ],
            max_tokens=150,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"Groq API error: {e}")
        return _fallback_answer(question, scene_context, language)


def _fallback_answer(question: str, scene_context: dict, language: str) -> str:
    """Simple rule-based fallback if Groq is unavailable"""
    detections  = scene_context.get("detections", [])
    depth_zones = scene_context.get("depth_zones", [])

    near_zones = [z for z in depth_zones if z.get("depth_zone") == "near"]

    # FIX: translations are keyed by language code (ta/hi/ml/kn/te) after detect.py fix
    def translated_label(label: str) -> str:
        det = next((d for d in detections if d["label"] == label), None)
        if det and language in det.get("translations", {}):
            return det["translations"][language]
        return label.replace("_", " ")

    near_names = [translated_label(z["label"]) for z in near_zones]
    count      = len(detections)
    # FIX: use plain ", " separator (works in all 6 languages)
    near_str   = ", ".join(near_names) if near_names else ""

    fallbacks = {
        "en": (
            f"Caution! {near_str} very close to you. Be careful." if near_names
            else f"I can see {count} object(s). Path seems clear."
        ),
        "ta": (
            f"கவனம்! {near_str} மிக அருகில் உள்ளது. கவனமாக இருங்கள்." if near_names
            else f"நான் {count} பொருட்களை பார்க்கிறேன். பாதை தெளிவாக உள்ளது."
        ),
        "hi": (
            f"सावधान! {near_str} बहुत करीब है। सावधान रहें।" if near_names
            else f"मैं {count} वस्तुएं देख रहा हूं। रास्ता साफ लग रहा है।"
        ),
        "ml": (
            f"ശ്രദ്ധ! {near_str} വളരെ അടുത്താണ്. ശ്രദ്ധിക്കുക." if near_names
            else f"ഞാൻ {count} വസ്തുക്കൾ കാണുന്നു. വഴി തെളിഞ്ഞതാണ്."
        ),
        "kn": (
            f"ಎಚ್ಚರಿಕೆ! {near_str} ತುಂಬಾ ಹತ್ತಿರದಲ್ಲಿದೆ. ಎಚ್ಚರಿಕೆಯಿಂದಿರಿ." if near_names
            else f"ನಾನು {count} ವಸ್ತುಗಳನ್ನು ನೋಡುತ್ತಿದ್ದೇನೆ. ದಾರಿ ಸ್ಪಷ್ಟವಾಗಿದೆ."
        ),
        "te": (
            f"జాగ్రత్త! {near_str} చాలా దగ్గరలో ఉంది. జాగ్రత్తగా ఉండండి." if near_names
            else f"నేను {count} వస్తువులు చూస్తున్నాను. దారి స్పష్టంగా ఉంది."
        ),
    }
    return fallbacks.get(language, fallbacks["en"])
