"""
HDF5 export for GameOn recordings.
Portable format that works with PyTorch, TensorFlow, and other frameworks.

Usage:
    from src.export.hdf5_export import export_to_hdf5
    
    export_to_hdf5(
        db_path='data/gameon.db',
        output_path='fortnite_dataset.h5',
        game_name='Fortnite'
    )
"""
import os
import sqlite3
from typing import Optional
from pathlib import Path

import numpy as np
import cv2

try:
    import h5py
    HDF5_AVAILABLE = True
except ImportError:
    HDF5_AVAILABLE = False
    print("⚠ h5py not installed. Install with: pip install h5py")


def export_to_hdf5(
    db_path: str,
    output_path: str,
    game_name: Optional[str] = None,
    compression: str = 'gzip',
    downsample_factor: int = 1,
    max_frames: Optional[int] = None
):
    """
    Export GameOn data to HDF5 format.
    
    Args:
        db_path: Path to GameOn database
        output_path: Output HDF5 file path
        game_name: Filter by game name (None = all games)
        compression: Compression method ('gzip', 'lzf', None)
        downsample_factor: Reduce resolution by this factor
        max_frames: Maximum frames to export (None = all)
    """
    if not HDF5_AVAILABLE:
        raise ImportError("h5py is required for HDF5 export")
    
    print(f"📦 Exporting to HDF5: {output_path}")
    
    # Load sessions
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    if game_name:
        query = "SELECT * FROM sessions WHERE game_name = ?"
        cursor.execute(query, (game_name,))
    else:
        query = "SELECT * FROM sessions"
        cursor.execute(query)
    
    sessions = cursor.fetchall()
    
    if not sessions:
        print("❌ No sessions found")
        return
    
    print(f"✓ Found {len(sessions)} sessions")
    
    # Create HDF5 file
    with h5py.File(output_path, 'w') as hf:
        # Metadata group
        meta_grp = hf.create_group('metadata')
        meta_grp.attrs['num_sessions'] = len(sessions)
        meta_grp.attrs['game_name'] = game_name or 'all'
        
        # Process each session
        for idx, session in enumerate(sessions):
            session_id = session[0]
            game = session[1]
            video_path = session[5]
            
            if not os.path.exists(video_path):
                print(f"⚠ Video not found: {video_path}")
                continue
            
            print(f"Processing session {idx + 1}/{len(sessions)}: {game}...")
            
            # Create session group
            sess_grp = hf.create_group(f'session_{session_id:04d}')
            sess_grp.attrs['session_id'] = session_id
            sess_grp.attrs['game_name'] = game
            sess_grp.attrs['fps'] = session[9] or 60
            
            # Load video
            cap = cv2.VideoCapture(video_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) // downsample_factor
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) // downsample_factor
            
            if max_frames:
                total_frames = min(total_frames, max_frames)
            
            # Create video dataset
            video_ds = sess_grp.create_dataset(
                'video',
                shape=(total_frames, height, width, 3),
                dtype=np.uint8,
                compression=compression
            )
            
            # Read frames
            frame_idx = 0
            while frame_idx < total_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Convert BGR to RGB
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Downsample if needed
                if downsample_factor > 1:
                    frame = cv2.resize(frame, (width, height))
                
                video_ds[frame_idx] = frame
                frame_idx += 1
                
                if frame_idx % 100 == 0:
                    print(f"  {frame_idx}/{total_frames} frames processed")
            
            cap.release()
            
            # Load input events
            cursor.execute(
                "SELECT timestamp_ms, input_device, button_key, action, value, x_position, y_position "
                "FROM input_events WHERE session_id = ? ORDER BY timestamp_ms",
                (session_id,)
            )
            events = cursor.fetchall()
            
            if events:
                # Store input events
                timestamps = np.array([e[0] for e in events], dtype=np.int64)
                devices = np.array([e[1].encode('utf-8') for e in events], dtype='S20')
                buttons = np.array([e[2].encode('utf-8') for e in events], dtype='S50')
                actions = np.array([e[3].encode('utf-8') for e in events], dtype='S20')
                values = np.array([e[4] if e[4] is not None else 0.0 for e in events], dtype=np.float32)
                x_pos = np.array([e[5] if e[5] is not None else 0.0 for e in events], dtype=np.float32)
                y_pos = np.array([e[6] if e[6] is not None else 0.0 for e in events], dtype=np.float32)
                
                # Create input events group
                input_grp = sess_grp.create_group('inputs')
                input_grp.create_dataset('timestamps', data=timestamps, compression=compression)
                input_grp.create_dataset('devices', data=devices, compression=compression)
                input_grp.create_dataset('buttons', data=buttons, compression=compression)
                input_grp.create_dataset('actions', data=actions, compression=compression)
                input_grp.create_dataset('values', data=values, compression=compression)
                input_grp.create_dataset('x_positions', data=x_pos, compression=compression)
                input_grp.create_dataset('y_positions', data=y_pos, compression=compression)
                
                print(f"  ✓ {len(events)} input events saved")
            
            print(f"  ✓ Session {session_id} complete")
    
    conn.close()
    
    file_size = os.path.getsize(output_path) / (1024 ** 3)
    print(f"\n✅ Export complete!")
    print(f"   Output: {output_path}")
    print(f"   Size: {file_size:.2f} GB")


def load_hdf5_dataset(hdf5_path: str, session_id: Optional[int] = None):
    """
    Load data from HDF5 file.
    
    Args:
        hdf5_path: Path to HDF5 file
        session_id: Specific session to load (None = first session)
        
    Returns:
        Dictionary with 'video', 'inputs', and 'metadata'
    """
    if not HDF5_AVAILABLE:
        raise ImportError("h5py is required")
    
    with h5py.File(hdf5_path, 'r') as hf:
        # Get session
        if session_id:
            sess_key = f'session_{session_id:04d}'
        else:
            sess_key = list(hf.keys())[1]  # Skip 'metadata'
        
        sess_grp = hf[sess_key]
        
        # Load data
        video = sess_grp['video'][:]
        
        inputs = None
        if 'inputs' in sess_grp:
            inputs = {
                'timestamps': sess_grp['inputs/timestamps'][:],
                'devices': sess_grp['inputs/devices'][:],
                'buttons': sess_grp['inputs/buttons'][:],
                'actions': sess_grp['inputs/actions'][:],
                'values': sess_grp['inputs/values'][:],
                'x_positions': sess_grp['inputs/x_positions'][:],
                'y_positions': sess_grp['inputs/y_positions'][:]
            }
        
        metadata = dict(sess_grp.attrs)
        
        return {
            'video': video,
            'inputs': inputs,
            'metadata': metadata
        }


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Export GameOn data to HDF5 format')
    parser.add_argument('--db', default='data/gameon.db', help='Database path')
    parser.add_argument('--game', help='Filter by game name')
    parser.add_argument('--output', default='gameon_dataset.h5', help='Output HDF5 file')
    parser.add_argument('--downsample', type=int, default=1, help='Downsample factor')
    parser.add_argument('--max-frames', type=int, help='Maximum frames per session')
    parser.add_argument('--compression', default='gzip', choices=['gzip', 'lzf', 'none'], help='Compression')
    
    args = parser.parse_args()
    
    compression = None if args.compression == 'none' else args.compression
    
    export_to_hdf5(
        db_path=args.db,
        output_path=args.output,
        game_name=args.game,
        compression=compression,
        downsample_factor=args.downsample,
        max_frames=args.max_frames
    )

