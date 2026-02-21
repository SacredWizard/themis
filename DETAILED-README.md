# Themis: AI Judge Council

A multi-agent AI system that evaluates short-form video ads and blog content for virality potential, audience distribution, and content quality.

## How It Works

Themis uses a **hierarchical sub-council debate architecture**:

1. **7 specialist judges** organized into Content and Market councils evaluate independently
2. **Statistical text forensics** detect AI-generated content
3. **2 rounds of internal debate** force judges to defend reasoning and identify blind spots
3. **Cross-council exchange** ensures holistic evaluation
4. **Adversarial Critic** reviews for logical flaws and biases
5. **Orchestrator** synthesizes final structured output

This multi-agent debate pattern produces higher-quality evaluations than single-pass analysis.

## Requirements

- **Python 3.10+**
- **FFmpeg** — for video keyframe extraction
- **OpenAI Whisper** — for audio transcription
- **Claude Code** v2.0+ — the CLI tool (`npm install -g @anthropic-ai/claude-code`)

### Install Dependencies

```bash
# macOS
brew install ffmpeg
pip install openai-whisper

# Ubuntu/Debian
sudo apt install ffmpeg
pip install openai-whisper

# Verify everything is installed
python3 scripts/check_dependencies.py
```

## Installation

There are three ways to install Themis as a Claude Code plugin:

### Option A: Plugin Directory (Recommended for Development)

Load Themis directly when launching Claude Code — no installation needed:

```bash
claude --plugin-dir /path/to/themis
```

This loads all skills, agents, and hooks from the Themis directory for that session. Best for development and testing since changes are picked up immediately.

### Option B: Install Script (Recommended for Regular Use)

The install script symlinks Themis skills and agents into your Claude Code configuration:

```bash
# Clone the repo
git clone git@github.com:SacredWizard/themis.git
cd themis

# Install into a specific project
cd /path/to/your/project
/path/to/themis/install.sh project

# OR install globally (available in all projects)
./install.sh user
```

**What the install script does:**
- Symlinks all 11 skill directories into `<target>/.claude/skills/`
- Symlinks all 3 agent files into `<target>/.claude/agents/`
- Runs the dependency checker

**Uninstall:**
```bash
cd /path/to/your/project
/path/to/themis/uninstall.sh project

# OR uninstall globally
/path/to/themis/uninstall.sh user
```

### Option C: Manual Installation

Copy or symlink the components yourself:

```bash
# For project-level installation
PROJECT_DIR=/path/to/your/project
THEMIS_DIR=/path/to/themis

# Symlink skills
mkdir -p "$PROJECT_DIR/.claude/skills"
for skill in "$THEMIS_DIR"/skills/themis-*/; do
    ln -s "$skill" "$PROJECT_DIR/.claude/skills/$(basename "$skill")"
done

# Symlink agents
mkdir -p "$PROJECT_DIR/.claude/agents"
for agent in "$THEMIS_DIR"/agents/themis-*.md; do
    ln -s "$agent" "$PROJECT_DIR/.claude/agents/$(basename "$agent")"
done
```

### Verify Installation

After installing, launch Claude Code and check that the skills are discovered:

```bash
claude
# Then type / and look for themis-evaluate in the skill list
```

You should see `/themis-evaluate` available. If not, check that the symlinks are correct:

```bash
ls -la .claude/skills/ | grep themis
ls -la .claude/agents/ | grep themis
```

## Quick Start

```bash
# Run full evaluation on a video (in Claude Code)
/themis-evaluate path/to/video.mp4

# Run fast evaluation (cheaper, single debate round)
/themis-evaluate path/to/video.mp4 --fast

# Evaluate a blog post or article
/themis-evaluate path/to/article.txt

# Use a specific Whisper model for better transcription
/themis-evaluate path/to/video.mp4 --whisper-model small
```

## Testing

### 1. Test Dependencies

```bash
python3 scripts/check_dependencies.py
```

Expected output: all 4 checks should show `[OK]`.

### 2. Test Video Preprocessing

```bash
# Preprocess a video (extract keyframes + transcribe audio)
python3 scripts/preprocess_video.py path/to/video.mp4 -o /tmp/test_payload.json --whisper-model tiny

# Verify the payload
python3 -c "
import json
with open('/tmp/test_payload.json') as f:
    p = json.load(f)
print(f'Keyframes: {p[\"keyframe_count\"]}')
print(f'Duration: {p[\"metadata\"][\"duration_sec\"]:.1f}s')
print(f'Transcript: {len(p[\"transcript\"][\"text\"])} chars')
print(f'Language: {p[\"transcript\"][\"language\"]}')
"
```

### 3. Test Token Estimation

```bash
# Estimate per-judge token costs
python3 scripts/format_payload.py /tmp/test_payload.json --estimate-tokens

# See caching analysis
python3 scripts/format_payload.py /tmp/test_payload.json --cache-analysis

# Compare full vs fast mode costs
python3 scripts/token_tracker.py --compare
```

### 4. Test Text Preprocessing & Forensics

```bash
# Preprocess a text file
python3 scripts/preprocess_text.py path/to/article.txt -o /tmp/test_text_payload.json

# Run AI detection forensics
python3 scripts/text_forensics.py /tmp/test_text_payload.json -o /tmp/test_forensics.json

# Or analyze a text file directly
python3 scripts/text_forensics.py --text-file path/to/article.txt
```

### 5. Test Score Merging

```bash
# Simulate a full merge with sample council outputs
python3 scripts/merge_scores.py \
  --content-council '{"consensus_scores":{"hook_effectiveness":{"score":75,"confidence":0.8},"emotional_resonance":{"score":68,"confidence":0.75},"production_quality":{"score":72,"confidence":0.85}}}' \
  --market-council '{"consensus_scores":{"trend_alignment":{"score":60,"confidence":0.7},"shareability":{"score":65,"confidence":0.72}}}' \
  --critic '{"challenges":[],"cross_council_tensions":[],"overall_confidence_adjustment":-0.05}' \
  --mode full --total-tokens 230000
```

Expected: virality score of 68/100, tier "strong", confidence 0.65.

### 6. Test Full Pipeline (in Claude Code)

```bash
# Launch Claude Code with Themis loaded
claude --plugin-dir /path/to/themis

# Then run:
/themis-evaluate path/to/video.mp4
```

This triggers the full pipeline:
1. Dependency check
2. Preprocessing (keyframes + transcription for video, section extraction for text)
3. Text forensics (AI detection metrics)
4. Token budget estimation
5. 7 judges evaluate in parallel (Round 1)
6. Judges revise after seeing peers (Round 2)
7. Cross-council exchange
8. Critic adversarial review
9. Final synthesis → JSON + narrative output

### 7. Test a Synthetic Video (No Real Content Needed)

```bash
# Generate a 5-second test video with FFmpeg
ffmpeg -y -f lavfi -i "testsrc2=duration=5:size=720x1280:rate=30" \
  -f lavfi -i "sine=frequency=440:duration=5" \
  -c:v libx264 -c:a aac -shortest test_video.mp4

# Preprocess it
python3 scripts/preprocess_video.py test_video.mp4 -o /tmp/test_payload.json --whisper-model tiny

# Verify
python3 scripts/format_payload.py /tmp/test_payload.json --estimate-tokens
```

## Utility Scripts

```bash
# Check all dependencies
python3 scripts/check_dependencies.py

# Preprocess video (extract keyframes + transcribe)
python3 scripts/preprocess_video.py video.mp4 -o payload.json --whisper-model base

# Preprocess text (extract sections + metadata)
python3 scripts/preprocess_text.py article.txt -o payload.json

# Run AI detection forensics on a payload or text file
python3 scripts/text_forensics.py payload.json -o forensics.json
python3 scripts/text_forensics.py --text-file article.txt

# Format payload for a specific judge
python3 scripts/format_payload.py payload.json -j hook_analyst

# Estimate token costs per judge
python3 scripts/format_payload.py payload.json --estimate-tokens

# Analyze prompt caching potential
python3 scripts/format_payload.py payload.json --cache-analysis

# Compare full vs fast mode costs
python3 scripts/token_tracker.py --compare

# Merge council scores into final output
python3 scripts/merge_scores.py --content-council cc.json --market-council mc.json --critic critic.json
```

## Output

Themis produces structured JSON with:
- **Virality score** (0-100) with component breakdowns (hook, emotion, production, trend, shareability) and a TLDR rationale
- **Authenticity verdict** (`likely_human`, `likely_ai`, `mixed`, `uncertain`) with statistical metrics and AI probability
- **Audience distribution** mapping to specific communities and platforms (TikTok, Reels, Shorts for video; Blog, Twitter/X, LinkedIn, Newsletter, Reddit/HN for text)
- **Strengths, weaknesses, and improvement suggestions** with expected impact ratings
- **Council disagreements** preserved for transparency (>20-point spreads are never averaged away)
- **Token usage and cost metadata**

## Modes

| Mode | Debate Rounds | Cross-Council | Models | Est. Tokens | Est. Cost |
|------|--------------|---------------|--------|-------------|-----------|
| Full | 2 + cross-council | Yes | Haiku/Sonnet/Opus | ~255K-350K | $1.40-2.60 |
| Fast | 1 only | No | Haiku/Sonnet | ~145K-185K | $0.70-1.00 |

## Architecture

```
INPUT (video or text)
  → Preprocessing (FFmpeg + Whisper for video, section extraction for text)
  → Text Forensics (statistical AI detection — pure Python)
  → Content Council (4 Sonnet judges, 2 debate rounds)
  │   ├── Hook Analyst (first 3-sec / headline effectiveness)
  │   ├── Emotion/Storytelling Analyst (emotional arc, persuasion)
  │   ├── Production Quality Analyst (visual, pacing, audio, editing)
  │   └── Authenticity Analyst (AI detection — forensics + qualitative)
  → Market Council (3 Sonnet judges, 2 debate rounds)
  │   ├── Trend & Cultural Analyst (trend alignment, timing)
  │   ├── Content Subject Analyst (subject/theme detection)
  │   └── Audience Mapper (community mapping, distribution)
  → Cross-council exchange (1 round)
  → Critic review (Opus — adversarial logic check)
  → Orchestrator synthesis (Opus — final JSON + narrative)
```

## Token Optimization

- **Prompt caching**: Shared payload cached across 7 judges (~40-60% savings on shared content)
- **Selective keyframe distribution**: Hook Analyst gets first 3-4 only; Critic gets none
- **Structured output**: JSON schema enforcement eliminates filler text (~15-20% output savings)
- **3-tier model allocation**: Haiku for preprocessing, Sonnet for judges, Opus for critic/synthesis

## Project Structure

```
themis/
├── .claude-plugin/plugin.json     # Plugin manifest (11 skills, 3 agents)
├── skills/
│   ├── themis-evaluate/           # Main entry point + reference docs
│   ├── themis-hook-analyst/       # Content Council: hook effectiveness
│   ├── themis-emotion-analyst/    # Content Council: emotional arc
│   ├── themis-production-analyst/ # Content Council: production quality
│   ├── themis-authenticity-analyst/ # Content Council: AI detection
│   ├── themis-trend-analyst/      # Market Council: trend alignment
│   ├── themis-subject-analyst/    # Market Council: subject detection
│   ├── themis-audience-mapper/    # Market Council: audience mapping
│   ├── themis-critic/             # Cross-cutting: adversarial review
│   ├── themis-synthesizer/        # Final synthesis
│   └── themis-preprocess/         # Video preprocessing
├── agents/
│   ├── themis-orchestrator.md     # Pipeline orchestration (Opus)
│   ├── themis-content-council-lead.md
│   └── themis-market-council-lead.md
├── scripts/
│   ├── check_dependencies.py      # Dependency validation
│   ├── preprocess_video.py        # FFmpeg + Whisper pipeline
│   ├── preprocess_text.py         # Text section extraction
│   ├── text_forensics.py          # Statistical AI detection
│   ├── format_payload.py          # Judge-specific payload formatting
│   ├── merge_scores.py            # Score aggregation + cost estimation
│   └── token_tracker.py           # Token budget + caching analysis
├── install.sh                     # Plugin installer
├── uninstall.sh                   # Plugin uninstaller
├── hooks/hooks.json
├── CLAUDE.md
└── README.md
```

## License

Apache License 2.0 with Non-Commercial Restriction. See [LICENSE](LICENSE) for details.

Free for personal, educational, and research use. Commercial use requires prior written permission.
