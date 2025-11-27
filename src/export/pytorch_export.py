"""
PyTorch Dataset export for GameOn recordings.

Usage:
    from src.export.pytorch_export import GameOnDataset
    
    dataset = GameOnDataset(
        db_path='data/gameon.db',
        game_name='Fortnite',
        sequence_length=16
    )
    
    dataloader = DataLoader(dataset, batch_size=32, shuffle=True)
"""
import os
import sqlite3
from typing import Optional, Dict, List, Tuple, Callable
from pathlib import Path

import numpy as np
import cv2

try:
    import torch
    from torch.utils.data import Dataset
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print("⚠ PyTorch not installed. Install with: pip install torch torchvision")


class GameOnDataset(Dataset):
    """PyTorch Dataset for GameOn gameplay recordings."""
    
    def __init__(
        self,
        db_path: str,
        game_name: Optional[str] = None,
        session_ids: Optional[List[int]] = None,
        sequence_length: int = 16,
        frame_skip: int = 1,
        transform: Optional[Callable] = None,
        load_audio: bool = False,
        target_size: Tuple[int, int] = (224, 224)
    ):
        """
        Initialize PyTorch dataset.
        
        Args:
            db_path: Path to GameOn database
            game_name: Filter sessions by game name (None = all games)
            session_ids: Specific session IDs to load (None = all)
            sequence_length: Number of frames per sample
            frame_skip: Sample every N frames (1 = all frames)
            transform: Optional transform to apply to frames
            load_audio: Whether to load audio data
            target_size: Resize frames to this size
        """
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch is required for this dataset")
        
        self.db_path = db_path
        self.game_name = game_name
        self.sequence_length = sequence_length
        self.frame_skip = frame_skip
        self.transform = transform
        self.load_audio = load_audio
        self.target_size = target_size
        
        # Load session metadata
        self.sessions = self._load_sessions(session_ids)
        
        # Build index of sequences
        self.sequences = self._build_sequence_index()
        
        print(f"✓ Loaded {len(self.sessions)} sessions")
        print(f"✓ Total sequences: {len(self.sequences)}")
    
    def _load_sessions(self, session_ids: Optional[List[int]]) -> List[Dict]:
        """Load session metadata from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if session_ids:
            placeholders = ','.join('?' * len(session_ids))
            query = f"SELECT * FROM sessions WHERE id IN ({placeholders})"
            cursor.execute(query, session_ids)
        elif self.game_name:
            query = "SELECT * FROM sessions WHERE game_name = ?"
            cursor.execute(query, (self.game_name,))
        else:
            query = "SELECT * FROM sessions"
            cursor.execute(query)
        
        sessions = []
        for row in cursor.fetchall():
            sessions.append({
                'id': row[0],
                'game_name': row[1],
                'video_path': row[5],
                'system_audio_path': row[6],
                'microphone_audio_path': row[7],
                'fps': row[9],
                'duration_seconds': row[4]
            })
        
        conn.close()
        return sessions
    
    def _build_sequence_index(self) -> List[Dict]:
        """Build index of all possible sequences."""
        sequences = []
        
        for session in self.sessions:
            video_path = session['video_path']
            
            if not os.path.exists(video_path):
                print(f"⚠ Video not found: {video_path}")
                continue
            
            # Get video info
            cap = cv2.VideoCapture(video_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.release()
            
            # Create sequences
            step = self.frame_skip * self.sequence_length
            for start_frame in range(0, total_frames - step, step // 2):
                sequences.append({
                    'session_id': session['id'],
                    'video_path': video_path,
                    'start_frame': start_frame,
                    'audio_path': session['system_audio_path'],
                    'mic_path': session['microphone_audio_path']
                })
        
        return sequences
    
    def _load_input_events(self, session_id: int, start_time_ms: int, end_time_ms: int) -> np.ndarray:
        """Load input events for a time range."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = """
        SELECT timestamp_ms, input_device, button_key, action, value, x_position, y_position
        FROM input_events
        WHERE session_id = ? AND timestamp_ms >= ? AND timestamp_ms <= ?
        ORDER BY timestamp_ms
        """
        
        cursor.execute(query, (session_id, start_time_ms, end_time_ms))
        events = cursor.fetchall()
        conn.close()
        
        # Convert to action vector
        # TODO: Customize this encoding based on your needs
        action_dim = 20  # Example: 20 possible actions
        actions = np.zeros((self.sequence_length, action_dim), dtype=np.float32)
        
        # Simple encoding (customize based on your game)
        for event in events:
            timestamp_ms, device, button, action, value, x, y = event
            
            # Map to frame index
            frame_idx = int((timestamp_ms - start_time_ms) * self.sequence_length / (end_time_ms - start_time_ms))
            if 0 <= frame_idx < self.sequence_length:
                # Simple one-hot encoding (customize this!)
                if device == 'keyboard':
                    # Map common keys
                    key_map = {'w': 0, 'a': 1, 's': 2, 'd': 3, 'space': 4}
                    if button.lower() in key_map:
                        actions[frame_idx, key_map[button.lower()]] = 1.0
                elif device == 'mouse':
                    if button == 'Button.left':
                        actions[frame_idx, 10] = 1.0
                    elif button == 'Button.right':
                        actions[frame_idx, 11] = 1.0
        
        return actions
    
    def __len__(self) -> int:
        """Return dataset size."""
        return len(self.sequences)
    
    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        """Get a sample."""
        sequence = self.sequences[idx]
        
        # Load video frames
        frames = []
        cap = cv2.VideoCapture(sequence['video_path'])
        cap.set(cv2.CAP_PROP_POS_FRAMES, sequence['start_frame'])
        
        for i in range(self.sequence_length):
            # Skip frames if needed
            for _ in range(self.frame_skip):
                ret, frame = cap.read()
                if not ret:
                    break
            
            if ret:
                # Convert BGR to RGB
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Resize
                frame = cv2.resize(frame, self.target_size)
                
                # Apply transform if provided
                if self.transform:
                    frame = self.transform(frame)
                else:
                    # Default: convert to tensor and normalize
                    frame = torch.from_numpy(frame).float() / 255.0
                    frame = frame.permute(2, 0, 1)  # HWC -> CHW
                
                frames.append(frame)
            else:
                # Pad with zeros if video ends
                frames.append(torch.zeros_like(frames[-1]) if frames else torch.zeros(3, *self.target_size))
        
        cap.release()
        
        # Stack frames: (T, C, H, W)
        frames = torch.stack(frames)
        
        # Load input events
        fps = 60  # Default FPS
        start_time_ms = int((sequence['start_frame'] / fps) * 1000)
        end_time_ms = int(((sequence['start_frame'] + self.sequence_length * self.frame_skip) / fps) * 1000)
        
        inputs = self._load_input_events(sequence['session_id'], start_time_ms, end_time_ms)
        inputs = torch.from_numpy(inputs).float()
        
        sample = {
            'frames': frames,
            'inputs': inputs,
            'session_id': sequence['session_id']
        }
        
        # TODO: Add audio loading if requested
        if self.load_audio and sequence['audio_path']:
            # Load audio features here
            pass
        
        return sample


def export_to_pytorch(
    db_path: str,
    output_path: str,
    game_name: Optional[str] = None,
    **dataset_kwargs
):
    """
    Export GameOn data to PyTorch-compatible format.
    
    Args:
        db_path: Path to GameOn database
        output_path: Output file path (.pt)
        game_name: Filter by game name
        **dataset_kwargs: Additional arguments for GameOnDataset
    """
    if not TORCH_AVAILABLE:
        print("❌ PyTorch not available")
        return
    
    # Create dataset
    dataset = GameOnDataset(db_path=db_path, game_name=game_name, **dataset_kwargs)
    
    # Save metadata
    data = {
        'dataset': dataset,
        'num_samples': len(dataset),
        'game_name': game_name,
        'sequence_length': dataset.sequence_length
    }
    
    torch.save(data, output_path)
    print(f"✓ Exported to {output_path}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Export GameOn data to PyTorch format')
    parser.add_argument('--db', default='data/gameon.db', help='Database path')
    parser.add_argument('--game', help='Filter by game name')
    parser.add_argument('--output', default='gameon_pytorch.pt', help='Output file')
    parser.add_argument('--seq-length', type=int, default=16, help='Sequence length')
    
    args = parser.parse_args()
    
    export_to_pytorch(
        db_path=args.db,
        output_path=args.output,
        game_name=args.game,
        sequence_length=args.seq_length
    )

