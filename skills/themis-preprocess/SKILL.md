---
name: themis-preprocess
description: Preprocessing skill for video content — extracts keyframes and transcription using FFmpeg and Whisper
---

# Themis Preprocess

Handles video preprocessing before judge evaluation. Called by the orchestrator as the first pipeline step.

## Video Preprocessing

### Step 1: Validate the video file exists and is a supported format
Supported: `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`

### Step 2: Run preprocessing script
```bash
python3 scripts/preprocess_video.py "<file_path>" -o /tmp/themis_payload.json --whisper-model <model>
```

Arguments:
- `--whisper-model`: tiny (fastest), base (default), small, medium, large (best quality)
- `--scene-threshold`: Scene change sensitivity 0.0-1.0 (default: 0.3, lower = more frames)
- `--max-frames`: Maximum keyframes to extract (default: 20)

### Step 3: Verify payload
After preprocessing, verify the payload contains:
- `source_file` — original filename
- `content_type` — "video"
- `metadata` — duration, resolution, fps, codec, has_audio
- `keyframes` — array of keyframe objects with base64 data
- `keyframe_count` — number of keyframes extracted
- `transcript` — text, segments with timestamps, language

### Step 4: Format judge payloads
```bash
python3 scripts/format_payload.py /tmp/themis_payload.json --estimate-tokens
```

This reports estimated token counts per judge. If total exceeds budget, consider:
- Reducing max-frames
- Using `--no-images` for text-heavy judges (critic, orchestrator)

## Output
The payload JSON at `/tmp/themis_payload.json` is ready for judge consumption.
