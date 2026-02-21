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
```

## Output

Themis produces structured JSON with:
- **Virality score** (0-100) with component breakdowns
- **Audience distribution** mapping to specific communities and platforms
- **Strengths, weaknesses, and improvement suggestions**
- **Council disagreements** preserved for transparency
- **Token usage and cost metadata**

## Modes

| Mode | Debate Rounds | Models | Est. Cost |
|------|--------------|--------|-----------|
| Full | 2 rounds + cross-council | Haiku/Sonnet/Opus | $1.20-2.00 |
| Fast | 1 round, no cross-council | Haiku/Sonnet | $0.60-1.00 |

## Architecture

```
VIDEO INPUT → Preprocessing (Haiku)
            → Content Council (3 Sonnet judges, 2 debate rounds)
            → Market Council (3 Sonnet judges, 2 debate rounds)
            → Cross-council exchange (1 round)
            → Critic review (Opus)
            → Orchestrator synthesis (Opus)
            → Structured JSON + Narrative output
```

## License

Proprietary
