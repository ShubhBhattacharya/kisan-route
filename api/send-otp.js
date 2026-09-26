// api/send-otp.js - Vercel Serverless Function for Fast2SMS Quick SMS (route=q)
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
    const rawOtp = body.otp;

    if (!rawPhone || !rawOtp) {
      return res.status(400).json({
        success: false,
        message: 'Both phone and otp parameters are required.'
      });
    }

    // 1. Ensure cleanPhone is strictly 10 digits:
    // Strip non-numeric characters, country code, leading zeros, and +91
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

    const otp = String(rawOtp).trim();
    if (!/^\d{4,6}$/.test(otp)) {
      return res.status(400).json({
        success: false,
        message: 'Invalid OTP format. Must be 4 to 6 numeric digits.'
      });
    }

    const apiKey = (process.env.FAST2SMS_API_KEY || process.env.SMS_API_KEY || '').trim();
    if (!apiKey) {
      console.error('[Fast2SMS] Missing FAST2SMS_API_KEY in server environment.');
      return res.status(500).json({
        success: false,
        message: 'FAST2SMS_API_KEY is not configured in server environment variables.'
      });
    }

    // 2. Fast2SMS Quick SMS Route (route=q):
    const messageText = `Your KisanRoute verification code is: ${otp}`;
    const fast2smsUrl = `https://www.fast2sms.com/dev/bulkV2?authorization=${encodeURIComponent(apiKey)}&route=q&message=${encodeURIComponent(messageText)}&language=english&flash=0&numbers=${encodeURIComponent(cleanPhone)}`;

    console.log(`[Fast2SMS] Sending Quick SMS (route=q) to ${cleanPhone}...`);

    let responseData = null;
    let isSuccess = false;

    // Strategy A: Standard GET request to Fast2SMS bulkV2 route=q
    try {
      const getRes = await fetch(fast2smsUrl, {
        method: 'GET',
        headers: {
          'authorization': apiKey,
          'cache-control': 'no-cache',
          'User-Agent': 'KisanRoute/1.0'
        }
      });

      const getRawText = await getRes.text();
      console.log(`[Fast2SMS Response] Status: ${getRes.status}, Body: ${getRawText}`);

      try {
        responseData = JSON.parse(getRawText);
      } catch (parseErr) {
        responseData = { return: false, message: getRawText };
      }

      if (responseData && responseData.return === true) {
        isSuccess = true;
      }
    } catch (getErr) {
      console.error('[Fast2SMS GET Network Error]:', getErr);
    }

    // Strategy B: POST request fallback if GET failed
    if (!isSuccess) {
      try {
        console.log('[Fast2SMS] Trying POST fallback for route=q...');
        const postRes = await fetch('https://www.fast2sms.com/dev/bulkV2', {
          method: 'POST',
          headers: {
            'authorization': apiKey,
            'Content-Type': 'application/json',
            'cache-control': 'no-cache',
            'User-Agent': 'KisanRoute/1.0'
          },
          body: JSON.stringify({
            route: 'q',
            message: messageText,
            language: 'english',
            flash: 0,
            numbers: cleanPhone
          })
        });

        const postRawText = await postRes.text();
        console.log(`[Fast2SMS POST Response] Status: ${postRes.status}, Body: ${postRawText}`);

        try {
          const postData = JSON.parse(postRawText);
          if (postData && postData.return === true) {
            responseData = postData;
            isSuccess = true;
          } else if (postData) {
            responseData = postData;
          }
        } catch (postParseErr) {
          if (!responseData) responseData = { return: false, message: postRawText };
        }
      } catch (postErr) {
        console.error('[Fast2SMS POST Network Error]:', postErr);
      }
    }

    // 3. If Fast2SMS responds with return: true, respond with { success: true }
    if (isSuccess && responseData && responseData.return === true) {
      return res.status(200).json({
        success: true,
        message: 'OTP sent successfully via Fast2SMS Quick SMS.',
        request_id: responseData.request_id || null
      });
    } else {
      let errMsg = 'Failed to send OTP via Fast2SMS.';
      if (responseData && responseData.message) {
        errMsg = Array.isArray(responseData.message)
          ? responseData.message.join(', ')
          : String(responseData.message);
      }
      console.error('[Fast2SMS Final Failure Body]:', JSON.stringify(responseData));
      return res.status(400).json({
        success: false,
        message: errMsg,
        fast2sms_response: responseData
      });
    }
  } catch (error) {
    console.error('[Fast2SMS Handler Exception]:', error);
    return res.status(500).json({
      success: false,
      message: error.message || 'Internal server error while dispatching SMS OTP.'
    });
  }
};
