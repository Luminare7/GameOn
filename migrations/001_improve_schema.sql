-- GameOn Database Schema Improvements
-- Migration: 001_improve_schema.sql
-- SMART VERSION: Handles incomplete/old databases by recreating tables

-- =============================================================================
-- STRATEGY: Drop and recreate tables to ensure correct schema
-- This is safe because:
-- 1. run_migration.py creates a backup first
-- 2. For new installs, tables won't exist anyway
-- 3. You can always restore from backup if needed
-- =============================================================================

-- =============================================================================
-- PART 1: Create sessions table with FULL schema
-- =============================================================================

-- Drop old incomplete table if it exists
DROP TABLE IF EXISTS sessions;

-- Create complete sessions table with all 18 columns
CREATE TABLE sessions (
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
    notes TEXT,
    video_width INTEGER,
    video_height INTEGER,
    video_codec TEXT,
    total_frames INTEGER,
    file_size_bytes INTEGER
);

-- Create indexes for sessions
CREATE INDEX idx_game_name ON sessions(game_name);
CREATE INDEX idx_start_time ON sessions(start_time);
CREATE INDEX idx_status ON sessions(status);

-- =============================================================================
-- PART 2: Create input_events table with action_code support
-- =============================================================================

-- Drop old table if it exists
DROP TABLE IF EXISTS input_events;

-- Create complete input_events table
CREATE TABLE input_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    timestamp_ms INTEGER NOT NULL,
    input_device TEXT,
    button_key TEXT,
    action TEXT,
    value REAL,
    x_position REAL,
    y_position REAL,
    action_code INTEGER,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (action_code) REFERENCES action_codes(id)
);

-- Create indexes for input_events
CREATE INDEX idx_session_events ON input_events(session_id, timestamp_ms);
CREATE INDEX idx_timestamp ON input_events(timestamp_ms);

-- =============================================================================
-- PART 3: Create action_codes table for ML-ready input encoding
-- =============================================================================

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

-- =============================================================================
-- PART 4: Create frame_timestamps table for perfect A/V sync
-- =============================================================================

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

-- =============================================================================
-- PART 5: Create session_health table for diagnostics
-- =============================================================================

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

-- =============================================================================
-- PART 6: Insert default action codes for common inputs
-- =============================================================================

-- Keyboard movement keys
INSERT OR IGNORE INTO action_codes (input_device, raw_input, encoded_value, description, category) VALUES
('keyboard', 'w', 0, 'Forward', 'movement'),
('keyboard', 'a', 1, 'Left', 'movement'),
('keyboard', 's', 2, 'Backward', 'movement'),
('keyboard', 'd', 3, 'Right', 'movement'),
('keyboard', 'space', 4, 'Jump', 'movement'),
('keyboard', 'shift', 5, 'Sprint/Crouch', 'movement'),
('keyboard', 'ctrl', 6, 'Crouch', 'movement'),
('keyboard', 'Key.shift', 7, 'Shift (pynput)', 'movement'),
('keyboard', 'Key.ctrl', 8, 'Ctrl (pynput)', 'movement'),
('keyboard', 'Key.space', 9, 'Space (pynput)', 'movement');

-- Keyboard number keys
INSERT OR IGNORE INTO action_codes (input_device, raw_input, encoded_value, description, category) VALUES
('keyboard', '1', 10, 'Number 1', 'weapon'),
('keyboard', '2', 11, 'Number 2', 'weapon'),
('keyboard', '3', 12, 'Number 3', 'weapon'),
('keyboard', '4', 13, 'Number 4', 'weapon'),
('keyboard', '5', 14, 'Number 5', 'weapon');

-- Keyboard special keys
INSERT OR IGNORE INTO action_codes (input_device, raw_input, encoded_value, description, category) VALUES
('keyboard', 'e', 15, 'Interact/Use', 'action'),
('keyboard', 'f', 16, 'Interact/Use Alt', 'action'),
('keyboard', 'r', 17, 'Reload', 'action'),
('keyboard', 'q', 18, 'Ability/Item', 'special'),
('keyboard', 'tab', 19, 'Tab/Inventory', 'special'),
('keyboard', 'Key.tab', 20, 'Tab (pynput)', 'special'),
('keyboard', 'Key.esc', 21, 'Escape', 'special');

-- Mouse buttons
INSERT OR IGNORE INTO action_codes (input_device, raw_input, encoded_value, description, category) VALUES
('mouse', 'Button.left', 30, 'Primary Fire/Action', 'attack'),
('mouse', 'Button.right', 31, 'Secondary Fire/Aim', 'attack'),
('mouse', 'Button.middle', 32, 'Middle Click', 'special'),
('mouse', 'move', 33, 'Mouse Movement', 'aim'),
('mouse', 'scroll', 34, 'Scroll Wheel', 'special');

-- Xbox controller buttons
INSERT OR IGNORE INTO action_codes (input_device, raw_input, encoded_value, description, category) VALUES
('xbox', 'BTN_SOUTH', 40, 'A Button', 'action'),
('xbox', 'BTN_EAST', 41, 'B Button', 'action'),
('xbox', 'BTN_WEST', 42, 'X Button', 'action'),
('xbox', 'BTN_NORTH', 43, 'Y Button', 'action'),
('xbox', 'BTN_TL', 44, 'Left Bumper', 'action'),
('xbox', 'BTN_TR', 45, 'Right Bumper', 'action'),
('xbox', 'BTN_SELECT', 46, 'Back/View', 'special'),
('xbox', 'BTN_START', 47, 'Start/Menu', 'special'),
('xbox', 'BTN_THUMBL', 48, 'Left Stick Click', 'action'),
('xbox', 'BTN_THUMBR', 49, 'Right Stick Click', 'action');

-- Xbox controller analog axes
INSERT OR IGNORE INTO action_codes (input_device, raw_input, encoded_value, description, category) VALUES
('xbox', 'ABS_X', 50, 'Left Stick X', 'movement'),
('xbox', 'ABS_Y', 51, 'Left Stick Y', 'movement'),
('xbox', 'ABS_RX', 52, 'Right Stick X', 'aim'),
('xbox', 'ABS_RY', 53, 'Right Stick Y', 'aim'),
('xbox', 'ABS_Z', 54, 'Left Trigger', 'attack'),
('xbox', 'ABS_RZ', 55, 'Right Trigger', 'attack');

-- PlayStation controller buttons
INSERT OR IGNORE INTO action_codes (input_device, raw_input, encoded_value, description, category) VALUES
('playstation', 'BTN_SOUTH', 60, 'Cross Button', 'action'),
('playstation', 'BTN_EAST', 61, 'Circle Button', 'action'),
('playstation', 'BTN_WEST', 62, 'Square Button', 'action'),
('playstation', 'BTN_NORTH', 63, 'Triangle Button', 'action'),
('playstation', 'BTN_TL', 64, 'L1', 'action'),
('playstation', 'BTN_TR', 65, 'R1', 'action'),
('playstation', 'BTN_TL2', 66, 'L2', 'attack'),
('playstation', 'BTN_TR2', 67, 'R2', 'attack'),
('playstation', 'BTN_SELECT', 68, 'Share', 'special'),
('playstation', 'BTN_START', 69, 'Options', 'special'),
('playstation', 'BTN_THUMBL', 70, 'L3', 'action'),
('playstation', 'BTN_THUMBR', 71, 'R3', 'action');

-- PlayStation controller analog axes
INSERT OR IGNORE INTO action_codes (input_device, raw_input, encoded_value, description, category) VALUES
('playstation', 'ABS_X', 72, 'Left Stick X', 'movement'),
('playstation', 'ABS_Y', 73, 'Left Stick Y', 'movement'),
('playstation', 'ABS_RX', 74, 'Right Stick X', 'aim'),
('playstation', 'ABS_RY', 75, 'Right Stick Y', 'aim');