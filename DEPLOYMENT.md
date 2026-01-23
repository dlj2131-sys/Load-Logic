# Deployment Guide

This FastAPI application can be deployed to several platforms. Here are the recommended options:

## Option 1: Render.com (Recommended for FastAPI)

1. **Push your code to GitHub** (if not already):
   ```bash
   git add .
   git commit -m "Ready for deployment"
   git push origin main
   ```

2. **Go to Render.com**:
   - Sign up/login at https://render.com
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select your repository

3. **Configure the service**:
   - **Name**: `oil-route-planner` (or your choice)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free tier is fine to start

4. **Environment Variables**:
   - Add `GOOGLE_MAPS_API_KEY` (your Google Maps API key)
   - Add `DEFAULT_DEPARTURE_TIME` = `07:00` (optional)
   - Add `DEFAULT_SERVICE_MINUTES` = `20` (optional)

5. **Deploy**: Click "Create Web Service"

Your app will be available at: `https://your-app-name.onrender.com`

---

## Option 2: Railway.app

1. **Install Railway CLI** (optional):
   ```bash
   npm i -g @railway/cli
   ```

2. **Deploy**:
   - Go to https://railway.app
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository
   - Railway will auto-detect it's a Python app
   - Add environment variables in the dashboard

3. **The `Procfile` is already configured** for Railway

---

## Option 3: Streamlit Cloud (Requires Conversion)

Since this is a FastAPI app, Streamlit Cloud isn't ideal. However, you can:

1. **Use the `streamlit_app.py` wrapper** (created for you)
2. **Deploy to Streamlit Cloud**:
   - Go to https://share.streamlit.io
   - Connect your GitHub repo
   - Set main file to: `streamlit_app.py`
   - Add secrets for `GOOGLE_MAPS_API_KEY`

**Note**: The Streamlit wrapper is a workaround. For best performance, use Render or Railway.

---

## Option 4: Fly.io

1. **Install Fly CLI**:
   ```bash
   powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"
   ```

2. **Login and deploy**:
   ```bash
   fly auth login
   fly launch
   ```

3. **Set secrets**:
   ```bash
   fly secrets set GOOGLE_MAPS_API_KEY=your_key_here
   ```

---

## Environment Variables Needed

Make sure to set these in your deployment platform:

- `GOOGLE_MAPS_API_KEY` - Your Google Maps API key (required for geocoding)
- `DEFAULT_DEPARTURE_TIME` - Default departure time (optional, default: 07:00)
- `DEFAULT_SERVICE_MINUTES` - Default service time per stop (optional, default: 20)

---

## Quick Deploy to Render (Easiest)

1. Push to GitHub
2. Go to https://render.com
3. New Web Service → Connect GitHub → Select repo
4. Use these settings:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add `GOOGLE_MAPS_API_KEY` in Environment
6. Deploy!

Your app will be live in ~5 minutes! 🚀
