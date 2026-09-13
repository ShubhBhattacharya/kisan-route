"""Mock AI chatbot logic.

Real intent-detection / LLM integration can replace `get_response` later.
The Flask API in blueprints/main.py exposes this over /api/chatbot/*, and
static/js/main.js calls that API — so the chatbot widget is genuinely
served by Python, not hardcoded in the browser.
"""

ROLE_PROMPTS = {
    "farmer": [
        "Check today's mandi rates",
        "Calculate my net profit",
        "Track my shipment",
        "Upload crop for quality check",
    ],
    "cluster": [
        "Find nearby farmers",
        "Create a selling group",
        "Split transport cost",
    ],
    "customer": [
        "Browse nearby crops",
        "Track my order",
        "Change payment method",
    ],
    "driver": [
        "Show nearby delivery requests",
        "Optimize my route",
        "Update shipment status",
    ],
    "wholesaler": [
        "Find farmer listings",
        "Negotiate a price",
        "Filter by crop type",
    ],
    "default": [
        "What is Kisan Route?",
        "How do I sign up?",
        "Contact support",
    ],
}

CANNED_RESPONSES = {
    "Check today's mandi rates": "Open your dashboard's Mandi Rate Detector to compare live rates across 7 nearby mandis and see the most profitable one.",
    "Calculate my net profit": "The Net Profit Calculator on your dashboard estimates revenue minus transport cost for your chosen crop and quantity.",
    "Track my shipment": "Shipment Tracking on your dashboard shows pickup, transit, mandi arrival, and delivery timestamps.",
    "Upload crop for quality check": "Go to Crop Quality Check, upload a photo, and you'll get a grade like Excellent, Good, or Average.",
    "Find nearby farmers": "Use the search bar on your cluster dashboard to find farmers already linked to Kisan Route.",
    "Create a selling group": "Add farmers to your group from the search results, then coordinate a joint mandi sale together.",
    "Split transport cost": "The Cost Splitting tool divides transport cost and profit evenly across your group members.",
    "Browse nearby crops": "Your dashboard lists nearby crop listings you can search and filter by crop type.",
    "Track my order": "Order Tracking shows each step from confirmation to delivery, with timestamps.",
    "Change payment method": "You can choose Cash on Delivery or UPI right on the order page before you confirm.",
    "Show nearby delivery requests": "Your dashboard lists open transport requests near you, with pickup and drop points.",
    "Optimize my route": "Accepting a request runs the route optimizer and shows suggested waypoints, distance, and ETA.",
    "Update shipment status": "The tracking page moves a shipment through Accepted, Pickup, Transit, and Delivered.",
    "Find farmer listings": "Your dashboard lists farmer crop listings sorted by distance from your mandi.",
    "Negotiate a price": "Open a listing and use Negotiate to send a price and quantity offer to the farmer.",
    "Filter by crop type": "Use the crop filter dropdown above the listings table to narrow results.",
    "What is Kisan Route?": "Kisan Route connects farmers, farmer clusters, customers, drivers, and wholesalers so crops move at fair prices with shared logistics.",
    "How do I sign up?": "Open the menu (the three dots, top-left), choose your role, and use Sign Up.",
    "Contact support": "This is a hackathon prototype, so live support isn't wired up yet — it's on the roadmap.",
}

DEFAULT_REPLY = (
    "I can help with mandi rates, profit calculation, shipment tracking, and more. "
    "This is a demo assistant with pre-set answers — full AI integration is planned."
)


def get_prompts(role: str):
    return ROLE_PROMPTS.get(role, ROLE_PROMPTS["default"])


def get_response(message: str) -> str:
    cleaned = (message or "").strip()
    if not cleaned:
        return DEFAULT_REPLY
    
    # 1. Exact match check
    if cleaned in CANNED_RESPONSES:
        return CANNED_RESPONSES[cleaned]

    # 2. Intelligent keyword & intent detection (Hindi, Hinglish, English)
    lower = cleaned.lower()

    if any(k in lower for k in ["mandi", "rate", "bhav", "daam", "price", "bhaav"]):
        return "📊 Mandi Rates: Aap Mandi Rate Detector page (/farmer/mandi-rates) par jakar live 7 mandiyon ke taaza bhav compare kar sakte hain aur sabse jyada munafewali mandi chun sakte hain."

    if any(k in lower for k in ["profit", "munafa", "kamai", "calculator", "nuksan", "hisab"]):
        return "💰 Profit Calculator: Net Profit Calculator (/farmer/profit-calculator) par apni fasal, kul upaj aur parivahan lagat daalkar apna shuddh munafa calculate kar sakte hain."

    if any(k in lower for k in ["quality", "jaanch", "grade", "photo", "image", "tasveer"]):
        return "🌾 Crop Quality Check: Crop Quality page (/farmer/crop-quality) par fasal ki photo upload karein, AI system turant Grade (A/B/C) aur quality score report bata deta hai."

    if any(k in lower for k in ["truck", "transport", "driver", "gadi", "gaadi", "load", "pickup", "route"]):
        return "🚚 Shared Transport: Kisan Route par shared trucks uplabdh hain jahan route optimizer se kam kharche me fasal mandi tak pahunchti hai."

    if any(k in lower for k in ["cluster", "samuh", "group", "samooh", "split"]):
        return "🤝 Kisan Cluster: Cluster Hub (/cluster/dashboard) me aas-paas ke kisan milkar ek sath fasal bech sakte hain aur truck ka kiraya aapas me baant sakte hain."

    if any(k in lower for k in ["customer", "grahak", "order", "buy", "khareed", "purchase", "shopping"]):
        return "🛒 Customer Store: Grahak (/customer/dashboard) par jakar kisan se direct taaza fasal saste daam me order kar sakte hain (Cash on Delivery aur UPI dono uplabdh)."

    if any(k in lower for k in ["wholesaler", "vyapari", "mandi trader", "negotiate", "arhatia"]):
        return "🏬 Wholesaler Portal: Thok vyapari (/wholesaler/dashboard) par jakar kisan ki list ki hui faslo par apna molbhaav (negotiation) bhej sakte hain."

    if any(k in lower for k in ["track", "kahan", "status", "shipment", "delivery"]):
        return "📍 Live Tracking: Live Tracking section me aapki fasal ya order ki live sthiti (Pickup, In-transit, Mandi Arrival, Delivered) timestamps ke sath dikhayi deti hai."

    if any(k in lower for k in ["insurance", "bima", "beema"]):
        return "🛡️ Fasal Bima: Transit Protect aur Weather Shield plans (/farmer/insurance) se fasal ke parivahan aur mausam ke nuksan se poora bima milta hai."

    if any(k in lower for k in ["yojana", "scheme", "sarkar", "subsidy", "pm kisan", "credit card"]):
        return "📜 Sarkari Yojanayein: Sarkari Schemes portal (/farmer/schemes) par PM-Kisan Samman Nidhi, Fasal Bima aur Kisan Credit Card ki jaankari prapt kar sakte hain."

    if any(k in lower for k in ["helpline", "support", "call", "contact", "phone", "number", "madad"]):
        return "📞 Helpline Support: Hamara toll-free helpline number 1800-123-4567 hai (Subah 8 se Shaam 8 baje). WhatsApp support: +91 98765-43210."

    if any(k in lower for k in ["login", "password", "demo", "account", "otp"]):
        return "🔑 Demo Login: Sabhi roles ke liye Demo Phone: 9876543210 aur Password: 123456 hai. Aap direct '1-Click Demo Login' button bhi use kar sakte hain."

    if any(k in lower for k in ["kisan route", "kya hai", "about", "bar", "feature"]):
        return "🌾 Kisan Route: Ek digital agricultural supply-chain platform hai jo kisan, cluster, customer, driver aur wholesaler ko direct jodta hai taaki behtar daam mile."

    return (
        "Namaste! 🙏 Main Kisan Route Sahayak hoon. Aap mujhse mandi rates, transport booking, "
        "profit calculation, fasal gunvatta jaanch, ya tracking ke baare me pooch sakte hain."
    )
