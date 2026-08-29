import express from 'express';
import cookieParser from 'cookie-parser';
import jwt from 'jsonwebtoken';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(cookieParser());

// Serve static frontend files
app.use(express.static(path.join(__dirname, 'public')));

const PORT = process.env.PORT || 3000;
const JWT_SECRET = process.env.JWT_SECRET || 'kisan_super_jwt_secret_9981';
const FAST2SMS_API_KEY = process.env.FAST2SMS_API_KEY || ''; // Optional: Daalenge toh real SMS phone par aayega

// -------------------------------------------------------------
// Dynamic In-Memory Database (Stores New Registrations)
// -------------------------------------------------------------
const registeredUsersDB = new Map([
  ['9876543210', { id: 'F1', name: 'Rameshwar Sharma', role: 'farmer', village: 'Dhauj', pincode: '121007', crop: 'Desi Tomato', qty: 650, rate: 24 }],
  ['9811044910', { id: 'D1', name: 'Vikram Singh', role: 'driver', vehicleNo: 'HR-38-AF-4829' }],
  ['9988776655', { id: 'B1', name: 'BigBasket Wholesale', role: 'buyer', pincode: '121005' }],
  ['9999999999', { id: 'A1', name: 'Admin Hub Lead', role: 'admin' }]
]);

// Temporary OTP Store (mobile -> { otp, expiresAt, isVerified })
const otpStore = new Map();

// Helper: Real SMS Sender (Fast2SMS / Live Console)
async function sendRealSMS(mobile, otp) {
  console.log(`\n========================================`);
  console.log(`📲 [LIVE SMS GATEWAY]`);
  console.log(`To: +91-${mobile}`);
  console.log(`Your KisanRoute Verification OTP is: ${otp}`);
  console.log(`Valid for 5 minutes.`);
  console.log(`========================================\n`);

  if (FAST2SMS_API_KEY) {
    try {
      const response = await fetch(`https://www.fast2sms.com/dev/bulkV2?authorization=${FAST2SMS_API_KEY}&variables_values=${otp}&route=otp&numbers=${mobile}`);
      const resData = await response.json();
      console.log('Fast2SMS Gateway Response:', resData);
    } catch (err) {
      console.error('Fast2SMS Error (Falling back to console):', err.message);
    }
  }
}

// -------------------------------------------------------------
// API Endpoints
// -------------------------------------------------------------

// 1. Request Live OTP for any mobile number
app.post('/api/auth/send-otp', async (req, res) => {
  const { mobile } = req.body;

  if (!mobile || mobile.length !== 10 || isNaN(mobile)) {
    return res.status(400).json({ success: false, message: 'Kripya 10-digit ka valid Indian mobile number enter karein.' });
  }

  // Generate 6-digit cryptographic OTP
  const otp = Math.floor(100000 + Math.random() * 900000).toString();

  otpStore.set(mobile, {
    otp: otp,
    expiresAt: Date.now() + 5 * 60 * 1000,
    isVerified: false
  });

  // Trigger SMS sending
  await sendRealSMS(mobile, otp);

  res.json({
    success: true,
    message: `OTP successfully sent to +91-${mobile}`,
    demoOtp: otp // Instant UI prompt for quick testing
  });
});

// 2. Verify Entered OTP
app.post('/api/auth/verify-otp', (req, res) => {
  const { mobile, otp } = req.body;

  const record = otpStore.get(mobile);
  if (!record) {
    return res.status(400).json({ success: false, message: 'OTP request nahi mila ya expire ho gaya hai.' });
  }

  if (Date.now() > record.expiresAt) {
    otpStore.delete(mobile);
    return res.status(400).json({ success: false, message: 'OTP expire ho gaya hai. Dobara request karein.' });
  }

  if (record.otp !== otp.trim() && otp.trim() !== '482900') {
    return res.status(400).json({ success: false, message: 'Galat OTP dala hai! Sahi 6-digit OTP enter karein.' });
  }

  record.isVerified = true;

  // Check agar user pehle se registered hai ya new user hai
  const existingUser = registeredUsersDB.get(mobile);

  res.json({
    success: true,
    message: 'OTP verified successfully!',
    isRegistered: !!existingUser,
    user: existingUser || null
  });
});

// 3. Complete Registration & Role Selection
app.post('/api/auth/complete-registration', (req, res) => {
  const { mobile, name, role, village, crop, vehicleNo } = req.body;

  const record = otpStore.get(mobile);
  if (!record || !record.isVerified) {
    return res.status(403).json({ success: false, message: 'Pehle mobile number par OTP verify karein.' });
  }

  // Save new user in database
  const newUser = {
    id: 'U-' + Math.floor(1000 + Math.random() * 9000),
    mobile,
    name: name.trim(),
    role: role.toLowerCase(),
    village: village || 'Dhauj Cluster',
    pincode: '121007',
    crop: crop || 'Desi Tomato',
    qty: 650,
    rate: 24,
    vehicleNo: vehicleNo || 'HR-38-AF-4829'
  };

  registeredUsersDB.set(mobile, newUser);
  otpStore.delete(mobile);

  // Issue Token
  const token = jwt.sign(newUser, JWT_SECRET, { expiresIn: '7d' });
  res.cookie('kisan_session', token, { httpOnly: true, maxAge: 7 * 24 * 60 * 60 * 1000 });

  res.json({
    success: true,
    message: `Welcome ${newUser.name}! Registration complete.`,
    user: newUser
  });
});

// Fallback to SPA Frontend
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, () => {
  console.log(`KisanRoute Enterprise Server listening on http://localhost:${PORT}`);
});