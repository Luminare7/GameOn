# GameOn 🎮

**Record gameplay video, audio, and inputs for AI training datasets**

GameOn allows gamers to spontaneously populate a database with:
- 📹 **Video** (screen capture at 60fps)
- 🔊 **System Audio** (game sounds)
- 🎤 **Microphone Audio** (voice chat)
- ⌨️ **Input Events** (keyboard, mouse, Xbox/PlayStation controllers)

All synchronized and stored in an SQLite database for easy access and training AI models like NIMA2.

---

## 🚀 Quick Start

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/GameOn.git
cd GameOn/mya
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Run GameOn**
```bash
# GUI Mode (recommended for beginners)
python main.py --gui

# CLI Mode (example)
python main.py --game "Fortnite" --keyboard --microphone --system-audio
```

---

## 💻 Usage

### GUI Mode

Launch the simple graphical interface:
```bash
python main.py --gui
```

Features:
- ✨ Easy configuration of all settings
- 📊 Real-time status log
- 🎮 Support for all input devices
- 🔴 One-click start/stop recording

### CLI Mode

#### Basic Examples

**Record with keyboard and microphone:**
```bash
python main.py --game "Counter-Strike 2" --keyboard --microphone
```

**Record with Xbox controller and system audio:**
```bash
python main.py --game "Elden Ring" --xbox --system-audio --fps 60
```

**Record with PlayStation controller:**
```bash
python main.py --game "Dark Souls 3" --playstation --microphone --system-audio
```

#### Command-Line Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--game NAME` | Game name (required) | - |
| `--keyboard` | Use keyboard + mouse | ✓ |
| `--xbox` | Use Xbox controller | - |
| `--playstation` | Use PlayStation controller | - |
| `--system-audio` | Capture system audio | - |
| `--microphone` | Capture microphone | - |
| `--fps N` | Video frame rate | 60 |
| `--monitor N` | Monitor index | 0 |
| `--latency N` | Input latency offset (ms) | 0 |
| `--no-mouse` | Disable mouse capture | - |
| `--no-dxcam` | Disable DXCam (Windows) | - |
| `--gui` | Launch GUI mode | - |
| `--list-devices` | List audio devices | - |
| `--stats` | Show database stats | - |

#### Advanced Examples

**Custom latency offset:**
```bash
python main.py --game "CS:GO" --keyboard --latency 50
```

**Specific monitor:**
```bash
python main.py --game "League of Legends" --keyboard --monitor 1
```

**High FPS recording:**
```bash
python main.py --game "Valorant" --keyboard --fps 120 --microphone
```

---

## 📊 Database Structure

GameOn stores data in an SQLite database (`data/gameon.db`) with the following structure:

### Sessions Table
- **id**: Unique session identifier
- **game_name**: Name of the game (indexed)
- **start_time**, **end_time**: Session timestamps
- **duration_seconds**: Total recording duration
- **video_path**, **system_audio_path**, **microphone_audio_path**: File paths
- **input_type**: Input device (keyboard/xbox/playstation)
- **fps**: Frame rate
- **latency_offset_ms**: Latency compensation

### Input Events Table
- **id**: Unique event identifier
- **session_id**: Foreign key to sessions
- **timestamp_ms**: Milliseconds from session start
- **input_device**: Device type
- **button_key**: Button/key identifier
- **action**: press/release/move/scroll
- **value**: Analog value (for controllers)
- **x_position**, **y_position**: Mouse/cursor position

### View Statistics
```bash
python main.py --stats
```

Example output:
```
📊 GameOn Database Statistics
============================================================
Total Sessions:      42
Unique Games:        7
Total Duration:      12.5 hours
Total Input Events:  1,234,567
============================================================
```

---

## 🗂️ Data Organization

```
data/
├── gameon.db                    # SQLite database
└── sessions/
    ├── Fortnite_20231127_143022/
    │   ├── video.avi
    │   ├── system_audio.wav
    │   └── microphone_audio.wav
    ├── EldenRing_20231127_153045/
    │   ├── video.avi
    │   ├── system_audio.wav
    │   └── microphone_audio.wav
    └── ...
```

Each session gets its own folder with:
- Video file (AVI format)
- System audio (WAV format, if enabled)
- Microphone audio (WAV format, if enabled)
- Database entries with all metadata and input events

---

## 🎯 Use Cases

### AI Training
- Train reinforcement learning agents
- Build datasets for NIMA2 or similar models
- Analyze player behavior patterns

### Game Analysis
- Review gameplay sessions
- Analyze input timing and patterns
- Create highlight reels

### Streaming & Content Creation
- Record gameplay with all inputs
- Review and improve gameplay
- Create tutorials

---

## 🛠️ Technical Details

### Video Capture
- **Windows**: DXCam (DirectX Desktop Duplication API) for hardware-accelerated capture
- **Cross-platform**: MSS (Python Screenshot) fallback
- **Frame rate**: 30-120 FPS
- **Format**: AVI with configurable codec

### Audio Capture
- **Windows**: PyAudioWPatch (WASAPI loopback for system audio)
- **Microphone**: SoundDevice
- **Format**: WAV, 44.1kHz stereo
- **Separate tracks**: System and microphone audio stored separately

### Input Capture
- **Keyboard/Mouse**: pynput (cross-platform)
- **Gamepads**: inputs library (Windows XInput/DirectInput)
- **Latency compensation**: Configurable offset for sync

---

## 🔧 Configuration

Edit `config.yaml` to set default values:

```yaml
recording:
  fps: 60
  video_codec: 'mp4v'
  latency_offset_ms: 0

audio:
  sample_rate: 44100
  channels: 2
  system_audio: true
  microphone_audio: true

input:
  device: 'keyboard'
  capture_mouse: true

display:
  monitor: 0
```

---

## 🐛 Troubleshooting

### Windows System Audio Not Working
- Install PyAudioWPatch: `pip install pyaudiowpatch`
- Enable "Stereo Mix" in Windows Sound settings

### Gamepad Not Detected
- Ensure controller is connected before starting
- Install inputs library: `pip install inputs`
- Check with: `python main.py --list-devices`

### Low Frame Rate
- Enable DXCam on Windows (default)
- Close other screen recording software
- Lower FPS with `--fps 30`

### Permission Errors (macOS)
- Grant screen recording permission in System Preferences
- Grant microphone access in System Preferences

---

## 📝 Requirements

- **Python**: 3.8+
- **OS**: Windows (recommended), macOS, Linux
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 1GB per hour of recording (approx.)

---

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- Video compression options
- Cloud storage integration
- Real-time streaming
- Additional gamepad support
- Performance optimizations

---

## 📄 License

See [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

Built for the gaming and AI community to create high-quality training datasets.

Special thanks to the developers of:
- mss, dxcam (screen capture)
- pynput, inputs (input capture)
- sounddevice, pyaudiowpatch (audio capture)

---

**Happy Gaming & Training! 🎮🤖**
