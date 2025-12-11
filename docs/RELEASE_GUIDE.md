# Step-by-Step Guide: Creating GameOn Releases on GitHub

This guide walks you through setting up automated builds so users can download and run GameOn without installing Python.

---

## 📁 Files to Add to Your Project

Add these files to your GameOn project:

```
GameOn/
├── .github/
│   └── workflows/
│       └── build-executables.yml    ← ADD THIS (GitHub Actions workflow)
├── build_executable.py              ← ADD THIS (build script)
├── main.py                          ← (already exists)
├── config.yaml                      ← (already exists)
├── requirements.txt                 ← (already exists)
├── src/                             ← (already exists)
└── ... (rest of your files)
```

**Important:** The `.github` folder starts with a dot - make sure it's named exactly `.github` (not `github`).

---

## 🚀 Step-by-Step Instructions

### Step 1: Copy Files to Your Project

1. Download the files I provided
2. Place `build_executable.py` in your project root (same folder as `main.py`)
3. Create the folder `.github/workflows/` in your project root
4. Place `build-executables.yml` inside `.github/workflows/`

Your folder should look like:
```
GameOn/
├── .github/
│   └── workflows/
│       └── build-executables.yml
├── build_executable.py
├── main.py
└── ...
```

### Step 2: Push to GitHub

Open terminal/command prompt in your GameOn folder:

```bash
# Add the new files
git add .github/workflows/build-executables.yml
git add build_executable.py

# Commit
git commit -m "Add automated build system for executables"

# Push to GitHub
git push origin main
```

### Step 3: Create a Release (This Triggers the Build!)

**Option A: Using GitHub Website (Easiest)**

1. Go to your repository on GitHub: `https://github.com/YOUR_USERNAME/GameOn`

2. Click **"Releases"** on the right sidebar (or go to `https://github.com/YOUR_USERNAME/GameOn/releases`)

3. Click **"Create a new release"** (or "Draft a new release")

4. Fill in the release form:
   - **Choose a tag:** Type `v1.0.0` and click "Create new tag: v1.0.0 on publish"
   - **Release title:** `GameOn v1.0.0`
   - **Description:** Write release notes (what's included, changes, etc.)

5. Click **"Publish release"**

6. **Wait ~10-15 minutes** - GitHub is now building your executables!

### Step 4: Watch the Build Progress

1. Go to the **"Actions"** tab in your repository

2. You'll see a workflow running called "Build Executables"

3. Click on it to watch the progress:
   - 🟡 Yellow = Building
   - ✅ Green = Success
   - ❌ Red = Failed (click to see error logs)

4. Three jobs run in parallel:
   - `build-windows` → Creates GameOn-Windows.zip
   - `build-macos` → Creates GameOn-macOS.zip
   - `build-linux` → Creates GameOn-Linux.tar.gz

### Step 5: Download Your Executables

Once the build completes (all green ✅):

1. Go back to **"Releases"**
2. Your release now has download files attached:

```
Assets:
📦 GameOn-Windows.zip    ← Windows users download this
📦 GameOn-macOS.zip      ← Mac users download this
📦 GameOn-Linux.tar.gz   ← Linux users download this
📦 Source code (zip)
📦 Source code (tar.gz)
```

### Step 6: Share with Users!

Share the release URL with your users:
```
https://github.com/YOUR_USERNAME/GameOn/releases/latest
```

Users just:
1. Download the ZIP for their platform
2. Extract it
3. Double-click `GameOn.exe` (Windows) or `GameOn.app` (macOS) or `GameOn` (Linux)

**No Python installation needed!**

---

## 🔄 Making Future Releases

For version 1.0.1, 1.1.0, etc.:

1. Make your code changes
2. Commit and push: `git add . && git commit -m "..." && git push`
3. Go to Releases → Create new release
4. Tag it `v1.0.1` (or whatever version)
5. Publish → Builds start automatically

---

## ❓ Troubleshooting

### Build failed (red ❌)

1. Click on the failed workflow
2. Click on the failed job (e.g., "build-windows")
3. Read the error logs
4. Common issues:
   - Missing dependency in requirements.txt
   - Import error (add to `hidden_imports` in build_executable.py)
   - Syntax error in code

### Can't see Actions tab

Make sure your repository is public, or you have GitHub Pro/Team for private repos.

### Build takes too long

Normal build time is 5-15 minutes per platform. If longer:
- Check if GitHub is having issues: https://www.githubstatus.com/
- The first build may be slower (caching)

### Users get security warnings

- **Windows:** "Windows protected your PC" - Click "More info" → "Run anyway"
- **macOS:** "Cannot be opened because developer cannot be verified" - Right-click → Open → Open

For production apps, you'd want code signing certificates (costs money).

---

## 📋 Quick Reference

| Action | Command/Steps |
|--------|---------------|
| Push code | `git push origin main` |
| Create release | GitHub → Releases → Create new release |
| Watch build | GitHub → Actions tab |
| Download executables | GitHub → Releases → Assets section |
| Share link | `https://github.com/USER/GameOn/releases/latest` |

---

## ✅ Checklist

Before your first release:

- [ ] `build_executable.py` is in project root
- [ ] `.github/workflows/build-executables.yml` exists
- [ ] Code is pushed to GitHub
- [ ] Repository is public (or you have paid GitHub plan)

For each release:

- [ ] Code changes committed and pushed
- [ ] Create new release with version tag (v1.0.0, v1.0.1, etc.)
- [ ] Wait for builds to complete (check Actions tab)
- [ ] Verify downloads work

---

That's it! Your users can now download GameOn and run it with a double-click. 🎮
