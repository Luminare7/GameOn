"""
Database manager for GameOn recording sessions.
"""
import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Tuple
from pathlib import Path

from .models import DatabaseSchema, Session, InputEvent


class DatabaseManager:
    """Manages SQLite database operations for GameOn."""
    
    def __init__(self, db_path: str):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_database_exists()
    
    def _ensure_database_exists(self):
        """Create database and tables if they don't exist."""
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Create tables
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for schema in DatabaseSchema.get_all_schemas():
                cursor.execute(schema)
            conn.commit()
    
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
            input_type, fps, latency_offset_ms, status, monitor_index, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                session.notes
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
            notes = ?
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
    
    def add_input_event(self, event: InputEvent):
        """
        Add an input event to the database.
        
        Args:
            event: InputEvent object to add
        """
        query = """
        INSERT INTO input_events (
            session_id, timestamp_ms, input_device, button_key,
            action, value, x_position, y_position
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
                event.y_position
            ))
            conn.commit()
    
    def add_input_events_batch(self, events: List[InputEvent]):
        """
        Add multiple input events in a batch (faster).
        
        Args:
            events: List of InputEvent objects
        """
        query = """
        INSERT INTO input_events (
            session_id, timestamp_ms, input_device, button_key,
            action, value, x_position, y_position
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.executemany(query, [
                (
                    event.session_id,
                    event.timestamp_ms,
                    event.input_device,
                    event.button_key,
                    event.action,
                    event.value,
                    event.x_position,
                    event.y_position
                )
                for event in events
            ])
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
                    y_position=row[8]
                )
                for row in rows
            ]
    
    def delete_session(self, session_id: int):
        """
        Delete a session and all its input events.
        
        Args:
            session_id: ID of session to delete
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Delete input events (will cascade if FK constraint is set)
            cursor.execute("DELETE FROM input_events WHERE session_id = ?", (session_id,))
            # Delete session
            cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()
    
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
            
            # Total recording time
            cursor.execute("SELECT SUM(duration_seconds) FROM sessions WHERE duration_seconds IS NOT NULL")
            total_duration = cursor.fetchone()[0] or 0
            
            # Total input events
            cursor.execute("SELECT COUNT(*) FROM input_events")
            total_events = cursor.fetchone()[0]
            
            # Games recorded
            cursor.execute("SELECT COUNT(DISTINCT game_name) FROM sessions")
            unique_games = cursor.fetchone()[0]
            
            return {
                'total_sessions': total_sessions,
                'total_duration_seconds': total_duration,
                'total_input_events': total_events,
                'unique_games': unique_games
            }

