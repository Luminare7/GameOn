"""
Simple GUI for GameOn recording control.
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import sys
import os
from pathlib import Path

from ..session import SessionManager
from ..database import DatabaseManager


class GameOnGUI:
    """Simple GUI for GameOn."""
    
    def __init__(self, root):
        """Initialize GUI."""
        self.root = root
        self.root.title("GameOn - Gameplay Recorder")
        self.root.geometry("600x700")
        self.root.resizable(False, False)
        
        # Session state
        self.session_manager = None
        self.is_recording = False
        
        # Setup UI
        self._setup_ui()
        
        # Load config
        self.data_dir = './data'
        self.db_path = os.path.join(self.data_dir, 'gameon.db')
        self.sessions_path = os.path.join(self.data_dir, 'sessions')
    
    def _setup_ui(self):
        """Setup user interface."""
        # Title
        title_frame = tk.Frame(self.root, bg='#2c3e50', height=60)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(
            title_frame,
            text="🎮 GameOn Recorder",
            font=("Arial", 20, "bold"),
            bg='#2c3e50',
            fg='white'
        )
        title_label.pack(pady=15)
        
        # Main container
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Game name
        tk.Label(main_frame, text="Game Name:", font=("Arial", 11, "bold")).pack(anchor=tk.W, pady=(0, 5))
        self.game_entry = tk.Entry(main_frame, font=("Arial", 11), width=50)
        self.game_entry.pack(fill=tk.X, pady=(0, 15))
        self.game_entry.insert(0, "Enter game name...")
        
        # Input type
        input_frame = tk.LabelFrame(main_frame, text="Input Device", font=("Arial", 10, "bold"), padx=10, pady=10)
        input_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.input_type = tk.StringVar(value='keyboard')
        tk.Radiobutton(input_frame, text="Keyboard + Mouse", variable=self.input_type, value='keyboard', font=("Arial", 10)).pack(anchor=tk.W)
        tk.Radiobutton(input_frame, text="Xbox Controller", variable=self.input_type, value='xbox', font=("Arial", 10)).pack(anchor=tk.W)
        tk.Radiobutton(input_frame, text="PlayStation Controller", variable=self.input_type, value='playstation', font=("Arial", 10)).pack(anchor=tk.W)
        
        # Audio options
        audio_frame = tk.LabelFrame(main_frame, text="Audio Capture", font=("Arial", 10, "bold"), padx=10, pady=10)
        audio_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.capture_system_audio = tk.BooleanVar(value=True)
        self.capture_microphone = tk.BooleanVar(value=True)
        
        tk.Checkbutton(audio_frame, text="System Audio (game sounds)", variable=self.capture_system_audio, font=("Arial", 10)).pack(anchor=tk.W)
        tk.Checkbutton(audio_frame, text="Microphone (voice chat)", variable=self.capture_microphone, font=("Arial", 10)).pack(anchor=tk.W)
        
        # Video options
        video_frame = tk.LabelFrame(main_frame, text="Video Settings", font=("Arial", 10, "bold"), padx=10, pady=10)
        video_frame.pack(fill=tk.X, pady=(0, 15))
        
        fps_frame = tk.Frame(video_frame)
        fps_frame.pack(fill=tk.X, pady=2)
        tk.Label(fps_frame, text="FPS:", font=("Arial", 10)).pack(side=tk.LEFT, padx=(0, 10))
        self.fps_var = tk.IntVar(value=60)
        fps_spinbox = tk.Spinbox(fps_frame, from_=30, to=120, textvariable=self.fps_var, width=10, font=("Arial", 10))
        fps_spinbox.pack(side=tk.LEFT)
        
        monitor_frame = tk.Frame(video_frame)
        monitor_frame.pack(fill=tk.X, pady=2)
        tk.Label(monitor_frame, text="Monitor:", font=("Arial", 10)).pack(side=tk.LEFT, padx=(0, 10))
        self.monitor_var = tk.IntVar(value=0)
        monitor_spinbox = tk.Spinbox(monitor_frame, from_=0, to=3, textvariable=self.monitor_var, width=10, font=("Arial", 10))
        monitor_spinbox.pack(side=tk.LEFT)
        
        # Advanced options
        advanced_frame = tk.LabelFrame(main_frame, text="Advanced", font=("Arial", 10, "bold"), padx=10, pady=10)
        advanced_frame.pack(fill=tk.X, pady=(0, 15))
        
        latency_frame = tk.Frame(advanced_frame)
        latency_frame.pack(fill=tk.X, pady=2)
        tk.Label(latency_frame, text="Latency Offset (ms):", font=("Arial", 10)).pack(side=tk.LEFT, padx=(0, 10))
        self.latency_var = tk.IntVar(value=0)
        latency_spinbox = tk.Spinbox(latency_frame, from_=-500, to=500, textvariable=self.latency_var, width=10, font=("Arial", 10))
        latency_spinbox.pack(side=tk.LEFT)
        
        # Control buttons
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.start_button = tk.Button(
            button_frame,
            text="▶ START RECORDING",
            font=("Arial", 12, "bold"),
            bg='#27ae60',
            fg='white',
            command=self.start_recording,
            height=2
        )
        self.start_button.pack(fill=tk.X, pady=(0, 10))
        
        self.stop_button = tk.Button(
            button_frame,
            text="⏹ STOP RECORDING",
            font=("Arial", 12, "bold"),
            bg='#e74c3c',
            fg='white',
            command=self.stop_recording,
            state=tk.DISABLED,
            height=2
        )
        self.stop_button.pack(fill=tk.X)
        
        # Status log
        log_frame = tk.LabelFrame(main_frame, text="Status Log", font=("Arial", 10, "bold"), padx=5, pady=5)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, font=("Courier", 9), state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Initial log message
        self.log("Welcome to GameOn! Configure settings and click START RECORDING.")
    
    def log(self, message: str):
        """Add message to log."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def start_recording(self):
        """Start recording session."""
        # Validate inputs
        game_name = self.game_entry.get().strip()
        if not game_name or game_name == "Enter game name...":
            messagebox.showerror("Error", "Please enter a game name")
            return
        
        # Disable start button
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.is_recording = True
        
        self.log("\n" + "="*60)
        self.log("Starting recording session...")
        self.log("="*60)
        
        # Create session manager
        try:
            self.session_manager = SessionManager(
                db_path=self.db_path,
                sessions_base_path=self.sessions_path,
                game_name=game_name,
                input_type=self.input_type.get(),
                fps=self.fps_var.get(),
                latency_offset_ms=self.latency_var.get(),
                capture_system_audio=self.capture_system_audio.get(),
                capture_microphone=self.capture_microphone.get(),
                monitor_index=self.monitor_var.get()
            )
            
            # Start in separate thread
            def start_thread():
                try:
                    success = self.session_manager.start_recording()
                    if success:
                        self.log("✅ Recording started successfully!")
                    else:
                        self.log("❌ Failed to start recording")
                        self.root.after(0, self._reset_buttons)
                except Exception as e:
                    self.log(f"❌ Error: {str(e)}")
                    self.root.after(0, self._reset_buttons)
            
            thread = threading.Thread(target=start_thread, daemon=True)
            thread.start()
            
        except Exception as e:
            self.log(f"❌ Error: {str(e)}")
            messagebox.showerror("Error", f"Failed to start recording: {str(e)}")
            self._reset_buttons()
    
    def stop_recording(self):
        """Stop recording session."""
        if not self.session_manager or not self.is_recording:
            return
        
        self.log("\n" + "="*60)
        self.log("Stopping recording...")
        self.log("="*60)
        
        # Stop in separate thread
        def stop_thread():
            try:
                self.session_manager.stop_recording()
                self.log("✅ Recording stopped and saved!")
                self.root.after(0, self._reset_buttons)
            except Exception as e:
                self.log(f"❌ Error stopping: {str(e)}")
                self.root.after(0, self._reset_buttons)
        
        thread = threading.Thread(target=stop_thread, daemon=True)
        thread.start()
        
        self.is_recording = False
    
    def _reset_buttons(self):
        """Reset button states."""
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
    
    def on_closing(self):
        """Handle window closing."""
        if self.is_recording:
            if messagebox.askokcancel("Quit", "Recording in progress. Stop recording and quit?"):
                self.stop_recording()
                self.root.after(1000, self.root.destroy)
        else:
            self.root.destroy()


def run_gui():
    """Run GUI application."""
    root = tk.Tk()
    app = GameOnGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
    return 0


if __name__ == '__main__':
    run_gui()

