// api/send-otp.js - Vercel Serverless Function (Demo/Sandbox Gateway)
module.exports = async function handler(req, res) {
  // CORS Headers
  res.setHeader('Access-Control-Allow-Credentials', 'true');
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS,POST');
  res.setHeader(
    'Access-Control-Allow-Headers',
    'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version'
  );

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({
      success: false,
      message: 'Method Not Allowed. Only POST requests are accepted.'
    });
  }

  try {
    let body = req.body;
    if (typeof body === 'string') {
      try {
        body = JSON.parse(body);
      } catch (e) {
        body = {};
      }
    }
    body = body || {};

    const rawPhone = body.phone;
    if (!rawPhone) {
      return res.status(400).json({
        success: false,
        message: 'Phone number is required.'
      });
    }

    // Clean phone: strip non-numeric characters, country code, leading zeros
    let digits = String(rawPhone).replace(/\D/g, '').replace(/^0+/, '');
    if (digits.length === 12 && digits.startsWith('91')) {
      digits = digits.slice(2);
    }
    const cleanPhone = digits.length >= 10 ? digits.slice(-10) : digits;

    if (cleanPhone.length !== 10 || !/^\d{10}$/.test(cleanPhone)) {
      return res.status(400).json({
        success: false,
        message: 'Invalid phone number format. Strictly a 10-digit Indian mobile number is required (e.g. 8700257488).'
      });
    }

    // Generate random 6-digit OTP (or use provided OTP)
    const otp = (body.otp && /^\d{6}$/.test(String(body.otp).trim()))
      ? String(body.otp).trim()
      : String(Math.floor(100000 + Math.random() * 900000));

    console.log(`[Sandbox SMS Gateway] Dispatched OTP ${otp} to phone +91 ${cleanPhone}`);

    // Return 200 JSON immediately
    return res.status(200).json({
      success: true,
      demoOtp: otp,
      phone: cleanPhone,
      message: "Demo SMS dispatched successfully via sandbox gateway."
    });
  } catch (error) {
    console.error('[Send OTP Handler Error]:', error);
    return res.status(500).json({
      success: false,
      message: error.message || 'Internal server error while generating OTP.'
    });
  }
};
