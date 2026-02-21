# Themis — AI Judge Council

## Overview
Themis is a multi-agent AI evaluation system for short-form video ads and blog content. It uses a hierarchical sub-council debate architecture with 6 specialist judges, a critic, and an orchestrator.

## Architecture
- **Content Council**: Hook Analyst, Emotion/Storytelling Analyst, Production Quality Analyst, Authenticity Analyst
- **Market Council**: Trend & Cultural Analyst, Content Subject Analyst, Audience Mapper
- **Cross-cutting**: Critic (adversarial review), Orchestrator (pipeline management + synthesis)

## Pipeline
```
Input → Preprocess → Text Forensics → Content Council (2 debate rounds) → Market Council (2 debate rounds)
      → Cross-council exchange → Critic review → Orchestrator synthesis → JSON + Narrative
```

## Model Allocation
- **Haiku**: Preprocessing (transcription formatting, metadata extraction)
- **Sonnet**: All 7 judge agents (evaluation, scoring, debate)
- **Opus**: Critic + Orchestrator (synthesis, adversarial review)

## Key Commands
- `/themis-evaluate <file>` — Run full evaluation pipeline on a video or text file
- `python3 scripts/preprocess_video.py <video>` — Extract keyframes + transcript
- `python3 scripts/text_forensics.py <payload>` — Run statistical AI detection on text
- `python3 scripts/check_dependencies.py` — Verify all dependencies

## Project Structure
- `skills/` — Judge skills (evaluation frameworks) and orchestration skills
- `agents/` — Orchestrator and council lead agent definitions
- `scripts/` — Python preprocessing and utility scripts
- `hooks/` — Plugin hooks (dependency checking)

## Conventions
- All judge outputs use structured JSON matching `skills/themis-evaluate/references/output-schema.md`
- Debate protocol defined in `skills/themis-evaluate/references/debate-protocol.md`
- Scores are 0-100 integers; confidence is 0.0-1.0 float
- Disagreements >20 points between judges are preserved, not averaged away
