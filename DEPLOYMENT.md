# Deployment Guide

## Option 1: Streamlit Cloud (Recommended for Frontend)

### Quick Deploy
1. Push to GitHub
2. Visit https://share.streamlit.io
3. Click "New app" and select:
   - Repository: dlj2131-sys/Load-Logic
   - Branch: main
   - Main file: streamlit_app.py

### Set Backend URL
- App settings → Secrets
- Add: `API_BASE_URL=https://your-backend-api.com`

### Pros: Free, automatic HTTPS, no server management
### Cons: Needs backend deployed elsewhere

---

## Option 2: Render (Simple, Cheap)

### Deploy Backend
- New → Web Service
- Connect GitHub repo
- Build: `pip install -r requirements.txt`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

### Deploy Frontend
- New → Web Service
- Build: `pip install -r streamlit_requirements.txt`
- Start: `streamlit run streamlit_app.py --server.port 8000 --server.headless true`
- Environment: `API_BASE_URL=https://your-backend-url`

### Cost: ~$7/month hobby tier

---

## Option 3: Docker Compose (Most Control)

### Create docker-compose.yml
```yaml
version: '3.8'
services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GOOGLE_MAPS_API_KEY=${GOOGLE_MAPS_API_KEY}
    volumes:
      - ./data:/app/data

  frontend:
    image: python:3.9
    working_dir: /app
    command: >
      sh -c "pip install -r streamlit_requirements.txt &&
             streamlit run streamlit_app.py"
    ports:
      - "8501:8501"
    environment:
      - API_BASE_URL=http://backend:8000
    depends_on:
      - backend
```

### Run
```bash
docker-compose up
```

---

## Local Development

### Terminal 1 (Backend)
```bash
python -m uvicorn app.main:app --reload
```

### Terminal 2 (Frontend)
```bash
streamlit run streamlit_app.py
```

Access: http://localhost:8501

---

## Deployment Checklist

- [ ] Code committed to GitHub
- [ ] `streamlit_app.py` in repo root
- [ ] `streamlit_requirements.txt` created
- [ ] Backend deployed (Render, Railway, etc.)
- [ ] `API_BASE_URL` environment variable set
- [ ] Frontend deployed (Streamlit Cloud or Docker)
- [ ] Test all features work
- [ ] Google Maps API key configured (if needed)

---

## Cost Estimate

| Service | Cost |
|---------|------|
| Streamlit Cloud (Frontend) | Free |
| Render (Backend) | $7/month |
| **Total** | **$7/month** |

Or free tier only: $0/month with some limitations

