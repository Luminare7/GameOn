"""
Audio capture module for GameOn.
Supports system audio and microphone capture separately.
"""
import time
import platform
import threading
import queue
from typing import Optional
from pathlib import Path

import sounddevice as sd
import soundfile as sf
import numpy as np


class AudioCapture:
    """Audio capture handler for system audio and microphone."""
    
    def __init__(
        self,
        sample_rate: int = 44100,
        channels: int = 2,
        capture_system: bool = True,
        capture_microphone: bool = True,
        system_output_path: Optional[str] = None,
        microphone_output_path: Optional[str] = None
    ):
        """
        Initialize audio capture.
        
        Args:
            sample_rate: Audio sample rate (Hz)
            channels: Number of audio channels (1=mono, 2=stereo)
            capture_system: Enable system audio capture
            capture_microphone: Enable microphone capture
            system_output_path: Path to save system audio
            microphone_output_path: Path to save microphone audio
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.capture_system = capture_system
        self.capture_microphone = capture_microphone
        self.system_output_path = system_output_path
        self.microphone_output_path = microphone_output_path
        
        self.is_recording = False
        self.system_stream = None
        self.mic_stream = None
        self.system_file = None
        self.mic_file = None
        
        self.system_device = None
        self.mic_device = None
        
        self._initialize_devices()
    
    def _initialize_devices(self):
        """Initialize audio devices."""
        system = platform.system()
        
        # List available devices
        devices = sd.query_devices()
        
        # Find system audio device (loopback/WASAPI on Windows)
        if system == 'Windows' and self.capture_system:
            try:
                # On Windows, try to find WASAPI loopback device
                import pyaudiowpatch as pyaudio
                
                p = pyaudio.PyAudio()
                wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
                
                # Find default loopback device
                for i in range(wasapi_info.get('deviceCount')):
                    device_info = p.get_device_info_by_host_api_device_index(
                        wasapi_info.get('index'), i
                    )
                    if device_info.get('maxInputChannels') > 0 and \
                       'loopback' in device_info.get('name', '').lower():
                        self.system_device = device_info.get('index')
                        print(f"✓ Found system audio device: {device_info.get('name')}")
                        break
                
                p.terminate()
                
            except ImportError:
                print("⚠ pyaudiowpatch not available. System audio capture may not work on Windows.")
            except Exception as e:
                print(f"⚠ Error detecting system audio device: {e}")
        
        # Find default microphone
        if self.capture_microphone:
            try:
                self.mic_device = sd.default.device[0]  # Default input device
                mic_info = sd.query_devices(self.mic_device, 'input')
                print(f"✓ Using microphone: {mic_info['name']}")
            except Exception as e:
                print(f"⚠ Error detecting microphone: {e}")
    
    def list_devices(self):
        """Print all available audio devices."""
        print("\n📢 Available Audio Devices:")
        print(sd.query_devices())
    
    def _system_audio_callback(self, indata, frames, time_info, status):
        """Callback for system audio stream."""
        if status:
            print(f"⚠ System audio status: {status}")
        
        if self.system_file and self.is_recording:
            try:
                self.system_file.write(indata.copy())
            except Exception as e:
                print(f"❌ Error writing system audio: {e}")
    
    def _microphone_callback(self, indata, frames, time_info, status):
        """Callback for microphone stream."""
        if status:
            print(f"⚠ Microphone status: {status}")
        
        if self.mic_file and self.is_recording:
            try:
                self.mic_file.write(indata.copy())
            except Exception as e:
                print(f"❌ Error writing microphone audio: {e}")
    
    def start_recording(self) -> bool:
        """
        Start recording audio.
        
        Returns:
            True if recording started successfully
        """
        if self.is_recording:
            print("⚠ Audio recording already in progress")
            return False
        
        success = True
        
        # Start system audio capture
        if self.capture_system and self.system_output_path:
            try:
                # Open output file
                self.system_file = sf.SoundFile(
                    self.system_output_path,
                    mode='w',
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    format='WAV'
                )
                
                # Start stream
                device = self.system_device if self.system_device is not None else sd.default.device[0]
                self.system_stream = sd.InputStream(
                    device=device,
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    callback=self._system_audio_callback
                )
                self.system_stream.start()
                print(f"🔊 System audio recording started: {self.system_output_path}")
                
            except Exception as e:
                print(f"❌ Failed to start system audio recording: {e}")
                success = False
        
        # Start microphone capture
        if self.capture_microphone and self.microphone_output_path:
            try:
                # Open output file
                self.mic_file = sf.SoundFile(
                    self.microphone_output_path,
                    mode='w',
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    format='WAV'
                )
                
                # Start stream
                device = self.mic_device if self.mic_device is not None else sd.default.device[0]
                self.mic_stream = sd.InputStream(
                    device=device,
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    callback=self._microphone_callback
                )
                self.mic_stream.start()
                print(f"🎤 Microphone recording started: {self.microphone_output_path}")
                
            except Exception as e:
                print(f"❌ Failed to start microphone recording: {e}")
                success = False
        
        self.is_recording = success
        return success
    
    def stop_recording(self):
        """Stop recording audio."""
        if not self.is_recording:
            return
        
        print("⏹ Stopping audio recording...")
        self.is_recording = False
        
        # Stop system audio
        if self.system_stream:
            try:
                self.system_stream.stop()
                self.system_stream.close()
                self.system_stream = None
            except Exception as e:
                print(f"⚠ Error stopping system audio: {e}")
        
        if self.system_file:
            try:
                self.system_file.close()
                self.system_file = None
                print("✓ System audio saved")
            except Exception as e:
                print(f"⚠ Error closing system audio file: {e}")
        
        # Stop microphone
        if self.mic_stream:
            try:
                self.mic_stream.stop()
                self.mic_stream.close()
                self.mic_stream = None
            except Exception as e:
                print(f"⚠ Error stopping microphone: {e}")
        
        if self.mic_file:
            try:
                self.mic_file.close()
                self.mic_file = None
                print("✓ Microphone audio saved")
            except Exception as e:
                print(f"⚠ Error closing microphone file: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_recording()


def list_audio_devices():
    """Helper function to list all audio devices."""
    print("\n📢 Available Audio Devices:")
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        device_type = []
        if device['max_input_channels'] > 0:
            device_type.append('INPUT')
        if device['max_output_channels'] > 0:
            device_type.append('OUTPUT')
        
        print(f"{i}: {device['name']}")
        print(f"   Type: {', '.join(device_type)}")
        print(f"   Channels: In={device['max_input_channels']}, Out={device['max_output_channels']}")
        print(f"   Sample Rate: {device['default_samplerate']} Hz")
        print()

