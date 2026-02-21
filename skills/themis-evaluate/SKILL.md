---
name: themis-evaluate
description: Main entry point for Themis evaluation. Orchestrates the full judge council pipeline to evaluate video ads and blog content for virality potential.
user_invocable: true
arguments: "file_path --fast --whisper-model"
---

# Themis Evaluate

Evaluate short-form video ads or blog content for virality potential, audience distribution, and content quality using the Themis AI Judge Council.

## Usage

```
/themis-evaluate path/to/video.mp4
/themis-evaluate path/to/video.mp4 --fast
/themis-evaluate path/to/article.txt --fast
```

## Execution Steps

### 1. Validate Input

Confirm the file exists and determine content type:
- Video: `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`
- Text: `.txt`, `.md`, `.html`

If the file doesn't exist or has an unsupported extension, stop and tell the user.

### 2. Check Dependencies

```bash
python3 scripts/check_dependencies.py
```

If any dependency is missing, stop and show the user the install instructions.

**Note:** For text content, FFmpeg and Whisper are not required. If only those dependencies are missing and the input is text, proceed anyway.

### 3. Preprocess

**For video:**
```bash
python3 scripts/preprocess_video.py "<file_path>" -o /tmp/themis_payload.json --whisper-model <model>
```

Default whisper model is `base`. Use `tiny` for faster processing, `large` for best transcription quality.

**For text:**
```bash
python3 scripts/preprocess_text.py "<file_path>" -o /tmp/themis_payload.json
```

Text preprocessing extracts sections, computes metadata (word count, reading time), and converts HTML if needed. No external dependencies required.

### 4. Estimate Token Budget & Show Cost Preview

```bash
python3 scripts/format_payload.py /tmp/themis_payload.json --estimate-tokens
python3 scripts/format_payload.py /tmp/themis_payload.json --cache-analysis
python3 scripts/token_tracker.py --mode <full|fast>
```

Report the estimated cost to the user:

**Video content:**
- Full mode: Show token count + estimated cost (~$1.20-2.00)
- Fast mode: Show token count + estimated cost (~$0.60-1.00)

**Text content** (significantly cheaper — no image tokens):
- Full mode: Show token count + estimated cost (~$0.30-0.60)
- Fast mode: Show token count + estimated cost (~$0.15-0.30)

- Show caching savings estimate

Proceed after reporting.

### 5. Run Judge Councils

**Parse the mode** from arguments: `--fast` flag enables fast mode.

#### Fast Mode Differences

| Aspect | Full Mode | Fast Mode |
|--------|-----------|-----------|
| Debate rounds | 2 (independent + informed) | 1 (independent only) |
| Cross-council exchange | Yes | Skipped |
| Critic model | Opus | Sonnet |
| Synthesis model | Opus | Sonnet |
| Judge model | Sonnet | Sonnet |
| Estimated tokens | ~230K-320K | ~130K-170K |
| Estimated cost | $1.20-2.40 | $0.60-0.90 |

#### Full Mode Pipeline

**Round 1 — Independent Evaluation:**

Launch all 6 judges in parallel using the Task tool. Each judge task should:
1. Read the reference files for context:
   - `skills/themis-evaluate/references/output-schema.md`
   - `skills/themis-evaluate/references/debate-protocol.md`
   - `skills/themis-evaluate/references/prompt-templates.md`
2. Read their own SKILL.md for evaluation framework
3. Read the payload from `/tmp/themis_payload.json` (using format_payload.py for their judge-specific view)
4. Produce Round 1 structured JSON output

Content Council judges (use `model: sonnet` for Task tool):
- **Hook Analyst**: `python3 scripts/format_payload.py /tmp/themis_payload.json -j hook_analyst`
- **Emotion Analyst**: `python3 scripts/format_payload.py /tmp/themis_payload.json -j emotion_analyst`
- **Production Analyst**: `python3 scripts/format_payload.py /tmp/themis_payload.json -j production_analyst`

Market Council judges (use `model: sonnet` for Task tool):
- **Trend Analyst**: `python3 scripts/format_payload.py /tmp/themis_payload.json -j trend_analyst`
- **Subject Analyst**: `python3 scripts/format_payload.py /tmp/themis_payload.json -j subject_analyst`
- **Audience Mapper**: `python3 scripts/format_payload.py /tmp/themis_payload.json -j audience_mapper`

**Round 2 — Informed Revision (skip in fast mode):**

For each council, share all Round 1 outputs with each judge. Launch 6 revised evaluations in parallel. Each judge must state what changed and why.

**Cross-Council Exchange (skip in fast mode):**

Share Content Council consensus with Market Council and vice versa. One round of response per council.

### 6. Critic Review

Use the themis-critic skill. Provide:
- Both council outputs (consensus if full mode, Round 1 outputs if fast mode)
- All individual judge outputs
- Cross-council responses (if full mode)

The critic must find at least one substantive challenge.

### 7. Synthesize Final Output

Use the themis-synthesizer skill. The synthesizer should:

1. **Compute scores** using `scripts/merge_scores.py` or manual calculation:
   ```bash
   python3 scripts/merge_scores.py \
     --content-council '<content_consensus_json>' \
     --market-council '<market_consensus_json>' \
     --critic '<critic_json>' \
     --mode full \
     --total-tokens <estimated_total>
   ```

2. **Apply aggregation rules** from output-schema.md:
   - Confidence-weighted averaging for component scores
   - Preserve disagreements >20 points
   - Incorporate critic adjustments (±10 max per dimension)
   - Compute virality tier from final weighted score

3. **Build distribution section** from Market Council data:
   - Primary audiences from Audience Mapper
   - Geographic reach assessment
   - Recommended strategy merging audience + trend timing

4. **Write narrative** sections:
   - Executive summary (3-5 sentences, professional, actionable)
   - Strengths (top 3-5, prioritize multi-judge consensus)
   - Weaknesses (top 3-5, include critic highlights)
   - Improvement suggestions (3-5, each with area/suggestion/expected_impact)

5. **Produce final JSON** conforming exactly to the output schema

### 8. Report Results

1. Save the full JSON to `<input_basename>_themis_evaluation.json`
2. Display to the user:

```
## Themis Evaluation: <filename>

**Virality: <score>/100 (<tier>)** | Confidence: <confidence>

### Component Scores
| Component | Score |
|-----------|-------|
| Hook Effectiveness | <score>/100 |
| Emotional Resonance | <score>/100 |
| Production Quality | <score>/100 |
| Trend Alignment | <score>/100 |
| Shareability | <score>/100 |

### Executive Summary
<executive_summary>

### Top Strengths
1. <strength>
2. <strength>
3. <strength>

### Key Weaknesses
1. <weakness>
2. <weakness>
3. <weakness>

### Primary Audiences
<for each audience — video content>
- **<community>** (relevance: <score>) — TikTok: <score> | Reels: <score> | Shorts: <score>
  <reasoning>
<for each audience — text content>
- **<community>** (relevance: <score>) — Blog: <score> | Twitter/X: <score> | LinkedIn: <score> | Newsletter: <score> | Reddit/HN: <score>
  <reasoning>

### Top Recommendations
1. **<area>**: <suggestion> (impact: <expected_impact>)
2. **<area>**: <suggestion> (impact: <expected_impact>)
3. **<area>**: <suggestion> (impact: <expected_impact>)

### Council Disagreements
<if any, show topic + both positions + resolution>

---
Mode: <mode> | Debate rounds: <rounds> | Tokens: <total> | Est. cost: $<cost>
```

## Reference Documents

Read these before starting the pipeline:
- [Output Schema](references/output-schema.md) — JSON structure for all outputs
- [Debate Protocol](references/debate-protocol.md) — How judges debate and reach consensus
- [Prompt Templates](references/prompt-templates.md) — Shared prompt fragments
