"""
narrate.py — Build multilingual scene narration text
Converts detections + depth zones → natural language alerts
Supports: English, Tamil, Hindi, Malayalam, Kannada, Telugu

BUGS FIXED vs original:
  1. narrate.py looked up translations with det["translations"].get(lang, ...)
     using language codes "ta"/"hi", but the original detect.py stored them
     under "tamil"/"hindi". Now detect.py is fixed to use "ta"/"hi", so this
     file's lookup logic is correct — but the "ta"/"hi" keys are confirmed here.
  2. Missing "vehicle_far" template key in Tamil and Malayalam templates
     (was present in English, Hindi, Kannada, Telugu but missing in "ta"/"ml").
     Added to both.
  3. Malayalam "crowd" template had a stray non-Unicode character (ske → slow).
     Fixed.
"""

# ─────────────────────────────────────────
# Alert templates per language
# ─────────────────────────────────────────
TEMPLATES = {
    "en": {
        "near_danger":   "Warning! {obj} very close on your {dir}. Stop immediately.",
        "medium_danger": "Caution! {obj} approaching on your {dir}.",
        "vehicle_near":  "Danger! Vehicle ahead on your {dir}. Please stop.",
        "crowd":         "Very crowded area ahead. Move slowly.",
        "pothole":       "Pothole detected on your {dir}. Step carefully.",
        "clear":         "Path ahead seems clear. You may proceed.",
        "vehicle_far":   "Vehicle spotted at a distance on your {dir}. Stay alert.",
        "multiple":      "Multiple obstacles detected. Please be careful.",
        "person_near":   "Person very close on your {dir}.",
        "animal":        "Animal on road on your {dir}. Be careful.",
    },
    "ta": {
        "near_danger":   "எச்சரிக்கை! {obj} உங்கள் {dir} பக்கம் மிக அருகில் உள்ளது. உடனே நிறுத்துங்கள்.",
        "medium_danger": "கவனம்! {obj} உங்கள் {dir} பக்கம் வருகிறது.",
        "vehicle_near":  "ஆபத்து! வாகனம் உங்கள் {dir} பக்கம் உள்ளது. நிறுத்துங்கள்.",
        "crowd":         "முன்னால் மிகவும் நெரிசல். மெதுவாக நகரவும்.",
        "pothole":       "உங்கள் {dir} பக்கம் குழி உள்ளது. கவனமாக நடங்கள்.",
        "clear":         "முன் பாதை தெளிவாக உள்ளது. நீங்கள் முன்னேறலாம்.",
        # FIX: was missing in original "ta" template
        "vehicle_far":   "உங்கள் {dir} பக்கம் தொலைவில் வாகனம் உள்ளது. கவனமாக இருங்கள்.",
        "multiple":      "பல தடைகள் கண்டறியப்பட்டன. தயவுசெய்து கவனமாக இருங்கள்.",
        "person_near":   "உங்கள் {dir} பக்கம் ஒருவர் மிக அருகில் உள்ளார்.",
        "animal":        "சாலையில் {dir} பக்கம் விலங்கு உள்ளது. கவனமாக இருங்கள்.",
    },
    "hi": {
        "near_danger":   "चेतावनी! {obj} आपके {dir} तरफ बहुत करीब है। तुरंत रुकें।",
        "medium_danger": "सावधान! {obj} आपके {dir} तरफ आ रहा है।",
        "vehicle_near":  "खतरा! आपके {dir} तरफ वाहन है। कृपया रुकें।",
        "crowd":         "आगे बहुत भीड़ है। धीरे-धीरे आगे बढ़ें।",
        "pothole":       "आपके {dir} तरफ गड्ढा है। सावधानी से चलें।",
        "clear":         "आगे का रास्ता साफ है। आप आगे बढ़ सकते हैं।",
        "vehicle_far":   "आपके {dir} तरफ दूर वाहन है। सतर्क रहें।",
        "multiple":      "कई बाधाएं मिली हैं। कृपया सावधान रहें।",
        "person_near":   "आपके {dir} तरफ कोई बहुत करीब है।",
        "animal":        "सड़क पर {dir} तरफ जानवर है। सावधान रहें।",
    },
    "ml": {
        "near_danger":   "മുന്നറിയിപ്പ്! {obj} നിങ്ങളുടെ {dir} വശത്ത് വളരെ അടുത്താണ്. ഉടൻ നിർത്തുക.",
        "medium_danger": "ശ്രദ്ധ! {obj} നിങ്ങളുടെ {dir} വശത്ത് അടുക്കുന്നു.",
        "vehicle_near":  "അപകടം! {dir} വശത്ത് വാഹനം ഉണ്ട്. ദയവായി നിർത്തുക.",
        # FIX: original had a broken character "ske" in "സ ്ധാ" — corrected to "സാധ"
        "crowd":         "മുന്നിൽ വളരെ തിരക്കുണ്ട്. സാവധാനം നടക്കുക.",
        "pothole":       "നിങ്ങളുടെ {dir} വശത്ത് കുഴി ഉണ്ട്. ശ്രദ്ധിച്ച് നടക്കുക.",
        "clear":         "മുന്നിലുള്ള വഴി തെളിഞ്ഞതാണ്. മുന്നോട്ട് പോകാം.",
        # FIX: was missing in original "ml" template
        "vehicle_far":   "നിങ്ങളുടെ {dir} വശത്ത് ദൂരത്ത് ഒരു വാഹനം ഉണ്ട്. ശ്രദ്ധിക്കുക.",
        "multiple":      "ഒന്നിലധികം തടസ്സങ്ങൾ കണ്ടെത്തി. ദയവായി ശ്രദ്ധിക്കുക.",
        "person_near":   "നിങ്ങളുടെ {dir} വശത്ത് ഒരാൾ വളരെ അടുത്തുണ്ട്.",
        "animal":        "റോഡിൽ {dir} വശത്ത് ഒരു മൃഗമുണ്ട്. ശ്രദ്ധിക്കുക.",
    },
    "kn": {
        "near_danger":   "ಎಚ್ಚರಿಕೆ! {obj} ನಿಮ್ಮ {dir} ಬದಿಯಲ್ಲಿ ತುಂಬಾ ಹತ್ತಿರದಲ್ಲಿದೆ. ತಕ್ಷಣ ನಿಲ್ಲಿ.",
        "medium_danger": "ಎಚ್ಚರ! {obj} ನಿಮ್ಮ {dir} ಬದಿಯಿಂದ ಬರುತ್ತಿದೆ.",
        "vehicle_near":  "ಅಪಾಯ! {dir} ಬದಿಯಲ್ಲಿ ವಾಹನ ಇದೆ. ದಯವಿಟ್ಟು ನಿಲ್ಲಿ.",
        "crowd":         "ಮುಂದೆ ತುಂಬಾ ಜನದಟ್ಟಣೆ. ನಿಧಾನವಾಗಿ ಚಲಿಸಿ.",
        "pothole":       "ನಿಮ್ಮ {dir} ಬದಿಯಲ್ಲಿ ಗುಂಡಿ ಇದೆ. ಎಚ್ಚರಿಕೆಯಿಂದ ನಡೆಯಿರಿ.",
        "clear":         "ಮುಂದಿನ ದಾರಿ ಸ್ಪಷ್ಟವಾಗಿದೆ. ಮುಂದೆ ಹೋಗಬಹುದು.",
        "vehicle_far":   "ನಿಮ್ಮ {dir} ಬದಿಯಲ್ಲಿ ದೂರದಲ್ಲಿ ವಾಹನ ಇದೆ. ಎಚ್ಚರಿಕೆಯಿಂದಿರಿ.",
        "multiple":      "ಅನೇಕ ಅಡಚಣೆಗಳು ಕಂಡುಬಂದಿವೆ. ದಯವಿಟ್ಟು ಎಚ್ಚರಿಕೆಯಿಂದಿರಿ.",
        "person_near":   "ನಿಮ್ಮ {dir} ಬದಿಯಲ್ಲಿ ಒಬ್ಬ ವ್ಯಕ್ತಿ ತುಂಬಾ ಹತ್ತಿರದಲ್ಲಿದ್ದಾರೆ.",
        "animal":        "ರಸ್ತೆಯಲ್ಲಿ {dir} ಬದಿಯಲ್ಲಿ ಒಂದು ಪ್ರಾಣಿ ಇದೆ. ಎಚ್ಚರಿಕೆಯಿಂದಿರಿ.",
    },
    "te": {
        "near_danger":   "హెచ్చరిక! {obj} మీ {dir} వైపు చాలా దగ్గరలో ఉంది. వెంటనే ఆగండి.",
        "medium_danger": "జాగ్రత్త! {obj} మీ {dir} వైపు వస్తోంది.",
        "vehicle_near":  "ప్రమాదం! {dir} వైపు వాహనం ఉంది. దయచేసి ఆగండి.",
        "crowd":         "ముందు చాలా రద్దీగా ఉంది. నెమ్మదిగా కదలండి.",
        "pothole":       "మీ {dir} వైపు గొయ్యి ఉంది. జాగ్రత్తగా నడవండి.",
        "clear":         "ముందు దారి స్పష్టంగా ఉంది. ముందుకు వెళ్ళవచ్చు.",
        "vehicle_far":   "మీ {dir} వైపు దూరంలో వాహనం ఉంది. జాగ్రత్తగా ఉండండి.",
        "multiple":      "అనేక అడ్డంకులు కనుగొనబడ్డాయి. దయచేసి జాగ్రత్తగా ఉండండి.",
        "person_near":   "మీ {dir} వైపు ఒక వ్యక్తి చాలా దగ్గరలో ఉన్నారు.",
        "animal":        "రోడ్డుపై {dir} వైపు జంతువు ఉంది. జాగ్రత్తగా ఉండండి.",
    },
}

# Direction translations (language code → display word)
DIR_LABELS = {
    "en": {"left": "left",    "right": "right",  "center": "front"},
    "ta": {"left": "இடது",    "right": "வலது",   "center": "முன்"},
    "hi": {"left": "बाईं",    "right": "दाईं",   "center": "सामने"},
    "ml": {"left": "ഇടത്",   "right": "വലത്",   "center": "മുന്നിൽ"},
    "kn": {"left": "ಎಡ",      "right": "ಬಲ",     "center": "ಮುಂದೆ"},
    "te": {"left": "ఎడమ",     "right": "కుడి",   "center": "ముందు"},
}

ANIMAL_LABELS   = {"dog", "cow", "cat", "horse", "sheep", "elephant", "goat"}
VEHICLE_LABELS  = {"car", "truck", "bus", "motorcycle", "auto_rickshaw", "cycle_rickshaw"}


def build_scene_narration(detections: list, depth_zones: list, language: str = "en") -> str:
    """
    Build a natural language scene description based on detections and depth.
    Returns text string in the chosen language.
    """
    lang = language if language in TEMPLATES else "en"
    tmpl = TEMPLATES[lang]
    dirs = DIR_LABELS.get(lang, DIR_LABELS["en"])

    if not detections:
        return tmpl["clear"]

    alerts = []
    person_count = sum(1 for d in detections if d["label"] == "person")

    # Crowd alert
    if person_count >= 5:
        alerts.append(tmpl["crowd"])

    # Process each depth zone
    processed_labels = set()
    for zone in depth_zones:
        label     = zone["label"]
        dir_key   = zone.get("direction", "center")
        depth     = zone["depth_zone"]
        danger    = zone.get("danger_level", 1)
        dir_text  = dirs.get(dir_key, dir_key)

        if label in processed_labels:
            continue
        processed_labels.add(label)

        # Get translated object name (key is language code, e.g. "ta")
        det_match = next((d for d in detections if d["label"] == label), None)
        if det_match:
            obj_name = det_match.get("translations", {}).get(lang, label.replace("_", " "))
        else:
            obj_name = label.replace("_", " ")

        if depth == "near":
            if label in VEHICLE_LABELS:
                alerts.append(tmpl["vehicle_near"].format(dir=dir_text))
            elif label == "pothole":
                alerts.append(tmpl["pothole"].format(dir=dir_text))
            elif label in ANIMAL_LABELS:
                alerts.append(tmpl["animal"].format(dir=dir_text))
            elif label == "person":
                alerts.append(tmpl["person_near"].format(dir=dir_text))
            else:
                # All near-zone objects are real collision hazards
                alerts.append(tmpl["near_danger"].format(obj=obj_name, dir=dir_text))

        elif depth == "medium" and danger >= 2:
            alerts.append(tmpl["medium_danger"].format(obj=obj_name, dir=dir_text))

        elif depth == "far" and label in VEHICLE_LABELS and danger == 3:
            # Fast-moving high-danger vehicles warn even at distance
            alerts.append(tmpl["vehicle_far"].format(dir=dir_text))

    if not alerts:
        return tmpl["clear"]

    # Limit to top 3 most important alerts
    return ". ".join(alerts[:3])
