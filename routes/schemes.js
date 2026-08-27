const express = require('express');
const router = express.Router();
const schemesData = require('../data/schemes.json');

router.get('/', (req, res) => {
  res.json(schemesData);
});

module.exports = router;