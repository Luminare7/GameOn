"""
Enhanced video capture with H.264/H.265 compression support.
"""
import time
import platform
import subprocess
import os
from typing import Optional, Tuple
from pathlib import Path
import threading
import queue

import mss
import cv2
import numpy as np


class VideoCapture:
    """Video capture handler with support for multiple backends and compression."""
    
    def __init__(
        self,
        fps: int = 60,
        monitor_index: int = 0,
        output_path: Optional[str] = None,
        codec: str = 'h264',
        quality: int = 20,
        use_dxcam: bool = True
    ):
        """
        Initialize video capture.
        
        Args:
            fps: Target frames per second
            monitor_index: Monitor to capture (0 = primary)
            output_path: Path to save video file
            codec: Video codec ('h264', 'h265', 'mp4v', 'mjpeg', 'raw')
            quality: Quality for H.264/H.265 (CRF: 0=best, 51=worst, 18-23 recommended)
            use_dxcam: Try to use DXCam on Windows (faster)
        """
        self.fps = fps
        self.monitor_index = monitor_index
        self.output_path = output_path
        self.codec = codec.lower()
        self.quality = quality
        self.use_dxcam = use_dxcam
        
        self.is_recording = False
        self.video_writer = None
        self.ffmpeg_process = None
        self.capture_thread = None
        self.frame_queue = queue.Queue(maxsize=120)
        
        # Determine backend
        self.backend = None
        self.camera = None
        self._initialize_backend()
    
    def _initialize_backend(self):
        """Initialize the appropriate capture backend."""
        system = platform.system()
        
        # Try DXCam on Windows if requested
        if system == 'Windows' and self.use_dxcam:
            try:
                import dxcam
                self.camera = dxcam.create(output_idx=self.monitor_index)
                self.backend = 'dxcam'
                print(f"✓ Using DXCam backend (DirectX) on monitor {self.monitor_index}")
                return
            except ImportError:
                print("⚠ DXCam not available, falling back to MSS")
            except Exception as e:
                print(f"⚠ DXCam initialization failed: {e}, falling back to MSS")
        
        # Set backend to MSS but don't create camera yet
        # MSS object must be created in the same thread that uses it (Windows threading issue)
        self.backend = 'mss'
        self.camera = None  # Will be created in capture thread
        print(f"✓ Using MSS backend (cross-platform) on monitor {self.monitor_index}")
    
    def get_monitor_info(self) -> dict:
        """Get information about the selected monitor."""
        if self.backend == 'dxcam':
            frame = self.camera.grab()
            if frame is not None:
                return {
                    'width': frame.shape[1],
                    'height': frame.shape[0],
                    'index': self.monitor_index
                }
        else:  # MSS
            # Create temporary MSS object in this thread to get monitor info
            with mss.mss() as temp_mss:
                monitors = temp_mss.monitors
                if self.monitor_index < len(monitors):
                    mon = monitors[self.monitor_index + 1]
                    return {
                        'width': mon['width'],
                        'height': mon['height'],
                        'left': mon['left'],
                        'top': mon['top'],
                        'index': self.monitor_index
                    }
        
        return {}
    
    def _use_ffmpeg_compression(self) -> bool:
        """Check if we should use FFmpeg for compression."""
        return self.codec in ['h264', 'h265']
    
    def _start_ffmpeg_process(self, width: int, height: int):
        """Start FFmpeg process for H.264/H.265 encoding."""
        if self.codec == 'h264':
            codec_args = [
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', str(self.quality),
                '-pix_fmt', 'yuv420p',
                '-movflags', '+faststart'
            ]
            output_ext = '.mp4'
        elif self.codec == 'h265':
            codec_args = [
                '-c:v', 'libx265',
                '-preset', 'medium',
                '-crf', str(self.quality),
                '-pix_fmt', 'yuv420p',
                '-tag:v', 'hvc1'
            ]
            output_ext = '.mp4'
        else:
            raise ValueError(f"Unsupported codec for FFmpeg: {self.codec}")
        
        # Update output path extension
        output_path = self.output_path
        if not output_path.endswith(output_ext):
            output_path = os.path.splitext(output_path)[0] + output_ext
            self.output_path = output_path
        
        # FFmpeg command
        cmd = [
            'ffmpeg',
            '-y',  # Overwrite output file
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-s', f'{width}x{height}',
            '-pix_fmt', 'bgr24',
            '-r', str(self.fps),
            '-i', '-',  # Input from stdin
        ] + codec_args + [
            output_path
        ]
        
        # Start FFmpeg process
        self.ffmpeg_process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        print(f"✓ FFmpeg encoder started: {self.codec.upper()} CRF {self.quality}")
    
    def _capture_frame_mss(self, mss_instance) -> Optional[np.ndarray]:
        """Capture a frame using MSS."""
        try:
            monitors = mss_instance.monitors
            mon = monitors[self.monitor_index + 1]
            
            screenshot = mss_instance.grab(mon)
            frame = np.array(screenshot)
            
            # Convert BGRA to BGR
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            
            return frame
        except Exception as e:
            print(f"Error capturing frame with MSS: {e}")
            return None
    
    def _capture_frame_dxcam(self) -> Optional[np.ndarray]:
        """Capture a frame using DXCam."""
        try:
            frame = self.camera.grab()
            if frame is None:
                return None
            
            # DXCam returns RGB, convert to BGR for OpenCV/FFmpeg
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            return frame
        except Exception as e:
            print(f"Error capturing frame with DXCam: {e}")
            return None
    
    def _capture_loop(self):
        """Main capture loop running in separate thread."""
        frame_time = 1.0 / self.fps
        last_capture = time.time()
        frame_count = 0
        
        print(f"📹 Video capture started at {self.fps} FPS")
        
        # Create MSS object in THIS thread if using MSS backend
        # This fixes Windows threading issue with thread-local storage
        mss_instance = None
        if self.backend == 'mss':
            mss_instance = mss.mss()
            print("✓ MSS instance created in capture thread")
        
        try:
            while self.is_recording:
                current_time = time.time()
                elapsed = current_time - last_capture
                
                if elapsed >= frame_time:
                    # Capture frame
                    if self.backend == 'dxcam':
                        frame = self._capture_frame_dxcam()
                    else:
                        frame = self._capture_frame_mss(mss_instance)
                    
                    if frame is not None:
                        try:
                            self.frame_queue.put((frame, current_time), timeout=0.01)
                            frame_count += 1
                        except queue.Full:
                            print("⚠ Frame buffer full, dropping frame")
                    
                    last_capture = current_time
                else:
                    time.sleep(max(0.001, frame_time - elapsed))
        finally:
            # Clean up MSS instance
            if mss_instance:
                mss_instance.close()
                print("✓ MSS instance closed")
        
        print(f"📹 Video capture stopped. Captured {frame_count} frames")
    
    def _write_loop(self):
        """Video writing loop running in separate thread."""
        frame_count = 0
        
        while self.is_recording or not self.frame_queue.empty():
            try:
                frame, timestamp = self.frame_queue.get(timeout=1.0)
                
                if self.ffmpeg_process:
                    # Write to FFmpeg stdin
                    try:
                        self.ffmpeg_process.stdin.write(frame.tobytes())
                        frame_count += 1
                    except Exception as e:
                        print(f"❌ Error writing to FFmpeg: {e}")
                        break
                elif self.video_writer:
                    # Write with OpenCV VideoWriter
                    self.video_writer.write(frame)
                    frame_count += 1
                
            except queue.Empty:
                continue
        
        print(f"💾 Video writing stopped. Wrote {frame_count} frames")
    
    def start_recording(self) -> bool:
        """Start recording video."""
        if self.is_recording:
            print("⚠ Recording already in progress")
            return False
        
        if not self.output_path:
            print("❌ No output path specified")
            return False
        
        # Get monitor dimensions
        monitor_info = self.get_monitor_info()
        width = monitor_info.get('width', 1920)
        height = monitor_info.get('height', 1080)
        
        # Choose encoding method
        if self._use_ffmpeg_compression():
            try:
                self._start_ffmpeg_process(width, height)
            except Exception as e:
                print(f"❌ Failed to start FFmpeg: {e}")
                print("   Falling back to OpenCV encoder")
                self.codec = 'mp4v'
        
        # Fallback to OpenCV VideoWriter
        if not self.ffmpeg_process:
            if self.codec == 'mjpeg':
                fourcc = cv2.VideoWriter_fourcc(*'MJPG')
            elif self.codec == 'raw':
                fourcc = 0  # Uncompressed
            else:  # mp4v
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            
            self.video_writer = cv2.VideoWriter(
                self.output_path,
                fourcc,
                self.fps,
                (width, height)
            )
            
            if not self.video_writer.isOpened():
                print(f"❌ Failed to open video writer for {self.output_path}")
                return False
        
        # Start recording
        self.is_recording = True
        
        # Start threads
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        
        self.write_thread = threading.Thread(target=self._write_loop, daemon=True)
        self.write_thread.start()
        
        codec_info = f"{self.codec.upper()}"
        if self.codec in ['h264', 'h265']:
            codec_info += f" CRF {self.quality}"
        
        print(f"✓ Recording started: {self.output_path}")
        print(f"  Resolution: {width}x{height} @ {self.fps}fps")
        print(f"  Codec: {codec_info}")
        
        return True
    
    def stop_recording(self):
        """Stop recording video."""
        if not self.is_recording:
            return
        
        print("⏹ Stopping video recording...")
        self.is_recording = False
        
        # Wait for threads to finish
        if self.capture_thread:
            self.capture_thread.join(timeout=5.0)
        if self.write_thread:
            self.write_thread.join(timeout=5.0)
        
        # Close FFmpeg process
        if self.ffmpeg_process:
            try:
                self.ffmpeg_process.stdin.close()
                self.ffmpeg_process.wait(timeout=5.0)
                self.ffmpeg_process = None
            except Exception as e:
                print(f"⚠ Error closing FFmpeg: {e}")
        
        # Release OpenCV VideoWriter
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
        
        print("✓ Video recording stopped")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_recording()
        
        # Note: MSS instance is now created and closed in capture thread
        # DXCam camera cleanup
        if self.backend == 'dxcam' and self.camera:
            # DXCam handles cleanup automatically
            pass
