# Render Deployment Guide

## Overview

This project has been configured to run on Render's free tier. The key challenge with Render's free tier is that services must expose an HTTP endpoint, otherwise they get shut down. This bot has been modified to run a dummy FastAPI server in the background while the scraper/bot runs in the main thread.

## How It Works

1. **FastAPI Server**: A lightweight FastAPI server runs in a background thread listening on the PORT environment variable provided by Render
2. **Health Endpoints**: 
   - `GET /` returns `{"status": "Bot and Scraper are running!"}`
   - `GET /health` returns `{"status": "healthy"}`
3. **Bot Process**: The main bot/scraper runs in the main thread as usual, polling for new projects and sending alerts
4. **Render Detection**: Render regularly pings the HTTP endpoint to verify the service is alive. If it doesn't respond, the service is terminated.

## Deployment Steps

### Option 1: Using render.yaml (Recommended)

1. Push your code to GitHub
2. Connect your GitHub repo to Render at https://dashboard.render.com
3. Click "New +" → "Web Service"
4. Select your repository
5. Render will automatically detect `render.yaml` and use those settings

**Key Configuration in render.yaml:**
- Plan: `free` (uses free tier)
- Start Command: `python monitor.py`
- Environment variables: PORT is set to 10000

### Option 2: Manual Setup via Render Dashboard

1. Create a new "Web Service" on Render
2. Connect your GitHub repository
3. Configure:
   - **Runtime**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python monitor.py`
4. Add Environment Variables:
   - `TELEGRAM_BOT_TOKEN`: Your bot token
   - `TELEGRAM_CHAT_ID`: Your chat ID
   - Any other environment variables your bot needs

### Option 3: Using Procfile

If Render doesn't automatically detect configuration, you can use the `Procfile`:

```
web: python monitor.py
```

Render will read this and use it for deployment.

## Environment Variables

Make sure to set these in Render's dashboard:

- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
- `TELEGRAM_CHAT_ID`: Your Telegram chat/channel ID
- `REQUEST_TIMEOUT`: (Optional) Request timeout in seconds
- `POLL_INTERVAL`: (Optional) Polling interval in seconds

## Monitoring

After deployment:

1. Visit `https://your-service-name.onrender.com/` to verify the service is running
2. Check the "Logs" tab in Render dashboard for bot output
3. The service will automatically restart if it crashes

## Free Tier Notes

- Free tier services go into an idle state after 15 minutes of inactivity
- If someone accesses the service, it automatically wakes up
- For production use, consider upgrading to a paid plan for guaranteed uptime

## Technical Details

**What Changed:**
- Added `fastapi` and `uvicorn` to requirements.txt
- Modified `main.py` to:
  - Import FastAPI, uvicorn, os, and threading modules
  - Create a FastAPI app with health check endpoints
  - Start the API server in a daemon thread before running the main bot loop
  - The daemon thread means when the bot exits, the server will exit too

**Files Modified:**
- `requirements.txt` - Added FastAPI and uvicorn dependencies
- `src/mostaql_alert/main.py` - Added FastAPI setup and threading logic

**Files Created:**
- `Procfile` - Tells Render how to start the application
- `render.yaml` - Detailed Render configuration (optional but recommended)

## Troubleshooting

### Service keeps crashing

Check the logs in Render dashboard. Common issues:
- Missing environment variables (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
- Network issues (check if Mostaqel website is accessible)
- Configuration errors in filters.yml

### Service starts but bot doesn't send alerts

1. Make sure your Telegram credentials are correct
2. Ensure the bot is started or added to your Telegram chat
3. Check that filters.yml is properly configured
4. Look for errors in the Render logs

### Port already in use

The code automatically gets the PORT from the environment. Render assigns this dynamically, so it should work fine. If testing locally, set the PORT environment variable:

```bash
export PORT=8000
python monitor.py
```
