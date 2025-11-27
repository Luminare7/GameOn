# PyTorch & TensorFlow Export Guide

## Overview

GameOn data can be exported to formats optimized for PyTorch and TensorFlow training.

---

## Database Location

**Default location:** `./data/gameon.db`

The database and all session data are stored in the `data/` directory, which is **already in `.gitignore`** to keep your data private until you decide to share it.

```
data/
├── gameon.db           # SQLite database (PRIVATE - in .gitignore)
└── sessions/           # Session directories (PRIVATE - in .gitignore)
    ├── Game1_20231127_143022/
    │   ├── video.mp4
    │   ├── system_audio.wav
    │   └── microphone_audio.wav
    └── ...
```

**Privacy:** Your recordings stay local until you explicitly export or share them.

---

## Export Formats

### 1. **PyTorch Dataset** (Recommended)
- Custom `torch.utils.data.Dataset` class
- Lazy loading (memory efficient)
- Automatic preprocessing pipeline
- Compatible with `DataLoader`

### 2. **TensorFlow Dataset**
- `tf.data.Dataset` format
- Efficient pipeline with prefetching
- Automatic batching and augmentation
- Compatible with `model.fit()`

### 3. **HDF5 Format**
- Universal format (works with both)
- Self-contained (video + inputs + metadata)
- Fast random access
- Chunked storage

### 4. **NumPy Arrays**
- Simple `.npz` format
- Good for small datasets
- Easy to load and inspect

---

## Export Tools

### PyTorch Export

```python
from src.export.pytorch_export import GameOnDataset

# Create PyTorch dataset
dataset = GameOnDataset(
    db_path='data/gameon.db',
    game_name='Fortnite',  # Optional: filter by game
    transform=None,        # Optional: custom transforms
    frame_skip=1,          # Sample every N frames
    sequence_length=16     # Number of frames per sample
)

# Use with DataLoader
from torch.utils.data import DataLoader

dataloader = DataLoader(
    dataset,
    batch_size=32,
    shuffle=True,
    num_workers=4
)

# Training loop
for batch in dataloader:
    frames = batch['frames']      # (B, T, C, H, W)
    inputs = batch['inputs']      # (B, T, num_actions)
    audio = batch['audio']        # (B, T, audio_channels)
    
    # Your model here
    predictions = model(frames, audio)
    loss = criterion(predictions, inputs)
    # ...
```

### TensorFlow Export

```python
from src.export.tensorflow_export import create_tf_dataset

# Create TensorFlow dataset
dataset = create_tf_dataset(
    db_path='data/gameon.db',
    game_name='Fortnite',
    batch_size=32,
    sequence_length=16,
    prefetch=True
)

# Training
model.fit(
    dataset,
    epochs=10,
    validation_data=val_dataset
)

# Or iterate manually
for batch in dataset:
    frames, inputs, audio = batch
    # frames: (B, T, H, W, C)
    # inputs: (B, T, num_actions)
    # audio: (B, T, audio_features)
    
    with tf.GradientTape() as tape:
        predictions = model(frames, audio)
        loss = loss_fn(inputs, predictions)
    # ...
```

### HDF5 Export

```python
from src.export.hdf5_export import export_to_hdf5

# Export sessions to HDF5
export_to_hdf5(
    db_path='data/gameon.db',
    output_path='fortnite_dataset.h5',
    game_name='Fortnite',
    compression='gzip',     # Compress data
    downsample_factor=2     # Reduce resolution if needed
)

# Load in PyTorch or TensorFlow
import h5py
with h5py.File('fortnite_dataset.h5', 'r') as f:
    video = f['video'][:]       # All video frames
    inputs = f['inputs'][:]     # All input events
    metadata = f['metadata'][:]  # Session metadata
```

---

## Data Format Specifications

### Frame Data
- **Shape**: `(T, H, W, C)` where T=time, H=height, W=width, C=channels
- **Type**: `uint8` (0-255) or `float32` (0.0-1.0)
- **Color**: RGB (converted from BGR if needed)
- **Resolution**: Original or downsampled

### Input Data
- **Shape**: `(T, A)` where T=time, A=actions
- **Type**: `float32`
- **Encoding**: One-hot or multi-hot encoding
- **Actions**: Keyboard keys, mouse buttons, gamepad buttons

**Example action vector:**
```python
actions = [
    0.0,  # W key
    1.0,  # A key (pressed)
    0.0,  # S key
    0.0,  # D key
    1.0,  # Mouse left (pressed)
    0.0,  # Mouse right
    0.5,  # Mouse X velocity (normalized)
    0.2,  # Mouse Y velocity (normalized)
    # ... more actions
]
```

### Audio Data
- **Shape**: `(T, F)` where T=time, F=frequency bins
- **Type**: `float32`
- **Format**: Mel spectrogram or raw waveform
- **Sample rate**: 44100 Hz or downsampled

---

## Usage Examples

### Example 1: Behavioral Cloning

```python
import torch
from src.export.pytorch_export import GameOnDataset

# Load dataset
dataset = GameOnDataset(
    db_path='data/gameon.db',
    game_name='Fortnite',
    sequence_length=1  # Single frame
)

# Simple CNN model
class BehavioralCloning(torch.nn.Module):
    def __init__(self, num_actions):
        super().__init__()
        self.cnn = torch.nn.Sequential(
            torch.nn.Conv2d(3, 32, 8, 4),
            torch.nn.ReLU(),
            torch.nn.Conv2d(32, 64, 4, 2),
            torch.nn.ReLU(),
            torch.nn.Flatten(),
            torch.nn.Linear(64 * 22 * 22, 512),
            torch.nn.ReLU(),
            torch.nn.Linear(512, num_actions)
        )
    
    def forward(self, x):
        return self.cnn(x)

# Train
model = BehavioralCloning(num_actions=10)
optimizer = torch.optim.Adam(model.parameters())

for epoch in range(10):
    for batch in dataloader:
        frames = batch['frames']
        actions = batch['inputs']
        
        predictions = model(frames)
        loss = torch.nn.functional.binary_cross_entropy_with_logits(
            predictions, actions
        )
        
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
```

### Example 2: Sequence Model (LSTM)

```python
import torch
from src.export.pytorch_export import GameOnDataset

dataset = GameOnDataset(
    db_path='data/gameon.db',
    game_name='Fortnite',
    sequence_length=16  # 16 frame sequences
)

class SequenceModel(torch.nn.Module):
    def __init__(self, num_actions):
        super().__init__()
        self.cnn = torch.nn.Conv2d(3, 64, 8, 4)
        self.lstm = torch.nn.LSTM(64 * 53 * 53, 256, 2)
        self.fc = torch.nn.Linear(256, num_actions)
    
    def forward(self, x):
        # x: (B, T, C, H, W)
        B, T = x.shape[:2]
        
        # Process each frame
        x = x.view(B * T, *x.shape[2:])
        x = self.cnn(x)
        x = x.view(B, T, -1)
        
        # LSTM
        x, _ = self.lstm(x)
        
        # Predict last action
        return self.fc(x[:, -1])
```

### Example 3: TensorFlow with Audio

```python
import tensorflow as tf
from src.export.tensorflow_export import create_tf_dataset

dataset = create_tf_dataset(
    db_path='data/gameon.db',
    game_name='CS:GO',
    include_audio=True,
    sequence_length=8
)

# Multi-modal model
video_input = tf.keras.Input(shape=(8, 224, 224, 3))
audio_input = tf.keras.Input(shape=(8, 128))

# Video branch
x = tf.keras.layers.TimeDistributed(
    tf.keras.layers.Conv2D(32, 3)
)(video_input)
x = tf.keras.layers.LSTM(128)(x)

# Audio branch
y = tf.keras.layers.LSTM(64)(audio_input)

# Combine
z = tf.keras.layers.Concatenate()([x, y])
output = tf.keras.layers.Dense(num_actions, activation='sigmoid')(z)

model = tf.keras.Model(
    inputs=[video_input, audio_input],
    outputs=output
)
```

---

## Advanced: Custom Preprocessing

```python
from torchvision import transforms

# Define preprocessing pipeline
transform = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),  # Augmentation
    transforms.ColorJitter(0.2, 0.2),   # Augmentation
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

dataset = GameOnDataset(
    db_path='data/gameon.db',
    transform=transform
)
```

---

## Performance Tips

### 1. **Use Compressed Video**
- H.264/H.265 reduces load times
- Automatic decompression in PyTorch/TF

### 2. **Frame Skipping**
- Sample every N frames to reduce data
- Many consecutive frames are similar

### 3. **Prefetching**
- Use `num_workers` in PyTorch DataLoader
- Use `prefetch()` in TensorFlow dataset

### 4. **Caching**
- Cache preprocessed frames for repeated use
- Store in HDF5 for fast random access

### 5. **Downsampling**
- Lower resolution for faster training
- 224x224 or 128x128 often sufficient

---

## Export CLI Commands

```bash
# Export to PyTorch format
python -m src.export.pytorch_export --game "Fortnite" --output fortnite_torch.pt

# Export to TensorFlow format
python -m src.export.tensorflow_export --game "Fortnite" --output fortnite_tf/

# Export to HDF5
python -m src.export.hdf5_export --game "Fortnite" --output fortnite.h5

# Export all sessions
python -m src.export.hdf5_export --all --output all_games.h5
```

---

## Data Sharing

When you're ready to share your dataset:

```bash
# 1. Export to HDF5 (portable format)
python -m src.export.hdf5_export --game "Fortnite" --output fortnite_dataset.h5

# 2. Share the HDF5 file (others can load it easily)
# The file contains video, audio, inputs, and metadata all in one!
```

Recipients can load it in PyTorch or TensorFlow without needing GameOn installed.

---

## Conclusion

GameOn provides flexible export options for AI training:
- ✅ Native PyTorch Dataset
- ✅ TensorFlow tf.data pipeline
- ✅ Portable HDF5 format
- ✅ Privacy preserved (data/ in .gitignore)
- ✅ Efficient preprocessing
- ✅ Ready for distributed training

The implementation is provided in the `src/export/` module!

