"""
Enhanced GUI for GameOn recording control with comprehensive tooltips.
FIXED: Scrollable canvas widget interactivity issue
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import queue
import time
import platform
import sys
import os
from pathlib import Path

from ..session import SessionManager
from ..database import DatabaseManager


class ToolTip:
    """Create a tooltip for a given widget."""
    
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
    
    def show_tooltip(self, event=None):
        """Display tooltip."""
        if self.tooltip_window or not self.text:
            return
        
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(
            tw,
            text=self.text,
            justify=tk.LEFT,
            background="#ffffe0",
            relief=tk.SOLID,
            borderwidth=1,
            font=("Arial", 9),
            wraplength=400,
            padx=8,
            pady=6
        )
        label.pack()
    
    def hide_tooltip(self, event=None):
        """Hide tooltip."""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


class _LineBufferedStream:
    """
    File-like stream that forwards complete lines to a callback.
    Used to safely pipe stdout/stderr into the GUI log.
    """

    def __init__(self, on_line):
        self._on_line = on_line
        self._buffer = ""

    def write(self, data):
        if not data:
            return 0
        # Tkinter-safe logging is handled by GameOnGUI via queueing.
        self._buffer += str(data)
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            if line.strip():
                self._on_line(line)
        return len(str(data))

    def flush(self):
        # Nothing to flush; the GUI log is not buffered at the widget level.
        return


class GUIStyle:
    """Central place for colors/fonts to keep UI code readable."""

    HEADER_BG = "#2c3e50"
    HEADER_FG = "white"
    HEADER_SUB_FG = "#ecf0f1"

    START_BG = "#27ae60"
    STOP_BG = "#e74c3c"
    STATS_BG = "#3498db"

    LOG_BG = "#f8f9fa"

    FONT_TITLE = ("Arial", 22, "bold")
    FONT_SUBTITLE = ("Arial", 9)
    FONT_SECTION = ("Arial", 11, "bold")
    FONT_LABEL = ("Arial", 10)
    FONT_LABEL_BOLD = ("Arial", 10, "bold")
    FONT_BUTTON_BIG = ("Arial", 13, "bold")
    FONT_BUTTON = ("Arial", 10)
    FONT_LOG = ("Courier", 9)


class GameOnGUI:
    """Enhanced GUI for GameOn with all parameters and tooltips."""
    
    def __init__(self, root):
        """Initialize GUI."""
        self.root = root
        self.style = GUIStyle()
        self.root.title("GameOn - Gameplay Recorder")
        self.root.geometry("700x900")
        self.root.resizable(True, True)
        
        # Session state
        self.session_manager = None
        self.is_recording = False
        self._state = "idle"  # idle | starting | recording | stopping
        self._recording_started_at = None
        self._recording_lock = threading.Lock()

        # Thread-safe UI/event bridge
        self._ui_queue: "queue.Queue[tuple]" = queue.Queue()
        self._drain_job = None

        # Stdout/stderr redirection (so background prints show up in GUI)
        self._orig_stdout = None
        self._orig_stderr = None
        self._stdout_stream = None
        self._stderr_stream = None
        
        # Setup UI
        self._setup_ui()
        self._start_queue_drain()
        
        # Load config
        self.data_dir = './data'
        self.db_path = os.path.join(self.data_dir, 'gameon.db')
        self.sessions_path = os.path.join(self.data_dir, 'sessions')
    
    def _create_labeled_widget(self, parent, label_text, widget, tooltip_text, **grid_kwargs):
        """Helper to create labeled widget with tooltip."""
        frame = tk.Frame(parent)
        frame.pack(fill=tk.X, pady=3)
        
        label = tk.Label(frame, text=label_text, font=self.style.FONT_LABEL, width=20, anchor='w')
        label.pack(side=tk.LEFT, padx=(0, 10))
        
        widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Add tooltip to both label and widget
        if tooltip_text:
            ToolTip(label, tooltip_text)
            ToolTip(widget, tooltip_text)
        
        return frame

    # ========================================
    # Thread-safe UI helpers
    # ========================================

    def _queue_log(self, message: str):
        self._ui_queue.put(("log", message))

    def _queue_status(self, message: str):
        self._ui_queue.put(("status", message))

    def _queue_error(self, title: str, message: str):
        self._ui_queue.put(("error", title, message))

    def _append_log_to_widget(self, message: str):
        """Must be called on the Tk main thread."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _start_queue_drain(self):
        """Begin periodic draining of the UI queue on the main thread."""
        if self._drain_job is None:
            self._drain_job = self.root.after(50, self._drain_ui_queue)

    def _drain_ui_queue(self):
        self._drain_job = None
        try:
            while True:
                item = self._ui_queue.get_nowait()
                kind = item[0]
                if kind == "log":
                    self._append_log_to_widget(item[1])
                elif kind == "status":
                    if hasattr(self, "status_var"):
                        self.status_var.set(item[1])
                elif kind == "error":
                    _, title, msg = item
                    messagebox.showerror(title, msg)
        except queue.Empty:
            pass

        # Update timer text if recording
        if self.is_recording and self._recording_started_at and hasattr(self, "timer_var"):
            elapsed = int(time.time() - self._recording_started_at)
            mm, ss = divmod(elapsed, 60)
            hh, mm = divmod(mm, 60)
            if hh:
                self.timer_var.set(f"{hh:d}:{mm:02d}:{ss:02d}")
            else:
                self.timer_var.set(f"{mm:02d}:{ss:02d}")

        self._start_queue_drain()

    def _install_stdio_redirect(self):
        """Redirect stdout/stderr into the GUI log (best-effort)."""
        if self._orig_stdout is not None:
            return  # already installed

        self._orig_stdout = sys.stdout
        self._orig_stderr = sys.stderr

        self._stdout_stream = _LineBufferedStream(lambda line: self._queue_log(line))
        self._stderr_stream = _LineBufferedStream(lambda line: self._queue_log(f"ERR: {line}"))

        sys.stdout = self._stdout_stream
        sys.stderr = self._stderr_stream

    def _restore_stdio(self):
        if self._orig_stdout is None:
            return
        sys.stdout = self._orig_stdout
        sys.stderr = self._orig_stderr
        self._orig_stdout = None
        self._orig_stderr = None
        self._stdout_stream = None
        self._stderr_stream = None

    def _set_controls_enabled(self, enabled: bool):
        """Enable/disable configuration controls during recording."""
        state = tk.NORMAL if enabled else tk.DISABLED
        # Some widgets are ttk and expect string states; tk widgets accept both.
        for w in getattr(self, "_config_widgets", []):
            try:
                w.configure(state=state)
            except Exception:
                try:
                    w.configure(state=("readonly" if enabled else "disabled"))
                except Exception:
                    pass
    
    def _setup_ui(self):
        """Setup user interface."""
        # Title bar
        title_frame = tk.Frame(self.root, bg=self.style.HEADER_BG, height=70)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(
            title_frame,
            text="🎮 GameOn Recorder",
            font=self.style.FONT_TITLE,
            bg=self.style.HEADER_BG,
            fg=self.style.HEADER_FG
        )
        title_label.pack(pady=12)
        
        subtitle = tk.Label(
            title_frame,
            text="Capture gameplay video, audio & inputs for AI training",
            font=self.style.FONT_SUBTITLE,
            bg=self.style.HEADER_BG,
            fg=self.style.HEADER_SUB_FG
        )
        subtitle.pack()
        
        # ===== FIXED: Main scrollable container =====
        container = tk.Frame(self.root)
        container.pack(fill=tk.BOTH, expand=True)
        
        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        
        # Create window and store the window ID
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        # Configure scrolling
        def configure_scroll(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        def configure_canvas_width(event):
            # Update the width of the scrollable frame to match canvas width
            canvas.itemconfig(canvas_window, width=event.width)
        
        scrollable_frame.bind("<Configure>", configure_scroll)
        canvas.bind("<Configure>", configure_canvas_width)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Enable mouse wheel scrolling
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # Bind mousewheel to canvas, not globally (to avoid issues)
        def bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        def unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
        
        canvas.bind("<Enter>", bind_mousewheel)
        canvas.bind("<Leave>", unbind_mousewheel)
        
        # Pack scrollbar and canvas
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        
        main_frame = tk.Frame(scrollable_frame, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        # ===== END FIXED SECTION =====
        
        # ===== GAME NAME =====
        game_section = tk.LabelFrame(main_frame, text="📝 Game Information", font=self.style.FONT_SECTION, padx=15, pady=10)
        game_section.pack(fill=tk.X, pady=(0, 10))
        
        game_label = tk.Label(game_section, text="Game Name:", font=self.style.FONT_LABEL_BOLD)
        game_label.pack(anchor=tk.W, pady=(0, 5))
        
        self.game_entry = tk.Entry(game_section, font=("Arial", 11), width=50)
        self.game_entry.pack(fill=tk.X, pady=(0, 5))
        self.game_entry.insert(0, "Enter game name...")
        
        # Clear placeholder on focus
        def clear_placeholder(event):
            if self.game_entry.get() == "Enter game name...":
                self.game_entry.delete(0, tk.END)
        
        def restore_placeholder(event):
            if not self.game_entry.get():
                self.game_entry.insert(0, "Enter game name...")
        
        self.game_entry.bind("<FocusIn>", clear_placeholder)
        self.game_entry.bind("<FocusOut>", restore_placeholder)
        
        ToolTip(self.game_entry, 
                "The name of the game you're recording.\n\n"
                "Used to organize sessions in the database.\n"
                "Example: 'Fortnite', 'Counter-Strike 2', 'Elden Ring'\n\n"
                "💡 Tip: Use consistent names for the same game.")
        
        # ===== INPUT DEVICE =====
        input_section = tk.LabelFrame(main_frame, text="🎮 Input Device", font=self.style.FONT_SECTION, padx=15, pady=10)
        input_section.pack(fill=tk.X, pady=(0, 10))
        
        self.input_type = tk.StringVar(value='keyboard')
        
        kb_radio = tk.Radiobutton(input_section, text="⌨️  Keyboard + Mouse", 
                                   variable=self.input_type, value='keyboard', 
                                   font=self.style.FONT_LABEL)
        kb_radio.pack(anchor=tk.W, pady=2)
        ToolTip(kb_radio,
                "Capture keyboard keys and mouse clicks/movements.\n\n"
                "✅ Best for: FPS games, MOBAs, strategy games\n"
                "📊 Captures: Key presses, mouse clicks, mouse position, scroll\n"
                "⚡ Performance: Very low CPU usage\n\n"
                "Note: Mouse movements are throttled to reduce data size.")
        
        xbox_radio = tk.Radiobutton(input_section, text="🎮 Xbox Controller", 
                                     variable=self.input_type, value='xbox', 
                                     font=self.style.FONT_LABEL)
        xbox_radio.pack(anchor=tk.W, pady=2)
        ToolTip(xbox_radio,
                "Capture Xbox controller inputs (XInput).\n\n"
                "✅ Best for: Console ports, racing games, platformers\n"
                "📊 Captures: All buttons, triggers, analog sticks\n"
                "🖥️  Platform: Windows only (XInput API)\n\n"
                "⚠️ Ensure controller is connected before starting.")
        
        ps_radio = tk.Radiobutton(input_section, text="🎮 PlayStation Controller", 
                                   variable=self.input_type, value='playstation', 
                                   font=self.style.FONT_LABEL)
        ps_radio.pack(anchor=tk.W, pady=2)
        ToolTip(ps_radio,
                "Capture PlayStation controller inputs (DirectInput).\n\n"
                "✅ Best for: PS4/PS5 games, console ports\n"
                "📊 Captures: All buttons, triggers, analog sticks\n"
                "🖥️  Platform: Windows only (DirectInput API)\n\n"
                "⚠️ Ensure controller is connected before starting.")
        
        self.capture_mouse = tk.BooleanVar(value=True)
        mouse_check = tk.Checkbutton(input_section, text="Include mouse events (keyboard mode only)", 
                                      variable=self.capture_mouse, font=("Arial", 9, "italic"))
        mouse_check.pack(anchor=tk.W, pady=(10, 2))
        ToolTip(mouse_check,
                "When using keyboard mode, also capture mouse events.\n\n"
                "✅ Recommended for most games (FPS, MOBA, RTS)\n"
                "📊 Captures: Clicks, movements, scroll wheel\n"
                "💾 Data size: Minimal (movements are throttled)\n\n"
                "Disable only if game doesn't use mouse.")
        
        # ===== AUDIO CAPTURE =====
        audio_section = tk.LabelFrame(main_frame, text="🔊 Audio Capture", font=self.style.FONT_SECTION, padx=15, pady=10)
        audio_section.pack(fill=tk.X, pady=(0, 10))
        
        self.capture_system_audio = tk.BooleanVar(value=True)
        self.sys_audio_check = tk.Checkbutton(audio_section, text="🎵 System Audio (game sounds)", 
                                              variable=self.capture_system_audio, font=self.style.FONT_LABEL)
        self.sys_audio_check.pack(anchor=tk.W, pady=2)
        ToolTip(self.sys_audio_check,
                "Capture system audio output (game sounds, music, effects).\n\n"
                "✅ Uses: WASAPI loopback (Windows)\n"
                "📊 Format: WAV, 44.1kHz stereo, ~50MB/hour\n"
                "📁 Saved as: system_audio.wav (separate file)\n\n"
                "🎯 Use for: Audio-based AI models, game sound analysis\n"
                "🖥️  Platform: Windows only (WASAPI required)\n\n"
                "💡 Tip: Captures everything your speakers would play.")
        
        self.capture_microphone = tk.BooleanVar(value=True)
        self.mic_check = tk.Checkbutton(audio_section, text="🎤 Microphone (voice chat)", 
                                        variable=self.capture_microphone, font=self.style.FONT_LABEL)
        self.mic_check.pack(anchor=tk.W, pady=2)
        ToolTip(self.mic_check,
                "Capture microphone input (your voice, team chat).\n\n"
                "✅ Cross-platform (works everywhere)\n"
                "📊 Format: WAV, 44.1kHz stereo, ~50MB/hour\n"
                "📁 Saved as: microphone_audio.wav (separate file)\n\n"
                "🎯 Use for: Communication analysis, voice commands\n\n"
                "💡 Tip: Stored separately from system audio for flexibility.")
        
        # ===== VIDEO SETTINGS =====
        video_section = tk.LabelFrame(main_frame, text="📹 Video Settings", font=self.style.FONT_SECTION, padx=15, pady=10)
        video_section.pack(fill=tk.X, pady=(0, 10))
        
        # FPS
        fps_frame = tk.Frame(video_section)
        fps_frame.pack(fill=tk.X, pady=3)
        fps_label = tk.Label(fps_frame, text="Frame Rate (FPS):", font=self.style.FONT_LABEL, width=20, anchor='w')
        fps_label.pack(side=tk.LEFT)
        self.fps_var = tk.IntVar(value=60)
        fps_spinbox = tk.Spinbox(fps_frame, from_=15, to=120, increment=15, 
                                  textvariable=self.fps_var, width=10, font=self.style.FONT_LABEL)
        fps_spinbox.pack(side=tk.LEFT)
        ToolTip(fps_label,
                "Video capture frame rate (frames per second).\n\n"
                "⚡ 30 FPS: Lower CPU, smaller files (~250MB/hour)\n"
                "✅ 60 FPS: Recommended, smooth motion (~500MB/hour)\n"
                "🚀 120 FPS: High-speed games, larger files (~1GB/hour)\n\n"
                "💡 Choose based on:\n"
                "  • Game speed (fast = higher FPS)\n"
                "  • Storage space available\n"
                "  • CPU performance\n\n"
                "Note: Files sizes with H.264 compression.")
        ToolTip(fps_spinbox,
                "Video capture frame rate (frames per second).\n\n"
                "⚡ 30 FPS: Lower CPU, smaller files (~250MB/hour)\n"
                "✅ 60 FPS: Recommended, smooth motion (~500MB/hour)\n"
                "🚀 120 FPS: High-speed games, larger files (~1GB/hour)")
        
        # Codec
        codec_frame = tk.Frame(video_section)
        codec_frame.pack(fill=tk.X, pady=3)
        codec_label = tk.Label(codec_frame, text="Video Codec:", font=self.style.FONT_LABEL, width=20, anchor='w')
        codec_label.pack(side=tk.LEFT)
        self.codec_var = tk.StringVar(value='h264')
        codec_combo = ttk.Combobox(codec_frame, textvariable=self.codec_var, 
                                    values=['h264', 'h265', 'mp4v', 'mjpeg', 'raw'],
                                    state='readonly', width=15, font=self.style.FONT_LABEL)
        codec_combo.pack(side=tk.LEFT)
        ToolTip(codec_label,
                "Video compression codec.\n\n"
                "✅ H.264 (Recommended): 20x compression, excellent quality\n"
                "🚀 H.265: 40x compression, slower encoding\n"
                "⚠️  MP4V: Basic codec, larger files\n"
                "❌ Raw: Uncompressed, ~10GB/hour (testing only)\n\n"
                "💡 Requires FFmpeg installed (brew/choco install ffmpeg)")
        ToolTip(codec_combo,
                "Video compression codec.\n\n"
                "✅ H.264 (Recommended): 20x compression, excellent quality\n"
                "🚀 H.265: 40x compression, slower encoding")
        
        # Quality
        quality_frame = tk.Frame(video_section)
        quality_frame.pack(fill=tk.X, pady=3)
        quality_label = tk.Label(quality_frame, text="Video Quality (CRF):", font=self.style.FONT_LABEL, width=20, anchor='w')
        quality_label.pack(side=tk.LEFT)
        self.quality_var = tk.IntVar(value=20)
        quality_spinbox = tk.Spinbox(quality_frame, from_=0, to=51, 
                                      textvariable=self.quality_var, width=10, font=self.style.FONT_LABEL)
        quality_spinbox.pack(side=tk.LEFT)
        quality_info = tk.Label(quality_frame, text="(lower = better)", font=("Arial", 9, "italic"), fg='gray')
        quality_info.pack(side=tk.LEFT, padx=(5, 0))
        ToolTip(quality_label,
                "Constant Rate Factor (CRF) for H.264/H.265.\n\n"
                "Quality Scale:\n"
                "  0 = Lossless (huge files)\n"
                "  18 = Nearly lossless (best for AI)\n"
                "  ✅ 20 = Excellent (recommended)\n"
                "  23 = High quality\n"
                "  51 = Worst quality\n\n"
                "💡 For AI training: 18-23 is perfect")
        ToolTip(quality_spinbox,
                "Constant Rate Factor (CRF) for H.264/H.265.\n\n"
                "✅ 20 = Excellent (recommended)\n"
                "Lower = Better quality, larger files")
        
        # Monitor
        monitor_frame = tk.Frame(video_section)
        monitor_frame.pack(fill=tk.X, pady=3)
        monitor_label = tk.Label(monitor_frame, text="Monitor:", font=self.style.FONT_LABEL, width=20, anchor='w')
        monitor_label.pack(side=tk.LEFT)
        self.monitor_var = tk.IntVar(value=0)
        monitor_spinbox = tk.Spinbox(monitor_frame, from_=0, to=5, 
                                      textvariable=self.monitor_var, width=10, font=self.style.FONT_LABEL)
        monitor_spinbox.pack(side=tk.LEFT)
        ToolTip(monitor_label,
                "Which monitor to capture.\n\n"
                "✅ 0 = Primary monitor (recommended)\n"
                "  1, 2, 3... = Secondary monitors")
        ToolTip(monitor_spinbox,
                "Which monitor to capture.\n\n"
                "✅ 0 = Primary monitor (recommended)")
        
        # DXCam
        self.use_dxcam = tk.BooleanVar(value=True)
        self.dxcam_check = tk.Checkbutton(video_section, text="Use DXCam (Windows DirectX optimization)", 
                                          variable=self.use_dxcam, font=("Arial", 9, "italic"))
        self.dxcam_check.pack(anchor=tk.W, pady=(8, 2))
        ToolTip(self.dxcam_check,
                "Enable DirectX hardware-accelerated capture (Windows only).\n\n"
                "✅ Advantages:\n"
                "  • 3x faster capture than MSS\n"
                "  • Lower CPU usage (~5% vs 15%)\n\n"
                "💡 Highly recommended for Windows!")
        
        # ===== ADVANCED SETTINGS =====
        advanced_section = tk.LabelFrame(main_frame, text="⚙️  Advanced Settings", font=self.style.FONT_SECTION, padx=15, pady=10)
        advanced_section.pack(fill=tk.X, pady=(0, 10))
        
        # Latency
        latency_frame = tk.Frame(advanced_section)
        latency_frame.pack(fill=tk.X, pady=3)
        latency_label = tk.Label(latency_frame, text="Latency Offset (ms):", font=self.style.FONT_LABEL, width=20, anchor='w')
        latency_label.pack(side=tk.LEFT)
        self.latency_var = tk.IntVar(value=0)
        latency_spinbox = tk.Spinbox(latency_frame, from_=-500, to=500, increment=10,
                                      textvariable=self.latency_var, width=10, font=self.style.FONT_LABEL)
        latency_spinbox.pack(side=tk.LEFT)
        ToolTip(latency_label,
                "Timing offset between video and inputs (milliseconds).\n\n"
                "When to adjust:\n"
                "  • Inputs appear BEFORE they should → Use positive (+50ms)\n"
                "  • Inputs appear AFTER they should → Use negative (-50ms)\n\n"
                "✅ Default (0ms) works for most systems")
        ToolTip(latency_spinbox,
                "Timing offset between video and inputs (milliseconds).\n\n"
                "✅ Default (0ms) works for most systems")
        
        # Sample Rate
        sample_frame = tk.Frame(advanced_section)
        sample_frame.pack(fill=tk.X, pady=3)
        sample_label = tk.Label(sample_frame, text="Audio Sample Rate:", font=self.style.FONT_LABEL, width=20, anchor='w')
        sample_label.pack(side=tk.LEFT)
        self.sample_rate_var = tk.IntVar(value=44100)
        sample_combo = ttk.Combobox(sample_frame, textvariable=self.sample_rate_var,
                                     values=[22050, 44100, 48000, 96000],
                                     state='readonly', width=15, font=self.style.FONT_LABEL)
        sample_combo.pack(side=tk.LEFT)
        ToolTip(sample_label,
                "Audio recording sample rate (Hz).\n\n"
                "✅ 44100 Hz: CD quality (recommended)")
        ToolTip(sample_combo,
                "Audio recording sample rate (Hz).\n\n"
                "✅ 44100 Hz: CD quality (recommended)")
        
        # ===== STORAGE INFO =====
        storage_section = tk.LabelFrame(main_frame, text="💾 Storage Estimate", font=self.style.FONT_SECTION, padx=15, pady=10)
        storage_section.pack(fill=tk.X, pady=(0, 10))
        
        self.storage_label = tk.Label(storage_section, text="", font=("Arial", 9), justify=tk.LEFT)
        self.storage_label.pack(anchor=tk.W)
        
        # Calculate button
        calc_btn = tk.Button(storage_section, text="📊 Calculate Storage", 
                              command=self._update_storage_estimate,
                              font=("Arial", 9))
        calc_btn.pack(anchor=tk.W, pady=(5, 0))
        
        # ===== CONTROL BUTTONS =====
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 15))
        
        self.start_button = tk.Button(
            button_frame,
            text="▶ START RECORDING",
            font=self.style.FONT_BUTTON_BIG,
            bg=self.style.START_BG,
            fg='white',
            command=self.start_recording,
            height=2,
            cursor='hand2'
        )
        self.start_button.pack(fill=tk.X, pady=(0, 10))
        
        self.stop_button = tk.Button(
            button_frame,
            text="⏹ STOP RECORDING",
            font=self.style.FONT_BUTTON_BIG,
            bg=self.style.STOP_BG,
            fg='white',
            command=self.stop_recording,
            state=tk.DISABLED,
            height=2,
            cursor='hand2'
        )
        self.stop_button.pack(fill=tk.X, pady=(0, 10))
        
        # Stats button
        stats_btn = tk.Button(
            button_frame,
            text="📊 View Statistics",
            font=self.style.FONT_BUTTON,
            command=self._show_stats,
            bg=self.style.STATS_BG,
            fg='white',
            cursor='hand2'
        )
        stats_btn.pack(fill=tk.X)

        # Status + progress + timer (visible feedback)
        status_frame = tk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(5, 10))

        self.status_var = tk.StringVar(value="Idle")
        status_label = tk.Label(status_frame, textvariable=self.status_var, font=self.style.FONT_LABEL_BOLD, anchor="w")
        status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.timer_var = tk.StringVar(value="00:00")
        timer_label = tk.Label(status_frame, textvariable=self.timer_var, font=self.style.FONT_LABEL, width=8, anchor="e")
        timer_label.pack(side=tk.RIGHT)

        self.progress = ttk.Progressbar(main_frame, mode="indeterminate")
        self.progress.pack(fill=tk.X, pady=(0, 10))
        self.progress.stop()
        
        # ===== STATUS LOG =====
        log_frame = tk.LabelFrame(main_frame, text="📜 Status Log", font=self.style.FONT_LABEL_BOLD, padx=5, pady=5)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=10,
            font=self.style.FONT_LOG,
            state=tk.DISABLED,
            bg=self.style.LOG_BG
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Initial messages
        self.log("✨ Welcome to GameOn - Gameplay Recorder for AI Training!")
        self.log("💡 Hover over any setting to see detailed explanations")
        self.log("📝 Configure your settings above and click START RECORDING")
        self.log("")

        # Track controls that should be disabled while recording
        self._config_widgets = [
            self.game_entry,
            kb_radio, xbox_radio, ps_radio,
            mouse_check,
            getattr(self, "sys_audio_check", None),
            getattr(self, "mic_check", None),
            fps_spinbox, codec_combo, quality_spinbox, monitor_spinbox,
            getattr(self, "dxcam_check", None),
            latency_spinbox, sample_combo,
            calc_btn,
        ]
        self._config_widgets = [w for w in self._config_widgets if w is not None]

        # Platform hints (so users see why something might not work)
        sys_name = platform.system()
        if sys_name != "Windows":
            self.log(f"ℹ️ Platform detected: {sys_name}. Some capture options are Windows-only (DXCam, system audio loopback, gamepads).")
        
        # Update storage estimate
        self._update_storage_estimate()
    
    def _update_storage_estimate(self):
        """Update storage estimate based on current settings."""
        fps = self.fps_var.get()
        codec = self.codec_var.get()
        
        # Estimate video size per hour
        if codec == 'h264':
            video_size = 500 * (fps / 60)  # ~500MB/hr at 60fps
        elif codec == 'h265':
            video_size = 250 * (fps / 60)  # ~250MB/hr at 60fps
        elif codec == 'mp4v':
            video_size = 1500 * (fps / 60)
        elif codec == 'mjpeg':
            video_size = 2000 * (fps / 60)
        else:  # raw
            video_size = 10000 * (fps / 60)
        
        # Audio size
        system_audio_size = 50 if self.capture_system_audio.get() else 0
        mic_size = 50 if self.capture_microphone.get() else 0
        
        total_size = video_size + system_audio_size + mic_size
        
        estimate_text = f"📊 Storage Estimate (per hour):\n"
        estimate_text += f"  Video ({codec.upper()} @ {fps}fps): ~{video_size:.0f} MB\n"
        if system_audio_size:
            estimate_text += f"  System Audio: ~{system_audio_size} MB\n"
        if mic_size:
            estimate_text += f"  Microphone: ~{mic_size} MB\n"
        estimate_text += f"  ─────────────────────\n"
        estimate_text += f"  Total: ~{total_size:.0f} MB/hour ({total_size/1024:.2f} GB/hour)"
        
        self.storage_label.config(text=estimate_text)
    
    def _show_stats(self):
        """Show database statistics."""
        try:
            db = DatabaseManager(self.db_path)
            stats = db.get_statistics()
            
            stats_text = f"📊 GameOn Database Statistics\n\n"
            stats_text += f"Total Sessions: {stats['total_sessions']}\n"
            stats_text += f"Completed Sessions: {stats['completed_sessions']}\n"
            stats_text += f"Unique Games: {stats['unique_games']}\n"
            stats_text += f"Total Duration: {stats['total_duration_seconds'] / 3600:.2f} hours\n"
            stats_text += f"Total Frames: {stats['total_frames']:,}\n"
            stats_text += f"Total Input Events: {stats['total_input_events']:,}\n"
            stats_text += f"Total Storage: {stats['total_storage_gb']:.2f} GB\n\n"
            stats_text += f"Database: {self.db_path}"
            
            messagebox.showinfo("Database Statistics", stats_text)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load statistics: {str(e)}")
    
    def log(self, message: str):
        """Add message to log."""
        # Thread-safe: can be called from worker threads.
        self._queue_log(message)
    
    def start_recording(self):
        """Start recording session."""
        # Validate inputs
        game_name = self.game_entry.get().strip()
        if not game_name or game_name == "Enter game name...":
            messagebox.showerror("Error", "Please enter a game name")
            return
        
        with self._recording_lock:
            if self._state != "idle":
                self.log(f"⚠ Cannot start right now (state: {self._state})")
                return
            self._state = "starting"
            # optimistic UI state
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self._set_controls_enabled(False)
            self.progress.start(10)
            self._queue_status("Starting…")
        
        self.log("\n" + "="*60)
        self.log("🎬 Starting recording session...")
        self.log("="*60)
        
        # Create session manager with ALL parameters passed in constructor
        try:
            # Make sure ./data exists when launched from unusual working dirs
            os.makedirs(self.data_dir, exist_ok=True)

            self.session_manager = SessionManager(
                db_path=self.db_path,
                sessions_base_path=self.sessions_path,
                game_name=game_name,
                input_type=self.input_type.get(),
                fps=self.fps_var.get(),
                sample_rate=self.sample_rate_var.get(),
                latency_offset_ms=self.latency_var.get(),
                capture_system_audio=self.capture_system_audio.get(),
                capture_microphone=self.capture_microphone.get(),
                capture_mouse=self.capture_mouse.get(),
                monitor_index=self.monitor_var.get(),
                use_dxcam=self.use_dxcam.get(),
                codec=self.codec_var.get(),
                quality=self.quality_var.get()
            )
            
            # Start in separate thread
            def start_thread():
                try:
                    self._install_stdio_redirect()
                    success = self.session_manager.start_recording()
                    if success:
                        self.is_recording = True
                        with self._recording_lock:
                            self._state = "recording"
                        self._recording_started_at = time.time()
                        self._queue_status("Recording")
                        self._queue_log("✅ Recording started successfully!")
                        self._queue_log("💡 Press STOP RECORDING when done")
                        self.root.after(0, lambda: self.progress.stop())
                    else:
                        self._queue_log("❌ Failed to start recording (see log for details).")
                        self._queue_status("Idle")
                        with self._recording_lock:
                            self._state = "idle"
                        self.root.after(0, self._reset_buttons)
                        self.root.after(0, lambda: self.progress.stop())
                        self._restore_stdio()
                except Exception as e:
                    self._queue_log(f"❌ Error while starting: {str(e)}")
                    self._queue_status("Idle")
                    self._queue_error("Error", f"Failed to start recording:\n\n{str(e)}")
                    with self._recording_lock:
                        self._state = "idle"
                    self.root.after(0, self._reset_buttons)
                    self.root.after(0, lambda: self.progress.stop())
                    self._restore_stdio()
            
            thread = threading.Thread(target=start_thread, daemon=True)
            thread.start()
            
        except Exception as e:
            self.log(f"❌ Error: {str(e)}")
            messagebox.showerror("Error", f"Failed to start recording: {str(e)}")
            with self._recording_lock:
                self._state = "idle"
            self._reset_buttons()
            self.progress.stop()
            self._restore_stdio()
    
    def stop_recording(self):
        """Stop recording session."""
        with self._recording_lock:
            if self._state == "starting":
                self.log("⏳ Still starting up. Please wait a moment, then press STOP again.")
                return
            if self._state != "recording" or not self.session_manager or not self.is_recording:
                return
            self._state = "stopping"
            self._queue_status("Stopping…")
            self.progress.start(10)
        
        self.log("\n" + "="*60)
        self.log("⏹ Stopping recording...")
        self.log("="*60)
        
        # Stop in separate thread
        def stop_thread():
            try:
                self.session_manager.stop_recording()
                self._queue_log("✅ Recording stopped and saved!")
                self._queue_log("💾 Check 'View Statistics' to see your session")
                self._queue_status("Idle")
                with self._recording_lock:
                    self._state = "idle"
                self.is_recording = False
                self._recording_started_at = None
                self.root.after(0, self._reset_buttons)
                self.root.after(0, lambda: self.progress.stop())
                self._restore_stdio()
            except Exception as e:
                self._queue_log(f"❌ Error stopping: {str(e)}")
                self._queue_status("Idle")
                self._queue_error("Error", f"Failed to stop recording:\n\n{str(e)}")
                with self._recording_lock:
                    self._state = "idle"
                self.is_recording = False
                self.root.after(0, self._reset_buttons)
                self.root.after(0, lambda: self.progress.stop())
                self._restore_stdio()
        
        thread = threading.Thread(target=stop_thread, daemon=True)
        thread.start()
    
    def _reset_buttons(self):
        """Reset button states."""
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self._set_controls_enabled(True)
        self.timer_var.set("00:00")
    
    def on_closing(self):
        """Handle window closing."""
        if self.is_recording or self._state in ("starting", "stopping"):
            if messagebox.askokcancel("Quit", "Recording in progress. Stop recording and quit?"):
                self.stop_recording()
                self.root.after(1000, self.root.destroy)
        else:
            self._restore_stdio()
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