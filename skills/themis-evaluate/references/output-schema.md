# Themis Output Schema v1.0

All Themis evaluations produce output conforming to this schema. Judges produce component outputs; the Orchestrator merges them into the final structure.

## Final Output Schema

```json
{
  "themis_version": "1.0.0",

  "input": {
    "source_file": "string — original filename",
    "content_type": "video | text",
    "duration_sec": "number | null — video duration in seconds",
    "keyframe_count": "integer — number of keyframes extracted",
    "word_count": "integer | null — for text content",
    "transcript_preview": "string — first 200 chars of transcript/text"
  },

  "virality": {
    "score": "integer 0-100 — overall virality potential",
    "tier": "low | moderate | promising | strong | exceptional",
    "components": {
      "hook_effectiveness": "integer 0-100",
      "emotional_resonance": "integer 0-100",
      "production_quality": "integer 0-100",
      "trend_alignment": "integer 0-100",
      "shareability": "integer 0-100"
    },
    "confidence": "float 0.0-1.0 — confidence in the overall score"
  },

  "distribution": {
    "primary_audiences": [
      {
        "community": "string — specific community name (e.g., 'BookTok', 'Sneakerheads', 'Dev Twitter')",
        "relevance_score": "integer 0-100",
        "platform_fit": {
          "comment": "For video: tiktok, reels, shorts. For text: blog, twitter_x, linkedin, newsletter, reddit_hn",
          "tiktok": "integer 0-100 (video only)",
          "reels": "integer 0-100 (video only)",
          "shorts": "integer 0-100 (video only)",
          "blog": "integer 0-100 (text only)",
          "twitter_x": "integer 0-100 (text only)",
          "linkedin": "integer 0-100 (text only)",
          "newsletter": "integer 0-100 (text only)",
          "reddit_hn": "integer 0-100 (text only)"
        },
        "reasoning": "string — why this community would engage"
      }
    ],
    "geographic_reach": {
      "potential": "local | regional | national | global",
      "cultural_barriers": ["string — barriers to cross-cultural spread"],
      "universal_themes": ["string — themes that transcend cultural boundaries"]
    },
    "recommended_strategy": "string — 2-3 sentence distribution recommendation"
  },

  "reasoning": {
    "executive_summary": "string — 3-5 sentence summary of evaluation",
    "strengths": ["string — key content strengths"],
    "weaknesses": ["string — key content weaknesses"],
    "improvement_suggestions": [
      {
        "area": "string — what to improve",
        "suggestion": "string — specific actionable suggestion",
        "expected_impact": "low | medium | high"
      }
    ],
    "council_disagreements": [
      {
        "topic": "string — what was disagreed on",
        "position_a": "string — one position with reasoning",
        "position_b": "string — opposing position with reasoning",
        "resolution": "string — how it was resolved or why it was preserved"
      }
    ]
  },

  "metadata": {
    "mode": "full | fast",
    "debate_rounds": "integer",
    "total_tokens_used": "integer",
    "estimated_cost_usd": "float",
    "judges_used": ["string — list of judge names"],
    "evaluation_timestamp": "string — ISO 8601"
  }
}
```

## Tier Mapping

| Score Range | Tier |
|------------|------|
| 0-20 | low |
| 21-40 | moderate |
| 41-60 | promising |
| 61-80 | strong |
| 81-100 | exceptional |

## Judge Output Schema

Each judge produces a structured evaluation that feeds into the final output. All judges share this base structure:

```json
{
  "judge": "string — judge identifier",
  "round": "integer — debate round number (1 or 2)",
  "scores": {
    "primary_score": "integer 0-100 — main evaluation dimension",
    "sub_scores": {
      "dimension_name": "integer 0-100"
    }
  },
  "confidence": "float 0.0-1.0",
  "reasoning": {
    "assessment": "string — main evaluation narrative",
    "evidence": ["string — specific evidence from content"],
    "concerns": ["string — identified issues"]
  },
  "revision_notes": "string | null — what changed from Round 1 (Round 2 only)"
}
```

### Judge-Specific Primary Dimensions

| Judge | Primary Score Maps To | Key Sub-Scores |
|-------|----------------------|-----------------|
| Hook Analyst | `hook_effectiveness` | attention_grab, opening_strength, curiosity_gap, first_frame_impact |
| Emotion Analyst | `emotional_resonance` | emotional_arc, persuasion_strength, authenticity, memorability |
| Production Analyst | `production_quality` | visual_quality, pacing, audio_quality, editing_craft |
| Trend Analyst | `trend_alignment` | trend_relevance, timing, cultural_moment, format_alignment |
| Subject Analyst | (feeds audience mapper) | subject_clarity, theme_strength, niche_specificity |
| Audience Mapper | `shareability` | community_fit, share_motivation, platform_optimization |

## Critic Output Schema

```json
{
  "judge": "critic",
  "challenges": [
    {
      "target_judge": "string — which judge's reasoning is challenged",
      "issue_type": "logical_flaw | anchoring_bias | missing_consideration | contradiction | overconfidence",
      "description": "string — what the issue is",
      "severity": "minor | moderate | major",
      "suggested_adjustment": "string — recommended fix"
    }
  ],
  "cross_council_tensions": [
    {
      "content_position": "string",
      "market_position": "string",
      "assessment": "string — which is more defensible and why"
    }
  ],
  "overall_confidence_adjustment": "float -0.2 to +0.1 — suggested adjustment to overall confidence"
}
```

## Score Aggregation Rules

1. **Component scores** are confidence-weighted averages from relevant judges
2. **Overall virality score** = weighted sum of components:
   - hook_effectiveness: 25%
   - emotional_resonance: 20%
   - production_quality: 15%
   - trend_alignment: 20%
   - shareability: 20%
3. **Disagreements >20 points** between judges on the same dimension are preserved in `council_disagreements`, not averaged away
4. **Critic adjustments** can shift scores by up to ±10 points with justification
5. **Confidence** is the minimum of individual judge confidences, adjusted by critic
