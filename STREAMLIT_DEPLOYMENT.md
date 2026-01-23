# Streamlit Cloud Deployment Guide

This guide will help you deploy your Heating Oil Route Planner to Streamlit Cloud.

## Prerequisites

1. A GitHub account
2. Your repository pushed to GitHub (already done ✅)
3. A Streamlit Cloud account (sign up at https://streamlit.io/cloud)

## Step 1: Push to GitHub

Your code has already been pushed to GitHub at:
- Repository: `https://github.com/dlj2131-sys/Load-Logic.git`

## Step 2: Deploy to Streamlit Cloud

1. **Go to Streamlit Cloud**
   - Visit: https://share.streamlit.io/
   - Sign in with your GitHub account

2. **Create a New App**
   - Click "New app" button
   - Select your repository: `dlj2131-sys/Load-Logic`
   - Branch: `main`
   - Main file path: `streamlit_app.py`

3. **Configure Secrets (Optional but Recommended)**
   - Click "Advanced settings"
   - Add your Google Maps API key as a secret:
     - Key: `GOOGLE_MAPS_API_KEY`
     - Value: Your actual API key
   - This allows the app to geocode addresses

4. **Deploy**
   - Click "Deploy!"
   - Streamlit Cloud will build and deploy your app
   - You'll get a URL like: `https://your-app-name.streamlit.app`

## Step 3: Using the App

### Without Google Maps API Key:
- You can still use the app with coordinates (lat,lon format)
- Example depot: `40.7128,-74.0060`
- Example stop: `40.7589,-73.9851`

### With Google Maps API Key:
- You can use full addresses
- Example depot: `123 Depot Rd, New York, NY 10001`
- Example stop: `456 Main St, Brooklyn, NY 11201`
- The app will geocode addresses automatically

## Troubleshooting

### App won't deploy
- Check that `streamlit_app.py` is in the root directory ✅
- Check that `requirements.txt` includes all dependencies ✅
- Check the deployment logs in Streamlit Cloud dashboard

### Geocoding not working
- Make sure `GOOGLE_MAPS_API_KEY` is set in Streamlit Cloud secrets
- Check that your API key is valid and has the Geocoding API enabled

### Import errors
- All dependencies should be in `requirements.txt`
- Make sure the app structure matches what's expected

## File Structure

```
oil_route_planner_stage2/
├── streamlit_app.py          # Main Streamlit app (entry point)
├── requirements.txt          # Python dependencies
├── app/                      # Application code
│   ├── main.py              # FastAPI app (not used in Streamlit)
│   ├── services/            # Business logic
│   └── ...
└── ...
```

## Notes

- The Streamlit app uses the same backend logic as the FastAPI app
- It calls functions directly (not through HTTP)
- All route planning features are available in the Streamlit interface
