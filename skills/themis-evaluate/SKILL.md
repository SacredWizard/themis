---
name: themis-evaluate
description: Main entry point for Themis evaluation. Orchestrates the full judge council pipeline to evaluate video ads and blog content for virality potential.
user_invocable: true
arguments: "<file_path> [--fast] [--whisper-model tiny|base|small|medium|large]"
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
- Text: `.txt`, `.md`, `.html` (Phase 2)

If the file doesn't exist or has an unsupported extension, stop and tell the user.

### 2. Check Dependencies

```bash
python3 scripts/check_dependencies.py
```

If any dependency is missing, stop and show the user the install instructions.

### 3. Preprocess

For video:
```bash
python3 scripts/preprocess_video.py "<file_path>" -o /tmp/themis_payload.json --whisper-model <model>
```

Default whisper model is `base`. Use `tiny` for faster processing, `large` for best transcription quality.

### 4. Estimate Token Budget

```bash
python3 scripts/format_payload.py /tmp/themis_payload.json --estimate-tokens
```

Report the estimated token count to the user and proceed.

### 5. Run Judge Councils

**Parse the mode** from arguments: `--fast` flag enables fast mode.

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

Use the themis-synthesizer skill to merge all outputs into the final JSON.

Apply score aggregation rules from output-schema.md:
- Confidence-weighted averaging for component scores
- Preserve disagreements >20 points
- Incorporate critic adjustments (±10 max)
- Compute virality tier from final score

### 8. Report Results

1. Save the full JSON to `<input_basename>_themis_evaluation.json`
2. Display to the user:
   - Virality score and tier
   - Top 3 strengths
   - Top 3 weaknesses
   - Primary audiences with platform fit
   - Executive summary
   - Token usage and estimated cost

## Reference Documents

Read these before starting the pipeline:
- [Output Schema](references/output-schema.md) — JSON structure for all outputs
- [Debate Protocol](references/debate-protocol.md) — How judges debate and reach consensus
- [Prompt Templates](references/prompt-templates.md) — Shared prompt fragments
