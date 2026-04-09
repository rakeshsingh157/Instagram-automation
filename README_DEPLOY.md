# 🚀 Deployment Guide for Render.com

Follow these steps to put your Instagram Automation Bot online.

## Step 1: Push to GitHub
1. Create a new **Private** repository on GitHub.
2. Push your project code to that repository.
   ```bash
   git init
   git add .
   git commit -m "initial commit"
   git remote add origin https://github.com/yourusername/your-repo-name.git
   git push -u origin main
   ```

## Step 2: Create Web Service on Render
1. Go to [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** and select **Blueprint**.
3. Connect your GitHub repository.
4. Render will detect the `render.yaml` file and prepare the service.

## Step 3: Configure Environment Variables
In the Render dashboard, go to your service settings and ensure these **Environment Variables** are filled:

| Variable | Description |
| --- | --- |
| `DATABASE_URL` | Your MySQL connection string (e.g. `mysql://user:pass@host/db`) |
| `INSTAGRAM_ACCESS_TOKEN` | Your Meta Graph API Permanent Token |
| `INSTAGRAM_PAGE_ID` | Your Instagram Business Account ID |
| `PUBLIC_URL` | The URL Render gives you (e.g. `https://your-bot.onrender.com`) |
| `CLOUDINARY_API_KEY` | From your Cloudinary Dashboard |
| `JSON2VIDEO_API_KEY` | From your Json2Video Dashboard |
| `HUGGINGFACE_API_KEY` | Your HF token for Flux Image generation |
| `BOT_USERNAME` | Admin username for your dashboard |
| `BOT_PASSWORD` | Admin password for your dashboard |

## Step 4: Keep-Alive (For Free Tier)
If you are on the **Free Tier**, your bot will "sleep" after 15 minutes. Use a service like **[Cron-job.org](https://cron-job.org/)** to ping your bot's `/ping` URL every 10 minutes:
`https://your-bot.onrender.com/ping`

This will keep the scheduler awake 24/7 for free! 🚀
