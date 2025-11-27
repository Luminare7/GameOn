# GameOn - Installation Guide

## Quick Install

### 1. Basic Installation (Required)
```bash
pip install -r requirements.txt
```

This installs:
- Video capture (MSS, OpenCV, DXCam)
- Audio capture (SoundDevice, PyAudioWPatch)
- Input capture (pynput, inputs)
- Database (SQLite)
- GUI (tkinter - included with Python)

### 2. FFmpeg (For H.264/H.265 Compression)

**Windows:**
```powershell
choco install ffmpeg
```
Or download from https://ffmpeg.org/download.html

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Verify installation:**
```bash
ffmpeg -version
```

### 3. ML Framework Support (Optional)

Choose based on your needs:

**PyTorch:**
```bash
pip install torch torchvision
```

**TensorFlow:**
```bash
pip install tensorflow
```

**HDF5 (Universal):**
```bash
pip install h5py
```

**All ML tools:**
```bash
pip install torch torchvision tensorflow h5py
```

---

## Installation Options

### Option A: Minimal (Recording Only)
```bash
pip install -r requirements.txt
```
✅ Record gameplay  
❌ No ML exports  
❌ Basic video codec only (no H.264/H.265)

### Option B: Recommended (Recording + Compression)
```bash
pip install -r requirements.txt
# Install FFmpeg (see above)
```
✅ Record gameplay  
✅ H.264/H.265 compression  
❌ No ML exports

### Option C: Full (Everything)
```bash
pip install -r requirements.txt
pip install torch torchvision tensorflow h5py
# Install FFmpeg (see above)
```
✅ Record gameplay  
✅ H.264/H.265 compression  
✅ All ML exports (PyTorch, TensorFlow, HDF5)

---

## Verify Installation

```bash
# Test basic functionality
python main.py --help

# Test GUI
python main.py --gui

# List audio devices
python main.py --list-devices

# Check FFmpeg (for compression)
ffmpeg -version
```

---

## Troubleshooting

### Issue: "ModuleNotFoundError"
**Solution:**
```bash
pip install --upgrade -r requirements.txt
```

### Issue: "FFmpeg not found"
**Solution:**
Install FFmpeg system-wide (see above), then restart your terminal.

### Issue: "pyaudiowpatch" error on Windows
**Solution:**
```bash
pip install pyaudiowpatch --upgrade
```

### Issue: GPU acceleration for PyTorch/TensorFlow
**PyTorch (CUDA):**
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

**TensorFlow (GPU):**
```bash
pip install tensorflow[and-cuda]
```

---

## Platform-Specific Notes

### Windows
- ✅ Full gamepad support
- ✅ DXCam for fast capture
- ✅ WASAPI system audio
- ⚠️ May need Visual C++ Redistributable

### macOS
- ✅ All features work
- ⚠️ Grant screen recording permission
- ⚠️ Grant microphone permission
- ⚠️ Gamepad support limited

### Linux
- ✅ Most features work
- ⚠️ Install PulseAudio for system audio
- ⚠️ May need additional permissions

---

## Development Installation

For contributors:
```bash
git clone https://github.com/yourusername/GameOn.git
cd GameOn
pip install -e .
pip install pytest black flake8  # Development tools
```

---

## Dependencies Overview

| Package | Purpose | Platform | Required |
|---------|---------|----------|----------|
| mss | Screen capture | All | ✅ Yes |
| opencv-python | Video processing | All | ✅ Yes |
| sounddevice | Audio capture | All | ✅ Yes |
| pynput | Input capture | All | ✅ Yes |
| dxcam | Fast capture | Windows | ⚠️ Optional |
| pyaudiowpatch | System audio | Windows | ⚠️ Optional |
| inputs | Gamepad support | Windows | ⚠️ Optional |
| torch | PyTorch export | All | ❌ No |
| tensorflow | TensorFlow export | All | ❌ No |
| h5py | HDF5 export | All | ❌ No |

---

## Disk Space Requirements

**Per hour of recording:**
- Uncompressed: ~10 GB
- H.264 (CRF 20): ~500 MB ✅ Recommended
- H.265 (CRF 22): ~250 MB

**Recommended:**
- 50 GB free for 100 hours of H.264 recordings
- SSD recommended for smooth recording

---

## Next Steps

After installation:
1. Read `README.md` for usage guide
2. Try `python main.py --gui` to test
3. See `USAGE.md` for examples
4. Check `IMPROVEMENTS.md` for new features

**Happy recording! 🎮**

