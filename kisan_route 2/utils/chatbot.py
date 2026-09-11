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
    return CANNED_RESPONSES.get((message or "").strip(), DEFAULT_REPLY)
