import os
from flask import Blueprint, request, jsonify
from services.whatsapp_service import send_to_whatsapp, ask_kisan_mitra_ai, build_dashboard_context
from models import User
from extensions import db

local_whatsapp_bp = Blueprint('local_whatsapp_bp', __name__)

@local_whatsapp_bp.route('/webhook/local-whatsapp', methods=['POST'])
def local_whatsapp_webhook():
    """
    Receives incoming WhatsApp messages forwarded from the local Node.js Baileys bridge.
    Looks up user context, generates a respectful Hindi/Hinglish reply via Kisan Mitra AI,
    and returns {"reply": ai_reply} so the Node bridge can send it back directly.
    """
    data = request.get_json(silent=True) or {}
    phone = str(data.get('phone', '')).strip()
    user_message = str(data.get('message', '')).strip()

    if not user_message:
        return jsonify({"reply": "नमस्ते जी! KisanRoute किसान मित्र सेवा में आपका स्वागत है। आप अपनी फसल, मंडी भाव या वाहन स्थिति के बारे में पूछ सकते हैं।", "status": "empty_message"}), 200

    try:
        # DB lookup for sender user
        phone_clean = phone[-10:] if len(phone) >= 10 else phone
        user = User.query.filter(
            (User.phone == phone) |
            (User.phone == phone_clean) |
            (User.phone.endswith(phone_clean))
        ).first()

        # Build live role and dashboard context
        user_context = build_dashboard_context(user, db.session)

        # Generate response using Kisan Mitra AI (Gemini 2.5 Flash)
        ai_reply = ask_kisan_mitra_ai(user_message, user_context)
        return jsonify({
            "status": "success",
            "reply": ai_reply,
            "phone": phone
        }), 200

    except Exception as e:
        print(f"[Local WhatsApp Webhook] Error: {e}")
        fallback_reply = (
            "राम-राम जी! KisanRoute किसान मित्र में आपका स्वागत है। "
            "वर्तमान में सर्वर व्यस्त है, कृपया कुछ समय बाद पुनः प्रयास करें या 1800-123-4567 पर कॉल करें।"
        )
        return jsonify({
            "status": "error",
            "reply": fallback_reply,
            "error": str(e)
        }), 200

@local_whatsapp_bp.route('/admin/local-broadcast-promo', methods=['POST'])
@local_whatsapp_bp.route('/admin/broadcast-promo', methods=['POST'])
def local_broadcast_promo():
    """
    Admin endpoint to broadcast updates/promotional messages to farmers, drivers, etc.,
    via the 100% free self-hosted Baileys WhatsApp Web bridge.
    """
    data = request.get_json(silent=True) or {}
    target_role = str(data.get('role', 'farmer')).strip().lower()
    promo_text = data.get('message', '').strip()

    if not promo_text:
        return jsonify({"error": "Message text is required"}), 400

    query = User.query
    if target_role and target_role != 'all':
        query = query.filter(User.role.ilike(target_role))

    users = query.all()
    sent_count = 0
    results = []

    for u in users:
        phone = getattr(u, 'phone', None)
        if phone:
            res = send_to_whatsapp(phone, promo_text)
            sent_count += 1
            results.append({"phone": phone, "result": res})

    return jsonify({
        "status": "success",
        "message": f"Broadcast dispatched to {sent_count} user(s) with role '{target_role}'.",
        "count": sent_count,
        "results": results
    }), 200
