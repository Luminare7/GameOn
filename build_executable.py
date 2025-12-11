#!/usr/bin/env python3
"""
GameOn Executable Builder

Automatically creates standalone executables for Windows, macOS, and Linux.
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

VERSION = "1.0.0"
APP_NAME = "GameOn"
DESCRIPTION = "Gameplay Recorder for AI Training"

# Files to include in the bundle
DATA_FILES = [
    ('config.yaml', '.'),
]

# Hidden imports that PyInstaller might miss
HIDDEN_IMPORTS = [
    'pynput.keyboard._win32',
    'pynput.keyboard._darwin',
    'pynput.keyboard._xorg',
    'pynput.mouse._win32',
    'pynput.mouse._darwin',
    'pynput.mouse._xorg',
    'sounddevice',
    'soundfile',
    'PIL._tkinter_finder',
    'pkg_resources.py2_warn',
]

# Modules to exclude (reduce size)
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
        import PyInstaller
        print(f"✓ PyInstaller {PyInstaller.__version__} found")
        return True
    except ImportError:
        print("✗ PyInstaller not found")
        print("  Install with: pip install pyinstaller")
        return False


def check_ffmpeg():
    """Check if FFmpeg is available for bundling."""
    ffmpeg_dirs = ['ffmpeg_bin', 'tools/ffmpeg', 'vendor/ffmpeg']
    
    for dir_path in ffmpeg_dirs:
        if os.path.exists(dir_path):
            print(f"✓ FFmpeg found in {dir_path}")
            return dir_path
    
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True)
        if result.returncode == 0:
            print("✓ System FFmpeg available (not bundled)")
            return None
    except FileNotFoundError:
        pass
    
    print("⚠ FFmpeg not found - H.264/H.265 will use fallback codec")
    return None


def clean_build():
    """Clean previous build artifacts."""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"  Removing {dir_name}/")
            shutil.rmtree(dir_name)
    
    import glob
    for file_path in glob.glob('*.spec'):
        if 'GameOn.spec' not in file_path:
            print(f"  Removing {file_path}")
            os.remove(file_path)
    
    print("✓ Clean complete")


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
            datas_str += f"        ('{src}', '{dst}'),\n"
    
    if ffmpeg_path:
        if plat == 'windows':
            ffmpeg_exe = os.path.join(ffmpeg_path, 'windows', 'ffmpeg.exe')
            if os.path.exists(ffmpeg_exe):
                datas_str += f"        ('{ffmpeg_exe}', '.'),\n"
        elif plat == 'macos':
            ffmpeg_exe = os.path.join(ffmpeg_path, 'macos', 'ffmpeg')
            if os.path.exists(ffmpeg_exe):
                datas_str += f"        ('{ffmpeg_exe}', '.'),\n"
        else:
            ffmpeg_exe = os.path.join(ffmpeg_path, 'linux', 'ffmpeg')
            if os.path.exists(ffmpeg_exe):
                datas_str += f"        ('{ffmpeg_exe}', '.'),\n"
    
    datas_str += "    ]"
    
    hiddenimports_str = "[\n"
    for imp in HIDDEN_IMPORTS:
        hiddenimports_str += f"        '{imp}',\n"
    
    if plat == 'windows':
        hiddenimports_str += "        'pyaudiowpatch',\n"
        hiddenimports_str += "        'dxcam',\n"
        hiddenimports_str += "        'inputs',\n"
    
    hiddenimports_str += "    ]"
    
    excludes_str = "[\n"
    for exc in EXCLUDES:
        excludes_str += f"        '{exc}',\n"
    excludes_str += "    ]"
    
    icon_str = f"'{icon}'" if icon else 'None'
    
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None
sys.path.insert(0, os.path.abspath('.'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas={datas_str},
    hiddenimports={hiddenimports_str},
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes={excludes_str},
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

'''
    
    if onefile:
        spec_content += f'''exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{APP_NAME}',
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
    icon={icon_str},
)
'''
    else:
        spec_content += f'''exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='{APP_NAME}',
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
    icon={icon_str},
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='{APP_NAME}',
)
'''
    
    if plat == 'macos' and not onefile:
        spec_content += f'''
app = BUNDLE(
    coll,
    name='{APP_NAME}.app',
    icon={icon_str},
    bundle_identifier='com.gameon.recorder',
    info_plist={{
        'CFBundleName': '{APP_NAME}',
        'CFBundleDisplayName': '{APP_NAME}',
        'CFBundleVersion': '{VERSION}',
        'CFBundleShortVersionString': '{VERSION}',
        'NSHighResolutionCapable': True,
        'NSMicrophoneUsageDescription': 'GameOn needs microphone access to record voice chat.',
        'NSScreenCaptureDescription': 'GameOn needs screen recording access to capture gameplay.',
    }},
)
'''
    
    return spec_content


def build_executable(onefile=False, clean=False):
    """Build the executable."""
    
    print("\n" + "="*60)
    print(f"🎮 Building {APP_NAME} v{VERSION}")
    print("="*60 + "\n")
    
    if not check_pyinstaller():
        return False
    
    if clean:
        print("\n📁 Cleaning previous builds...")
        clean_build()
    
    print("\n🔍 Checking FFmpeg...")
    ffmpeg_path = check_ffmpeg()
    
    print("\n📝 Creating spec file...")
    spec_content = create_spec_file(onefile=onefile, ffmpeg_path=ffmpeg_path)
    
    spec_path = 'GameOn.spec'
    with open(spec_path, 'w') as f:
        f.write(spec_content)
    print(f"✓ Created {spec_path}")
    
    print("\n🔨 Building executable...")
    print("   This may take a few minutes...\n")
    
    cmd = ['pyinstaller', '--clean', '--noconfirm', spec_path]
    
    try:
        subprocess.run(cmd, check=True)
        print("\n✓ Build completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Build failed with error code {e.returncode}")
        return False
    
    print("\n📦 Post-build tasks...")
    
    plat = get_platform()
    if onefile:
        exe_path = f'dist/{APP_NAME}.exe' if plat == 'windows' else f'dist/{APP_NAME}'
    else:
        exe_path = f'dist/{APP_NAME}.app' if plat == 'macos' else f'dist/{APP_NAME}'
    
    if os.path.exists(exe_path):
        if os.path.isfile(exe_path):
            size = os.path.getsize(exe_path) / (1024 * 1024)
        else:
            size = sum(
                os.path.getsize(os.path.join(dirpath, filename))
                for dirpath, dirnames, filenames in os.walk(exe_path)
                for filename in filenames
            ) / (1024 * 1024)
        
        print(f"\n" + "="*60)
        print("✅ BUILD SUCCESSFUL!")
        print("="*60)
        print(f"\n📁 Output: {exe_path}")
        print(f"📊 Size: {size:.1f} MB\n")
        
        return True
    else:
        print(f"\n✗ Expected output not found: {exe_path}")
        return False


def create_assets_directory():
    """Create assets directory with placeholder files."""
    if not os.path.exists('assets'):
        os.makedirs('assets')
        print(f"✓ Created assets/ directory")


def main():
    parser = argparse.ArgumentParser(description='Build GameOn standalone executable')
    parser.add_argument('--onefile', action='store_true', help='Create single-file executable')
    parser.add_argument('--clean', action='store_true', help='Clean previous builds first')
    parser.add_argument('--spec-only', action='store_true', help='Only generate spec file')
    
    args = parser.parse_args()
    
    if not os.path.exists('main.py'):
        print("✗ Error: main.py not found")
        print("  Run this script from the GameOn project root directory")
        sys.exit(1)
    
    create_assets_directory()
    
    if args.spec_only:
        ffmpeg_path = check_ffmpeg()
        spec_content = create_spec_file(onefile=args.onefile, ffmpeg_path=ffmpeg_path)
        with open('GameOn.spec', 'w') as f:
            f.write(spec_content)
        print("✓ Created GameOn.spec")
    else:
        success = build_executable(onefile=args.onefile, clean=args.clean)
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
