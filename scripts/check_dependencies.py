#!/usr/bin/env python3
"""Check that all Themis dependencies are available."""

import shutil
import subprocess
import sys


def check_python_version():
    """Require Python 3.10+."""
    major, minor = sys.version_info[:2]
    if major < 3 or (major == 3 and minor < 10):
        return False, f"Python 3.10+ required, found {major}.{minor}"
    return True, f"Python {major}.{minor}"


def check_ffmpeg():
    """Check FFmpeg is installed and accessible."""
    path = shutil.which("ffmpeg")
    if not path:
        return False, "FFmpeg not found. Install: brew install ffmpeg"
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True, text=True, timeout=10
        )
        version_line = result.stdout.split("\n")[0] if result.stdout else "unknown"
        return True, version_line
    except (subprocess.TimeoutExpired, OSError) as e:
        return False, f"FFmpeg found but error running: {e}"


def check_ffprobe():
    """Check FFprobe is installed (ships with FFmpeg)."""
    path = shutil.which("ffprobe")
    if not path:
        return False, "ffprobe not found. Should be included with FFmpeg."
    return True, f"Found at {path}"


def check_whisper():
    """Check OpenAI Whisper is installed."""
    try:
        import whisper  # noqa: F401
        return True, f"whisper {getattr(whisper, '__version__', 'installed')}"
    except ImportError:
        return False, "openai-whisper not found. Install: pip install openai-whisper"


def main():
    checks = [
        ("Python version", check_python_version),
        ("FFmpeg", check_ffmpeg),
        ("ffprobe", check_ffprobe),
        ("OpenAI Whisper", check_whisper),
    ]

    all_ok = True
    print("Themis Dependency Check")
    print("=" * 50)

    for name, check_fn in checks:
        ok, detail = check_fn()
        status = "OK" if ok else "MISSING"
        print(f"  [{status:>7}] {name}: {detail}")
        if not ok:
            all_ok = False

    print("=" * 50)
    if all_ok:
        print("All dependencies satisfied.")
        return 0
    else:
        print("Some dependencies are missing. See above for install instructions.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
