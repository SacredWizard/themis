#!/usr/bin/env python3
"""
Preprocess video for Themis evaluation.

Extracts scene-change keyframes using FFmpeg and transcribes audio using Whisper.
Outputs a structured JSON payload for judge consumption.
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def get_video_metadata(video_path: str) -> dict:
    """Extract video metadata using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")

    probe = json.loads(result.stdout)
    video_stream = next(
        (s for s in probe.get("streams", []) if s["codec_type"] == "video"),
        {}
    )
    audio_stream = next(
        (s for s in probe.get("streams", []) if s["codec_type"] == "audio"),
        None
    )
    fmt = probe.get("format", {})

    return {
        "duration_sec": float(fmt.get("duration", 0)),
        "width": int(video_stream.get("width", 0)),
        "height": int(video_stream.get("height", 0)),
        "fps": _parse_fps(video_stream.get("r_frame_rate", "30/1")),
        "codec": video_stream.get("codec_name", "unknown"),
        "has_audio": audio_stream is not None,
        "file_size_bytes": int(fmt.get("size", 0)),
    }


def _parse_fps(fps_str: str) -> float:
    """Parse FFmpeg fps fraction string like '30/1'."""
    try:
        if "/" in fps_str:
            num, den = fps_str.split("/")
            return round(float(num) / float(den), 2)
        return float(fps_str)
    except (ValueError, ZeroDivisionError):
        return 30.0


def extract_keyframes(video_path: str, output_dir: str, threshold: float = 0.3,
                      max_frames: int = 20, min_frames: int = 5) -> list[dict]:
    """
    Extract scene-change keyframes using FFmpeg.

    Uses the 'select' filter with scene change detection. Falls back to
    uniform sampling if scene detection yields too few frames.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Scene-change detection
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vf", f"select='gt(scene,{threshold})',showinfo",
        "-vsync", "vfr",
        "-frame_pts", "1",
        f"{output_dir}/frame_%04d.jpg",
        "-y", "-loglevel", "info"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    frames = sorted(Path(output_dir).glob("frame_*.jpg"))

    # Fallback to uniform sampling if too few frames
    if len(frames) < min_frames:
        # Clean up sparse results
        for f in frames:
            f.unlink()

        metadata = get_video_metadata(video_path)
        duration = metadata["duration_sec"]
        interval = max(duration / (min_frames + 1), 0.5)

        cmd = [
            "ffmpeg", "-i", video_path,
            "-vf", f"fps=1/{interval}",
            f"{output_dir}/frame_%04d.jpg",
            "-y", "-loglevel", "warning"
        ]
        subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        frames = sorted(Path(output_dir).glob("frame_*.jpg"))

    # Cap at max_frames (keep first, last, and evenly distributed middle)
    if len(frames) > max_frames:
        indices = [0] + [
            int(i * (len(frames) - 1) / (max_frames - 1))
            for i in range(1, max_frames - 1)
        ] + [len(frames) - 1]
        indices = sorted(set(indices))
        keep = [frames[i] for i in indices]
        for f in frames:
            if f not in keep:
                f.unlink()
        frames = keep

    # Build frame metadata
    frame_data = []
    for i, frame_path in enumerate(frames):
        with open(frame_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        frame_data.append({
            "index": i,
            "filename": frame_path.name,
            "base64": b64,
            "media_type": "image/jpeg",
        })

    return frame_data


def transcribe_audio(video_path: str, model_name: str = "base") -> dict:
    """Transcribe video audio using OpenAI Whisper."""
    try:
        import whisper
    except ImportError:
        return {
            "text": "",
            "segments": [],
            "language": "unknown",
            "error": "Whisper not installed. Install: pip install openai-whisper"
        }

    model = whisper.load_model(model_name)
    result = model.transcribe(video_path, verbose=False)

    segments = []
    for seg in result.get("segments", []):
        segments.append({
            "start": round(seg["start"], 2),
            "end": round(seg["end"], 2),
            "text": seg["text"].strip(),
        })

    return {
        "text": result.get("text", "").strip(),
        "segments": segments,
        "language": result.get("language", "unknown"),
    }


def preprocess(video_path: str, output_path: str | None = None,
               whisper_model: str = "base", scene_threshold: float = 0.3,
               max_frames: int = 20) -> dict:
    """Run full preprocessing pipeline and return payload."""
    video_path = os.path.abspath(video_path)
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")

    print(f"Preprocessing: {video_path}")

    # 1. Extract metadata
    print("  Extracting metadata...")
    metadata = get_video_metadata(video_path)
    print(f"  Duration: {metadata['duration_sec']:.1f}s, "
          f"Resolution: {metadata['width']}x{metadata['height']}")

    # 2. Extract keyframes
    with tempfile.TemporaryDirectory(prefix="themis_frames_") as tmpdir:
        print(f"  Extracting keyframes (threshold={scene_threshold})...")
        frames = extract_keyframes(
            video_path, tmpdir,
            threshold=scene_threshold,
            max_frames=max_frames
        )
        print(f"  Extracted {len(frames)} keyframes")

        # 3. Transcribe audio
        print(f"  Transcribing audio (model={whisper_model})...")
        if metadata["has_audio"]:
            transcript = transcribe_audio(video_path, model_name=whisper_model)
            print(f"  Transcript: {len(transcript['text'])} chars, "
                  f"{len(transcript['segments'])} segments")
        else:
            transcript = {"text": "", "segments": [], "language": "none"}
            print("  No audio track found")

        # 4. Build payload
        payload = {
            "source_file": os.path.basename(video_path),
            "content_type": "video",
            "metadata": metadata,
            "keyframes": frames,
            "keyframe_count": len(frames),
            "transcript": transcript,
        }

    # 5. Save payload
    if output_path is None:
        output_path = os.path.splitext(video_path)[0] + "_payload.json"

    with open(output_path, "w") as f:
        json.dump(payload, f, indent=2)
    payload_size = os.path.getsize(output_path)
    print(f"  Payload saved: {output_path} ({payload_size:,} bytes)")

    return payload


def main():
    parser = argparse.ArgumentParser(
        description="Preprocess video for Themis evaluation"
    )
    parser.add_argument("video", help="Path to video file")
    parser.add_argument("-o", "--output", help="Output payload JSON path")
    parser.add_argument("--whisper-model", default="base",
                        choices=["tiny", "base", "small", "medium", "large"],
                        help="Whisper model size (default: base)")
    parser.add_argument("--scene-threshold", type=float, default=0.3,
                        help="Scene change detection threshold (default: 0.3)")
    parser.add_argument("--max-frames", type=int, default=20,
                        help="Maximum keyframes to extract (default: 20)")
    args = parser.parse_args()

    try:
        preprocess(
            args.video,
            output_path=args.output,
            whisper_model=args.whisper_model,
            scene_threshold=args.scene_threshold,
            max_frames=args.max_frames,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
