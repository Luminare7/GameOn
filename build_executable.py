#!/usr/bin/env python3
"""
GameOn Executable Builder

Automatically creates standalone executables for Windows and macOS.
Users can download and run without installing Python or dependencies.

Usage:
    python build_executable.py              # Build for current platform
    python build_executable.py --onefile    # Create single-file executable
    python build_executable.py --clean      # Clean previous builds first
"""

import os
import sys
import shutil
import platform
import subprocess
import argparse
from pathlib import Path

# ============================================================================
# Configuration
# ============================================================================

VERSION = "1.0.2"
APP_NAME = "GameOn"
DESCRIPTION = "Gameplay Recorder for AI Training"

# Files to include in the bundle
DATA_FILES = [
    ('config.yaml', '.'),
]

# Hidden imports that PyInstaller might miss
# Platform-specific imports are added dynamically in create_spec_file()
HIDDEN_IMPORTS = [
    'sounddevice',
    'soundfile',
]

# Modules to exclude (reduce size and avoid missing module errors)
EXCLUDES = [
    'matplotlib',
    'scipy',
    'pandas',
    'jupyter',
    'IPython',
    'notebook',
    'pytest',
    'sphinx',
    'docutils',
    'PIL._tkinter_finder',
    'pkg_resources.py2_warn',
]

# ============================================================================
# Build Functions
# ============================================================================

def get_platform():
    """Get current platform name."""
    system = platform.system().lower()
    if system == 'darwin':
        return 'macos'
    return system


def check_pyinstaller():
    """Check if PyInstaller is installed."""
    try:
        import importlib
        pyinstaller = importlib.import_module("PyInstaller")
        version = getattr(pyinstaller, "__version__", "unknown")
        print("[OK] PyInstaller {} found".format(version))
        return True
    except ImportError:
        print("[ERROR] PyInstaller not found")
        print("  Install with: pip install pyinstaller")
        return False


def check_ffmpeg():
    """Check if FFmpeg is available for bundling."""
    ffmpeg_dirs = ['ffmpeg_bin', 'tools/ffmpeg', 'vendor/ffmpeg']
    
    for dir_path in ffmpeg_dirs:
        if os.path.exists(dir_path):
            print("[OK] FFmpeg found in {}".format(dir_path))
            return dir_path
    
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True)
        if result.returncode == 0:
            print("[OK] System FFmpeg available (not bundled)")
            return None
    except FileNotFoundError:
        pass
    
    print("[WARN] FFmpeg not found - H.264/H.265 will use fallback codec")
    return None


def clean_build():
    """Clean previous build artifacts."""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print("  Removing {}/".format(dir_name))
            shutil.rmtree(dir_name)
    
    import glob
    for file_path in glob.glob('*.spec'):
        if 'GameOn.spec' not in file_path:
            print("  Removing {}".format(file_path))
            os.remove(file_path)
    
    print("[OK] Clean complete")


def create_spec_file(onefile=False, ffmpeg_path=None):
    """Create PyInstaller spec file with all configurations."""
    
    plat = get_platform()
    
    if plat == 'windows':
        icon = 'assets/icon.ico' if os.path.exists('assets/icon.ico') else None
        console = False
    elif plat == 'macos':
        icon = 'assets/icon.icns' if os.path.exists('assets/icon.icns') else None
        console = False
    else:
        icon = 'assets/icon.png' if os.path.exists('assets/icon.png') else None
        console = False
    
    datas_str = "[\n"
    for src, dst in DATA_FILES:
        if os.path.exists(src):
            datas_str += "        ('{}', '{}'),\n".format(src, dst)
    
    if ffmpeg_path:
        if plat == 'windows':
            ffmpeg_exe = os.path.join(ffmpeg_path, 'windows', 'ffmpeg.exe')
            if os.path.exists(ffmpeg_exe):
                datas_str += "        ('{}', '.'),\n".format(ffmpeg_exe)
        elif plat == 'macos':
            ffmpeg_exe = os.path.join(ffmpeg_path, 'macos', 'ffmpeg')
            if os.path.exists(ffmpeg_exe):
                datas_str += "        ('{}', '.'),\n".format(ffmpeg_exe)
    
    datas_str += "    ]"
    
    # Build hidden imports list - PLATFORM SPECIFIC ONLY
    hiddenimports_str = "[\n"
    for imp in HIDDEN_IMPORTS:
        hiddenimports_str += "        '{}',\n".format(imp)
    
    # Add platform-specific pynput backends (ONLY for current platform)
    if plat == 'windows':
        hiddenimports_str += "        'pynput.keyboard._win32',\n"
        hiddenimports_str += "        'pynput.mouse._win32',\n"
        hiddenimports_str += "        'pyaudiowpatch',\n"
        hiddenimports_str += "        'dxcam',\n"
        hiddenimports_str += "        'inputs',\n"
    elif plat == 'macos':
        hiddenimports_str += "        'pynput.keyboard._darwin',\n"
        hiddenimports_str += "        'pynput.mouse._darwin',\n"
    
    hiddenimports_str += "    ]"
    
    # Build excludes list
    excludes_str = "[\n"
    for exc in EXCLUDES:
        excludes_str += "        '{}',\n".format(exc)
    excludes_str += "    ]"
    
    icon_str = "'{}'".format(icon) if icon else 'None'
    
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None
sys.path.insert(0, os.path.abspath('.'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas={datas},
    hiddenimports={hiddenimports},
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes={excludes},
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

'''.format(datas=datas_str, hiddenimports=hiddenimports_str, excludes=excludes_str)
    
    if onefile:
        spec_content += '''exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console={console},
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon={icon},
)
'''.format(name=APP_NAME, console=console, icon=icon_str)
    else:
        spec_content += '''exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='{name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console={console},
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon={icon},
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='{name}',
)
'''.format(name=APP_NAME, console=console, icon=icon_str)
    
    if plat == 'macos' and not onefile:
        spec_content += '''
app = BUNDLE(
    coll,
    name='{name}.app',
    icon={icon},
    bundle_identifier='com.gameon.recorder',
    info_plist={{
        'CFBundleName': '{name}',
        'CFBundleDisplayName': '{name}',
        'CFBundleVersion': '{version}',
        'CFBundleShortVersionString': '{version}',
        'NSHighResolutionCapable': True,
        'NSMicrophoneUsageDescription': 'GameOn needs microphone access to record voice chat.',
        'NSScreenCaptureDescription': 'GameOn needs screen recording access to capture gameplay.',
    }},
)
'''.format(name=APP_NAME, version=VERSION, icon=icon_str)
    
    return spec_content


def build_executable(onefile=False, clean=False):
    """Build the executable."""
    
    print("")
    print("=" * 60)
    print("Building {} v{}".format(APP_NAME, VERSION))
    print("=" * 60)
    print("")
    
    if not check_pyinstaller():
        return False
    
    if clean:
        print("")
        print("[INFO] Cleaning previous builds...")
        clean_build()
    
    print("")
    print("[INFO] Checking FFmpeg...")
    ffmpeg_path = check_ffmpeg()
    
    print("")
    print("[INFO] Creating spec file...")
    spec_content = create_spec_file(onefile=onefile, ffmpeg_path=ffmpeg_path)
    
    spec_path = 'GameOn.spec'
    with open(spec_path, 'w') as f:
        f.write(spec_content)
    print("[OK] Created {}".format(spec_path))
    
    print("")
    print("[INFO] Building executable...")
    print("   This may take a few minutes...")
    print("")
    
    cmd = ['pyinstaller', '--clean', '--noconfirm', spec_path]
    
    try:
        subprocess.run(cmd, check=True)
        print("")
        print("[OK] Build completed successfully!")
    except subprocess.CalledProcessError as e:
        print("")
        print("[ERROR] Build failed with error code {}".format(e.returncode))
        return False
    
    print("")
    print("[INFO] Post-build tasks...")
    
    plat = get_platform()
    if onefile:
        exe_path = 'dist/{}.exe'.format(APP_NAME) if plat == 'windows' else 'dist/{}'.format(APP_NAME)
    else:
        exe_path = 'dist/{}.app'.format(APP_NAME) if plat == 'macos' else 'dist/{}'.format(APP_NAME)
    
    if os.path.exists(exe_path):
        if os.path.isfile(exe_path):
            size = os.path.getsize(exe_path) / (1024 * 1024)
        else:
            size = sum(
                os.path.getsize(os.path.join(dirpath, filename))
                for dirpath, dirnames, filenames in os.walk(exe_path)
                for filename in filenames
            ) / (1024 * 1024)
        
        print("")
        print("=" * 60)
        print("BUILD SUCCESSFUL!")
        print("=" * 60)
        print("")
        print("Output: {}".format(exe_path))
        print("Size: {:.1f} MB".format(size))
        print("")
        
        return True
    else:
        print("")
        print("[ERROR] Expected output not found: {}".format(exe_path))
        return False


def create_assets_directory():
    """Create assets directory with placeholder files."""
    if not os.path.exists('assets'):
        os.makedirs('assets')
        print("[OK] Created assets/ directory")


def main():
    parser = argparse.ArgumentParser(description='Build GameOn standalone executable')
    parser.add_argument('--onefile', action='store_true', help='Create single-file executable')
    parser.add_argument('--clean', action='store_true', help='Clean previous builds first')
    parser.add_argument('--spec-only', action='store_true', help='Only generate spec file')
    
    args = parser.parse_args()
    
    if not os.path.exists('main.py'):
        print("[ERROR] main.py not found")
        print("  Run this script from the GameOn project root directory")
        sys.exit(1)
    
    create_assets_directory()
    
    if args.spec_only:
        ffmpeg_path = check_ffmpeg()
        spec_content = create_spec_file(onefile=args.onefile, ffmpeg_path=ffmpeg_path)
        with open('GameOn.spec', 'w') as f:
            f.write(spec_content)
        print("[OK] Created GameOn.spec")
    else:
        success = build_executable(onefile=args.onefile, clean=args.clean)
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()