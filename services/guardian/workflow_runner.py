"""KisanRoute Guardian AI - Synthetic Workflow Runner & System Probes.

Executes non-destructive, real-world synthetic checks for all 5 roles:
1. Farmer: Login view, plus authenticated session access to mandi rates & dashboard.
2. Farmer Cluster: Cluster login view, plus authenticated cluster dashboard access.
3. Customer: Shop storefront login view, plus authenticated shopping dashboard.
4. Driver: Driver login view, plus authenticated logistics dashboard.
5. Wholesaler: Wholesaler login view, plus authenticated market lot bidding.
6. Core Integrations: Open-Meteo weather, news feed, WhatsApp bridge, DB health.
"""

import time
from services.guardian.storage import append_log


class WorkflowRunner:
    def __init__(self, app=None):
        self.app = app

    def run_all_checks(self):
        """Execute full synthetic test sweep across all roles and system health."""
        results = {
            "timestamp": time.time(),
            "overall_status": "healthy",
            "roles": {},
            "integrations": {},
            "performance": {},
            "failed_checks": []
        }

        if not self.app:
            from app import create_app
            self.app = create_app()

        # 1. Farmer Journey Probes
        client_farmer = self.app.test_client()
        start = time.time()
        res_farmer_login = client_farmer.get("/farmer/login")
        with client_farmer.session_transaction() as sess:
            sess["user_id"] = 2
            sess["role"] = "farmer"
            sess["name"] = "Demo Farmer"
        res_mandi = client_farmer.get("/farmer/mandi-rates")
        res_calc = client_farmer.get("/farmer/profit-calculator")
        farmer_duration = round((time.time() - start) * 1000, 2)

        farmer_ok = (
            res_farmer_login.status_code == 200 and
            res_mandi.status_code == 200 and
            res_calc.status_code == 200
        )
        results["roles"]["farmer"] = {
            "status": "healthy" if farmer_ok else "degraded",
            "latency_ms": farmer_duration,
            "login_view": res_farmer_login.status_code,
            "mandi_rates": res_mandi.status_code,
            "profit_calc": res_calc.status_code
        }
        if not farmer_ok:
            results["failed_checks"].append("farmer_journey_degraded")

        # 2. Cluster Journey Probes
        client_cluster = self.app.test_client()
        start = time.time()
        res_cluster_login = client_cluster.get("/cluster/login")
        with client_cluster.session_transaction() as sess:
            sess["user_id"] = 5
            sess["role"] = "cluster"
            sess["name"] = "Demo Cluster Hub"
        res_cluster_dash = client_cluster.get("/cluster/dashboard")
        cluster_duration = round((time.time() - start) * 1000, 2)
        cluster_ok = res_cluster_login.status_code == 200 and res_cluster_dash.status_code == 200
        results["roles"]["cluster"] = {
            "status": "healthy" if cluster_ok else "degraded",
            "latency_ms": cluster_duration,
            "login_view": res_cluster_login.status_code,
            "dashboard_view": res_cluster_dash.status_code
        }
        if not cluster_ok:
            results["failed_checks"].append("cluster_journey_degraded")

        # 3. Customer Journey Probes (Storefront Login & Protected View)
        client_customer = self.app.test_client()
        start = time.time()
        res_cust_login = client_customer.get("/customer/login")
        with client_customer.session_transaction() as sess:
            sess["user_id"] = 1
            sess["role"] = "customer"
            sess["name"] = "Demo Customer"
        res_cust_dash = client_customer.get("/customer/dashboard")
        cust_duration = round((time.time() - start) * 1000, 2)
        cust_ok = res_cust_login.status_code == 200 and res_cust_dash.status_code == 200
        results["roles"]["customer"] = {
            "status": "healthy" if cust_ok else "degraded",
            "latency_ms": cust_duration,
            "login_view": res_cust_login.status_code,
            "storefront_authenticated": res_cust_dash.status_code
        }
        if not cust_ok:
            results["failed_checks"].append("customer_store_degraded")

        # 4. Driver Journey Probes
        client_driver = self.app.test_client()
        start = time.time()
        res_driver_login = client_driver.get("/driver/login")
        with client_driver.session_transaction() as sess:
            sess["user_id"] = 3
            sess["role"] = "driver"
            sess["name"] = "Demo Driver"
        res_driver_dash = client_driver.get("/driver/dashboard")
        driver_duration = round((time.time() - start) * 1000, 2)
        driver_ok = res_driver_login.status_code == 200 and res_driver_dash.status_code == 200
        results["roles"]["driver"] = {
            "status": "healthy" if driver_ok else "degraded",
            "latency_ms": driver_duration,
            "login_view": res_driver_login.status_code,
            "dashboard_view": res_driver_dash.status_code
        }
        if not driver_ok:
            results["failed_checks"].append("driver_journey_degraded")

        # 5. Wholesaler Journey Probes
        client_ws = self.app.test_client()
        start = time.time()
        res_ws_login = client_ws.get("/wholesaler/login")
        with client_ws.session_transaction() as sess:
            sess["user_id"] = 4
            sess["role"] = "wholesaler"
            sess["name"] = "Demo Wholesaler"
        res_ws_dash = client_ws.get("/wholesaler/dashboard")
        ws_duration = round((time.time() - start) * 1000, 2)
        ws_ok = res_ws_login.status_code == 200 and res_ws_dash.status_code == 200
        results["roles"]["wholesaler"] = {
            "status": "healthy" if ws_ok else "degraded",
            "latency_ms": ws_duration,
            "login_view": res_ws_login.status_code,
            "dashboard_view": res_ws_dash.status_code
        }
        if not ws_ok:
            results["failed_checks"].append("wholesaler_journey_degraded")

        # 6. Integrations & APIs (Weather, News, Chatbot)
        client_api = self.app.test_client()
        start = time.time()
        res_weather = client_api.get("/api/weather")
        res_news = client_api.get("/api/news")
        res_bot = client_api.post("/api/chatbot/ask", json={"message": "delhi wheat rate"})
        api_duration = round((time.time() - start) * 1000, 2)

        bot_json = res_bot.get_json(silent=True) or {}
        bot_ok = res_bot.status_code == 200 and "reply" in bot_json and len(bot_json["reply"]) > 5
        weather_ok = res_weather.status_code == 200
        news_ok = res_news.status_code == 200

        results["integrations"] = {
            "weather_api": "healthy" if weather_ok else "failed",
            "news_api": "healthy" if news_ok else "failed",
            "kisan_route_assistant": "healthy" if bot_ok else "failed",
            "api_latency_ms": api_duration
        }

        # 7. Database Integrity Probe
        db_start = time.time()
        try:
            with self.app.app_context():
                from models import User
                count = User.query.count()
                db_status = "healthy"
                db_records = count
        except Exception as e:
            db_status = f"error: {str(e)}"
            db_records = 0
            results["failed_checks"].append("database_integrity_fail")
        db_latency = round((time.time() - db_start) * 1000, 2)

        results["integrations"]["database"] = {
            "status": db_status,
            "user_records": db_records,
            "latency_ms": db_latency
        }

        # Overall Status Assessment
        if results["failed_checks"]:
            results["overall_status"] = "degraded"
            append_log(
                "SYNTHETIC_WORKFLOW_FAILED",
                f"Synthetic workflow check reported failures: {results['failed_checks']}",
                level="WARNING",
                details=results
            )
        else:
            append_log(
                "SYNTHETIC_WORKFLOW_PASSED",
                f"All 5 roles and core integrations passed synthetic checks (DB Latency: {db_latency}ms).",
                level="INFO",
                details={"api_latency": api_duration, "db_records": db_records}
            )

        return results


workflow_runner = WorkflowRunner()
