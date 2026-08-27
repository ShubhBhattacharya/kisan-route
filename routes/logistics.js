const express = require('express');
const router = express.Router();
const translations = require('../data/translations.json');

// 1. Calculate Shared Logistics Cost per Farmer
router.post('/calculate-split', (req, res) => {
  const { total_truck_fare, pickups } = req.body;
  // pickups example: [{ farmer_id: "F1", name: "Ramesh", qty_kg: 500, distance_km: 20 }, ...]

  if (!total_truck_fare || !pickups || pickups.length === 0) {
    return res.status(400).json({ error: 'Provide total_truck_fare and pickup list' });
  }

  const totalWeight = pickups.reduce((acc, p) => acc + p.qty_kg, 0);
  const totalWeightDist = pickups.reduce((acc, p) => acc + (p.qty_kg * p.distance_km), 0);

  const breakdown = pickups.map(p => {
    // Pro-rata based on weight-distance factor
    const shareRatio = (p.qty_kg * p.distance_km) / totalWeightDist;
    const individualCost = Math.round(shareRatio * total_truck_fare);
    const soloEstimatedCost = Math.round(p.distance_km * 40); // Standard individual tempo cost
    
    return {
      farmer_id: p.farmer_id,
      name: p.name,
      qty_kg: p.qty_kg,
      distance_km: p.distance_km,
      pooled_cost: individualCost,
      solo_cost: soloEstimatedCost,
      savings: soloEstimatedCost - individualCost
    };
  });

  res.json({
    total_truck_fare,
    total_weight_kg: totalWeight,
    farmer_breakdown: breakdown
  });
});

// 2. Multilingual SMS Generator / Webhook Simulation
router.post('/send-sms', (req, res) => {
  const { phone, language, event_type, params } = req.body;
  // language: 'hi', 'pa', 'mr', 'bn', etc.

  const lang = language || 'hi';
  const template = translations[event_type]?.[lang] || translations[event_type]?.['en'];

  if (!template) {
    return res.status(404).json({ error: 'Message template not found' });
  }

  let formattedMessage = template;
  for (const [key, value] of Object.entries(params || {})) {
    formattedMessage = formattedMessage.replace(new RegExp(`{${key}}`, 'g'), value);
  }

  // Simulated SMS Delivery
  const logEntry = {
    to: phone,
    language: lang,
    message: formattedMessage,
    status: 'DELIVERED',
    timestamp: new Date()
  };

  res.json({ success: true, sms_log: logEntry });
});

module.exports = router;