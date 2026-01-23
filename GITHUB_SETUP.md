# How to Push This Code to GitHub

## Step 1: Install Git (if not already installed)

1. Download Git for Windows from: https://git-scm.com/download/win
2. Install it with default settings
3. **Restart your PowerShell/terminal** after installation

## Step 2: Verify Git Installation

Open a new PowerShell window and run:
```powershell
git --version
```

You should see something like `git version 2.x.x`

## Step 3: Configure Git (first time only)

```powershell
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

## Step 4: Initialize Git Repository

In your project directory (`C:\Users\david\oil_route_planner_stage2`), run:

```powershell
cd C:\Users\david\oil_route_planner_stage2
git init
```

## Step 5: Add Files to Git

```powershell
git add .
```

This adds all files (respecting .gitignore)

## Step 6: Create Initial Commit

```powershell
git commit -m "Initial commit: Heating Oil Route Planner"
```

## Step 7: Create GitHub Repository

1. Go to https://github.com
2. Click the "+" icon in the top right
3. Select "New repository"
4. Name it (e.g., "oil-route-planner")
5. **Don't** initialize with README, .gitignore, or license (we already have these)
6. Click "Create repository"

## Step 8: Connect Local Repository to GitHub

GitHub will show you commands. Use these (replace `YOUR_USERNAME` and `REPO_NAME`):

```powershell
git remote add origin https://github.com/YOUR_USERNAME/REPO_NAME.git
git branch -M main
git push -u origin main
```

## Step 9: Enter GitHub Credentials

When you push, you'll be prompted for:
- **Username**: Your GitHub username
- **Password**: Use a **Personal Access Token** (not your GitHub password)

### To create a Personal Access Token:
1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Give it a name (e.g., "oil-route-planner")
4. Select scopes: check `repo` (full control of private repositories)
5. Click "Generate token"
6. **Copy the token immediately** (you won't see it again!)
7. Use this token as your password when pushing

## Alternative: Using GitHub Desktop

If you prefer a GUI:
1. Download GitHub Desktop: https://desktop.github.com/
2. Install and sign in
3. File → Add Local Repository
4. Select your project folder
5. Click "Publish repository" button

## Troubleshooting

If you get errors:
- Make sure Git is in your PATH (restart terminal after installation)
- Check that you're in the correct directory
- Verify your GitHub credentials/token
