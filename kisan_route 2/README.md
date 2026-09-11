# Kisan Route — Hackathon Prototype

A multi-page, role-based Flask website for an agri-tech platform connecting
**farmers, farmer clusters, customers, drivers, and wholesalers**. Backend,
routing, and page logic are all Python (Flask + Jinja templates) — no
frontend framework, no build step.

Everything runs locally with **zero paid services**: OTP, payments, crop
grading, and route optimization are all mock/placeholder modules, clearly
marked in the code so real APIs can replace them later without touching
anything else.

---

## 1. What you need installed (once)

- **Python 3.10+** — check with `python3 --version` (Windows: `python --version`)
- **VS Code** with the **Python extension** (Microsoft) installed
- That's it — no Node, no database server (SQLite is a single file).

---

## 2. Open the project in VS Code (click by click)

1. Unzip `kisan_route.zip` somewhere sensible, e.g. `Desktop/kisan_route`.
2. Open **VS Code**.
3. **File → Open Folder…** → select the unzipped `kisan_route` folder → **Select Folder**.
4. VS Code will show the file tree on the left: `app.py`, `blueprints/`, `templates/`, `static/`, etc.
5. Open **Terminal → New Terminal** from the top menu. A terminal panel opens at the bottom, already pointed at the project folder.

---

## 3. Create a virtual environment (click by click)

A virtual environment keeps this project's Python packages separate from
everything else on your machine. In the terminal you just opened:

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows (PowerShell):**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

You'll know it worked because the terminal prompt now starts with `(venv)`.

> If VS Code pops up a notification bottom-right saying *"We noticed a new
> virtual environment... Select it for the workspace?"* → click **Yes**.
> If it doesn't ask, press `Ctrl+Shift+P` (`Cmd+Shift+P` on Mac), type
> **Python: Select Interpreter**, press Enter, and choose the one that
> shows `('venv': venv)`.

---

## 4. Install dependencies (one command)

Still in the same terminal, with `(venv)` showing:

```bash
pip install -r requirements.txt
```

This installs Flask, Flask-SQLAlchemy, and Werkzeug — three small packages.
It takes a few seconds.

---

## 5. Run the app

```bash
python app.py
```

You should see something like:

```
 * Running on http://127.0.0.1:5000
 * Debug mode: on
```

The **first run** also creates `kisanroute.db` (a SQLite file) in the
project folder — that's your database, already set up, nothing to configure.

Open your browser to **http://127.0.0.1:5000** — you should see the Kisan
Route homepage with the rotating background, the "⋮" menu button top-left,
and role buttons.

To stop the server later: click into the terminal and press `Ctrl+C`.

---

## 6. Try every role (suggested demo order)

Use the **⋮ menu** (top-left) or the role buttons on the homepage.

| Role | Try this |
|---|---|
| 🌾 **Farmer** | Sign up → note the on-screen demo OTP → verify → log in → try Crop Quality Check (upload any image), Mandi Rate Detector, Net Profit Calculator, Shipment Tracking |
| 🤝 **Farmer Cluster** | Sign up → verify → log in → search farmers, "Add to group", try Cost Splitting |
| 🛒 **Customer** | Sign up (accept terms) → log in → order a crop → choose **UPI** → simulate payment → see tracking |
| 🚚 **Driver** | Sign up → log in → fill out the one-time profile setup → accept a delivery request → see the optimized route |
| 🏬 **Wholesaler** | Sign up → log in → filter by crop → negotiate a price on a listing |

Also try, on any page:
- The **language dropdown** (top-right) — switch to हिंदी and back.
- The **💬 chatbot** (bottom-right) — it shows role-aware quick questions and answers from the Flask backend.
- The **🎙️ voice button** — it speaks a short greeting out loud using your browser's built-in text-to-speech (Chrome/Edge support this well).
- The **carousel Pause/Play** button and **‹ ›** arrows on the homepage.

---

## 7. Project structure

```
kisan_route/
├── app.py                  # App factory: registers blueprints, sets up i18n
├── config.py                # Settings (secret key, DB path, upload folder)
├── extensions.py             # Shared SQLAlchemy instance
├── models.py                 # Single User model (role column + JSON extra fields)
├── requirements.txt
├── blueprints/                # One file per role = one set of routes
│   ├── main.py                # Home, About, language switch, chatbot API
│   ├── farmer.py
│   ├── cluster.py
│   ├── customer.py
│   ├── driver.py
│   └── wholesaler.py
├── utils/                     # Swappable mock/placeholder logic
│   ├── otp.py                 # Mock OTP generation/verification
│   ├── payment.py              # Mock UPI payment simulation
│   ├── crop_quality.py          # Placeholder computer-vision grading
│   ├── mandi.py                # Mock mandi rate data (7 regions)
│   ├── route_optimizer.py       # Placeholder route optimizer
│   ├── chatbot.py              # Mock chatbot prompts + canned answers
│   └── auth.py                 # @login_required(role) decorator
├── translations/
│   └── strings.py             # LANGUAGES list + TRANSLATIONS dict (en, hi filled in)
├── templates/
│   ├── base.html               # Shared layout: navbar, chatbot, voice button, footer
│   ├── home.html / about.html
│   ├── partials/                # navbar, chatbot, voice assistant, footer
│   ├── farmer/ ... wholesaler/  # One folder per role's pages
└── static/
    ├── css/style.css           # All styling (earthy green / off-white theme)
    ├── js/main.js                # Menu, carousel, chatbot, voice assistant behavior
    ├── images/                  # Put real photos here (see images/README.txt)
    └── uploads/                 # Farmer/cluster crop photo uploads land here
```

**Why one `User` table for every role?** Each role needs slightly different
signup fields (Aadhaar for farmers, vehicle number for drivers, business
name for wholesalers, and so on). Instead of five separate tables, `User`
has the common fields as real columns (`role`, `full_name`, `phone`,
`password_hash`) and everything role-specific in one JSON column
(`extra_json`, via `get_extra()` / `set_extra()`). This keeps the schema
simple for a hackathon build; splitting into per-role tables later is a
straightforward refactor if you need it.

---

## 8. Where the mock systems are (and how to replace them later)

Every placeholder is isolated in `utils/`, so swapping in a real service
means editing one file, not hunting through templates:

| Mock module | Replace with, eventually |
|---|---|
| `utils/otp.py` | Real SMS via MSG91, Twilio, etc. |
| `utils/payment.py` | Real UPI/payment gateway (Razorpay, Cashfree, etc.) |
| `utils/crop_quality.py` | A real trained CNN/vision model served via an API |
| `utils/mandi.py` | A live mandi price API or scraped/official dataset |
| `utils/route_optimizer.py` | OSRM, Google Directions, or a custom VRP solver |
| `utils/chatbot.py` | A real LLM-backed assistant behind the same `/api/chatbot/*` routes |

The homepage carousel uses CSS-gradient placeholders instead of photos —
see `static/images/README.txt` for exactly which files to drop in and
which line to change in `static/css/style.css`.

---

## 9. Adding another language

Open `translations/strings.py`:

1. Add the language code + display name to the `LANGUAGES` list (several
   are already listed but not yet translated — they currently fall back to
   English automatically).
2. Add a new entry to the `TRANSLATIONS` dict with the same keys as `"en"`.

Nothing else needs to change — `app.py`'s `t()` helper and every template
already use these keys.

---

## 10. Troubleshooting

**"externally-managed-environment" error when running `pip install`**
You're not inside the virtual environment. Re-run step 3's activate
command — the prompt should show `(venv)` before you `pip install`.

**`ModuleNotFoundError: No module named 'flask'`**
Same cause — activate the venv first, then `pip install -r requirements.txt`.

**"Address already in use" / port 5000 busy**
Another program is using port 5000 (common on Macs, due to AirPlay Receiver).
Run instead: `flask --app app run --port 5001` and open
`http://127.0.0.1:5001`. Or turn off AirPlay Receiver in macOS System
Settings → General → AirPlay Receiver.

**Changes to a template don't show up**
Make sure the terminal still shows the server running with
`Debug mode: on` — it auto-reloads on save. If you stopped it, just run
`python app.py` again.

**Uploaded crop photo doesn't show**
Only common image formats are previewed; the grading result still appears
either way since it's a placeholder based on the filename, not real
image analysis.

**Want to start over with a clean database**
Stop the server, delete `kisanroute.db`, run `python app.py` again — a
fresh empty database is created automatically.

---

## 11. Presenting tomorrow — a few honest talking points

- The backend, routing, and every page is real, working Python/Flask — not a static mockup.
- OTP, payments, crop grading, and route optimization are clearly-marked
  mock modules for the demo; the architecture is built so real APIs drop
  into `utils/` without touching routes or templates.
- The language system is genuinely modular (add a language = add one dict
  entry) but only English and Hindi are fully translated right now — say
  so if asked, rather than implying full coverage.
- The chatbot is real client → Flask API → response, not just hardcoded
  JavaScript, which is worth mentioning if judges ask about the "AI" layer.
