# GitHub Actions Deployment Setup

This guide will help you set up automatic deployment using GitHub Actions.

## What This Does

Every time you push code to the `main` branch:
- ✅ Frontend automatically deploys to Vercel
- ✅ Backend automatically deploys to Railway
- ✅ No manual deployment needed!

---

## Prerequisites

1. **Vercel Account** - Sign up at https://vercel.com
2. **Railway Account** - Sign up at https://railway.app
3. **GitHub Repository** - Your Finvestor repo (already have this!)

---

## Step 1: Setup Vercel (Frontend)

### 1.1 Create Vercel Project
1. Go to https://vercel.com/dashboard
2. Click "Add New" → "Project"
3. Import your Finvestor GitHub repository
4. Configure:
   - **Framework Preset**: Vite
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
5. Click "Deploy" (just once, manually)

### 1.2 Get Vercel Credentials
1. Go to https://vercel.com/account/tokens
2. Create a new token
3. Copy the token (save it for later)

4. Go to your Vercel project settings
5. Copy your **Project ID** and **Org ID** from the settings page

### 1.3 Add Secrets to GitHub
1. Go to your GitHub repo: `Settings` → `Secrets and variables` → `Actions`
2. Click "New repository secret" and add:

| Secret Name | Value | Where to Find |
|------------|-------|---------------|
| `VERCEL_TOKEN` | Your Vercel token | From step 1.2 |
| `VERCEL_ORG_ID` | Your organization ID | Vercel project settings |
| `VERCEL_PROJECT_ID` | Your project ID | Vercel project settings |
| `VITE_API_URL` | Your backend URL | From Railway (step 2) |

---

## Step 2: Setup Railway (Backend)

### 2.1 Create Railway Project
1. Go to https://railway.app/dashboard
2. Click "New Project"
3. Choose "Deploy from GitHub repo"
4. Select your Finvestor repository
5. Railway will detect your Python backend automatically

### 2.2 Add PostgreSQL Database
1. In your Railway project, click "New"
2. Select "Database" → "PostgreSQL"
3. Railway will automatically create a database
4. Copy the `DATABASE_URL` from the database settings

### 2.3 Configure Environment Variables
In your Railway backend service, add these variables:
- `DATABASE_URL` - (auto-populated from PostgreSQL)
- `FINNHUB_API_KEY` - Your Finnhub API key
- `ALPHAVANTAGE_API_KEY` - Your AlphaVantage API key
- Any other secrets from your `backend/.env`

### 2.4 Get Railway Token
1. Go to https://railway.app/account/tokens
2. Create a new token
3. Copy the token

### 2.5 Add Railway Secret to GitHub
1. Go to your GitHub repo: `Settings` → `Secrets and variables` → `Actions`
2. Click "New repository secret"
3. Add:

| Secret Name | Value | Where to Find |
|------------|-------|---------------|
| `RAILWAY_TOKEN` | Your Railway token | From step 2.4 |

### 2.6 Get Your Backend URL
1. After Railway deploys, go to your backend service
2. Go to "Settings" → "Domains"
3. Copy your Railway URL (e.g., `https://your-app.railway.app`)
4. Add this as `VITE_API_URL` secret in GitHub (from step 1.3)

---

## Step 3: Test Automatic Deployment

Now you're all set! Test it:

1. Make a small change to your code
2. Commit and push to `main`:
   ```bash
   git add .
   git commit -m "Test automatic deployment"
   git push
   ```
3. Go to your GitHub repo → "Actions" tab
4. Watch your workflows run!
5. Your app will automatically deploy

---

## What Gets Deployed When

### Frontend Changes
- Triggered when files in `frontend/` change
- Deploys to Vercel
- Takes ~2-3 minutes

### Backend Changes
- Triggered when files in `backend/` change
- Deploys to Railway
- Takes ~3-5 minutes

---

## Troubleshooting

### Workflow Fails?
1. Check the "Actions" tab in GitHub
2. Click on the failed workflow
3. Read the error logs
4. Common issues:
   - Missing secrets (check step 1.3 and 2.5)
   - Wrong secret values
   - Build errors (test locally first)

### Need to Update Secrets?
1. Go to GitHub repo → `Settings` → `Secrets and variables` → `Actions`
2. Find the secret you want to update
3. Click "Update" and enter the new value

### Want to Disable Auto-Deploy?
1. Go to `.github/workflows/` in your repo
2. Delete or rename the workflow files
3. Commit and push

---

## Alternative: Manual Deployment (Simpler)

If GitHub Actions feels like overkill, you can just:

1. **Vercel**: Connect your GitHub repo directly in Vercel dashboard
   - Auto-deploys on push (no GitHub Actions needed)

2. **Railway**: Connect your GitHub repo directly in Railway dashboard
   - Auto-deploys on push (no GitHub Actions needed)

Both platforms have built-in GitHub integration without needing GitHub Actions!

---

## Cost

- **GitHub Actions**: Free (2,000 minutes/month on free tier)
- **Vercel**: Free tier available (hobby projects)
- **Railway**: $5/month free credit

---

## Questions?

If you run into issues:
1. Check the Actions logs in GitHub
2. Check Vercel deployment logs
3. Check Railway deployment logs
4. Make sure all secrets are correct

