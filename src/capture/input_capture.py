"""
Input capture module for GameOn.
Supports keyboard, mouse, Xbox, and PlayStation controllers.
"""
import time
import platform
import threading
from typing import Optional, Callable, List
from datetime import datetime
from collections import deque

from pynput import keyboard, mouse


class InputCapture:
    """Input capture handler for keyboard, mouse, and gamepads."""
    
    def __init__(
        self,
        input_type: str = 'keyboard',
        capture_mouse: bool = True,
        latency_offset_ms: int = 0,
        event_callback: Optional[Callable] = None
    ):
        """
        Initialize input capture.
        
        Args:
            input_type: Type of input ('keyboard', 'xbox', 'playstation')
            capture_mouse: Capture mouse events (only for keyboard mode)
            latency_offset_ms: Milliseconds to offset timestamps (for sync)
            event_callback: Callback function for each input event
        """
        self.input_type = input_type.lower()
        self.capture_mouse = capture_mouse and input_type == 'keyboard'
        self.latency_offset_ms = latency_offset_ms
        self.event_callback = event_callback
        
        self.is_recording = False
        self.start_time = None
        
        # Listeners
        self.keyboard_listener = None
        self.mouse_listener = None
        self.gamepad_thread = None
        
        # Event buffer
        self.events = deque(maxlen=10000)  # Buffer for events
        
        print(f"🎮 Input capture initialized: {self.input_type}")
    
    def get_timestamp_ms(self) -> int:
        """Get current timestamp in milliseconds from recording start."""
        if not self.start_time:
            return 0
        elapsed = (time.time() - self.start_time) * 1000
        return int(elapsed + self.latency_offset_ms)
    
    def _on_keyboard_press(self, key):
        """Callback for keyboard press events."""
        if not self.is_recording:
            return
        
        try:
            # Try to get character
            key_name = key.char if hasattr(key, 'char') else str(key)
        except AttributeError:
            key_name = str(key)
        
        event = {
            'timestamp_ms': self.get_timestamp_ms(),
            'input_device': 'keyboard',
            'button_key': key_name,
            'action': 'press',
            'value': 1.0,
            'x_position': None,
            'y_position': None
        }
        
        self.events.append(event)
        
        if self.event_callback:
            self.event_callback(event)
    
    def _on_keyboard_release(self, key):
        """Callback for keyboard release events."""
        if not self.is_recording:
            return
        
        try:
            key_name = key.char if hasattr(key, 'char') else str(key)
        except AttributeError:
            key_name = str(key)
        
        event = {
            'timestamp_ms': self.get_timestamp_ms(),
            'input_device': 'keyboard',
            'button_key': key_name,
            'action': 'release',
            'value': 0.0,
            'x_position': None,
            'y_position': None
        }
        
        self.events.append(event)
        
        if self.event_callback:
            self.event_callback(event)
    
    def _on_mouse_click(self, x, y, button, pressed):
        """Callback for mouse click events."""
        if not self.is_recording:
            return
        
        event = {
            'timestamp_ms': self.get_timestamp_ms(),
            'input_device': 'mouse',
            'button_key': str(button),
            'action': 'press' if pressed else 'release',
            'value': 1.0 if pressed else 0.0,
            'x_position': float(x),
            'y_position': float(y)
        }
        
        self.events.append(event)
        
        if self.event_callback:
            self.event_callback(event)
    
    def _on_mouse_move(self, x, y):
        """Callback for mouse move events."""
        if not self.is_recording:
            return
        
        # Only record every Nth mouse move to avoid overwhelming the database
        if len(self.events) % 10 == 0:  # Record 1 in 10 move events
            event = {
                'timestamp_ms': self.get_timestamp_ms(),
                'input_device': 'mouse',
                'button_key': 'move',
                'action': 'move',
                'value': None,
                'x_position': float(x),
                'y_position': float(y)
            }
            
            self.events.append(event)
            
            if self.event_callback:
                self.event_callback(event)
    
    def _on_mouse_scroll(self, x, y, dx, dy):
        """Callback for mouse scroll events."""
        if not self.is_recording:
            return
        
        event = {
            'timestamp_ms': self.get_timestamp_ms(),
            'input_device': 'mouse',
            'button_key': 'scroll',
            'action': 'scroll',
            'value': float(dy),  # Vertical scroll amount
            'x_position': float(x),
            'y_position': float(y)
        }
        
        self.events.append(event)
        
        if self.event_callback:
            self.event_callback(event)
    
    def _gamepad_loop(self):
        """Loop for capturing gamepad inputs."""
        system = platform.system()
        
        if system != 'Windows':
            print("⚠ Gamepad capture is currently only supported on Windows")
            return
        
        try:
            import inputs
            
            print(f"🎮 Gamepad capture started ({self.input_type})")
            
            while self.is_recording:
                try:
                    events = inputs.get_gamepad()
                    
                    for event in events:
                        if not self.is_recording:
                            break
                        
                        # Map event type
                        action = 'press' if event.ev_type == 'Key' else 'move'
                        
                        input_event = {
                            'timestamp_ms': self.get_timestamp_ms(),
                            'input_device': self.input_type,
                            'button_key': event.code,
                            'action': action,
                            'value': float(event.state),
                            'x_position': None,
                            'y_position': None
                        }
                        
                        self.events.append(input_event)
                        
                        if self.event_callback:
                            self.event_callback(input_event)
                
                except inputs.UnpluggedError:
                    print("⚠ Gamepad disconnected")
                    time.sleep(1.0)
                except Exception as e:
                    print(f"⚠ Gamepad error: {e}")
                    time.sleep(0.1)
        
        except ImportError:
            print("❌ 'inputs' library not installed. Gamepad capture unavailable.")
        except Exception as e:
            print(f"❌ Gamepad initialization error: {e}")
    
    def start_recording(self) -> bool:
        """
        Start recording input events.
        
        Returns:
            True if recording started successfully
        """
        if self.is_recording:
            print("⚠ Input recording already in progress")
            return False
        
        self.is_recording = True
        self.start_time = time.time()
        self.events.clear()
        
        # Start keyboard/mouse capture
        if self.input_type == 'keyboard':
            try:
                # Start keyboard listener
                self.keyboard_listener = keyboard.Listener(
                    on_press=self._on_keyboard_press,
                    on_release=self._on_keyboard_release
                )
                self.keyboard_listener.start()
                print("⌨️  Keyboard capture started")
                
                # Start mouse listener if enabled
                if self.capture_mouse:
                    self.mouse_listener = mouse.Listener(
                        on_click=self._on_mouse_click,
                        on_move=self._on_mouse_move,
                        on_scroll=self._on_mouse_scroll
                    )
                    self.mouse_listener.start()
                    print("🖱️  Mouse capture started")
                
                return True
                
            except Exception as e:
                print(f"❌ Failed to start keyboard/mouse capture: {e}")
                self.is_recording = False
                return False
        
        # Start gamepad capture
        elif self.input_type in ['xbox', 'playstation']:
            try:
                self.gamepad_thread = threading.Thread(
                    target=self._gamepad_loop,
                    daemon=True
                )
                self.gamepad_thread.start()
                return True
                
            except Exception as e:
                print(f"❌ Failed to start gamepad capture: {e}")
                self.is_recording = False
                return False
        
        else:
            print(f"❌ Unknown input type: {self.input_type}")
            self.is_recording = False
            return False
    
    def stop_recording(self) -> List[dict]:
        """
        Stop recording input events.
        
        Returns:
            List of captured events
        """
        if not self.is_recording:
            return []
        
        print("⏹ Stopping input capture...")
        self.is_recording = False
        
        # Stop keyboard listener
        if self.keyboard_listener:
            try:
                self.keyboard_listener.stop()
                self.keyboard_listener = None
            except Exception as e:
                print(f"⚠ Error stopping keyboard listener: {e}")
        
        # Stop mouse listener
        if self.mouse_listener:
            try:
                self.mouse_listener.stop()
                self.mouse_listener = None
            except Exception as e:
                print(f"⚠ Error stopping mouse listener: {e}")
        
        # Wait for gamepad thread
        if self.gamepad_thread:
            self.gamepad_thread.join(timeout=2.0)
            self.gamepad_thread = None
        
        # Get captured events
        captured_events = list(self.events)
        print(f"✓ Input capture stopped. Captured {len(captured_events)} events")
        
        return captured_events
    
    def get_events(self) -> List[dict]:
        """Get all captured events without stopping recording."""
        return list(self.events)
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_recording()

