# Streamlit Cloud Deployment Guide

This guide will help you deploy your Heating Oil Route Planner to Streamlit Cloud.

## Prerequisites

1. ✅ Your code is on GitHub: `https://github.com/dlj2131-sys/Load-Logic.git`
2. A Streamlit Cloud account (sign up at https://streamlit.io/cloud)
   - **Note**: If your account was blocked, you may need to:
     - Contact Streamlit support to resolve the issue
     - Create a new account with a different email
     - Wait for the fair-use limit to reset

## Step 1: Prepare Your Repository

✅ Your repository is already prepared with:
- `streamlit_app.py` - Main Streamlit application
- `requirements.txt` - All dependencies including `nest-asyncio` for async handling
- Proper file structure

## Step 2: Deploy to Streamlit Cloud

1. **Go to Streamlit Cloud**
   - Visit: https://share.streamlit.io/
   - Sign in with your GitHub account

2. **Create a New App**
   - Click **"New app"** button
   - Select your repository: `dlj2131-sys/Load-Logic`
   - Branch: `main`
   - Main file path: `streamlit_app.py`

3. **Configure Secrets (Required for Address Geocoding)**
   - Click **"Advanced settings"** to expand
   - Click **"Secrets"** tab
   - Add your Google Maps API key:
     ```toml
     GOOGLE_MAPS_API_KEY = "your-actual-api-key-here"
     ```
   - Click **"Save"**

4. **Deploy**
   - Click **"Deploy!"**
   - Streamlit Cloud will:
     - Install dependencies from `requirements.txt`
     - Build your app
     - Deploy it
   - Wait ~2-5 minutes for the first deployment

5. **Access Your App**
   - Once deployed, you'll get a URL like: `https://your-app-name.streamlit.app`
   - The app will be live and accessible!

## Step 3: Using the App

### Without Google Maps API Key:
- You can still use the app with **coordinates** (lat,lon format)
- Example depot: `40.7128,-74.0060`
- Example stop: `40.7589,-73.9851`
- The app will work but won't geocode addresses

### With Google Maps API Key:
- You can use **full addresses**
- Example depot: `123 Depot Rd, New York, NY 10001`
- Example stop: `456 Main St, Brooklyn, NY 11201`
- The app will automatically geocode addresses to coordinates

## Features

✅ **Route Planning**
- Enter depot (address or coordinates)
- Add multiple customer stops
- Specify gallons per stop (optional)
- Configure max drivers, stops per driver, and truck capacity

✅ **Route Optimization**
- Automatic clustering of stops
- Capacity-aware routing
- Google Maps links for each driver route

✅ **Results Display**
- Driver-by-driver breakdown
- Capacity checks
- Ordered delivery lists
- Clickable Google Maps links

## Troubleshooting

### App won't deploy
- ✅ Check that `streamlit_app.py` is in the root directory
- ✅ Check that `requirements.txt` includes all dependencies
- ✅ View deployment logs in Streamlit Cloud dashboard
- ✅ Check for any import errors in the logs

### Geocoding not working
- ✅ Make sure `GOOGLE_MAPS_API_KEY` is set in Streamlit Cloud secrets
- ✅ Check that your API key is valid
- ✅ Verify the Geocoding API is enabled in Google Cloud Console
- ✅ Use coordinates format if API key is not available

### Async/Event loop errors
- ✅ The app uses `nest-asyncio` to handle async in Streamlit
- ✅ This should be automatically installed from `requirements.txt`
- ✅ If you see errors, check that `nest-asyncio>=1.6.0` is in requirements.txt

### Import errors
- ✅ All dependencies should be in `requirements.txt`
- ✅ Check the deployment logs for missing packages
- ✅ Ensure the app structure matches what's expected

### Account blocked (403 error)
- Contact Streamlit support: support@streamlit.io
- Explain your use case
- They may be able to unblock your account
- Alternatively, create a new account with a different email

## File Structure

```
oil_route_planner_stage2/
├── streamlit_app.py          # Main Streamlit app (entry point) ✅
├── requirements.txt          # Python dependencies ✅
├── app/                      # Application code
│   ├── services/            # Business logic
│   │   ├── delivery_router.py
│   │   ├── maps.py
│   │   └── links.py
│   └── ...
└── ...
```

## Environment Variables

The app reads `GOOGLE_MAPS_API_KEY` from:
1. Streamlit secrets (in Streamlit Cloud) - **Recommended**
2. Environment variables (local development)
3. `.env` file (local development)

## Notes

- The Streamlit app uses the same backend logic as the FastAPI app
- It calls functions directly (not through HTTP)
- All route planning features are available in the Streamlit interface
- The app is optimized for Streamlit Cloud's environment
- Async functions are handled using `nest-asyncio` for compatibility

## Support

If you encounter issues:
1. Check the deployment logs in Streamlit Cloud
2. Verify all dependencies are in `requirements.txt`
3. Ensure `GOOGLE_MAPS_API_KEY` is set correctly in secrets
4. Contact Streamlit support if account issues persist
