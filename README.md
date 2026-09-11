# 🌾 KisanRoute - Agri Supply Chain & Logistics Platform

An intelligent agro-logistics platform designed to connect farmers, wholesalers, clusters, and drivers for optimized crop transportation and direct market linkage.

---

## 🚀 Key Features

* **Role-Based Portals:** Dedicated dashboards for Farmers, Wholesalers, Cluster Hubs, Drivers, and Consumers.
* **Smart Route Optimization:** Optimized dispatch algorithms to reduce produce transit time and post-harvest losses.
* **Dynamic Demand & Matching:** Real-time crop transport requests with pickup and mandi drop-off tracking.
* **Authentication & Security:** Secure login and profile verification for platform users.

---

## 🛠️ Tech Stack

* **Backend:** Python (Flask), Flask Blueprints, Werkzeug
* **Database & ORM:** SQLAlchemy
* **Frontend:** HTML5, CSS3, JavaScript, Jinja2 Templates
* **Version Control:** Git & GitHub

---

## 📂 Project Structure

```text
kisan_route 2/
│── blueprints/          # Role-based route controllers (farmer, driver, etc.)
│── static/              # CSS stylesheets, scripts, and media
│── templates/           # Jinja HTML UI templates
│── utils/               # Route optimizer & authentication helpers
│── extensions.py        # Database and platform instances
│── models.py            # User and transaction schemas
└── config.py            # Application configuration
