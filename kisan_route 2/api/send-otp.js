// api/send-otp.js - Vercel Serverless Function for Fast2SMS Quick OTP
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

    const phone = body.phone;
    const otp = body.otp;

    if (!phone || !otp) {
      return res.status(400).json({
        success: false,
        message: 'Both phone and otp parameters are required.'
      });
    }

    // Clean phone: keep only numeric digits and take the last 10 digits
    const cleanedDigits = String(phone).replace(/\D/g, '');
    const cleanPhone = cleanedDigits.length >= 10 ? cleanedDigits.slice(-10) : cleanedDigits;

    if (cleanPhone.length !== 10) {
      return res.status(400).json({
        success: false,
        message: 'Invalid phone number. Must be a valid 10-digit Indian mobile number.'
      });
    }

    const cleanOtp = String(otp).trim();
    if (!/^\d{4,6}$/.test(cleanOtp)) {
      return res.status(400).json({
        success: false,
        message: 'Invalid OTP format. Must be 4 to 6 numeric digits.'
      });
    }

    const apiKey = process.env.FAST2SMS_API_KEY || process.env.SMS_API_KEY;
    if (!apiKey) {
      return res.status(500).json({
        success: false,
        message: 'FAST2SMS_API_KEY is not configured in the server environment variables.'
      });
    }

    // Fast2SMS Quick OTP API via GET request
    const fast2smsUrl = `https://www.fast2sms.com/dev/bulkV2?authorization=${encodeURIComponent(apiKey)}&variables_values=${encodeURIComponent(cleanOtp)}&route=otp&numbers=${encodeURIComponent(cleanPhone)}`;

    const response = await fetch(fast2smsUrl, {
      method: 'GET',
      headers: {
        'cache-control': 'no-cache'
      }
    });

    const data = await response.json();

    if (data && data.return === true) {
      return res.status(200).json({
        success: true,
        message: 'OTP sent successfully via Fast2SMS.',
        request_id: data.request_id || null
      });
    } else {
      let errMsg = 'Failed to send OTP via Fast2SMS.';
      if (data && data.message) {
        errMsg = Array.isArray(data.message) ? data.message.join(', ') : String(data.message);
      }
      return res.status(400).json({
        success: false,
        message: errMsg,
        fast2sms_response: data
      });
    }
  } catch (error) {
    console.error('Error in send-otp handler:', error);
    return res.status(500).json({
      success: false,
      message: error.message || 'Internal server error while dispatching SMS OTP.'
    });
  }
};
