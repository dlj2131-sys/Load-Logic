# Deploy Streamlit App on Render

Follow these steps to deploy your **Load Logic** Streamlit app on Render.

**Two apps:**
- **`streamlit_app.py`** — Route Planner only (simpler).
- **`full_streamlit_app.py`** — Full system: **Route Planner**, **Requests**, **Book**, **Dashboard** (no backend API).

Use **`full_streamlit_app.py`** for the full app.

---

## 1. Push your code to GitHub

Make sure your latest code is on GitHub:

```bash
git add .
git commit -m "Ready for Render deployment"
git push origin main
```

Repo: `https://github.com/dlj2131-sys/Load-Logic`

---

## 2. Open Render

1. Go to **https://render.com**
2. Sign in (use **"Sign in with GitHub"**)
3. Allow Render to access your GitHub if prompted

---

## 3. Create a new Web Service

1. Click the **"New +"** button (top right)
2. Choose **"Web Service"**
3. Find **"dlj2131-sys/Load-Logic"** in the list and click **"Connect"**
   - If you don’t see it, click **"Configure account"** and grant access to that repo

---

## 4. Configure the service

Use these **exact** values:

| Field | Value |
|-------|--------|
| **Name** | `load-logic` (or `oil-route-planner`) |
| **Region** | e.g. **Oregon (US West)** or **Frankfurt** – pick closest to you |
| **Branch** | `main` |
| **Root Directory** | *(leave blank)* |
| **Runtime** | **Python 3** |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `streamlit run full_streamlit_app.py --server.port $PORT --server.address 0.0.0.0` |

**Start Command (copy‑paste) for full app:**
```
streamlit run full_streamlit_app.py --server.port $PORT --server.address 0.0.0.0
```

For route-planner-only: use `streamlit_app.py` instead of `full_streamlit_app.py`.

---

## 5. Add environment variable

1. Scroll to **"Environment"** (or **"Environment Variables"**)
2. Click **"Add Environment Variable"** (or **"Add Variable"**)
3. **Key:** `GOOGLE_MAPS_API_KEY`
4. **Value:** your Google Maps API key
5. Click **"Add"** (or **Save**)

---

## 6. Deploy

1. Click **"Create Web Service"**
2. Render will:
   - Clone your repo
   - Run `pip install -r requirements.txt`
   - Start Streamlit with the command above
3. Wait **5–15 minutes** for the first build (especially with heavier deps)
4. Check the **Logs** tab for progress or errors

---

## 7. Use your app

When the deploy shows **"Live"** (green):

- Your app URL will be something like: **`https://load-logic.onrender.com`**
- Open it in a browser – you’ll see **Load Logic** with Route Planner, Requests, Book, and Dashboard

**Note:** On Render’s free tier, `data/` (requests, routes) is ephemeral and resets on redeploy. For a persistent DB you’d need to add one later.

---

## Troubleshooting

### Build fails (e.g. `sentence-transformers`, `ortools`, etc.)

Your `requirements.txt` has extra packages. If the build fails or times out:

1. Open the **Build logs** on Render.
2. In **Build Command**, change to:
   ```
   pip install -r requirements-render.txt
   ```
3. The repo includes `requirements-render.txt` with only what the route planner needs. **Redeploy**.

### App crashes or "Application failed to respond"

- Check the **Logs** tab (runtime logs, not build).
- Ensure **Start Command** is exactly:
  ```bash
  streamlit run full_streamlit_app.py --server.port $PORT --server.address 0.0.0.0
  ```

### Slow first load

- On the **free** plan, the app sleeps after ~15 minutes of no traffic.
- The first request after sleep can take **30–60 seconds** to wake it up. That’s normal.

### Google Maps / geocoding not working

- Confirm `GOOGLE_MAPS_API_KEY` is set in **Environment** on Render.
- Redeploy after changing env vars if needed.

---

## Summary

| Step | What you do |
|------|-------------|
| 1 | Push code to GitHub |
| 2 | Go to render.com, sign in with GitHub |
| 3 | New + → Web Service → Connect `Load-Logic` |
| 4 | Set Build Command, Start Command (`full_streamlit_app.py`), Branch = `main` |
| 5 | Add `GOOGLE_MAPS_API_KEY` |
| 6 | Create Web Service, wait for "Live" |
| 7 | Open the given URL |

You’ll have your **Streamlit** app running on Render.
