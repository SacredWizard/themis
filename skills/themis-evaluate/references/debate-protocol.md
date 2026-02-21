# Themis Debate Protocol

## Overview

The debate protocol structures how 6 specialist judges evaluate content through a multi-round process designed to surface disagreements, challenge assumptions, and produce higher-quality evaluations than single-pass analysis.

## Councils

### Content Council
- **Hook Analyst** — First 3 seconds / opening effectiveness
- **Emotion/Storytelling Analyst** — Emotional arc, persuasion, narrative
- **Production Quality Analyst** — Visual quality, pacing, audio, editing
- **Authenticity Analyst** — AI content detection (statistical forensics + qualitative analysis)

**Note:** The Authenticity Analyst participates in debate rounds but its scores do NOT contribute to the virality consensus. Its output is passed through as a separate `authenticity` section in the final output.

### Market Council
- **Trend & Cultural Analyst** — Trend alignment, cultural moments, timing
- **Content Subject Analyst** — Subject/theme/object detection and classification
- **Audience Mapper** — Community mapping, platform fit, distribution strategy

## Debate Rounds

### Round 1: Independent Evaluation
- All 6 judges evaluate in parallel
- No visibility into each other's work
- Each produces structured output per the judge output schema
- Council leads collect and hold outputs

### Round 2: Informed Revision
- Each judge receives all Round 1 outputs from their council
- Judges must explicitly state:
  1. What they changed (if anything)
  2. Why they changed it (which peer's reasoning influenced them)
  3. What they still disagree with and why
- A revision that changes nothing must explain why the original assessment stands despite peer input
- Council leads collect revised outputs

### Council Consensus
Each council lead produces a consensus output:

1. **Confidence-weighted averaging**: Scores averaged weighted by each judge's stated confidence
2. **Disagreement preservation**: If any two judges differ by >20 points on a dimension, the disagreement is recorded with both positions and reasoning — not averaged away
3. **Consensus narrative**: Council lead writes a merged assessment incorporating all judges' key observations

### Cross-Council Exchange
- Each council receives the other council's consensus output
- Each council has one round to respond:
  - "Does the other council's assessment change our view?"
  - "Are there tensions between content quality and market potential?"
  - "What does the other council's data reveal that we missed?"
- Council leads produce updated consensus if warranted

### Critic Review
The Critic (Opus-tier) receives:
- Both councils' final consensus outputs
- All individual judge outputs from Round 2
- Cross-council exchange responses

The Critic checks for:
1. **Logical flaws**: Conclusions not supported by evidence
2. **Contradictions**: Judges or councils contradicting each other without acknowledgment
3. **Anchoring bias**: Scores clustering around a first-stated number
4. **Missing considerations**: Obvious factors no judge addressed
5. **Overconfidence**: High confidence without sufficient evidence

### Orchestrator Synthesis
The Orchestrator (Opus-tier) receives everything and produces:
- Final structured JSON output per the output schema
- Narrative executive summary
- Incorporation of critic challenges into final scores/reasoning

## Fast Mode

In fast mode, the protocol is shortened:
- Round 1 only (skip Round 2 informed revision)
- Skip cross-council exchange
- Critic review still occurs but with Round 1 outputs only
- All models use Sonnet (no Opus for critic/orchestrator)

## Consensus Mechanism: Confidence-Weighted Averaging

For each scored dimension where multiple judges contribute:

```
final_score = sum(judge_score_i * judge_confidence_i) / sum(judge_confidence_i)
```

Example:
- Hook Analyst scores hook_effectiveness at 72, confidence 0.85
- (Only Hook Analyst scores this dimension, so it passes through)

For shared dimensions (e.g., overall assessment):
- Judge A: 65, confidence 0.9
- Judge B: 78, confidence 0.7
- Judge C: 70, confidence 0.8
- Result: (65×0.9 + 78×0.7 + 70×0.8) / (0.9 + 0.7 + 0.8) = 69.8 → 70

## Disagreement Rules

1. **>20 point spread**: Preserved as a council_disagreement in the output
2. **>30 point spread**: Flagged for Critic review with high severity
3. **Unanimous agreement** (all within 10 points): Noted as high-confidence consensus
4. **Never silently average away**: Large disagreements indicate genuine uncertainty — surfacing them is more valuable than false precision

## Anti-Patterns to Avoid

- **Groupthink**: Round 2 should not converge everything to the mean. Judges should only change scores when they have a genuine reason.
- **Anchoring to the first score read**: Judges should evaluate the reasoning, not just the number.
- **Politeness convergence**: Judges should not soften disagreements to avoid conflict. Preserved disagreements are a feature.
- **Score inflation**: Real content varies widely. Not everything is a 70. Use the full 0-100 range.
