# Deploy to Render.com - Quick Guide

Since Streamlit Cloud has account limitations, let's deploy your FastAPI app to Render.com instead. This is actually better suited for your application!

## Step-by-Step Deployment

### 1. Verify Your Code is on GitHub ✅
Your code is already at: `https://github.com/dlj2131-sys/Load-Logic.git`

### 2. Go to Render.com
1. Visit: https://render.com
2. Sign up or log in (you can use GitHub to sign in)

### 3. Create a New Web Service
1. Click **"New +"** button (top right)
2. Select **"Web Service"**
3. Connect your GitHub account if prompted
4. Select your repository: **`dlj2131-sys/Load-Logic`**

### 4. Configure the Service
Render should auto-detect your `render.yaml`, but verify these settings:

- **Name**: `oil-route-planner` (or your choice)
- **Environment**: `Python 3`
- **Region**: Choose closest to you
- **Branch**: `main`
- **Root Directory**: Leave empty (or `.` if needed)
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Plan**: **Free** (to start)

### 5. Add Environment Variables
Click **"Advanced"** and add:

- **Key**: `GOOGLE_MAPS_API_KEY`
  - **Value**: Your actual Google Maps API key
  - **Sync**: Unchecked (so it's not synced across environments)

- **Key**: `DEFAULT_DEPARTURE_TIME`
  - **Value**: `07:00`
  - **Sync**: Checked (optional)

- **Key**: `DEFAULT_SERVICE_MINUTES`
  - **Value**: `20`
  - **Sync**: Checked (optional)

### 6. Deploy!
1. Click **"Create Web Service"**
2. Render will:
   - Clone your repo
   - Install dependencies
   - Start your FastAPI app
3. Wait ~5-10 minutes for the first deployment

### 7. Access Your App
Once deployed, your app will be available at:
- `https://oil-route-planner.onrender.com` (or your chosen name)

You can access:
- Main app: `https://your-app.onrender.com/`
- Route planner: `https://your-app.onrender.com/admin/route-planner`
- Owner dashboard: `https://your-app.onrender.com/owner/dashboard`
- API docs: `https://your-app.onrender.com/docs`

## Notes

- **Free tier**: Apps sleep after 15 minutes of inactivity (first request may be slow)
- **Upgrade**: For always-on, upgrade to a paid plan ($7/month)
- **Custom domain**: You can add your own domain in settings
- **Logs**: View deployment and runtime logs in the Render dashboard

## Troubleshooting

### Build fails
- Check that `requirements.txt` has all dependencies
- View build logs in Render dashboard

### App won't start
- Verify `GOOGLE_MAPS_API_KEY` is set correctly
- Check runtime logs in Render dashboard
- Ensure `app.main:app` is the correct module path

### Slow first request
- This is normal on free tier (app wakes up)
- Consider upgrading for always-on performance

## Alternative: Railway.app

If Render doesn't work, try Railway:
1. Go to https://railway.app
2. New Project → Deploy from GitHub
3. Select your repo
4. Add `GOOGLE_MAPS_API_KEY` in Variables
5. Railway auto-detects Python and uses your `Procfile`
