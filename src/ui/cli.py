"""
Command-line interface for GameOn.
"""
import argparse
import sys
import os
from pathlib import Path

import yaml

from ..session import SessionManager
from ..database import DatabaseManager
from ..capture import list_audio_devices


def load_config(config_path: str = 'config.yaml') -> dict:
    """Load configuration from YAML file."""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"⚠ Config file not found: {config_path}")
        return {}
    except Exception as e:
        print(f"⚠ Error loading config: {e}")
        return {}


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for CLI."""
    parser = argparse.ArgumentParser(
        description='GameOn - Record gameplay video, audio, and inputs for AI training',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Record with keyboard and mouse
  python main.py --game "Fortnite" --keyboard --microphone
  
  # Record with Xbox controller, 60fps
  python main.py --game "Elden Ring" --xbox --fps 60 --system-audio
  
  # Record with custom latency offset
  python main.py --game "CS:GO" --keyboard --latency 50
  
  # Record with H.265 compression (smaller files)
  python main.py --game "Valorant" --keyboard --codec h265 --quality 22
  
  # Use GUI mode
  python main.py --gui
  
  # List audio devices
  python main.py --list-devices
  
  # View session statistics
  python main.py --stats
        """
    )
    
    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        '--gui',
        action='store_true',
        help='Launch GUI interface instead of CLI'
    )
    mode_group.add_argument(
        '--list-devices',
        action='store_true',
        help='List available audio devices and exit'
    )
    mode_group.add_argument(
        '--stats',
        action='store_true',
        help='Show database statistics and exit'
    )
    
    # Recording options
    parser.add_argument(
        '--game',
        type=str,
        help='Name of the game being recorded (required for recording)'
    )
    
    # Input device selection (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        '--keyboard',
        action='store_true',
        help='Capture keyboard and mouse inputs (default)'
    )
    input_group.add_argument(
        '--xbox',
        action='store_true',
        help='Capture Xbox controller inputs'
    )
    input_group.add_argument(
        '--playstation',
        action='store_true',
        help='Capture PlayStation controller inputs'
    )
    
    # Audio options
    parser.add_argument(
        '--system-audio',
        action='store_true',
        help='Capture system audio (game sounds)'
    )
    parser.add_argument(
        '--microphone',
        action='store_true',
        help='Capture microphone audio (voice chat)'
    )
    parser.add_argument(
        '--no-mouse',
        action='store_true',
        help='Disable mouse capture (keyboard mode only)'
    )
    
    # Video options
    parser.add_argument(
        '--fps',
        type=int,
        default=None,
        help='Video frame rate (default: from config or 60)'
    )
    parser.add_argument(
        '--monitor',
        type=int,
        default=0,
        help='Monitor index to capture (default: 0 = primary)'
    )
    parser.add_argument(
        '--no-dxcam',
        action='store_true',
        help='Disable DXCam optimization on Windows'
    )
    parser.add_argument(
        '--codec',
        type=str,
        choices=['h264', 'h265', 'mp4v', 'mjpeg', 'raw'],
        default=None,
        help='Video codec (default: from config or h264)'
    )
    parser.add_argument(
        '--quality',
        type=int,
        default=None,
        help='Video quality CRF 0-51 for H.264/H.265 (default: from config or 20, lower=better)'
    )
    
    # Advanced options
    parser.add_argument(
        '--latency',
        type=int,
        default=0,
        help='Input latency offset in milliseconds (default: 0)'
    )
    parser.add_argument(
        '--sample-rate',
        type=int,
        default=44100,
        help='Audio sample rate (default: 44100 Hz)'
    )
    parser.add_argument(
        '--data-dir',
        type=str,
        default='./data',
        help='Base directory for data storage (default: ./data)'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )
    
    return parser


def run_cli(args: argparse.Namespace):
    """Run CLI recording mode."""
    
    # Load config
    config = load_config(args.config)
    recording_config = config.get('recording', {})
    audio_config = config.get('audio', {})
    
    # Determine input type
    if args.xbox:
        input_type = 'xbox'
    elif args.playstation:
        input_type = 'playstation'
    else:
        input_type = 'keyboard'
    
    # Determine audio settings (CLI flags override config)
    capture_system_audio = args.system_audio
    capture_microphone = args.microphone
    
    # If neither specified on CLI, check config
    if not capture_system_audio and not capture_microphone:
        capture_system_audio = audio_config.get('system_audio', False)
        capture_microphone = audio_config.get('microphone_audio', False)
    
    # Determine video settings (CLI flags override config)
    fps = args.fps if args.fps is not None else recording_config.get('fps', 60)
    codec = args.codec if args.codec is not None else recording_config.get('video_codec', 'h264')
    quality = args.quality if args.quality is not None else recording_config.get('video_quality', 20)
    
    # Setup paths
    data_dir = args.data_dir
    sessions_path = os.path.join(data_dir, 'sessions')
    db_path = os.path.join(data_dir, 'gameon.db')
    
    # Create session manager
    session_manager = SessionManager(
        db_path=db_path,
        sessions_base_path=sessions_path,
        game_name=args.game,
        input_type=input_type,
        fps=fps,
        sample_rate=args.sample_rate,
        latency_offset_ms=args.latency,
        capture_system_audio=capture_system_audio,
        capture_microphone=capture_microphone,
        capture_mouse=not args.no_mouse,
        monitor_index=args.monitor,
        use_dxcam=not args.no_dxcam,
        codec=codec,
        quality=quality
    )
    
    # Start recording
    if not session_manager.start_recording():
        print("\n❌ Failed to start recording session")
        return 1
    
    # Wait for user to stop
    try:
        print("\n💡 Press Ctrl+C to stop recording\n")
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Recording interrupted by user")
    
    # Stop recording
    session_manager.stop_recording()
    
    return 0


def show_stats(data_dir: str):
    """Show database statistics."""
    db_path = os.path.join(data_dir, 'gameon.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return
    
    db_manager = DatabaseManager(db_path)
    stats = db_manager.get_statistics()
    
    print("\n" + "="*60)
    print("📊 GameOn Database Statistics")
    print("="*60)
    print(f"Total Sessions:      {stats['total_sessions']}")
    print(f"Completed Sessions:  {stats['completed_sessions']}")
    print(f"Unique Games:        {stats['unique_games']}")
    print(f"Total Duration:      {stats['total_duration_seconds'] / 3600:.2f} hours")
    print(f"Total Frames:        {stats['total_frames']:,}")
    print(f"Total Input Events:  {stats['total_input_events']:,}")
    print(f"Total Storage:       {stats['total_storage_gb']:.2f} GB")
    print("="*60 + "\n")
    
    # Show recent sessions
    recent = db_manager.get_all_sessions(limit=10)
    if recent:
        print("Recent Sessions:")
        print("-" * 60)
        for session in recent:
            duration = session.duration_seconds or 0
            codec_info = session.video_codec or 'unknown'
            size_mb = (session.file_size_bytes or 0) / (1024**2)
            print(f"  [{session.id}] {session.game_name}")
            print(f"      Start: {session.start_time}")
            print(f"      Duration: {duration // 60}m {duration % 60}s")
            print(f"      Input: {session.input_type}, Codec: {codec_info}")
            if size_mb > 0:
                print(f"      Size: {size_mb:.1f} MB")
            print()


def main():
    """Main entry point for CLI."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Handle special modes
    if args.list_devices:
        list_audio_devices()
        return 0
    
    if args.stats:
        show_stats(args.data_dir)
        return 0
    
    if args.gui:
        # Import GUI here to avoid dependencies if not needed
        from .gui import run_gui
        return run_gui()
    
    # If no game specified, launch GUI by default
    # This allows double-clicking the app on macOS to open the GUI
    if not args.game:
        from .gui import run_gui
        return run_gui()
    
    return run_cli(args)


if __name__ == '__main__':
    sys.exit(main())