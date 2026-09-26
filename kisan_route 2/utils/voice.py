"""Intelligent Voice Assistant Module for KisanRoute.

Provides multilingual natural speech processing, intent & navigation detection,
accurate AI agricultural Q&A, and speech-ready text formatting.
"""

import re
from typing import Dict, Any, Optional
from utils.chatbot import get_response, try_external_ai, detect_crop, detect_location


# Action / Navigation Route Mappings
NAV_INTENTS = [
    # Farmer Dashboard
    {
        "keywords": [
            "farmer dashboard", "kisan dashboard", "open farmer", "farmer portal", 
            "kisan portal", "kisan page", "farmer login", "farmer account",
            "किसान डैशबोर्ड", "किसान पोर्टल", "किसान लॉगिन"
        ],
        "url": "/farmer/dashboard",
        "label": "Farmer Dashboard",
        "reply_hi": "जी, किसान डैशबोर्ड खोला जा रहा है।",
        "reply_en": "Opening the Farmer Dashboard now."
    },
    # Driver Dashboard
    {
        "keywords": [
            "driver dashboard", "driver portal", "driver login", "open driver", 
            "transport portal", "gadi portal", "truck portal", "logistics portal",
            "चालक डैशबोर्ड", "ड्राइवर पोर्टल", "ड्राइवर डैशबोर्ड", "ड्राइवर लॉगिन"
        ],
        "url": "/driver/dashboard",
        "label": "Driver & Logistics Dashboard",
        "reply_hi": "जी, ड्राइवर व ट्रांसपोर्ट डैशबोर्ड खोला जा रहा है।",
        "reply_en": "Opening the Driver and Transport Dashboard now."
    },
    # Customer Store
    {
        "keywords": [
            "customer store", "customer dashboard", "open customer", "buy crop", 
            "customer portal", "online order", "grahak portal", "grahak dashboard",
            "ग्राहक स्टोर", "ग्राहक डैशबोर्ड", "ग्राहक पोर्टल", "फसल खरीद"
        ],
        "url": "/customer/dashboard",
        "label": "Customer Store",
        "reply_hi": "जी, ग्राहक स्टोर खोला जा रहा है जहाँ से आप ताज़ा फसल सीधे खरीद सकते हैं।",
        "reply_en": "Opening the Customer Store now."
    },
    # Cluster Hub
    {
        "keywords": [
            "cluster hub", "cluster dashboard", "open cluster", "kisan samuh", 
            "samooh hub", "pooling hub", "क्लस्टर हब", "क्लस्टर डैशबोर्ड", "किसान समूह"
        ],
        "url": "/cluster/dashboard",
        "label": "Cluster Aggregation Hub",
        "reply_hi": "जी, किसान क्लस्टर हब खोला जा रहा है।",
        "reply_en": "Opening the Cluster Aggregation Hub now."
    },
    # Wholesaler Portal
    {
        "keywords": [
            "wholesaler portal", "wholesaler dashboard", "open wholesaler", "mandi vyapari", 
            "thok vyapari", "trader portal", "vyapari portal", "थोक व्यापारी", "व्यापारी पोर्टल"
        ],
        "url": "/wholesaler/dashboard",
        "label": "Wholesaler Trading Portal",
        "reply_hi": "जी, थोक व्यापारी ट्रेडिंग पोर्टल खोला जा रहा है।",
        "reply_en": "Opening the Wholesaler Trading Portal now."
    },
    # Mandi Rates
    {
        "keywords": [
            "mandi rate page", "mandi rates page", "show mandi rates", "mandi rate dikhao", 
            "mandi bhav dikhao", "mandi portal", "rate comparison", "compare mandi",
            "मंडी भाव पेज", "मंडी रेट पेज", "मंडी भाव दिखाओ", "मंडी दर"
        ],
        "url": "/farmer/mandi-rates",
        "label": "Mandi Rates Detector",
        "reply_hi": "जी, लाइव मंडी भाव तुलना पेज खोला जा रहा है।",
        "reply_en": "Opening live Mandi Rates comparison now."
    },
    # Profit Calculator
    {
        "keywords": [
            "profit calculator", "munafa calculator", "net profit", "kamai calculator", 
            "hisab calculator", "calculator kholo", "calculate profit", "मुनाफा कैलकुलेटर"
        ],
        "url": "/farmer/profit-calculator",
        "label": "Net Profit Calculator",
        "reply_hi": "जी, नेट मुनाफा कैलकुलेटर खोला जा रहा है।",
        "reply_en": "Opening Net Profit Calculator now."
    },
    # Crop Quality Checker
    {
        "keywords": [
            "crop quality", "quality check", "photo check", "grade check", 
            "fasal janch", "fasal ki photo", "fasal quality", "गुणवत्ता जांच", "क्वालिटी चेक"
        ],
        "url": "/farmer/crop-quality",
        "label": "Crop Quality Check",
        "reply_hi": "जी, क्रॉप क्वालिटी जांच पेज खोला जा रहा है। यहाँ आप अपनी फसल की फोटो अपलोड कर सकते हैं।",
        "reply_en": "Opening Crop Quality Check. You can upload your crop photo for grading."
    },
    # Shipment Tracking
    {
        "keywords": [
            "tracking", "track", "shipment", "track order", "track shipment", "kahan pahuncha", 
            "shipment status", "order status", "live tracking", "ट्रैकिंग", "लाइव ट्रैकिंग", "गाड़ी कहां पहुंची"
        ],
        "url": "/farmer/tracking",
        "label": "Live Shipment Tracking",
        "reply_hi": "जी, लाइव शिपमेंट ट्रैकिंग खोली जा रही है।",
        "reply_en": "Opening live shipment tracking now."
    },
    # Government Schemes
    {
        "keywords": [
            "sarkari yojana", "govt schemes", "pm kisan", "kcc yojana", 
            "schemes page", "subsidy page", "सरकारी योजना", "योजनाएं"
        ],
        "url": "/farmer/schemes",
        "label": "Government Schemes",
        "reply_hi": "जी, सरकारी कृषि योजनाओं का पेज खोला जा रहा है।",
        "reply_en": "Opening Government Agricultural Schemes now."
    },
    # Crop Insurance
    {
        "keywords": [
            "insurance page", "bima page", "fasal bima", "crop protection", 
            "weather protection", "transit protect", "फसल बीमा", "बीमा"
        ],
        "url": "/farmer/insurance",
        "label": "Crop Protection & Insurance",
        "reply_hi": "जी, फसल बीमा व सुरक्षा पेज खोला जा रहा है।",
        "reply_en": "Opening Crop Protection and Insurance plans now."
    },
    # Home Page
    {
        "keywords": [
            "home page", "go to home", "open home", "main page", 
            "home jao", "mukhya prishth", "होम पेज", "होम पर जाओ"
        ],
        "url": "/",
        "label": "Home Page",
        "reply_hi": "जी, मुख्य पृष्ठ (होम पेज) पर ले जा रहा हूँ।",
        "reply_en": "Navigating to the home page now."
    },
    # About KisanRoute
    {
        "keywords": [
            "about page", "open about", "about kisan route", "about kisanroute", 
            "about section", "कंपनी के बारे में", "हमारे बारे में"
        ],
        "url": "/about",
        "label": "About KisanRoute",
        "reply_hi": "जी, KisanRoute के बारे में जानकारी का पेज खोला जा रहा है।",
        "reply_en": "Opening About KisanRoute page now."
    }
]


def is_devanagari(text: str) -> bool:
    """Check if the text contains Devanagari characters."""
    return bool(re.search(r'[\u0900-\u097F]', text))


def detect_query_language(text: str, default_lang: str = "hi-IN") -> str:
    """Detect whether query is primarily Hindi/Hinglish or English."""
    cleaned = (text or "").strip().lower()
    if is_devanagari(cleaned):
        return "hi-IN"

    # Common English phrasing patterns
    if re.search(r'\b(what|how|where|when|who|why|which|show|tell|open|can you|help me|explain|hello|hi|thanks|thank)\b', cleaned):
        return "en-IN"

    hindi_markers = [
        "kya", "kaise", "batao", "bataiye", "kholo", "bhav", "bhaav", "daam", "gehun",
        "tamatar", "aloo", "pyaz", "fasal", "mandi", "namaste", "dhanyawad",
        "shukriya", "pani", "dawa", "dawai", "chahiye", "hai", "hain", "karo", "dikhao",
        "madad", "kitna", "kahan", "samuh", "vyapari", "kiraya", "gadi", "gaadi"
    ]
    if any(re.search(r'\b' + re.escape(w) + r'\b', cleaned) for w in hindi_markers):
        return "hi-IN"

    # Check if predominantly english words
    english_markers = [
        "price", "rate", "weather", "wheat", "rice", "tomato", "potato", "driver", "farmer", "customer",
        "cluster", "wholesaler", "tracking", "status", "dashboard"
    ]
    if any(re.search(r'\b' + re.escape(w) + r'\b', cleaned) for w in english_markers):
        return "en-IN"

    return default_lang or "hi-IN"


def clean_text_for_speech(raw_text: str) -> str:
    """Format raw markdown / URLs / bullets into clear, natural spoken text."""
    if not raw_text:
        return ""
    text = raw_text

    # Remove URLs like https://...
    text = re.sub(r'https?://\S+', '', text)
    # Remove markdown bold/italics
    text = re.sub(r'[*_~`#]', '', text)
    # Convert bullet points to pauses
    text = re.sub(r'^[•\-\*]\s+', '', text, flags=re.MULTILINE)
    # Remove excessive symbols
    text = re.sub(r'[|✦►→•👉📞🎥📜💡🌾🚚🛒🤝🏬💰📍🛡️⚡🌱🍅🥔🍚]', ' ', text)
    # Replace rupees symbol with spoken word
    text = text.replace('₹', 'रुपये ')
    # Replace slashes in units
    text = text.replace('/ kg', ' प्रति किलो ').replace('/ qtl', ' प्रति क्विंटल ').replace('/ Qtl', ' प्रति क्विंटल ')
    text = text.replace('kg', 'किलो').replace('Qtl', 'क्विंटल')
    # Remove trailing dangling phrases like 'ऐप का पूरा वर्किंग डेमो वीडियो:' or 'देखें:'
    text = re.sub(r'(ऐप का पूरा वर्किंग डेमो वीडियो:?|डेमो वीडियो:?|अधिक जानकारी के लिए देखें:?|देखें:?)\s*$', '', text).strip()
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def process_voice_query(query: str, lang_hint: Optional[str] = None, role: Optional[str] = None) -> Dict[str, Any]:
    """Main voice assistant processor.

    Returns dict with:
        reply: Speech-ready natural language response
        raw_reply: Formatted text for caption display
        lang: Target BCP-47 language tag ('hi-IN' or 'en-IN')
        action: Navigation action or None
    """
    raw_query = (query or "").strip()
    if not raw_query:
        lang = lang_hint or "hi-IN"
        if lang.startswith("en"):
            return {
                "reply": "I'm listening. You can ask me about mandi rates, weather, crop diseases, or ask me to open any dashboard.",
                "spoken_reply": "I am listening. Ask about mandi rates, weather, or dashboards.",
                "raw_reply": "🎙️ I'm listening. Ask about mandi rates, weather, or dashboards.",
                "lang": "en-IN",
                "action": None
            }
        return {
            "reply": "मैं सुन रहा हूँ। आप मुझसे मंडी भाव, मौसम, फसल रोग या कोई भी डैशबोर्ड खोलने के लिए कह सकते हैं।",
            "spoken_reply": "मैं सुन रहा हूँ। आप मुझसे मंडी भाव, मौसम, या डैशबोर्ड खोलने के लिए कह सकते हैं।",
            "raw_reply": "🎙️ मैं सुन रहा हूँ। मंडी भाव, मौसम या डैशबोर्ड के बारे में पूछें।",
            "lang": "hi-IN",
            "action": None
        }

    lower_query = raw_query.lower()
    detected_lang = detect_query_language(raw_query, lang_hint or "hi-IN")
    is_hindi = detected_lang.startswith("hi")

    # 1. Check for Navigation / Action Commands
    for nav in NAV_INTENTS:
        if any(k in lower_query for k in nav["keywords"]):
            speech_confirmation = nav["reply_hi"] if is_hindi else nav["reply_en"]
            return {
                "reply": speech_confirmation,
                "spoken_reply": speech_confirmation,
                "raw_reply": speech_confirmation,
                "lang": detected_lang,
                "action": {
                    "type": "navigate",
                    "url": nav["url"],
                    "label": nav["label"]
                }
            }

    # 2. Check for Role-Specific Quick Navigation: "open dashboard"
    if any(k in lower_query for k in ["dashboard", "डैशबोर्ड", "portal", "पोर्टल", "kholo", "open"]):
        user_role = role or "farmer"
        target_url = f"/{user_role}/dashboard"
        reply = f"जी, {user_role.capitalize()} डैशबोर्ड खोला जा रहा है।" if is_hindi else f"Opening {user_role.capitalize()} dashboard now."
        return {
            "reply": reply,
            "spoken_reply": reply,
            "raw_reply": reply,
            "lang": detected_lang,
            "action": {
                "type": "navigate",
                "url": target_url,
                "label": f"{user_role.capitalize()} Dashboard"
            }
        }

    # 3. Retrieve intelligent response from KisanRoute AI / Chatbot Knowledge Base
    raw_response = get_response(raw_query)

    # 3. Handle Curated English Responses if English query detected
    if not is_hindi:
        english_faq = {
            "what is kisan route": "KisanRoute is a digital platform connecting farmers directly to mandis, buyers, and transport with zero middlemen, ensuring fair prices for every farmer.",
            "what is kisanroute": "KisanRoute is a direct farm-to-market platform connecting farmers directly to mandis, buyers, and transport with zero middlemen.",
            "who are you": "I am your KisanRoute Voice Assistant. Ask me about live mandi rates, weather, crop diseases, or ask me to open any dashboard.",
            "what can you do": "I can answer questions about mandi rates, weather forecasts, crop disease remedies, and open any dashboard on KisanRoute for you.",
            "how does this work": "You can talk to me in Hindi or English. Ask for crop rates, weather, or say commands like 'open driver dashboard' or 'check tracking'.",
            "how to use": "Simply speak to me in Hindi or English. You can ask for crop prices, weather forecasts, or ask me to open any portal.",
            "helpline": "KisanRoute helpline is available toll-free at 1800-123-4567 from 8 AM to 8 PM, or via WhatsApp at +91 98765-43210.",
            "customer care": "You can reach customer support at 1800-123-4567 or via email at support@kisanapp.com.",
            "demo login": "You can use 1-Click Demo login on any role page with mobile number 9876543210 and password 123456.",
            "hello": "Hello! I am your KisanRoute Voice Assistant. How can I help you today?",
            "hi": "Hi there! I am your KisanRoute Assistant. You can ask me about mandi rates, weather, or ask me to open any dashboard.",
            "thank you": "You're very welcome! Let me know if you need anything else on KisanRoute.",
            "thanks": "You're welcome! Happy farming and fair trading with KisanRoute!"
        }
        for k, v in english_faq.items():
            if k in lower_query:
                return {
                    "reply": v,
                    "spoken_reply": v,
                    "raw_reply": v,
                    "lang": "en-IN",
                    "action": None
                }

        # Check if external AI can answer directly in English
        ai_resp = try_external_ai(f"Answer concisely in English in 2 sentences for a farmer using KisanRoute: {raw_query}")
        if ai_resp:
            speech_text = clean_text_for_speech(ai_resp)
            return {
                "reply": speech_text,
                "spoken_reply": speech_text,
                "raw_reply": ai_resp,
                "lang": "en-IN",
                "action": None
            }

    # Format speech-friendly spoken text
    spoken_text = clean_text_for_speech(raw_response)

    # Shorten overly verbose lists for speech (keep first 2-3 key sentences)
    sentences = re.split(r'(?<=[.!?।])\s+', spoken_text)
    if len(sentences) > 4:
        spoken_text = " ".join(sentences[:3])

    # Check if a relevant contextual action should be attached
    action = None
    if any(w in lower_query for w in ["mandi", "rate", "bhav", "price", "daam", "भाव", "मंडी"]):
        action = {"type": "navigate", "url": "/farmer/mandi-rates", "label": "Mandi Rates"}
    elif any(w in lower_query for w in ["weather", "mausam", "barish", "मौसम", "बारिश"]):
        action = {"type": "scroll", "target": "#weatherWidget", "label": "Live Weather"}
    elif any(w in lower_query for w in ["rog", "disease", "ilaj", "keeda", "दवा", "रोग"]):
        action = {"type": "navigate", "url": "/farmer/crop-quality", "label": "Crop Health Check"}

    return {
        "reply": spoken_text,
        "spoken_reply": spoken_text,
        "raw_reply": raw_response,
        "lang": detected_lang,
        "action": action
    }
