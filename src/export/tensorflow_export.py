"""
TensorFlow Dataset export for GameOn recordings.

Usage:
    from src.export.tensorflow_export import create_tf_dataset
    
    dataset = create_tf_dataset(
        db_path='data/gameon.db',
        game_name='Fortnite',
        batch_size=32,
        sequence_length=16
    )
    
    model.fit(dataset, epochs=10)
"""
import os
import sqlite3
from typing import Optional, Tuple, Generator
from pathlib import Path

import numpy as np
import cv2

try:
    import tensorflow as tf
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    print("⚠ TensorFlow not installed. Install with: pip install tensorflow")


def load_sessions(db_path: str, game_name: Optional[str] = None):
    """Load session metadata from database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    if game_name:
        query = "SELECT id, video_path, system_audio_path, fps, duration_seconds FROM sessions WHERE game_name = ?"
        cursor.execute(query, (game_name,))
    else:
        query = "SELECT id, video_path, system_audio_path, fps, duration_seconds FROM sessions"
        cursor.execute(query)
    
    sessions = cursor.fetchall()
    conn.close()
    
    return sessions


def load_input_events(db_path: str, session_id: int, start_ms: int, end_ms: int, action_dim: int = 20):
    """Load and encode input events."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    query = """
    SELECT timestamp_ms, input_device, button_key, action, value
    FROM input_events
    WHERE session_id = ? AND timestamp_ms >= ? AND timestamp_ms <= ?
    ORDER BY timestamp_ms
    """
    
    cursor.execute(query, (session_id, start_ms, end_ms))
    events = cursor.fetchall()
    conn.close()
    
    # Encode to action vector (customize based on your game)
    actions = np.zeros(action_dim, dtype=np.float32)
    
    # Simple encoding
    for timestamp_ms, device, button, action, value in events:
        if device == 'keyboard':
            key_map = {'w': 0, 'a': 1, 's': 2, 'd': 3, 'space': 4}
            if button.lower() in key_map:
                actions[key_map[button.lower()]] = 1.0
        elif device == 'mouse':
            if button == 'Button.left':
                actions[10] = 1.0
            elif button == 'Button.right':
                actions[11] = 1.0
    
    return actions


def frame_generator(
    db_path: str,
    game_name: Optional[str] = None,
    sequence_length: int = 16,
    target_size: Tuple[int, int] = (224, 224),
    frame_skip: int = 1
) -> Generator[Tuple[np.ndarray, np.ndarray], None, None]:
    """Generate (frames, actions) pairs."""
    
    sessions = load_sessions(db_path, game_name)
    
    for session_id, video_path, audio_path, fps, duration in sessions:
        if not os.path.exists(video_path):
            continue
        
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        frames_buffer = []
        frame_idx = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_idx % frame_skip == 0:
                # Convert BGR to RGB
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                # Resize
                frame = cv2.resize(frame, target_size)
                # Normalize
                frame = frame.astype(np.float32) / 255.0
                
                frames_buffer.append(frame)
                
                if len(frames_buffer) == sequence_length:
                    # Get timestamp range
                    start_ms = int((frame_idx - sequence_length * frame_skip) / fps * 1000)
                    end_ms = int(frame_idx / fps * 1000)
                    
                    # Load corresponding inputs
                    actions = load_input_events(db_path, session_id, start_ms, end_ms)
                    
                    # Yield sequence
                    frames_array = np.stack(frames_buffer)  # (T, H, W, C)
                    yield frames_array, actions
                    
                    # Slide window by half
                    frames_buffer = frames_buffer[sequence_length // 2:]
            
            frame_idx += 1
        
        cap.release()


def create_tf_dataset(
    db_path: str,
    game_name: Optional[str] = None,
    batch_size: int = 32,
    sequence_length: int = 16,
    target_size: Tuple[int, int] = (224, 224),
    frame_skip: int = 1,
    shuffle_buffer: int = 1000,
    prefetch: bool = True
):
    """
    Create TensorFlow dataset from GameOn recordings.
    
    Args:
        db_path: Path to GameOn database
        game_name: Filter by game name
        batch_size: Batch size
        sequence_length: Number of frames per sequence
        target_size: Resize frames to (height, width)
        frame_skip: Sample every N frames
        shuffle_buffer: Shuffle buffer size
        prefetch: Enable prefetching
        
    Returns:
        tf.data.Dataset
    """
    if not TF_AVAILABLE:
        raise ImportError("TensorFlow is required")
    
    # Define output signature
    output_signature = (
        tf.TensorSpec(shape=(sequence_length, *target_size, 3), dtype=tf.float32),  # frames
        tf.TensorSpec(shape=(20,), dtype=tf.float32)  # actions
    )
    
    # Create dataset from generator
    dataset = tf.data.Dataset.from_generator(
        lambda: frame_generator(db_path, game_name, sequence_length, target_size, frame_skip),
        output_signature=output_signature
    )
    
    # Shuffle
    if shuffle_buffer > 0:
        dataset = dataset.shuffle(shuffle_buffer)
    
    # Batch
    dataset = dataset.batch(batch_size)
    
    # Prefetch
    if prefetch:
        dataset = dataset.prefetch(tf.data.AUTOTUNE)
    
    return dataset


def export_to_tfrecord(
    db_path: str,
    output_dir: str,
    game_name: Optional[str] = None,
    examples_per_file: int = 1000
):
    """
    Export GameOn data to TFRecord format.
    
    Args:
        db_path: Path to GameOn database
        output_dir: Output directory for TFRecord files
        game_name: Filter by game name
        examples_per_file: Number of examples per TFRecord file
    """
    if not TF_AVAILABLE:
        print("❌ TensorFlow not available")
        return
    
    os.makedirs(output_dir, exist_ok=True)
    
    file_idx = 0
    example_count = 0
    writer = None
    
    generator = frame_generator(db_path, game_name)
    
    for frames, actions in generator:
        # Create new writer if needed
        if writer is None or example_count >= examples_per_file:
            if writer:
                writer.close()
            
            output_path = os.path.join(output_dir, f'gameon_{file_idx:04d}.tfrecord')
            writer = tf.io.TFRecordWriter(output_path)
            file_idx += 1
            example_count = 0
            print(f"Writing {output_path}...")
        
        # Create TF example
        feature = {
            'frames': tf.train.Feature(float_list=tf.train.FloatList(value=frames.flatten())),
            'frames_shape': tf.train.Feature(int64_list=tf.train.Int64List(value=frames.shape)),
            'actions': tf.train.Feature(float_list=tf.train.FloatList(value=actions)),
        }
        
        example = tf.train.Example(features=tf.train.Features(feature=feature))
        writer.write(example.SerializeToString())
        example_count += 1
    
    if writer:
        writer.close()
    
    print(f"✓ Exported {file_idx} TFRecord files to {output_dir}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Export GameOn data to TensorFlow format')
    parser.add_argument('--db', default='data/gameon.db', help='Database path')
    parser.add_argument('--game', help='Filter by game name')
    parser.add_argument('--output', default='gameon_tf/', help='Output directory')
    parser.add_argument('--format', choices=['dataset', 'tfrecord'], default='tfrecord', help='Export format')
    
    args = parser.parse_args()
    
    if args.format == 'tfrecord':
        export_to_tfrecord(
            db_path=args.db,
            output_dir=args.output,
            game_name=args.game
        )
    else:
        print("Use create_tf_dataset() in your training script for tf.data.Dataset format")

