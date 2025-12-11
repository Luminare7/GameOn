-- GameOn Database Schema Improvements
-- Add missing indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_timestamp ON input_events(timestamp_ms);
CREATE INDEX IF NOT EXISTS idx_status ON sessions(status);

-- Add video metadata columns to sessions table
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS video_width INTEGER;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS video_height INTEGER;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS video_codec TEXT;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS total_frames INTEGER;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS file_size_bytes INTEGER;

-- Create action codes table for consistent input encoding
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

-- Add action_code reference to input_events
ALTER TABLE input_events ADD COLUMN IF NOT EXISTS action_code INTEGER REFERENCES action_codes(id);

-- Create frame timestamps table for perfect A/V sync
CREATE TABLE IF NOT EXISTS frame_timestamps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    frame_number INTEGER NOT NULL,
    capture_timestamp_ms INTEGER NOT NULL,
    write_timestamp_ms INTEGER,
    dropped BOOLEAN DEFAULT 0,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_frame_timing ON frame_timestamps(session_id, frame_number);

-- Create session health table for diagnostics
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

-- Insert default action codes for common inputs
INSERT OR IGNORE INTO action_codes (input_device, raw_input, encoded_value, description, category) VALUES
-- Keyboard movement
('keyboard', 'w', 0, 'Forward', 'movement'),
('keyboard', 'a', 1, 'Left', 'movement'),
('keyboard', 's', 2, 'Backward', 'movement'),
('keyboard', 'd', 3, 'Right', 'movement'),
('keyboard', 'space', 4, 'Jump', 'movement'),
('keyboard', 'shift', 5, 'Sprint/Crouch', 'movement'),
('keyboard', 'ctrl', 6, 'Crouch', 'movement'),
-- Mouse
('mouse', 'Button.left', 10, 'Primary Fire/Action', 'attack'),
('mouse', 'Button.right', 11, 'Secondary Fire/Aim', 'attack'),
('mouse', 'Button.middle', 12, 'Middle Click', 'special'),
('mouse', 'move', 15, 'Mouse Movement', 'aim'),
-- Xbox controller
('xbox', 'BTN_SOUTH', 20, 'A Button', 'action'),
('xbox', 'BTN_EAST', 21, 'B Button', 'action'),
('xbox', 'BTN_WEST', 22, 'X Button', 'action'),
('xbox', 'BTN_NORTH', 23, 'Y Button', 'action'),
('xbox', 'ABS_X', 28, 'Left Stick X', 'movement'),
('xbox', 'ABS_Y', 29, 'Left Stick Y', 'movement'),
-- PlayStation controller
('playstation', 'BTN_SOUTH', 40, 'Cross Button', 'action'),
('playstation', 'BTN_EAST', 41, 'Circle Button', 'action'),
('playstation', 'BTN_WEST', 42, 'Square Button', 'action'),
('playstation', 'BTN_NORTH', 43, 'Triangle Button', 'action');

