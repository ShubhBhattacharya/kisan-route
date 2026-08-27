const express = require('express');
const router = express.Router();
const { v4: uuidv4 } = require('uuid');

// 1. Buyer creates an order (Payment goes into Escrow - status: HELD)
router.post('/create', (req, res) => {
  const { buyer_id, listing_id, quantity_kg } = req.body;
  
  const listing = global.db.listings.find(l => l.id === listing_id);
  if (!listing) return res.status(404).json({ error: 'Listing not found' });
  if (listing.quantity_kg < quantity_kg) {
    return res.status(400).json({ error: 'Insufficient quantity available' });
  }

  const totalAmount = listing.price_per_kg * quantity_kg;
  const otp = Math.floor(1000 + Math.random() * 9000).toString(); // 4-digit OTP

  const newOrder = {
    id: uuidv4(),
    buyer_id,
    farmer_id: listing.farmer_id,
    listing_id,
    crop_name: listing.crop_name,
    quantity_kg: Number(quantity_kg),
    total_amount: totalAmount,
    escrow_status: 'HELD', // 'HELD', 'RELEASED', 'REFUNDED'
    delivery_otp: otp,
    created_at: new Date()
  };

  // Update listing stock
  listing.quantity_kg -= Number(quantity_kg);
  if (listing.quantity_kg === 0) listing.status = 'sold';

  global.db.orders.push(newOrder);

  res.status(201).json({
    message: 'Payment locked in Escrow. Order initiated.',
    order: newOrder
  });
});

// 2. Driver verifies OTP on delivery -> 100% Escrow released to Farmer
router.post('/verify-delivery', (req, res) => {
  const { order_id, otp } = req.body;
  
  const order = global.db.orders.find(o => o.id === order_id);
  if (!order) return res.status(404).json({ error: 'Order not found' });
  if (order.escrow_status !== 'HELD') {
    return res.status(400).json({ error: `Order is already ${order.escrow_status}` });
  }

  if (order.delivery_otp !== otp) {
    return res.status(400).json({ error: 'Invalid Delivery OTP' });
  }

  order.escrow_status = 'RELEASED';
  order.completed_at = new Date();

  res.json({
    message: 'OTP verified. Escrow funds transferred to Farmer.',
    order
  });
});

// 3. Auto-Refund / Dispute Trigger (Damage in transit or wrong quality)
router.post('/auto-refund', (req, res) => {
  const { order_id, reason, proof_image } = req.body;

  const order = global.db.orders.find(o => o.id === order_id);
  if (!order) return res.status(404).json({ error: 'Order not found' });
  if (order.escrow_status === 'RELEASED') {
    return res.status(400).json({ error: 'Funds already paid to farmer. Cannot auto-refund.' });
  }

  order.escrow_status = 'REFUNDED';
  order.refund_details = {
    reason: reason || 'Quality mismatch / Transit damage',
    proof_image: proof_image || 'proof.jpg',
    refunded_at: new Date()
  };

  res.json({
    message: 'Auto-refund processed successfully. Amount credited back to Buyer.',
    order
  });
});

// 4. Get all orders
router.get('/', (req, res) => {
  res.json(global.db.orders);
});

module.exports = router;