"""Very small, modular i18n layer.

LANGUAGES is the full list shown in the language switcher. TRANSLATIONS
only has to contain a language once someone has actually translated its
strings — app.py's `t()` helper automatically falls back to English for
any language/key that isn't filled in yet, so adding a new language later
is just adding one more dict entry here, nothing else in the codebase
needs to change.
"""

LANGUAGES = [
    ("en", "English"),
    ("hi", "हिंदी"),
    ("mr", "मराठी"),
    ("ta", "தமிழ்"),
    ("te", "తెలుగు"),
    ("bn", "বাংলা"),
    ("gu", "ગુજરાતી"),
    ("pa", "ਪੰਜਾਬੀ"),
    ("kn", "ಕನ್ನಡ"),
    ("ml", "മലയാളം"),
]

TRANSLATIONS = {
    "en": {
        "site_name": "Kisan Route",
        "nav_farmer": "Farmer",
        "nav_cluster": "Farmer Cluster",
        "nav_customer": "Customer",
        "nav_driver": "Driver",
        "nav_wholesaler": "Wholesaler",
        "nav_about": "About",
        "menu_title": "Choose your role",
        "hero_tagline": "Connecting farmers, clusters, customers, drivers and wholesalers on one route to fair value.",
        "hero_cta": "Choose your role below to begin",
        "problem_title": "The problem we're solving",
        "problem_text": "Smallholder farmers often sell at low prices because of poor market access, unclear mandi rates, and expensive, uncoordinated transport. Kisan Route brings price transparency, shared logistics, and direct market access into one platform.",
        "chatbot_title": "Kisan Route Assistant",
        "chatbot_sub": "Ask about rates, orders, deliveries, or your dashboard.",
        "voice_title": "Voice Assistant",
        "voice_prompt_farmer": "Hi, I'm your Kisan Route voice assistant. Ask about mandi rates, profit, or your shipment.",
        "voice_prompt_cluster": "Hi, this is your cluster assistant. I can help you find farmers or split costs.",
        "voice_prompt_customer": "Hi, I can help you browse crops, place an order, or track delivery.",
        "voice_prompt_driver": "Hi, I can show nearby delivery requests and optimize your route.",
        "voice_prompt_wholesaler": "Hi, I can help you find farmer listings near your mandi.",
        "voice_prompt_default": "Welcome to Kisan Route. Choose your role from the menu to get started.",
    },
    "hi": {
        "site_name": "किसान रूट",
        "nav_farmer": "किसान",
        "nav_cluster": "किसान समूह",
        "nav_customer": "ग्राहक",
        "nav_driver": "चालक",
        "nav_wholesaler": "थोक व्यापारी",
        "nav_about": "हमारे बारे में",
        "menu_title": "अपनी भूमिका चुनें",
        "hero_tagline": "किसानों, समूहों, ग्राहकों, चालकों और थोक व्यापारियों को एक ही मंच पर जोड़ना।",
        "hero_cta": "शुरू करने के लिए नीचे अपनी भूमिका चुनें",
        "problem_title": "हम जिस समस्या को हल कर रहे हैं",
        "problem_text": "छोटे किसानों को अक्सर सीमित बाज़ार पहुंच, अस्पष्ट मंडी दरों और महंगे परिवहन के कारण कम कीमत पर फसल बेचनी पड़ती है। किसान रूट पारदर्शी दरें, साझा परिवहन और सीधी बाज़ार पहुंच एक ही मंच पर लाता है।",
        "chatbot_title": "किसान रूट सहायक",
        "chatbot_sub": "दरों, ऑर्डर, डिलीवरी या अपने डैशबोर्ड के बारे में पूछें।",
        "voice_title": "वॉइस सहायक",
        "voice_prompt_farmer": "नमस्ते, मैं आपका किसान रूट वॉइस सहायक हूं। मंडी दर, मुनाफ़ा या शिपमेंट के बारे में पूछें।",
        "voice_prompt_cluster": "नमस्ते, यह आपका समूह सहायक है। मैं किसान खोजने या लागत बांटने में मदद कर सकता हूं।",
        "voice_prompt_customer": "नमस्ते, मैं फसलें देखने, ऑर्डर करने या डिलीवरी ट्रैक करने में मदद कर सकता हूं।",
        "voice_prompt_driver": "नमस्ते, मैं आस-पास की डिलीवरी दिखा सकता हूं और आपका रूट अनुकूलित कर सकता हूं।",
        "voice_prompt_wholesaler": "नमस्ते, मैं आपकी मंडी के पास किसान लिस्टिंग खोजने में मदद कर सकता हूं।",
        "voice_prompt_default": "किसान रूट में आपका स्वागत है। शुरू करने के लिए मेनू से अपनी भूमिका चुनें।",
    },
}


def translate(lang: str, key: str) -> str:
    table = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    return table.get(key, TRANSLATIONS["en"].get(key, key))
