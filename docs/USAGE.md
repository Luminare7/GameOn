# GameOn Usage Examples

## Quick Start Examples

### 1. First Time Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Test with GUI (easiest)
python main.py --gui
```

### 2. Basic CLI Recording
```bash
# Keyboard + Mouse with microphone
python main.py --game "Fortnite" --keyboard --microphone

# Xbox controller with system audio
python main.py --game "Elden Ring" --xbox --system-audio

# PlayStation controller with both audio sources
python main.py --game "Dark Souls" --playstation --microphone --system-audio
```

### 3. Advanced CLI Options
```bash
# High FPS recording
python main.py --game "CS:GO" --keyboard --fps 120 --microphone

# With latency compensation (inputs lag 50ms behind video)
python main.py --game "Valorant" --keyboard --latency 50 --system-audio

# Record specific monitor
python main.py --game "League of Legends" --keyboard --monitor 1 --microphone

# Keyboard only (no mouse)
python main.py --game "Minecraft" --keyboard --no-mouse --microphone
```

### 4. Utility Commands
```bash
# List available audio devices
python main.py --list-devices

# View recording statistics
python main.py --stats

# Get help
python main.py --help
```

## Workflow

1. **Start the game** you want to record
2. **Run GameOn** with your preferred settings:
   ```bash
   python main.py --game "Your Game" --keyboard --microphone --system-audio
   ```
3. **Play the game** normally - everything is being recorded
4. **Press Ctrl+C** when done to stop recording
5. **Files are automatically saved** to `data/sessions/YourGame_TIMESTAMP/`

## Tips

### For Best Results
- Close other screen recording software
- Use SSD for storage (faster writes)
- On Windows, DXCam is automatically used for better performance
- Adjust `--latency` if inputs seem out of sync with video

### Storage Space
- Approximately **1GB per hour** of recording (depends on resolution/fps)
- Video: ~800MB/hour
- Audio: ~50MB/hour per track
- Input events: <1MB/hour

### Synchronization
If you notice input events are not aligned with the video:
```bash
# If inputs appear BEFORE they should in the video
python main.py --game "Game" --keyboard --latency 50

# If inputs appear AFTER they should in the video  
python main.py --game "Game" --keyboard --latency -50
```

## Accessing Recorded Data

### Database Queries
```python
from src.database import DatabaseManager

db = DatabaseManager('data/gameon.db')

# Get all sessions for a game
sessions = db.get_sessions_by_game("Fortnite")

# Get input events for a session
events = db.get_input_events(session_id=1)

# Get statistics
stats = db.get_statistics()
print(stats)
```

### File Structure
```
data/
├── gameon.db                          # SQLite database
└── sessions/
    └── YourGame_20231127_143022/
        ├── video.avi                  # Screen recording
        ├── system_audio.wav           # Game sounds
        └── microphone_audio.wav       # Voice chat
```

## Troubleshooting

### Issue: "No audio devices found"
**Solution**: 
```bash
python main.py --list-devices
```
Check available devices and ensure drivers are installed.

### Issue: "Failed to start video capture"
**Solution**:
- On macOS: Grant screen recording permission in System Preferences
- On Windows: Close other apps using screen capture
- Try `--no-dxcam` flag

### Issue: "Gamepad not detected"
**Solution**:
- Connect controller before starting
- Install inputs: `pip install inputs`
- Only works on Windows currently

### Issue: Low FPS / Dropped Frames
**Solution**:
- Lower FPS: `--fps 30`
- Close other programs
- Ensure sufficient disk space
- Use SSD for storage

## Platform-Specific Notes

### Windows (Recommended)
- DXCam enabled by default (faster)
- Full gamepad support (XInput/DirectInput)
- WASAPI loopback for system audio

### macOS
- Grant screen recording permission
- Grant microphone permission
- Limited to keyboard/mouse input
- May need to enable audio loopback device

### Linux
- Install required audio libraries
- May need PulseAudio for system audio capture
- Limited gamepad support

## Contributing Data to AI Training

After recording sessions:

1. **Organize by game** - Database automatically indexes by game name
2. **Export for training** - Use database queries to extract data
3. **Sync verification** - Check latency alignment before using data
4. **Clean data** - Remove incomplete sessions if needed

Example export script:
```python
from src.database import DatabaseManager
import json

db = DatabaseManager('data/gameon.db')
sessions = db.get_sessions_by_game("Fortnite")

for session in sessions:
    events = db.get_input_events(session.id)
    
    data = {
        'session_id': session.id,
        'video_path': session.video_path,
        'audio_paths': {
            'system': session.system_audio_path,
            'microphone': session.microphone_audio_path
        },
        'events': [e.to_dict() for e in events]
    }
    
    # Export to JSON
    with open(f'export_session_{session.id}.json', 'w') as f:
        json.dump(data, f, indent=2)
```

---

For more information, see [README.md](README.md)

