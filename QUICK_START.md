# GameOn - Quick Reference

## 📁 Project Structure
```
GameOn/
├── README.md                    # 👈 START HERE - Main documentation
├── context_for_agent.md         # 🤖 For AI agents - Complete context
├── main.py                      # Entry point
├── config.yaml                  # Configuration
├── requirements.txt             # Dependencies
│
├── docs/                        # 📚 All documentation
│   ├── IMPROVEMENTS.md          # Latest features (compression, ML exports)
│   ├── INSTALL.md               # Installation guide
│   ├── USAGE.md                 # Usage examples
│   ├── PROJECT_SUMMARY.md       # Complete overview
│   ├── VIDEO_COMPRESSION.md     # H.264/H.265 guide
│   └── ML_EXPORT.md             # PyTorch/TensorFlow export
│
├── src/                         # Source code
│   ├── capture/                 # Video/audio/input capture
│   ├── database/                # SQLite models & manager
│   ├── session/                 # Session orchestration
│   ├── export/                  # ML framework exports
│   └── ui/                      # CLI & GUI interfaces
│
└── data/                        # 🔒 Runtime data (gitignored)
    ├── gameon.db                # Database
    └── sessions/                # Recorded sessions
```

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt
brew install ffmpeg  # or: choco install ffmpeg (Windows)

# Start recording (GUI)
python main.py --gui

# Start recording (CLI)
python main.py --game "Fortnite" --keyboard --microphone --system-audio

# Check your data
python main.py --stats

# Export for ML training
python -m src.export.pytorch_export --game "Fortnite" --output dataset.pt
```

## 📖 Documentation Guide

| Need | Read |
|------|------|
| **Getting started** | README.md |
| **Installation** | docs/INSTALL.md |
| **Usage examples** | docs/USAGE.md |
| **New features** | docs/IMPROVEMENTS.md |
| **Complete overview** | docs/PROJECT_SUMMARY.md |
| **Video compression** | docs/VIDEO_COMPRESSION.md |
| **ML exports** | docs/ML_EXPORT.md |
| **For AI agents** | context_for_agent.md |

## 🤖 For AI Agents

If you're an AI agent helping with this project:
1. **Read `context_for_agent.md` first** - Contains complete project context
2. Provides architecture, design decisions, code patterns, and common issues
3. Saves tokens by giving you the full picture upfront

## 🔑 Key Features

- ✅ **Video Capture:** 60fps with H.264 compression (20x smaller files)
- ✅ **Audio Capture:** System + microphone (separate tracks)
- ✅ **Input Capture:** Keyboard, mouse, Xbox, PlayStation controllers
- ✅ **Database:** SQLite with indexed sessions and input events
- ✅ **CLI + GUI:** Command-line flags and simple graphical interface
- ✅ **ML Exports:** PyTorch Dataset, TensorFlow pipeline, HDF5 format
- ✅ **Privacy:** All data in .gitignore until you choose to share

## 📞 Common Commands

```bash
# Recording
python main.py --game "Game" --keyboard --microphone
python main.py --gui

# Utilities
python main.py --stats
python main.py --list-devices
python main.py --help

# Exports
python -m src.export.pytorch_export --game "Game" --output data.pt
python -m src.export.hdf5_export --game "Game" --output data.h5
```

## 🎯 Typical Workflow

1. **Record:** `python main.py --game "Fortnite" --keyboard --microphone`
2. **Play:** Game recording happens automatically
3. **Stop:** Press Ctrl+C (CLI) or Stop button (GUI)
4. **Export:** `python -m src.export.pytorch_export --game "Fortnite"`
5. **Train:** Use exported dataset in your ML model

## 🔒 Privacy

- ✅ All recordings stored in `data/` folder
- ✅ `data/` folder is in .gitignore
- ✅ Database and all media files gitignored
- ✅ Share exported .h5 files when ready

---

**For full documentation, start with README.md**
**For AI agent context, read context_for_agent.md**

