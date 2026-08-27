const express = require('express');
const router = express.Router();
const { v4: uuidv4 } = require('uuid');

router.post('/register', (req, res) => {
  const { name, phone, role, language, upi_id } = req.body;
  if (!phone || !role) {
    return res.status(400).json({ error: 'Phone and role are required' });
  }

  const existing = global.db.users.find(u => u.phone === phone);
  if (existing) return res.status(400).json({ error: 'User already exists' });

  const newUser = {
    id: uuidv4(),
    name: name || 'Kisan User',
    phone,
    role, // 'farmer', 'buyer', 'driver'
    language: language || 'hi',
    upi_id: upi_id || ''
  };

  global.db.users.push(newUser);
  res.status(201).json({ message: 'User registered successfully', user: newUser });
});

router.post('/login', (req, res) => {
  const { phone } = req.body;
  const user = global.db.users.find(u => u.phone === phone);
  if (!user) return res.status(404).json({ error: 'User not found' });
  res.json({ message: 'Login successful', user });
});

module.exports = router;