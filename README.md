# Heating Oil Route Planner (Local UI)

This is a local, installable MVP that:

- Takes a depot address + a list of delivery addresses
- Optimizes the stop order while respecting:
  - Delivery window: 8:00 AM to 6:00 PM Eastern
  - Service time per stop (default 20 minutes; can be overridden per address in `data/stop_context.json`)
  - Optional lunch break window: 11:30 AM to 1:00 PM (skippable if infeasible)
  - Return to depot at the end
- Returns a schedule with 30-minute ETA windows and a **single multi-stop Google Maps directions link**

## 1) Install

### Windows (PowerShell)

```powershell
cd path\to\oil_route_planner
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### macOS/Linux

```bash
cd path/to/oil_route_planner
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2) Add your Google Maps API key (recommended)

Copy the example env file and add your key:

```bash
cp .env.example .env
```

Then edit `.env` and set:

```
GOOGLE_MAPS_API_KEY=YOUR_KEY_HERE
```

If you do not set a key, the app will still run, but it will use synthetic travel times (the schedule will be feasible, but routing is not geographically accurate).

## 3) Run the app

```bash
uvicorn app.main:app --reload
```

Open:

- http://127.0.0.1:8000

## 4) Stop notes / service times (lightweight local “RAG”)

Edit:

- `data/stop_context.json`

Add entries like:

```json
{
  "match": "55 Elm St, Bloomfield, NJ",
  "service_minutes": 25,
  "notes": ["Dog in yard", "Fill pipe behind gate"],
  "time_window": {"start": "09:00", "end": "18:00"}
}
```

The app uses fuzzy matching to attach notes/service times to the closest address.

## Notes

- All times are interpreted in America/New_York (ET).
- The “Google Maps” link is a single multi-stop directions link (origin=depot, destination=depot, waypoints=all stops). Depending on platform, very long waypoint lists can sometimes be unreliable, but this MVP generates the single-link format as requested.
