const express = require('express');
const cors = require('cors');
require('dotenv').config();

const app = express();
app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// Rich Enterprise Mock Database (Flipkart / Agri-ERP Style)
global.db = {
  users: [
    { id: 'USR-LEAD-01', phone: '9812043890', email: 'shubh.lead@kisanroute.in', password: 'pass', name: 'Sardar Gurpreet Singh (Shubh)', role: 'lead_farmer', cluster: 'Faridabad Hub #04', kyc: 'VERIFIED' },
    { id: 'USR-BUYER-01', phone: '9876543210', email: 'procurement@bigbasket.com', password: 'pass', name: 'BigBasket North Wholesale (Rahul Verma)', role: 'buyer', business_gst: '07AABCB1234F1Z1' },
    { id: 'USR-DRIVER-01', phone: '9811044910', email: 'vikram.logistics@kisanroute.in', password: 'pass', name: 'Vikram Singh (Fleet Driver)', role: 'driver', vehicle_no: 'HR-38-AF-4829', vehicle_type: 'Mini Truck (Tata Ace)' },
    { id: 'USR-FARMER-01', phone: '9812011223', email: 'rameshwar@kisanroute.in', password: 'pass', name: 'Rameshwar Sharma', role: 'member_farmer', village: 'Dhauj (121007)' },
    { id: 'USR-ADMIN-01', phone: '9999900000', email: 'admin@kisanroute.gov.in', password: 'admin', name: 'Nodal Officer (Haryana Agri Dept)', role: 'admin' }
  ],
  orders: [
    {
      order_id: 'OD-2026-FBD-8821',
      date: '27-Aug-2026, 02:15 PM',
      buyer_name: 'BigBasket Wholesale Hub',
      delivery_address: 'Warehouse #4B, Sector 15 APMC Corridor, Faridabad - 121003',
      crop_name: 'Desi Fresh Tomato (Grade A)',
      quantity_kg: 650,
      price_per_kg: 24,
      subtotal: 15600,
      gst_amount: 780,
      logistics_cut: 624,
      net_farmer_payout: 14976,
      escrow_status: 'IN_TRANSIT', // 'CONFIRMED', 'PACKED', 'IN_TRANSIT', 'DELIVERED', 'REFUNDED'
      delivery_otp: '4829',
      tentative_delivery: 'Today, 27-Aug by 05:30 PM (In ~1h 45m)',
      assigned_driver: 'Vikram Singh (Tata Ace &bull; HR-38-AF-4829)',
      timeline: [
        { title: 'Order Placed & Escrow Locked', time: '02:15 PM', status: 'done', desc: '₹16,380 held safely in Escrow Custody' },
        { title: 'Cluster Quality Audit & AI Scan', time: '02:40 PM', status: 'done', desc: 'Grade A (96% Freshness Score) Certified' },
        { title: 'Packed & QR Crated', time: '03:10 PM', status: 'done', desc: '26 plastic ventilated crates sealed' },
        { title: 'Dispatched from Dhauj Farm Gate', time: '03:30 PM', status: 'current', desc: 'Driver Vikram Singh moving via Mathura Road' },
        { title: 'Delivered & OTP Verified', time: 'Pending (~05:30 PM)', status: 'pending', desc: 'Requires Buyer 4-digit OTP: 4829' }
      ]
    }
  ]
};

// --- AUTH API (Flipkart / Amazon Style Login) ---
app.post('/api/auth/login', (req, res) => {
  const { identifier, password } = req.body;
  const user = global.db.users.find(u => (u.email === identifier || u.phone === identifier) && u.password === password);
  if (!user) {
    return res.status(401).json({ success: false, message: 'Invalid User ID/Phone or Password!' });
  }
  res.json({ success: true, user, message: `Welcome back, ${user.name}!` });
});

// --- ORDERS API ---
app.get('/api/orders/track/:order_id', (req, res) => {
  const order = global.db.orders.find(o => o.order_id === req.params.order_id) || global.db.orders[0];
  res.json(order);
});

// --- DISPATCH & OTP VERIFY ---
app.post('/api/orders/verify-otp', (req, res) => {
  const { order_id, otp } = req.body;
  const order = global.db.orders.find(o => o.order_id === order_id) || global.db.orders[0];
  if (order.delivery_otp !== otp) {
    return res.status(400).json({ success: false, message: 'Invalid 4-digit Delivery OTP!' });
  }
  order.escrow_status = 'DELIVERED';
  order.timeline[4].status = 'done';
  order.timeline[4].time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  res.json({ success: true, message: `OTP ${otp} Verified! ₹${order.net_farmer_payout.toLocaleString()} transferred to Farmer Bank Account.` });
});

// Auto-Refund API
app.post('/api/orders/auto-refund', (req, res) => {
  const { order_id, reason } = req.body;
  const order = global.db.orders.find(o => o.order_id === order_id) || global.db.orders[0];
  order.escrow_status = 'REFUNDED';
  res.json({ success: true, message: `Dispute Accepted (${reason}). Instant refund of ₹${order.subtotal.toLocaleString()} credited back to Buyer Wallet.` });
});

const PORT = process.env.PORT || 5000;
app.listen(PORT, () => {
  console.log(`🚀 KisanRoute Enterprise Engine active on http://localhost:${PORT}`);
});