import os
from flask import Blueprint, request, jsonify, current_app
from services.whatsapp_service import send_whatsapp_text, ask_kisan_mitra_ai, build_dashboard_context
from models import User
from extensions import db

whatsapp_bp = Blueprint('whatsapp_bp', __name__)
VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "kisanroute_secure_verify_token_2026")

@whatsapp_bp.route('/webhook/whatsapp', methods=['GET'])
def verify_webhook():
    """Meta Webhook Verification Challenge handler."""
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    if mode == 'subscribe' and token == VERIFY_TOKEN:
        print("[WhatsApp Webhook] Verification successful!")
        return str(challenge), 200
    
    print("[WhatsApp Webhook] Verification failed: Token mismatch or invalid mode.")
    return "Verification failed", 403

@whatsapp_bp.route('/webhook/whatsapp', methods=['POST'])
def receive_message():
    """Receives incoming messages from Meta WhatsApp Cloud API and replies via Kisan Mitra AI."""
    body = request.get_json(silent=True) or {}
    
    try:
        entries = body.get('entry', [])
        if not entries:
            return jsonify({"status": "no_entry"}), 200

        changes = entries[0].get('changes', [])
        if not changes:
            return jsonify({"status": "no_changes"}), 200

        value = changes[0].get('value', {})
        messages = value.get('messages', [])
        
        if not messages:
            # Could be delivery status updates, read receipts, etc.
            return jsonify({"status": "no_message"}), 200
            
        msg = messages[0]
        from_phone = str(msg.get('from', '')).strip()
        user_text = msg.get('text', {}).get('body', '').strip()

        if not from_phone or not user_text:
            return jsonify({"status": "ignored"}), 200

        print(f"[WhatsApp Webhook] Message received from {from_phone}: {user_text}")

        # 1. DB me user lookup karein (matches full phone or 10-digit standard Indian phone)
        phone_clean = from_phone[-10:] if len(from_phone) >= 10 else from_phone
        user = User.query.filter(
            (User.phone == from_phone) | 
            (User.phone == phone_clean) |
            (User.phone.endswith(phone_clean))
        ).first()

        # 2. User ke role aur live DB ke mutabiq status assemble karein
        user_context = build_dashboard_context(user, db.session)

        # 3. AI se context-aware answer lein
        ai_reply = ask_kisan_mitra_ai(user_text, user_context)

        # 4. WhatsApp par wapas bhej dein
        send_result = send_whatsapp_text(from_phone, ai_reply)
        print(f"[WhatsApp Webhook] Replied to {from_phone} with: {ai_reply[:60]}... Result: {send_result}")

    except Exception as e:
        print(f"[WhatsApp Webhook] Error handling WhatsApp webhook: {e}")

    return jsonify({"status": "success"}), 200

@whatsapp_bp.route('/admin/broadcast-promo', methods=['POST'])
def broadcast_promo():
    """Admin endpoint to broadcast promotional/update messages to farmers, drivers, etc."""
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

    for u in users:
        phone = getattr(u, 'phone', None)
        if phone:
            send_whatsapp_text(phone, promo_text)
            sent_count += 1
    
    return jsonify({
        "status": "success",
        "message": f"Broadcast sent to {sent_count} {target_role}(s) successfully!",
        "count": sent_count
    }), 200
