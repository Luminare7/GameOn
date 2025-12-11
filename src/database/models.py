"""
Database models for GameOn recording sessions.
"""
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any


class DatabaseSchema:
    """Database schema definitions."""
    
    CREATE_SESSIONS_TABLE = """
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_name TEXT NOT NULL,
        start_time TIMESTAMP NOT NULL,
        end_time TIMESTAMP,
        duration_seconds INTEGER,
        video_path TEXT,
        system_audio_path TEXT,
        microphone_audio_path TEXT,
        input_type TEXT,
        fps INTEGER DEFAULT 60,
        latency_offset_ms INTEGER DEFAULT 0,
        status TEXT DEFAULT 'recording',
        monitor_index INTEGER DEFAULT 0,
        notes TEXT
    );
    """
    
    CREATE_SESSIONS_GAME_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_game_name ON sessions(game_name);
    """
    
    CREATE_SESSIONS_TIME_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_start_time ON sessions(start_time);
    """
    
    CREATE_INPUT_EVENTS_TABLE = """
    CREATE TABLE IF NOT EXISTS input_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        timestamp_ms INTEGER NOT NULL,
        input_device TEXT,
        button_key TEXT,
        action TEXT,
        value REAL,
        x_position REAL,
        y_position REAL,
        FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
    );
    """
    
    CREATE_INPUT_EVENTS_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_session_events ON input_events(session_id, timestamp_ms);
    """
    
    CREATE_ACTION_CODES_TABLE = """
    CREATE TABLE IF NOT EXISTS action_codes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        input_device TEXT NOT NULL,
        raw_input TEXT NOT NULL,
        encoded_value INTEGER NOT NULL,
        description TEXT,
        category TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(input_device, raw_input)
    );
    """
    
    CREATE_FRAME_TIMESTAMPS_TABLE = """
    CREATE TABLE IF NOT EXISTS frame_timestamps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        frame_number INTEGER NOT NULL,
        capture_timestamp_ms INTEGER NOT NULL,
        write_timestamp_ms INTEGER,
        dropped BOOLEAN DEFAULT 0,
        FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
    );
    """
    
    CREATE_SESSION_HEALTH_TABLE = """
    CREATE TABLE IF NOT EXISTS session_health (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        check_time TIMESTAMP NOT NULL,
        disk_space_gb REAL,
        cpu_percent REAL,
        memory_mb REAL,
        frames_captured INTEGER,
        frames_dropped INTEGER,
        FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
    );
    """
    
    @classmethod
    def get_all_schemas(cls) -> List[str]:
        """Get all schema creation statements."""
        return [
            cls.CREATE_SESSIONS_TABLE,
            cls.CREATE_SESSIONS_GAME_INDEX,
            cls.CREATE_SESSIONS_TIME_INDEX,
            cls.CREATE_INPUT_EVENTS_TABLE,
            cls.CREATE_INPUT_EVENTS_INDEX,
            cls.CREATE_ACTION_CODES_TABLE,
            cls.CREATE_FRAME_TIMESTAMPS_TABLE,
            cls.CREATE_SESSION_HEALTH_TABLE
        ]


class Session:
    """Represents a recording session."""
    
    def __init__(
        self,
        game_name: str,
        start_time: datetime,
        input_type: str = 'keyboard',
        fps: int = 60,
        latency_offset_ms: int = 0,
        monitor_index: int = 0,
        session_id: Optional[int] = None,
        end_time: Optional[datetime] = None,
        duration_seconds: Optional[int] = None,
        video_path: Optional[str] = None,
        system_audio_path: Optional[str] = None,
        microphone_audio_path: Optional[str] = None,
        status: str = 'recording',
        notes: Optional[str] = None,
        video_width: Optional[int] = None,
        video_height: Optional[int] = None,
        video_codec: Optional[str] = None,
        total_frames: Optional[int] = None,
        file_size_bytes: Optional[int] = None
    ):
        self.id = session_id
        self.game_name = game_name
        self.start_time = start_time
        self.end_time = end_time
        self.duration_seconds = duration_seconds
        self.video_path = video_path
        self.system_audio_path = system_audio_path
        self.microphone_audio_path = microphone_audio_path
        self.input_type = input_type
        self.fps = fps
        self.latency_offset_ms = latency_offset_ms
        self.monitor_index = monitor_index
        self.status = status
        self.notes = notes
        self.video_width = video_width
        self.video_height = video_height
        self.video_codec = video_codec
        self.total_frames = total_frames
        self.file_size_bytes = file_size_bytes
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary."""
        return {
            'id': self.id,
            'game_name': self.game_name,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration_seconds,
            'video_path': self.video_path,
            'system_audio_path': self.system_audio_path,
            'microphone_audio_path': self.microphone_audio_path,
            'input_type': self.input_type,
            'fps': self.fps,
            'latency_offset_ms': self.latency_offset_ms,
            'monitor_index': self.monitor_index,
            'status': self.status,
            'notes': self.notes
        }
    
    @classmethod
    def from_db_row(cls, row: tuple) -> 'Session':
        """Create Session from database row."""
        return cls(
            session_id=row[0],
            game_name=row[1],
            start_time=datetime.fromisoformat(row[2]) if row[2] else None,
            end_time=datetime.fromisoformat(row[3]) if row[3] else None,
            duration_seconds=row[4],
            video_path=row[5],
            system_audio_path=row[6],
            microphone_audio_path=row[7],
            input_type=row[8],
            fps=row[9],
            latency_offset_ms=row[10],
            status=row[11],
            monitor_index=row[12],
            notes=row[13]
        )


class InputEvent:
    """Represents an input event (keyboard, mouse, or gamepad)."""
    
    def __init__(
        self,
        session_id: int,
        timestamp_ms: int,
        input_device: str,
        button_key: str,
        action: str,
        value: Optional[float] = None,
        x_position: Optional[float] = None,
        y_position: Optional[float] = None,
        event_id: Optional[int] = None,
        action_code: Optional[int] = None
    ):
        self.id = event_id
        self.session_id = session_id
        self.timestamp_ms = timestamp_ms
        self.input_device = input_device
        self.button_key = button_key
        self.action = action
        self.value = value
        self.x_position = x_position
        self.y_position = y_position
        self.action_code = action_code
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'timestamp_ms': self.timestamp_ms,
            'input_device': self.input_device,
            'button_key': self.button_key,
            'action': self.action,
            'value': self.value,
            'x_position': self.x_position,
            'y_position': self.y_position,
            'action_code': self.action_code
        }
    
    def to_normalized_dict(self, screen_width: int, screen_height: int) -> Dict[str, Any]:
        """Convert to normalized representation for ML training."""
        data = self.to_dict()
        
        # Normalize mouse positions to [0, 1]
        if self.x_position is not None:
            data['x_normalized'] = self.x_position / screen_width
        if self.y_position is not None:
            data['y_normalized'] = self.y_position / screen_height
        
        # Normalize controller analog values to [-1, 1]
        if self.input_device in ['xbox', 'playstation'] and self.value is not None:
            data['value_normalized'] = (self.value - 128) / 128.0
        
        return data


class ActionCode:
    """Represents an action code mapping."""
    
    def __init__(
        self,
        input_device: str,
        raw_input: str,
        encoded_value: int,
        description: Optional[str] = None,
        category: Optional[str] = None,
        action_code_id: Optional[int] = None,
        created_at: Optional[datetime] = None
    ):
        self.id = action_code_id
        self.input_device = input_device
        self.raw_input = raw_input
        self.encoded_value = encoded_value
        self.description = description
        self.category = category
        self.created_at = created_at
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'input_device': self.input_device,
            'raw_input': self.raw_input,
            'encoded_value': self.encoded_value,
            'description': self.description,
            'category': self.category,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class FrameTimestamp:
    """Represents a frame timing record."""
    
    def __init__(
        self,
        session_id: int,
        frame_number: int,
        capture_timestamp_ms: int,
        write_timestamp_ms: Optional[int] = None,
        dropped: bool = False,
        frame_id: Optional[int] = None
    ):
        self.id = frame_id
        self.session_id = session_id
        self.frame_number = frame_number
        self.capture_timestamp_ms = capture_timestamp_ms
        self.write_timestamp_ms = write_timestamp_ms
        self.dropped = dropped
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'session_id': self.session_id,
            'frame_number': self.frame_number,
            'capture_timestamp_ms': self.capture_timestamp_ms,
            'write_timestamp_ms': self.write_timestamp_ms,
            'dropped': self.dropped
        }


class SessionHealth:
    """Represents a session health check."""
    
    def __init__(
        self,
        session_id: int,
        check_time: datetime,
        disk_space_gb: Optional[float] = None,
        cpu_percent: Optional[float] = None,
        memory_mb: Optional[float] = None,
        frames_captured: Optional[int] = None,
        frames_dropped: Optional[int] = None,
        health_id: Optional[int] = None
    ):
        self.id = health_id
        self.session_id = session_id
        self.check_time = check_time
        self.disk_space_gb = disk_space_gb
        self.cpu_percent = cpu_percent
        self.memory_mb = memory_mb
        self.frames_captured = frames_captured
        self.frames_dropped = frames_dropped
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'session_id': self.session_id,
            'check_time': self.check_time.isoformat(),
            'disk_space_gb': self.disk_space_gb,
            'cpu_percent': self.cpu_percent,
            'memory_mb': self.memory_mb,
            'frames_captured': self.frames_captured,
            'frames_dropped': self.frames_dropped
        }

