---
name: themis-preprocess
description: Preprocessing skill for video and text content — extracts keyframes, transcription, and text structure for judge evaluation
---

# Themis Preprocess

Handles content preprocessing before judge evaluation. Called by the orchestrator as the first pipeline step. Supports both video and text content.

## Content Type Detection

Determine the content type from the file extension:
- **Video**: `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`
- **Text**: `.txt`, `.md`, `.html`

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

## Text Preprocessing

### Step 1: Validate the text file exists and is a supported format
Supported: `.txt`, `.md`, `.html`

### Step 2: Run preprocessing script
```bash
python3 scripts/preprocess_text.py "<file_path>" -o /tmp/themis_payload.json
```

The script handles:
- **HTML files**: Strips tags, converts to markdown-style text, preserves structure
- **Markdown files**: Read as-is with section extraction
- **Plain text files**: Read as-is with section extraction

### Step 3: Verify payload
After preprocessing, verify the payload contains:
- `source_file` — original filename
- `content_type` — "text"
- `metadata` — word_count, sentence_count, paragraph_count, reading_time_min, title, file_format
- `keyframes` — empty array (text has no images)
- `keyframe_count` — 0
- `transcript.text` — the full text content (reuses transcript field for compatibility)
- `sections` — array of extracted sections with headings and word counts

### Step 4: Format judge payloads
```bash
python3 scripts/format_payload.py /tmp/themis_payload.json --estimate-tokens
```

Text payloads are significantly cheaper than video (no image tokens).

## Payload Compatibility

Both video and text payloads share the same base structure:
- `source_file`, `content_type`, `metadata`, `keyframes`, `keyframe_count`, `transcript`

Text payloads add:
- `sections` — structured section breakdown

This allows format_payload.py and downstream judges to handle both content types through the same pipeline. Judges adapt their evaluation criteria based on the `content_type` field.

## Output
The payload JSON at `/tmp/themis_payload.json` is ready for judge consumption.
