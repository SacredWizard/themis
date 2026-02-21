#!/usr/bin/env python3
"""
Merge and aggregate scores from Themis judge councils.

Handles confidence-weighted averaging, disagreement detection,
cross-council adjustments, and critic adjustments.
"""

import argparse
import json
import sys
from datetime import datetime, timezone


# Virality component weights
COMPONENT_WEIGHTS = {
    "hook_effectiveness": 0.25,
    "emotional_resonance": 0.20,
    "production_quality": 0.15,
    "trend_alignment": 0.20,
    "shareability": 0.20,
}

TIER_THRESHOLDS = [
    (81, "exceptional"),
    (61, "strong"),
    (41, "promising"),
    (21, "moderate"),
    (0, "low"),
]

# Max adjustments per source
MAX_CROSS_COUNCIL_ADJUSTMENT = 5
MAX_CRITIC_ADJUSTMENT = 10


def score_to_tier(score: int) -> str:
    """Map a 0-100 score to a virality tier."""
    for threshold, tier in TIER_THRESHOLDS:
        if score >= threshold:
            return tier
    return "low"


def confidence_weighted_average(scores_and_confidences: list[tuple[int, float]]) -> tuple[int, float]:
    """
    Compute confidence-weighted average.

    Args:
        scores_and_confidences: List of (score, confidence) tuples

    Returns:
        (weighted_average_score, combined_confidence)
    """
    if not scores_and_confidences:
        return 0, 0.0

    total_weight = sum(c for _, c in scores_and_confidences)
    if total_weight == 0:
        return 0, 0.0

    weighted_sum = sum(s * c for s, c in scores_and_confidences)
    avg_score = round(weighted_sum / total_weight)
    min_confidence = min(c for _, c in scores_and_confidences)

    return avg_score, min_confidence


def detect_disagreements(judge_outputs: list[dict], threshold: int = 20) -> list[dict]:
    """
    Detect score disagreements exceeding the threshold.

    Returns list of disagreement records.
    """
    disagreements = []

    if len(judge_outputs) < 2:
        return disagreements

    # Compare primary scores between all judge pairs
    for i in range(len(judge_outputs)):
        for j in range(i + 1, len(judge_outputs)):
            a = judge_outputs[i]
            b = judge_outputs[j]

            score_a = a.get("scores", {}).get("primary_score", 0)
            score_b = b.get("scores", {}).get("primary_score", 0)
            spread = abs(score_a - score_b)

            if spread > threshold:
                disagreements.append({
                    "topic": f"Overall assessment ({a['judge']} vs {b['judge']})",
                    "position_a": f"{a['judge']} scored {score_a}: {a.get('reasoning', {}).get('assessment', '')[:200]}",
                    "position_b": f"{b['judge']} scored {score_b}: {b.get('reasoning', {}).get('assessment', '')[:200]}",
                    "spread": spread,
                    "resolution": "preserved" if spread > 30 else "noted",
                })

    return disagreements


def apply_adjustment(score: int, adjustment: float, max_adj: int) -> int:
    """Apply a bounded adjustment to a score."""
    adj = max(-max_adj, min(max_adj, round(adjustment)))
    return max(0, min(100, score + adj))


def merge_council_scores(
    content_council: dict,
    market_council: dict,
    critic: dict | None = None,
    cross_council_content_response: dict | None = None,
    cross_council_market_response: dict | None = None,
) -> dict:
    """
    Merge all council outputs into final component scores.

    Returns the complete Themis output structure.
    """
    # Extract base scores from councils
    cc_scores = content_council.get("consensus_scores", {})
    mc_scores = market_council.get("consensus_scores", {})

    components = {
        "hook_effectiveness": cc_scores.get("hook_effectiveness", {}).get("score", 50),
        "emotional_resonance": cc_scores.get("emotional_resonance", {}).get("score", 50),
        "production_quality": cc_scores.get("production_quality", {}).get("score", 50),
        "trend_alignment": mc_scores.get("trend_alignment", {}).get("score", 50),
        "shareability": mc_scores.get("shareability", {}).get("score", 50),
    }

    # Apply cross-council adjustments if present
    if cross_council_content_response:
        adjustments = cross_council_content_response.get("score_adjustments", {})
        for dim, adj in adjustments.items():
            if dim in components:
                components[dim] = apply_adjustment(
                    components[dim], adj, MAX_CROSS_COUNCIL_ADJUSTMENT
                )

    if cross_council_market_response:
        adjustments = cross_council_market_response.get("score_adjustments", {})
        for dim, adj in adjustments.items():
            if dim in components:
                components[dim] = apply_adjustment(
                    components[dim], adj, MAX_CROSS_COUNCIL_ADJUSTMENT
                )

    # Apply critic adjustments
    if critic:
        for challenge in critic.get("challenges", []):
            adj = challenge.get("suggested_adjustment", "")
            # Parse numeric adjustments from suggestion text
            if isinstance(adj, (int, float)):
                target = challenge.get("target_judge", "")
                # Map judge to component
                judge_to_component = {
                    "hook_analyst": "hook_effectiveness",
                    "emotion_analyst": "emotional_resonance",
                    "production_analyst": "production_quality",
                    "trend_analyst": "trend_alignment",
                    "audience_mapper": "shareability",
                }
                if target in judge_to_component:
                    dim = judge_to_component[target]
                    components[dim] = apply_adjustment(
                        components[dim], adj, MAX_CRITIC_ADJUSTMENT
                    )

    # Calculate overall virality score
    virality_score = round(sum(
        components[dim] * weight
        for dim, weight in COMPONENT_WEIGHTS.items()
    ))
    virality_score = max(0, min(100, virality_score))

    # Calculate confidence
    all_confidences = []
    for council in [content_council, market_council]:
        for score_data in council.get("consensus_scores", {}).values():
            if isinstance(score_data, dict) and "confidence" in score_data:
                all_confidences.append(score_data["confidence"])

    base_confidence = min(all_confidences) if all_confidences else 0.5
    critic_adj = critic.get("overall_confidence_adjustment", 0.0) if critic else 0.0
    final_confidence = max(0.0, min(1.0, base_confidence + critic_adj))

    # Collect disagreements
    all_disagreements = (
        content_council.get("disagreements", []) +
        market_council.get("disagreements", [])
    )
    if critic:
        for tension in critic.get("cross_council_tensions", []):
            all_disagreements.append({
                "topic": tension.get("tension_type", "Cross-council tension"),
                "position_a": tension.get("content_position", ""),
                "position_b": tension.get("market_position", ""),
                "resolution": tension.get("assessment", ""),
            })

    return {
        "virality": {
            "score": virality_score,
            "tier": score_to_tier(virality_score),
            "components": components,
            "confidence": round(final_confidence, 2),
        },
        "disagreements": all_disagreements,
    }


def build_metadata(mode: str, debate_rounds: int, judges_used: list[str],
                   total_tokens: int = 0) -> dict:
    """Build the metadata section."""
    # Cost estimation
    # Rough: assume 60% input, 40% output tokens
    # Sonnet: $3/$15 per MTok, Opus: $15/$75 per MTok
    # Assume ~70% Sonnet, ~30% Opus usage
    input_tokens = int(total_tokens * 0.6)
    output_tokens = int(total_tokens * 0.4)
    sonnet_fraction = 0.7
    opus_fraction = 0.3

    sonnet_cost = (
        (input_tokens * sonnet_fraction * 3 / 1_000_000) +
        (output_tokens * sonnet_fraction * 15 / 1_000_000)
    )
    opus_cost = (
        (input_tokens * opus_fraction * 15 / 1_000_000) +
        (output_tokens * opus_fraction * 75 / 1_000_000)
    )

    return {
        "mode": mode,
        "debate_rounds": debate_rounds,
        "total_tokens_used": total_tokens,
        "estimated_cost_usd": round(sonnet_cost + opus_cost, 2),
        "judges_used": judges_used,
        "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
    }


def main():
    parser = argparse.ArgumentParser(description="Merge Themis council scores")
    parser.add_argument("--content-council", required=True,
                        help="Content Council consensus JSON (string or file path)")
    parser.add_argument("--market-council", required=True,
                        help="Market Council consensus JSON (string or file path)")
    parser.add_argument("--critic", help="Critic output JSON (string or file path)")
    parser.add_argument("--mode", default="full", choices=["full", "fast"])
    parser.add_argument("--total-tokens", type=int, default=0)
    args = parser.parse_args()

    def load_json(val: str) -> dict:
        """Load JSON from a string or file path."""
        try:
            return json.loads(val)
        except json.JSONDecodeError:
            with open(val) as f:
                return json.load(f)

    content = load_json(args.content_council)
    market = load_json(args.market_council)
    critic = load_json(args.critic) if args.critic else None

    result = merge_council_scores(content, market, critic)

    debate_rounds = 2 if args.mode == "full" else 1
    judges = ["hook_analyst", "emotion_analyst", "production_analyst",
              "trend_analyst", "subject_analyst", "audience_mapper"]
    metadata = build_metadata(args.mode, debate_rounds, judges, args.total_tokens)

    output = {**result, "metadata": metadata}
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
