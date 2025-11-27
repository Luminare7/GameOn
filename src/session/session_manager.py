"""
Session manager for GameOn.
Orchestrates video, audio, and input capture for recording sessions.
"""
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..capture import VideoCapture, AudioCapture, InputCapture
from ..database import DatabaseManager, Session, InputEvent


class SessionManager:
    """Manages recording sessions and coordinates all capture modules."""
    
    def __init__(
        self,
        db_path: str,
        sessions_base_path: str,
        game_name: str,
        input_type: str = 'keyboard',
        fps: int = 60,
        sample_rate: int = 44100,
        latency_offset_ms: int = 0,
        capture_system_audio: bool = True,
        capture_microphone: bool = True,
        capture_mouse: bool = True,
        monitor_index: int = 0,
        use_dxcam: bool = True
    ):
        """
        Initialize session manager.
        
        Args:
            db_path: Path to SQLite database
            sessions_base_path: Base directory for session data
            game_name: Name of the game being recorded
            input_type: Type of input device ('keyboard', 'xbox', 'playstation')
            fps: Video frames per second
            sample_rate: Audio sample rate
            latency_offset_ms: Input latency offset in milliseconds
            capture_system_audio: Enable system audio capture
            capture_microphone: Enable microphone capture
            capture_mouse: Enable mouse capture (keyboard mode only)
            monitor_index: Monitor to capture
            use_dxcam: Use DXCam on Windows if available
        """
        self.db_manager = DatabaseManager(db_path)
        self.sessions_base_path = sessions_base_path
        self.game_name = game_name
        self.input_type = input_type
        self.fps = fps
        self.sample_rate = sample_rate
        self.latency_offset_ms = latency_offset_ms
        self.capture_system_audio = capture_system_audio
        self.capture_microphone = capture_microphone
        self.capture_mouse = capture_mouse
        self.monitor_index = monitor_index
        self.use_dxcam = use_dxcam
        
        # Session state
        self.current_session: Optional[Session] = None
        self.session_id: Optional[int] = None
        self.session_path: Optional[str] = None
        
        # Capture modules
        self.video_capture: Optional[VideoCapture] = None
        self.audio_capture: Optional[AudioCapture] = None
        self.input_capture: Optional[InputCapture] = None
        
        self.is_recording = False
    
    def _create_session_directory(self) -> str:
        """
        Create a unique directory for this session.
        
        Returns:
            Path to session directory
        """
        # Create base directory if it doesn't exist
        os.makedirs(self.sessions_base_path, exist_ok=True)
        
        # Generate unique session folder name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        game_slug = self.game_name.replace(' ', '_').replace('/', '_')
        session_name = f"{game_slug}_{timestamp}"
        
        session_path = os.path.join(self.sessions_base_path, session_name)
        os.makedirs(session_path, exist_ok=True)
        
        return session_path
    
    def start_recording(self) -> bool:
        """
        Start recording session.
        
        Returns:
            True if session started successfully
        """
        if self.is_recording:
            print("⚠ Recording already in progress")
            return False
        
        print(f"\n{'='*60}")
        print(f"🎮 Starting GameOn recording session")
        print(f"{'='*60}")
        print(f"Game: {self.game_name}")
        print(f"Input: {self.input_type}")
        print(f"Video: {self.fps} FPS, Monitor {self.monitor_index}")
        print(f"Audio: System={self.capture_system_audio}, Mic={self.capture_microphone}")
        print(f"Latency offset: {self.latency_offset_ms} ms")
        print(f"{'='*60}\n")
        
        # Create session directory
        self.session_path = self._create_session_directory()
        print(f"📁 Session directory: {self.session_path}")
        
        # Define file paths
        video_path = os.path.join(self.session_path, "video.avi")
        system_audio_path = os.path.join(self.session_path, "system_audio.wav") if self.capture_system_audio else None
        mic_audio_path = os.path.join(self.session_path, "microphone_audio.wav") if self.capture_microphone else None
        
        # Create session in database
        self.current_session = Session(
            game_name=self.game_name,
            start_time=datetime.now(),
            input_type=self.input_type,
            fps=self.fps,
            latency_offset_ms=self.latency_offset_ms,
            monitor_index=self.monitor_index,
            video_path=video_path,
            system_audio_path=system_audio_path,
            microphone_audio_path=mic_audio_path,
            status='recording'
        )
        
        self.session_id = self.db_manager.create_session(self.current_session)
        self.current_session.id = self.session_id
        print(f"✓ Session created in database (ID: {self.session_id})")
        
        # Initialize video capture
        self.video_capture = VideoCapture(
            fps=self.fps,
            monitor_index=self.monitor_index,
            output_path=video_path,
            use_dxcam=self.use_dxcam
        )
        
        # Initialize audio capture
        self.audio_capture = AudioCapture(
            sample_rate=self.sample_rate,
            channels=2,
            capture_system=self.capture_system_audio,
            capture_microphone=self.capture_microphone,
            system_output_path=system_audio_path,
            microphone_output_path=mic_audio_path
        )
        
        # Initialize input capture
        self.input_capture = InputCapture(
            input_type=self.input_type,
            capture_mouse=self.capture_mouse,
            latency_offset_ms=self.latency_offset_ms
        )
        
        # Start all captures
        success = True
        
        if not self.video_capture.start_recording():
            print("❌ Failed to start video capture")
            success = False
        
        if not self.audio_capture.start_recording():
            print("⚠ Audio capture failed (non-critical)")
        
        if not self.input_capture.start_recording():
            print("❌ Failed to start input capture")
            success = False
        
        if success:
            self.is_recording = True
            print(f"\n{'='*60}")
            print("✅ RECORDING IN PROGRESS")
            print(f"{'='*60}\n")
        else:
            print("\n❌ Failed to start recording session")
            self._cleanup()
        
        return success
    
    def stop_recording(self):
        """Stop recording session and save data."""
        if not self.is_recording:
            print("⚠ No recording in progress")
            return
        
        print(f"\n{'='*60}")
        print("⏹ Stopping recording session...")
        print(f"{'='*60}\n")
        
        self.is_recording = False
        
        # Stop all captures
        if self.video_capture:
            self.video_capture.stop_recording()
        
        if self.audio_capture:
            self.audio_capture.stop_recording()
        
        input_events = []
        if self.input_capture:
            input_events = self.input_capture.stop_recording()
        
        # Save input events to database
        if input_events and self.session_id:
            print(f"💾 Saving {len(input_events)} input events to database...")
            
            event_objects = [
                InputEvent(
                    session_id=self.session_id,
                    timestamp_ms=event['timestamp_ms'],
                    input_device=event['input_device'],
                    button_key=event['button_key'],
                    action=event['action'],
                    value=event.get('value'),
                    x_position=event.get('x_position'),
                    y_position=event.get('y_position')
                )
                for event in input_events
            ]
            
            # Save in batches for efficiency
            batch_size = 1000
            for i in range(0, len(event_objects), batch_size):
                batch = event_objects[i:i + batch_size]
                self.db_manager.add_input_events_batch(batch)
            
            print(f"✓ Input events saved")
        
        # Update session in database
        if self.current_session and self.session_id:
            self.current_session.end_time = datetime.now()
            duration = (self.current_session.end_time - self.current_session.start_time).total_seconds()
            self.current_session.duration_seconds = int(duration)
            self.current_session.status = 'completed'
            
            self.db_manager.update_session(self.current_session)
            print(f"✓ Session updated (Duration: {duration:.1f} seconds)")
        
        # Print summary
        print(f"\n{'='*60}")
        print("✅ RECORDING COMPLETED")
        print(f"{'='*60}")
        print(f"Session ID: {self.session_id}")
        print(f"Duration: {self.current_session.duration_seconds} seconds")
        print(f"Location: {self.session_path}")
        print(f"Input events: {len(input_events)}")
        print(f"{'='*60}\n")
        
        self._cleanup()
    
    def _cleanup(self):
        """Clean up capture modules."""
        self.video_capture = None
        self.audio_capture = None
        self.input_capture = None
        self.current_session = None
        self.session_id = None
        self.session_path = None
    
    def get_session_info(self) -> dict:
        """Get information about current session."""
        if not self.current_session:
            return {}
        
        return {
            'session_id': self.session_id,
            'game_name': self.game_name,
            'is_recording': self.is_recording,
            'start_time': self.current_session.start_time,
            'session_path': self.session_path
        }
    
    def __enter__(self):
        """Context manager entry."""
        self.start_recording()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.is_recording:
            self.stop_recording()

