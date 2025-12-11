"""
Database manager for GameOn recording sessions.

Enhanced with action code auto-creation, batch operations, and session recovery.
"""
import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict
from pathlib import Path

from .models import DatabaseSchema, Session, InputEvent, ActionCode, FrameTimestamp, SessionHealth


class DatabaseManager:
    """Manages SQLite database operations for GameOn."""
    
    def __init__(self, db_path: str):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._action_code_cache = {}  # Cache for action codes
        self._ensure_database_exists()
    
    def _ensure_database_exists(self):
        """Create database and tables if they don't exist."""
        # Create directory if it doesn't exist
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        
        # Create tables
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for schema in DatabaseSchema.get_all_schemas():
                cursor.execute(schema)
            conn.commit()
    
    # ========================================
    # Session Methods
    # ========================================
    
    def create_session(self, session: Session) -> int:
        """
        Create a new recording session.
        
        Args:
            session: Session object to create
            
        Returns:
            Session ID
        """
        query = """
        INSERT INTO sessions (
            game_name, start_time, end_time, duration_seconds,
            video_path, system_audio_path, microphone_audio_path,
            input_type, fps, latency_offset_ms, status, monitor_index, notes,
            video_width, video_height, video_codec, total_frames, file_size_bytes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (
                session.game_name,
                session.start_time.isoformat() if session.start_time else None,
                session.end_time.isoformat() if session.end_time else None,
                session.duration_seconds,
                session.video_path,
                session.system_audio_path,
                session.microphone_audio_path,
                session.input_type,
                session.fps,
                session.latency_offset_ms,
                session.status,
                session.monitor_index,
                session.notes,
                session.video_width,
                session.video_height,
                session.video_codec,
                session.total_frames,
                session.file_size_bytes
            ))
            conn.commit()
            return cursor.lastrowid
    
    def update_session(self, session: Session):
        """
        Update an existing session.
        
        Args:
            session: Session object with updated data
        """
        query = """
        UPDATE sessions SET
            game_name = ?,
            start_time = ?,
            end_time = ?,
            duration_seconds = ?,
            video_path = ?,
            system_audio_path = ?,
            microphone_audio_path = ?,
            input_type = ?,
            fps = ?,
            latency_offset_ms = ?,
            status = ?,
            monitor_index = ?,
            notes = ?,
            video_width = ?,
            video_height = ?,
            video_codec = ?,
            total_frames = ?,
            file_size_bytes = ?
        WHERE id = ?
        """
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (
                session.game_name,
                session.start_time.isoformat() if session.start_time else None,
                session.end_time.isoformat() if session.end_time else None,
                session.duration_seconds,
                session.video_path,
                session.system_audio_path,
                session.microphone_audio_path,
                session.input_type,
                session.fps,
                session.latency_offset_ms,
                session.status,
                session.monitor_index,
                session.notes,
                session.video_width,
                session.video_height,
                session.video_codec,
                session.total_frames,
                session.file_size_bytes,
                session.id
            ))
            conn.commit()
    
    def get_session(self, session_id: int) -> Optional[Session]:
        """
        Get a session by ID.
        
        Args:
            session_id: ID of session to retrieve
            
        Returns:
            Session object or None if not found
        """
        query = "SELECT * FROM sessions WHERE id = ?"
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (session_id,))
            row = cursor.fetchone()
            
            if row:
                return Session.from_db_row(row)
            return None
    
    def get_sessions_by_game(self, game_name: str) -> List[Session]:
        """
        Get all sessions for a specific game.
        
        Args:
            game_name: Name of the game
            
        Returns:
            List of Session objects
        """
        query = "SELECT * FROM sessions WHERE game_name = ? ORDER BY start_time DESC"
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (game_name,))
            rows = cursor.fetchall()
            
            return [Session.from_db_row(row) for row in rows]
    
    def get_all_sessions(self, limit: Optional[int] = None) -> List[Session]:
        """
        Get all sessions.
        
        Args:
            limit: Maximum number of sessions to return
            
        Returns:
            List of Session objects
        """
        query = "SELECT * FROM sessions ORDER BY start_time DESC"
        if limit:
            query += f" LIMIT {limit}"
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            
            return [Session.from_db_row(row) for row in rows]
    
    def get_incomplete_sessions(self) -> List[Session]:
        """
        Get sessions that didn't complete properly.
        
        Returns:
            List of incomplete Session objects
        """
        query = "SELECT * FROM sessions WHERE status = 'recording' OR end_time IS NULL"
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            return [Session.from_db_row(row) for row in rows]
    
    def mark_session_failed(self, session_id: int, error: str):
        """
        Mark a session as failed.
        
        Args:
            session_id: ID of the session
            error: Error message to store
        """
        query = "UPDATE sessions SET status = 'failed', notes = ? WHERE id = ?"
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (error, session_id))
            conn.commit()
    
    def delete_session(self, session_id: int):
        """
        Delete a session and all its related data.
        
        Args:
            session_id: ID of session to delete
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # These will cascade due to foreign keys
            cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()
    
    # ========================================
    # Action Code Methods
    # ========================================
    
    def get_or_create_action_code(
        self, 
        input_device: str, 
        raw_input: str,
        description: Optional[str] = None,
        category: Optional[str] = None
    ) -> int:
        """
        Get existing action code or create new one.
        
        Args:
            input_device: Device type (keyboard, mouse, xbox, playstation)
            raw_input: Raw input identifier (key name, button code)
            description: Human-readable description (optional)
            category: Category (movement, attack, action, special) (optional)
            
        Returns:
            Action code ID
        """
        cache_key = f"{input_device}:{raw_input}"
        
        # Check cache first
        if cache_key in self._action_code_cache:
            return self._action_code_cache[cache_key]
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Try to find existing
            cursor.execute(
                "SELECT id FROM action_codes WHERE input_device = ? AND raw_input = ?",
                (input_device, raw_input)
            )
            row = cursor.fetchone()
            
            if row:
                action_code_id = row[0]
            else:
                # Create new - get next encoded value for this device
                cursor.execute(
                    "SELECT MAX(encoded_value) FROM action_codes WHERE input_device = ?",
                    (input_device,)
                )
                max_val = cursor.fetchone()[0]
                encoded_value = (max_val + 1) if max_val is not None else 0
                
                cursor.execute(
                    """INSERT INTO action_codes (input_device, raw_input, encoded_value, description, category)
                       VALUES (?, ?, ?, ?, ?)""",
                    (input_device, raw_input, encoded_value, description, category)
                )
                conn.commit()
                action_code_id = cursor.lastrowid
            
            # Cache it
            self._action_code_cache[cache_key] = action_code_id
            return action_code_id
    
    def get_action_mapping(self, input_device: Optional[str] = None) -> Dict[str, int]:
        """
        Get action code mapping for ML training.
        
        Args:
            input_device: Filter by device type (None = all devices)
            
        Returns:
            Dictionary mapping "device:button" to encoded value
        """
        query = "SELECT input_device, raw_input, encoded_value FROM action_codes"
        params = []
        
        if input_device:
            query += " WHERE input_device = ?"
            params.append(input_device)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            mapping = {}
            for device, raw, encoded in cursor.fetchall():
                key = f"{device}:{raw}"
                mapping[key] = encoded
            
            return mapping
    
    # ========================================
    # Input Event Methods
    # ========================================
    
    def add_input_event(self, event: InputEvent):
        """
        Add an input event to the database.
        Automatically creates action code if needed.
        
        Args:
            event: InputEvent object to add
        """
        # Get or create action code
        action_code = self.get_or_create_action_code(
            event.input_device,
            event.button_key
        )
        
        query = """
        INSERT INTO input_events (
            session_id, timestamp_ms, input_device, button_key,
            action, value, x_position, y_position, action_code
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (
                event.session_id,
                event.timestamp_ms,
                event.input_device,
                event.button_key,
                event.action,
                event.value,
                event.x_position,
                event.y_position,
                action_code
            ))
            conn.commit()
    
    def add_input_events_batch(self, events: List[InputEvent]):
        """
        Add multiple input events in a batch (faster).
        Automatically creates action codes if needed.
        
        Args:
            events: List of InputEvent objects
        """
        query = """
        INSERT INTO input_events (
            session_id, timestamp_ms, input_device, button_key,
            action, value, x_position, y_position, action_code
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            data = []
            for event in events:
                # Get or create action code for each event
                action_code = self.get_or_create_action_code(
                    event.input_device,
                    event.button_key
                )
                
                data.append((
                    event.session_id,
                    event.timestamp_ms,
                    event.input_device,
                    event.button_key,
                    event.action,
                    event.value,
                    event.x_position,
                    event.y_position,
                    action_code
                ))
            
            cursor.executemany(query, data)
            conn.commit()
    
    def get_input_events(self, session_id: int) -> List[InputEvent]:
        """
        Get all input events for a session.
        
        Args:
            session_id: ID of the session
            
        Returns:
            List of InputEvent objects
        """
        query = "SELECT * FROM input_events WHERE session_id = ? ORDER BY timestamp_ms"
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (session_id,))
            rows = cursor.fetchall()
            
            return [
                InputEvent(
                    event_id=row[0],
                    session_id=row[1],
                    timestamp_ms=row[2],
                    input_device=row[3],
                    button_key=row[4],
                    action=row[5],
                    value=row[6],
                    x_position=row[7],
                    y_position=row[8],
                    action_code=row[9] if len(row) > 9 else None
                )
                for row in rows
            ]
    
    def get_input_events_batch(
        self,
        session_id: int,
        start_frame: int,
        end_frame: int,
        fps: int
    ) -> List[InputEvent]:
        """
        Get input events for a specific frame range.
        
        Args:
            session_id: ID of the session
            start_frame: Starting frame number
            end_frame: Ending frame number
            fps: Frames per second of the video
            
        Returns:
            List of InputEvent objects in the frame range
        """
        start_ms = int((start_frame / fps) * 1000)
        end_ms = int((end_frame / fps) * 1000)
        
        query = """
            SELECT * FROM input_events 
            WHERE session_id = ? AND timestamp_ms BETWEEN ? AND ?
            ORDER BY timestamp_ms
        """
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (session_id, start_ms, end_ms))
            rows = cursor.fetchall()
            
            return [
                InputEvent(
                    event_id=row[0],
                    session_id=row[1],
                    timestamp_ms=row[2],
                    input_device=row[3],
                    button_key=row[4],
                    action=row[5],
                    value=row[6],
                    x_position=row[7],
                    y_position=row[8],
                    action_code=row[9] if len(row) > 9 else None
                )
                for row in rows
            ]
    
    # ========================================
    # Frame Timing Methods
    # ========================================
    
    def add_frame_timestamp(self, frame: FrameTimestamp):
        """
        Add a frame timestamp record.
        
        Args:
            frame: FrameTimestamp object
        """
        query = """
        INSERT INTO frame_timestamps (
            session_id, frame_number, capture_timestamp_ms, 
            write_timestamp_ms, dropped
        ) VALUES (?, ?, ?, ?, ?)
        """
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (
                frame.session_id,
                frame.frame_number,
                frame.capture_timestamp_ms,
                frame.write_timestamp_ms,
                frame.dropped
            ))
            conn.commit()
    
    def add_frame_timestamps_batch(self, frames: List[FrameTimestamp]):
        """
        Add multiple frame timestamps in batch.
        
        Args:
            frames: List of FrameTimestamp objects
        """
        query = """
        INSERT INTO frame_timestamps (
            session_id, frame_number, capture_timestamp_ms,
            write_timestamp_ms, dropped
        ) VALUES (?, ?, ?, ?, ?)
        """
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.executemany(query, [
                (f.session_id, f.frame_number, f.capture_timestamp_ms,
                 f.write_timestamp_ms, f.dropped)
                for f in frames
            ])
            conn.commit()
    
    # ========================================
    # Session Health Methods
    # ========================================
    
    def add_health_check(self, health: SessionHealth):
        """
        Add a session health check record.
        
        Args:
            health: SessionHealth object
        """
        query = """
        INSERT INTO session_health (
            session_id, check_time, disk_space_gb, cpu_percent,
            memory_mb, frames_captured, frames_dropped
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (
                health.session_id,
                health.check_time.isoformat(),
                health.disk_space_gb,
                health.cpu_percent,
                health.memory_mb,
                health.frames_captured,
                health.frames_dropped
            ))
            conn.commit()
    
    # ========================================
    # Statistics and Utilities
    # ========================================
    
    def get_statistics(self) -> dict:
        """
        Get database statistics.
        
        Returns:
            Dictionary with statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total sessions
            cursor.execute("SELECT COUNT(*) FROM sessions")
            total_sessions = cursor.fetchone()[0]
            
            # Completed sessions
            cursor.execute("SELECT COUNT(*) FROM sessions WHERE status = 'completed'")
            completed_sessions = cursor.fetchone()[0]
            
            # Total recording time
            cursor.execute("SELECT SUM(duration_seconds) FROM sessions WHERE duration_seconds IS NOT NULL")
            total_duration = cursor.fetchone()[0] or 0
            
            # Total input events
            cursor.execute("SELECT COUNT(*) FROM input_events")
            total_events = cursor.fetchone()[0]
            
            # Games recorded
            cursor.execute("SELECT COUNT(DISTINCT game_name) FROM sessions")
            unique_games = cursor.fetchone()[0]
            
            # Total frames
            cursor.execute("SELECT SUM(total_frames) FROM sessions WHERE total_frames IS NOT NULL")
            total_frames = cursor.fetchone()[0] or 0
            
            # Total storage
            cursor.execute("SELECT SUM(file_size_bytes) FROM sessions WHERE file_size_bytes IS NOT NULL")
            total_bytes = cursor.fetchone()[0] or 0
            
            return {
                'total_sessions': total_sessions,
                'completed_sessions': completed_sessions,
                'total_duration_seconds': total_duration,
                'total_input_events': total_events,
                'unique_games': unique_games,
                'total_frames': total_frames,
                'total_storage_gb': total_bytes / (1024**3) if total_bytes else 0
            }