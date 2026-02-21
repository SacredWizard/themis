# Themis: AI Judge Council

A multi-agent AI system that evaluates short-form video ads and blog content for virality potential, audience distribution, and content quality.

## How It Works

Themis uses a **hierarchical sub-council debate architecture**:

1. **6 specialist judges** organized into Content and Market councils evaluate independently
2. **2 rounds of internal debate** force judges to defend reasoning and identify blind spots
3. **Cross-council exchange** ensures holistic evaluation
4. **Adversarial Critic** reviews for logical flaws and biases
5. **Orchestrator** synthesizes final structured output

This multi-agent debate pattern produces higher-quality evaluations than single-pass analysis.

## Requirements

- Python 3.10+
- FFmpeg (for video keyframe extraction)
- OpenAI Whisper (`pip install openai-whisper`) for transcription
- Claude Code with plugin support

## Quick Start

```bash
# Verify dependencies
python3 scripts/check_dependencies.py

# Preprocess a video
python3 scripts/preprocess_video.py path/to/video.mp4

# Run full evaluation (in Claude Code)
/themis-evaluate path/to/video.mp4

# Run fast evaluation (cheaper, single debate round)
/themis-evaluate path/to/video.mp4 --fast
```

## Utility Scripts

```bash
# Check all dependencies
python3 scripts/check_dependencies.py

# Preprocess video (extract keyframes + transcribe)
python3 scripts/preprocess_video.py video.mp4 -o payload.json --whisper-model base

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
- **Virality score** (0-100) with component breakdowns (hook, emotion, production, trend, shareability)
- **Audience distribution** mapping to specific communities and platforms (TikTok, Reels, Shorts)
- **Strengths, weaknesses, and improvement suggestions** with expected impact ratings
- **Council disagreements** preserved for transparency (>20-point spreads are never averaged away)
- **Token usage and cost metadata**

## Modes

| Mode | Debate Rounds | Cross-Council | Models | Est. Tokens | Est. Cost |
|------|--------------|---------------|--------|-------------|-----------|
| Full | 2 + cross-council | Yes | Haiku/Sonnet/Opus | ~230K-320K | $1.20-2.40 |
| Fast | 1 only | No | Haiku/Sonnet | ~130K-170K | $0.60-0.90 |

## Architecture

```
VIDEO INPUT → Preprocessing (FFmpeg keyframes + Whisper transcription)
            → Content Council (3 Sonnet judges, 2 debate rounds)
            │   ├── Hook Analyst (first 3-sec effectiveness)
            │   ├── Emotion/Storytelling Analyst (emotional arc, persuasion)
            │   └── Production Quality Analyst (visual, pacing, audio, editing)
            → Market Council (3 Sonnet judges, 2 debate rounds)
            │   ├── Trend & Cultural Analyst (trend alignment, timing)
            │   ├── Content Subject Analyst (subject/theme detection)
            │   └── Audience Mapper (community mapping, distribution)
            → Cross-council exchange (1 round)
            → Critic review (Opus — adversarial logic check)
            → Orchestrator synthesis (Opus — final JSON + narrative)
```

## Token Optimization

- **Prompt caching**: Shared payload cached across 6 judges (~40-60% savings on shared content)
- **Selective keyframe distribution**: Hook Analyst gets first 3-4 only; Critic gets none
- **Structured output**: JSON schema enforcement eliminates filler text (~15-20% output savings)
- **3-tier model allocation**: Haiku for preprocessing, Sonnet for judges, Opus for critic/synthesis

## Project Structure

```
themis/
├── .claude-plugin/plugin.json     # Plugin manifest
├── skills/
│   ├── themis-evaluate/           # Main entry point + reference docs
│   ├── themis-hook-analyst/       # Content Council: hook effectiveness
│   ├── themis-emotion-analyst/    # Content Council: emotional arc
│   ├── themis-production-analyst/ # Content Council: production quality
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
│   ├── format_payload.py          # Judge-specific payload formatting
│   ├── merge_scores.py            # Score aggregation + cost estimation
│   └── token_tracker.py           # Token budget + caching analysis
├── hooks/hooks.json
├── CLAUDE.md
└── README.md
```

## License

Apache License 2.0 with Non-Commercial Restriction. See [LICENSE](LICENSE) for details.

Free for personal, educational, and research use. Commercial use requires prior written permission.
