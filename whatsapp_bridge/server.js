/**
 * KisanRoute WhatsApp Bridge Microservice
 * 100% Free, Self-Hosted 2-Way Baileys WhatsApp Web Automation
 */
const { 
    default: makeWASocket, 
    useMultiFileAuthState, 
    DisconnectReason, 
    fetchLatestBaileysVersion 
} = require('@whiskeysockets/baileys');
const express = require('express');
const qrcode = require('qrcode-terminal');
const axios = require('axios');
const path = require('path');
const fs = require('fs');

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 3000;
const FLASK_WEBHOOK_URL = process.env.FLASK_WEBHOOK_URL || 'http://127.0.0.1:5000/webhook/local-whatsapp';
const AUTH_DIR = path.join(__dirname, 'auth_info_baileys');

if (!fs.existsSync(AUTH_DIR)) {
    fs.mkdirSync(AUTH_DIR, { recursive: true });
}

let sock = null;
let isConnected = false;

async function connectToWhatsApp() {
    try {
        const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
        const { version } = await fetchLatestBaileysVersion().catch(() => ({ 
            version: [2, 3000, 1015901307] 
        }));

        console.log(`[WhatsApp Bridge] Connecting with Baileys v${version.join('.')}...`);

        sock = makeWASocket({
            version,
            auth: state,
            printQRInTerminal: false,
            defaultQueryTimeoutMs: 60000,
            connectTimeoutMs: 60000,
            keepAliveIntervalMs: 25000
        });

        sock.ev.on('creds.update', saveCreds);

        sock.ev.on('connection.update', (update) => {
            const { connection, lastDisconnect, qr } = update;

            if (qr) {
                console.log('\n======================================================');
                console.log('  SCAN THIS QR CODE IN WHATSAPP TO CONNECT KISAN MITRA:');
                console.log('======================================================\n');
                qrcode.generate(qr, { small: true });
                console.log('\n(Open WhatsApp > Linked Devices > Link a Device)\n');
            }

            if (connection === 'close') {
                isConnected = false;
                const statusCode = lastDisconnect?.error?.output?.statusCode;
                const shouldReconnect = statusCode !== DisconnectReason.loggedOut;
                console.log(`[WhatsApp Bridge] Connection closed (code: ${statusCode}). Reconnecting: ${shouldReconnect}`);
                if (shouldReconnect) {
                    setTimeout(connectToWhatsApp, 4000);
                } else {
                    console.log('[WhatsApp Bridge] Logged out. Delete auth_info_baileys and restart to generate new QR.');
                }
            } else if (connection === 'open') {
                isConnected = true;
                console.log('\n======================================================');
                console.log('  [WhatsApp Bridge] WhatsApp Web Connected Successfully!');
                console.log('  Kisan Mitra AI 2-Way Bot is now LIVE & ACTIVE!');
                console.log('======================================================\n');
            }
        });

        // 2-Way Incoming WhatsApp Message Listener
        sock.ev.on('messages.upsert', async (m) => {
            try {
                if (m.type !== 'notify') return;
                
                for (const msg of m.messages) {
                    if (!msg.message || msg.key.fromMe) continue;

                    const remoteJid = msg.key.remoteJid;
                    if (!remoteJid || remoteJid.includes('@g.us') || remoteJid === 'status@broadcast') {
                        continue;
                    }

                    // Extract pure phone number
                    const phone = remoteJid.replace('@s.whatsapp.net', '').replace('@c.us', '');

                    // Extract incoming text
                    const userText = msg.message.conversation ||
                                     msg.message.extendedTextMessage?.text ||
                                     msg.message.imageMessage?.caption ||
                                     msg.message.videoMessage?.caption || '';

                    if (!userText.trim()) continue;

                    console.log(`[WhatsApp Bridge] Message from ${phone}: "${userText.trim()}"`);

                    // Forward to Flask Backend for Kisan Mitra AI processing ({ phone, text })
                    try {
                        const flaskResponse = await axios.post(FLASK_WEBHOOK_URL, {
                            phone: phone,
                            text: userText.trim(),
                            message: userText.trim()
                        }, { timeout: 30000 });

                        const aiReply = flaskResponse.data?.reply;
                        if (aiReply && aiReply.trim()) {
                            console.log(`[WhatsApp Bridge] Sending Kisan Mitra reply to ${phone}: "${aiReply.substring(0, 60)}..."`);
                            await sock.sendMessage(remoteJid, { text: aiReply.trim() });
                        }
                    } catch (forwardErr) {
                        console.error(`[WhatsApp Bridge] Error from Flask backend: ${forwardErr.message}`);
                    }
                }
            } catch (err) {
                console.error('[WhatsApp Bridge] Error processing incoming message:', err);
            }
        });

    } catch (err) {
        console.error('[WhatsApp Bridge] Setup error:', err);
        setTimeout(connectToWhatsApp, 5000);
    }
}

// POST /send: Outgoing WhatsApp Message API
app.post('/send', async (req, res) => {
    const { phone, message, send_vcard } = req.body || {};

    if (!phone || !message) {
        return res.status(400).json({ error: 'Phone and message fields are required' });
    }

    if (!sock || !isConnected) {
        console.warn(`[WhatsApp Bridge] Outgoing queued or skipped: Socket not connected yet.`);
        return res.status(503).json({ 
            status: 'disconnected', 
            warning: 'WhatsApp Web socket is not connected or waiting for QR scan.' 
        });
    }

    // Sanitize the recipient phone
    let cleanPhone = String(phone).replace(/[^0-9]/g, "");
    if (cleanPhone.length === 10) cleanPhone = "91" + cleanPhone;
    let targetJid = `${cleanPhone}@s.whatsapp.net`;

    // If sending to the bot's own connected account:
    if (sock.user && cleanPhone === sock.user.id.split(':')[0]) {
        targetJid = sock.user.id; // Send directly to full JID
    }

    try {
        // Dispatch WhatsApp Contact Card (vCard) so recipient can tap "Save Contact" in 1-click
        const isWelcome = send_vcard || 
                          String(message).includes('Kisan Mitra') || 
                          String(message).includes('swagat') ||
                          String(message).includes('Namaste');

        if (isWelcome && sock.user) {
            try {
                const botPhone = sock.user.id.split(':')[0];
                const vcard = 'BEGIN:VCARD\n'
                            + 'VERSION:3.0\n'
                            + 'FN:Kisan Mitra (KisanRoute AI)\n'
                            + 'ORG:KisanRoute;\n'
                            + 'TEL;type=CELL;type=VOICE;waid=' + botPhone + ':+' + botPhone + '\n'
                            + 'END:VCARD';

                await sock.sendMessage(targetJid, {
                    contacts: {
                        displayName: 'Kisan Mitra',
                        contacts: [{ vcard }]
                    }
                });
                console.log(`[WhatsApp Bridge] Dispatched Kisan Mitra Contact Card (vCard) to ${cleanPhone}`);
            } catch (vcardErr) {
                console.warn('[WhatsApp Bridge] Notice: Error sending vCard:', vcardErr.message);
            }
        }

        console.log(`[WhatsApp Bridge] Dispatching message to ${cleanPhone} (${targetJid}): "${String(message).substring(0, 50)}..."`);
        const result = await sock.sendMessage(targetJid, { text: String(message) });
        return res.json({ status: 'sent', messageId: result?.key?.id, to: cleanPhone, jid: targetJid });
    } catch (err) {
        console.error(`[WhatsApp Bridge] Failed to send message to ${cleanPhone}:`, err.message);
        return res.status(500).json({ error: err.message });
    }
});

// GET /status: Service Health & Connection Status
app.get('/status', (req, res) => {
    res.json({
        service: 'KisanRoute WhatsApp Bridge',
        connected: isConnected,
        port: PORT,
        flaskWebhook: FLASK_WEBHOOK_URL
    });
});

app.listen(PORT, '127.0.0.1', () => {
    console.log(`[WhatsApp Bridge] HTTP Server listening on http://127.0.0.1:${PORT}`);
    connectToWhatsApp();
});
