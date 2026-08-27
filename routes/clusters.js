const express = require('express');
const router = express.Router();
const { v4: uuidv4 } = require('uuid');

// In-Memory Cluster Data Store
global.db.clusters = [];
global.db.vehicles = [
  { type: 'Motorcycle', max_cap_kg: 50, cost_per_km: 10 },
  { type: 'E-Rickshaw', max_cap_kg: 350, cost_per_km: 20 },
  { type: 'Mini Truck (Tata Ace)', max_cap_kg: 1000, cost_per_km: 35 },
  { type: 'Heavy Truck', max_cap_kg: 5000, cost_per_km: 60 }
];

// 1. Group / Cluster Registration with Lead Farmer
router.post('/register', (req, res) => {
  const { group_name, village_name, allowed_pincodes, head_farmer, member_farmers } = req.body;

  if (!group_name || !head_farmer || !head_farmer.phone) {
    return res.status(400).json({ error: 'Group name and Lead Farmer details required' });
  }

  const newCluster = {
    id: uuidv4(),
    group_name,
    village_name: village_name || 'Faridabad Hub',
    allowed_pincodes: allowed_pincodes || ['121001', '121002', '121003', '121004', '121005'],
    lead_farmer: {
      id: uuidv4(),
      name: head_farmer.name,
      phone: head_farmer.phone,
      role: 'GROUP_HEAD_SUPERVISOR'
    },
    members: (member_farmers || []).map(f => ({
      id: uuidv4(),
      name: f.name,
      phone: f.phone,
      allocated_land_acres: f.land || 1
    })),
    pipeline: {
      production_tracked_kg: 0,
      cleaning_status: 'PENDING',
      sorting_grading_status: 'PENDING',
      packaging_status: 'PENDING',
      billing_gst_ready: false
    },
    created_at: new Date()
  };

  global.db.clusters.push(newCluster);
  res.status(201).json({ message: 'Farmer Cluster registered successfully', cluster: newCluster });
});

// 2. Supervisor / Process Owner Status Update (Cleaning, Sorting, Packaging, GST)
router.post('/update-process', (req, res) => {
  const { cluster_id, stage, status, details } = req.body;
  // stage: 'cleaning', 'sorting', 'packaging', 'billing_gst'

  const cluster = global.db.clusters.find(c => c.id === cluster_id);
  if (!cluster) return res.status(404).json({ error: 'Cluster not found' });

  if (stage === 'cleaning') cluster.pipeline.cleaning_status = status;
  if (stage === 'sorting') cluster.pipeline.sorting_grading_status = status;
  if (stage === 'packaging') cluster.pipeline.packaging_status = status;
  if (stage === 'billing_gst') {
    cluster.pipeline.billing_gst_ready = (status === 'COMPLETED');
    cluster.pipeline.gst_invoice = {
      invoice_no: `INV-${Date.now().toString().slice(-6)}`,
      gst_rate: '5%',
      taxable_amount: details?.amount || 0,
      total_with_gst: details?.amount ? Math.round(details.amount * 1.05) : 0
    };
  }

  res.json({ message: `Stage ${stage} updated`, pipeline: cluster.pipeline });
});

// 3. Smart Vehicle Allotment & Pincode Filter
router.post('/allot-vehicle', (req, res) => {
  const { cluster_id, total_weight_kg, destination_pincode } = req.body;

  const cluster = global.db.clusters.find(c => c.id === cluster_id);
  if (cluster && !cluster.allowed_pincodes.includes(destination_pincode)) {
    return res.status(403).json({
      error: `Delivery not available in pincode ${destination_pincode}. Active pincodes: ${cluster.allowed_pincodes.join(', ')}`
    });
  }

  // Choose optimal vehicle based on capacity
  let allottedVehicle = global.db.vehicles[global.db.vehicles.length - 1]; // Default largest
  for (let v of global.db.vehicles) {
    if (total_weight_kg <= v.max_cap_kg) {
      allottedVehicle = v;
      break;
    }
  }

  res.json({
    assigned_vehicle: allottedVehicle.type,
    max_capacity_kg: allottedVehicle.max_cap_kg,
    base_rate_per_km: allottedVehicle.cost_per_km,
    status: 'DISPATCH_READY',
    pincode_verified: true
  });
});

// 4. Get all clusters
router.get('/', (req, res) => {
  res.json(global.db.clusters);
});

module.exports = router;