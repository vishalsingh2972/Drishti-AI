"""
detect.py — YOLOv8n Object Detection
Loads fine-tuned Indian road model (or base model as fallback)

BUGS FIXED vs original:
  1. Translation key mismatch: INDIAN_ROAD_CLASSES used "tamil"/"hindi" but
     narrate.py / chat.py look up by language code "ta"/"hi". This caused
     ALL Tamil/Hindi translations to silently fall back to the raw label
     (English). Fixed: keys are now "ta" / "hi" consistently.
  2. Translation filter in run_detection() was filtering by
     ["tamil", "hindi", "ml", "kn", "te"] — so it was passing the wrong keys
     AND dropping "ta"/"hi" entries. Fixed to match the new key names.
  3. "traffic light" normalises to "traffic_light" after .replace(" ", "_"),
     but the dict had key "traffic light" (with a space) — so class_info was
     always {} for traffic lights. Fixed by using underscore key.
  4. Same issue for "stop sign" → "stop_sign".
"""

import cv2
import numpy as np
import base64
from ultralytics import YOLO
import os

# ─────────────────────────────────────────
# Load model once at startup (not per request)
# ─────────────────────────────────────────
MODEL_PATH = os.environ.get("YOLO_MODEL_PATH", "models/best.pt")
FALLBACK_PATH = "yolov8n.pt"  # auto-downloaded if not found

try:
    model = YOLO(MODEL_PATH)
    print(f"✅ Loaded fine-tuned model: {MODEL_PATH}")
except Exception:
    model = YOLO(FALLBACK_PATH)
    print(f"⚠️ Using base YOLOv8n (not fine-tuned)")

# ─────────────────────────────────────────
# Indian road priority classes
# Danger level: 3=high, 2=medium, 1=low
# Translation keys MUST match language codes: ta, hi, ml, kn, te
# ─────────────────────────────────────────
INDIAN_ROAD_CLASSES = {
    # Standard COCO classes (always available)
    # FIX: keys changed from "tamil"/"hindi" → "ta"/"hi"
    # FIX: "traffic light" / "stop sign" → "traffic_light" / "stop_sign"
    "person":           {"danger": 2, "ta": "நபர்",              "hi": "व्यक्ति",       "ml": "വ്യക്തി",           "kn": "ವ್ಯಕ್ತಿ",           "te": "వ్యక్తి"},
    "car":              {"danger": 3, "ta": "கார்",               "hi": "कार",           "ml": "കാർ",               "kn": "ಕಾರು",             "te": "కారు"},
    "truck":            {"danger": 3, "ta": "லாரி",              "hi": "ट्रक",           "ml": "ട്രക്ക്",           "kn": "ಟ್ರಕ್",            "te": "ట్రక్కు"},
    "bus":              {"danger": 3, "ta": "பேருந்து",           "hi": "बस",            "ml": "ബസ്",               "kn": "ಬಸ್",              "te": "బస్సు"},
    "motorcycle":       {"danger": 3, "ta": "மோட்டார் சைக்கிள்", "hi": "मोटरसाइकिल",    "ml": "മോട്ടോർസൈക്കിൾ",   "kn": "ಮೋಟಾರ್‌ಸೈಕಲ್",    "te": "మోటార్‌సైకిల్"},
    "bicycle":          {"danger": 2, "ta": "சைக்கிள்",          "hi": "साइकिल",        "ml": "സൈക്കിൾ",           "kn": "ಸೈಕಲ್",            "te": "సైకిల్"},
    "dog":              {"danger": 2, "ta": "நாய்",               "hi": "कुत्ता",        "ml": "നായ",               "kn": "ನಾಯಿ",             "te": "కుక్క"},
    "cow":              {"danger": 3, "ta": "பசு",                "hi": "गाय",           "ml": "പശു",               "kn": "ಹಸು",              "te": "ఆవు"},
    "chair":            {"danger": 1, "ta": "நாற்காலி",           "hi": "कुर्सी",        "ml": "കസേര",              "kn": "ಕುರ್ಚಿ",           "te": "కుర్చీ"},
    "bench":            {"danger": 1, "ta": "பெஞ்ச்",            "hi": "बेंच",           "ml": "ബെഞ്ച്",            "kn": "ಬೆಂಚ್",            "te": "బెంచ్"},
    # FIX: "traffic light" → "traffic_light" (label is lowercased + spaces→underscores)
    "traffic_light":    {"danger": 2, "ta": "சிக்னல்",           "hi": "ट्रैफिक लाइट",  "ml": "ട്രാഫിക് ലൈറ്റ്",  "kn": "ಟ್ರಾಫಿಕ್ ಲೈಟ್",   "te": "ట్రాఫిక్ లైట్"},
    # FIX: "stop sign" → "stop_sign"
    "stop_sign":        {"danger": 2, "ta": "நிறுத்த சின்னம்",  "hi": "स्टॉप साइन",    "ml": "സ്റ്റോപ്പ് ചിഹ്നം", "kn": "ನಿಲ್ಲಿಸಿ ಚಿಹ್ನೆ",  "te": "స్టాప్ సైన్"},

    # Custom Indian road classes (from fine-tuned model)
    "auto_rickshaw":    {"danger": 3, "ta": "ஆட்டோ ரிக்ஷா",     "hi": "ऑटो रिक्शा",    "ml": "ഓട്ടോ റിക്ഷ",       "kn": "ಆಟೋ ರಿಕ್ಷಾ",       "te": "ఆటో రిక్షా"},
    "cycle_rickshaw":   {"danger": 2, "ta": "சைக்கிள் ரிக்ஷா",  "hi": "साइकिल रिक्शा", "ml": "സൈക്കിൾ റിക്ഷ",    "kn": "ಸೈಕಲ್ ರಿಕ್ಷಾ",     "te": "సైకిల్ రిక్షా"},
    "pothole":          {"danger": 2, "ta": "குழி",               "hi": "गड्ढा",         "ml": "കുഴി",              "kn": "ಗುಂಡಿ",            "te": "గొయ్యి"},
    "speed_breaker":    {"danger": 1, "ta": "ஸ்பீட் பிரேக்கர்", "hi": "स्पीड ब्रेकर",  "ml": "സ്പീഡ് ബ്രേക്കർ",  "kn": "ಸ್ಪೀಡ್ ಬ್ರೇಕರ್",   "te": "స్పీడ్ బ్రేకర్"},
    "street_vendor":    {"danger": 1, "ta": "தெரு வியாபாரி",    "hi": "सड़क विक्रेता",  "ml": "തെരുവ് കച്ചവടക്കാരൻ", "kn": "ಬೀದಿ ವ್ಯಾಪಾರಿ", "te": "వీధి వ్యాపారి"},
    # Extra Indian road objects
    "cat":              {"danger": 1, "ta": "பூனை",               "hi": "बिल्ली",        "ml": "പൂച്ച",             "kn": "ಬೆಕ್ಕು",            "te": "పిల్లి"},
    "horse":            {"danger": 2, "ta": "குதிரை",             "hi": "घोड़ा",          "ml": "കുതിര",             "kn": "ಕುದುರೆ",            "te": "గుర్రం"},
    "sheep":            {"danger": 1, "ta": "ஆடு",                "hi": "भेड़",           "ml": "ആട്",               "kn": "ಕುರಿ",              "te": "గొర్రె"},
}

CONFIDENCE_THRESHOLD = 0.45
DANGER_NEAR_THRESHOLD = 0.6   # box height ratio — object fills >60% → near

# Language codes that narrate.py / chat.py use for translations
TRANSLATION_LANGS = {"ta", "hi", "ml", "kn", "te"}


def run_detection(image_bytes: bytes):
    """
    Input:  raw image bytes
    Output: list of detections + annotated frame as base64
    """
    # Decode image
    nparr = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if frame is None:
        return [], ""
    h, w = frame.shape[:2]

    results = model(frame, conf=CONFIDENCE_THRESHOLD, verbose=False)[0]

    detections = []
    for box in results.boxes:
        cls_id = int(box.cls[0])
        label = model.names[cls_id].lower().replace(" ", "_")
        conf = float(box.conf[0])
        x1, y1, x2, y2 = map(int, box.xyxy[0])

        # Determine horizontal position (LEFT / CENTER / RIGHT)
        cx = (x1 + x2) / 2
        if cx < w * 0.33:
            direction = "left"
        elif cx > w * 0.66:
            direction = "right"
        else:
            direction = "center"

        # Box size ratio for rough proximity
        box_ratio = (y2 - y1) / h

        class_info = INDIAN_ROAD_CLASSES.get(label, {"danger": 1})

        # FIX: filter by correct language codes (ta/hi/ml/kn/te)
        translations = {k: v for k, v in class_info.items() if k in TRANSLATION_LANGS}

        detections.append({
            "label": label,
            "confidence": round(conf, 2),
            "direction": direction,
            "box": [x1, y1, x2, y2],
            "box_ratio": round(box_ratio, 2),
            "danger_level": class_info.get("danger", 1),
            "translations": translations,
        })

    # Sort by danger level (highest first)
    detections.sort(key=lambda d: d["danger_level"], reverse=True)

    # Draw bounding boxes on frame
    annotated = results.plot()
    _, buffer = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 70])
    annotated_b64 = "data:image/jpeg;base64," + base64.b64encode(buffer).decode()

    return detections, annotated_b64
