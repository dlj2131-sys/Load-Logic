# Streamlit Frontend Setup

This document explains how to run Load Logic with a Streamlit frontend that wraps your existing FastAPI backend.

## Quick Start

### 1. Install Streamlit Dependencies

```bash
pip install -r streamlit_requirements.txt
```

Or install individually:
```bash
pip install streamlit requests pandas
```

### 2. Start the FastAPI Backend (in one terminal)

```bash
cd /path/to/Load-Logic
python -m uvicorn app.main:app --reload --port 8000
```

The backend will be available at `http://localhost:8000`

### 3. Start the Streamlit Frontend (in another terminal)

```bash
cd /path/to/Load-Logic
streamlit run streamlit_app.py
```

This will start the Streamlit app, typically available at `http://localhost:8501`

## Configuration

### Custom API URL

If your FastAPI backend runs on a different host/port, set the `API_BASE_URL` environment variable:

```bash
# Example: Running on a different machine
API_BASE_URL=http://192.168.1.100:8000 streamlit run streamlit_app.py
```

Or in your `.env` file:
```
API_BASE_URL=http://localhost:8000
```

## Features

The Streamlit frontend provides four main pages:

### 🗺️ Route Planner
- Input depot location (address or coordinates)
- Add delivery stops in an editable table
- Set optimization parameters (max drivers, stops per driver, truck capacity)
- Plan routes and view results with:
  - Driver assignments
  - Stop sequences
  - Capacity utilization
  - Google Maps links

### 📋 Pending Requests
- View all pending delivery requests
- See customer info, addresses, fuel quantities
- Filter by priority

### 📦 Book Delivery
- Customer booking form to submit delivery requests
- Captures:
  - Customer contact info
  - Delivery address
  - Tank details and current level
  - Fuel type and quantity
  - Special instructions and considerations
  - Preferred delivery date and priority

### 📊 Dashboard
- Overview metrics (pending requests, urgent orders, total gallons, empty tanks)
- Charts showing distribution by priority and tank level

## Deployment to Streamlit Cloud

### Prerequisites
- GitHub account with this repo
- Streamlit Cloud account

### Steps

1. **Push to GitHub** (if not already):
```bash
git add streamlit_app.py streamlit_requirements.txt
git commit -m "Add Streamlit frontend"
git push origin main
```

2. **Deploy to Streamlit Cloud**:
   - Go to https://share.streamlit.io
   - Click "New app"
   - Connect your GitHub repo
   - Set these values:
     - **Repository**: your-github/Load-Logic
     - **Branch**: main
     - **Main file path**: streamlit_app.py

3. **Configure Secrets** (in Streamlit Cloud dashboard):
   - Go to your app settings
   - Click "Secrets"
   - Add:
     ```
     API_BASE_URL = "https://your-backend-api.com"
     ```

## Local Development

### Running Both Locally

**Terminal 1 - Start FastAPI Backend:**
```bash
python -m uvicorn app.main:app --reload
```

**Terminal 2 - Start Streamlit:**
```bash
streamlit run streamlit_app.py
```

### Hot Reload
- FastAPI will auto-reload on code changes (with `--reload`)
- Streamlit will auto-reload on file changes

## Troubleshooting

### "API server is not responding"
- Make sure FastAPI backend is running on port 8000
- Check `API_BASE_URL` matches your backend address
- Verify backend is accessible: `curl http://localhost:8000/api/health`

### "Could not geocode depot"
- Ensure your Google Maps API key is configured in the backend's `.env`
- Or use coordinates (lat,lon) instead of addresses

### Module not found errors
- Reinstall requirements: `pip install -r streamlit_requirements.txt`
- Make sure you're using the correct Python environment

## Architecture

The Streamlit app is a **thin client** that calls your existing FastAPI backend APIs:

```
User → Streamlit UI → FastAPI Backend → Business Logic
         (localhost:8501)  (localhost:8000)
```

Benefits:
- Keeps backend intact
- Easy to switch frontends (web, mobile, etc.)
- Streamlit handles UI, FastAPI handles logic
- No code duplication

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_BASE_URL` | `http://localhost:8000` | FastAPI backend URL |

## Next Steps

1. **Run locally** and test all features
2. **Deploy backend** to a server (AWS, Heroku, etc.)
3. **Update API_BASE_URL** to point to deployed backend
4. **Deploy Streamlit** to Streamlit Cloud
5. **Share the link** with users

## Additional Resources

- [Streamlit Docs](https://docs.streamlit.io/)
- [Streamlit Cloud Deployment](https://docs.streamlit.io/streamlit-community-cloud/deploy-your-app)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
