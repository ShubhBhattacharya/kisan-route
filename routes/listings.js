const express = require('express');
const router = express.Router();
const { v4: uuidv4 } = require('uuid');

// Farmer creates listing
router.post('/', (req, res) => {
  const { farmer_id, crop_name, quantity_kg, price_per_kg, quality_grade, location } = req.body;

  if (!crop_name || !quantity_kg || !price_per_kg) {
    return res.status(400).json({ error: 'Crop name, quantity, and price are required' });
  }

  const newListing = {
    id: uuidv4(),
    farmer_id: farmer_id || 'farmer-1',
    crop_name,
    quantity_kg: Number(quantity_kg),
    price_per_kg: Number(price_per_kg),
    quality_grade: quality_grade || 'Grade A',
    status: 'available',
    location: location || { lat: 26.8467, lng: 80.9462, address: 'Kanpur, UP' },
    created_at: new Date()
  };

  global.db.listings.push(newListing);
  res.status(201).json({ message: 'Crop listed successfully', listing: newListing });
});

// Get all active listings
router.get('/', (req, res) => {
  res.json(global.db.listings);
});

module.exports = router;