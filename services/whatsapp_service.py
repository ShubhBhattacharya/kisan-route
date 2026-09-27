import os
import requests
from google import genai
from google.genai import types

def _get_genai_client():
    """Returns an initialized Google GenAI Client instance safely."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        # Fallback to alternative key names if present
        api_key = os.getenv("GOOGLE_API_KEY") or "dummy_key_for_init"
    return genai.Client(api_key=api_key)

def send_whatsapp_text(to_phone, message_text):
    """WhatsApp par text message bhejne ke liye using Meta WhatsApp Cloud API."""
    whatsapp_token = os.getenv("WHATSAPP_TOKEN")
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    
    if not whatsapp_token or not phone_number_id:
        print(f"[WhatsApp Service] Warning: WHATSAPP_TOKEN or WHATSAPP_PHONE_NUMBER_ID not configured.")
        return {"error": "WhatsApp credentials not configured", "status": "skipped"}
    
    url = f"https://graph.facebook.com/v19.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {whatsapp_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": str(to_phone),
        "type": "text",
        "text": {"body": str(message_text)}
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=12)
        return response.json()
    except Exception as e:
        print(f"[WhatsApp Service] Network error sending WhatsApp message to {to_phone}: {e}")
def send_to_whatsapp(phone, message):
    """
    Sends WhatsApp message via the free self-hosted Baileys bridge microservice (default http://127.0.0.1:3000/send).
    Non-blocking / safe fallback so Flask app never breaks if bridge is offline or scanning QR.
    """
    bridge_url = os.getenv("WHATSAPP_BRIDGE_URL", "http://127.0.0.1:3000/send")
    payload = {
        "phone": str(phone),
        "message": str(message)
    }
    try:
        resp = requests.post(bridge_url, json=payload, timeout=5)
        if "application/json" in resp.headers.get("content-type", ""):
            return resp.json()
        return {"status": "ok", "response": resp.text}
    except Exception as e:
        print(f"[Local WhatsApp Bridge] Notice: Could not send to {phone} via bridge ({bridge_url}): {e}")
        return {"error": str(e), "status": "bridge_offline"}

def build_dashboard_context(user, db_session=None):
    """User ke role ke mutabiq live DB status assemble karna."""
    if not user:
        return "User: Guest / Naya Kisan bhai on KisanRoute platform."

    role = getattr(user, 'role', '').lower()
    name = getattr(user, 'name', getattr(user, 'full_name', 'Kisan Bhai'))
    phone = getattr(user, 'phone', '')
    extra = {}
    if hasattr(user, 'get_extra') and callable(user.get_extra):
        extra = user.get_extra() or {}

    try:
        from models import Bid
        # Check if there are active bids for this user
        user_bids = Bid.query.filter(
            (Bid.farmer_name == name) | (Bid.wholesaler_phone == phone)
        ).all()
    except Exception:
        user_bids = []

    if role == 'farmer':
        crop = extra.get('crop_type') or 'Gehu'
        if user_bids:
            latest_bid = user_bids[-1]
            return (
                f"User Name: {name}, Role: Kisan (Farmer). "
                f"Active Deal: {latest_bid.crop} ({latest_bid.offer_qty} Qtl, "
                f"Offered Rate: ₹{latest_bid.offer_price}/Qtl, Status: {latest_bid.status})."
            )
        return (
            f"User Name: {name}, Role: Kisan (Farmer). "
            f"Fasal: {crop}, Status: Khet se Mandi connection ready. Direct buyers active."
        )

    elif role == 'driver':
        vehicle = extra.get('vehicle_number', 'UP-16-TR-2026')
        return (
            f"User Name: {name}, Role: Driver (Logistics Partner). "
            f"Vehicle: {vehicle}, Assigned Route: Palwal to Rohtak Mandi, Status: Active Trip."
        )

    elif role == 'cluster':
        return (
            f"User Name: {name}, Role: Cluster Head (समूह संचालक). "
            f"Managed Farmers: 15, Active Produce Batches: 3, Status: Dynamic Fair Price Normalizer active."
        )

    elif role == 'wholesaler':
        return (
            f"User Name: {name}, Role: Wholesaler (थोक आढ़ती/खरीदार). "
            f"Status: Direct Farm-Gate Procurement active, Verified Bids enabled."
        )

    elif role == 'customer':
        return (
            f"User Name: {name}, Role: Customer (उपभोक्ता). "
            f"Status: Quick-Commerce Farm-Fresh Produce Orders active (45 mins delivery)."
        )

    return f"User Name: {name}, Role: Registered Member on KisanRoute."

def ask_kisan_mitra_ai(user_query, user_context):
    """Live Context ke sath AI ka Hindi/Hinglish reply generate karna."""
    system_instruction = f"""
    Aap 'Kisan Mitra' hain — KisanRoute ke official smart digital saathi.
    Platform Knowledge: KisanRoute khet se mandi tak transparent pricing, vehicle coordination aur direct buyer link deta hai.
    User ka Live Dashboard Status: {user_context}
    Rules:
    1. Hamesha aadar se baat karein ('Ji' lagakar).
    2. Sirf Hindi / Hinglish me asaan shabdon me jawab dein (max 2-3 lines).
    3. Agar user status pooche, toh unke live dashboard data ke hisaab se sahi info dein.
    4. Jab bhi fasal ka bhav, tracking ya mandi ke baare me poochein, spasht aur saaf jawab dein.
    """

    try:
        client = _get_genai_client()
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_query,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.3
            )
        )
        if response and response.text:
            return response.text.strip()
    except Exception as e:
        print(f"[Kisan Mitra AI] Generation error: {e}")

    # Graceful fallback response
    return (
        f"राम-राम जी! मैं आपका किसान मित्र। आपके सवाल '{user_query}' को समझ लिया है। "
        f"KisanRoute पर आपका स्वागत है। अधिक जानकारी या सहायता के लिए हमारे टोल-फ्री नंबर 1800-123-4567 पर संपर्क करें।"
    )
