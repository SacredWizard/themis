#!/usr/bin/env python3
"""
Token usage tracking and cost estimation for Themis evaluation pipeline.

Tracks per-stage token usage and computes cost estimates based on
model pricing tiers.
"""

import json
import sys
from datetime import datetime, timezone


# Model pricing per million tokens (as of 2025)
MODEL_PRICING = {
    "haiku": {"input": 0.25, "output": 1.25},
    "sonnet": {"input": 3.00, "output": 15.00},
    "opus": {"input": 15.00, "output": 75.00},
}

# Which model each pipeline stage uses
STAGE_MODELS = {
    # Full mode
    "full": {
        "preprocess": "haiku",
        "hook_analyst_r1": "sonnet",
        "emotion_analyst_r1": "sonnet",
        "production_analyst_r1": "sonnet",
        "trend_analyst_r1": "sonnet",
        "subject_analyst_r1": "sonnet",
        "audience_mapper_r1": "sonnet",
        "hook_analyst_r2": "sonnet",
        "emotion_analyst_r2": "sonnet",
        "production_analyst_r2": "sonnet",
        "trend_analyst_r2": "sonnet",
        "subject_analyst_r2": "sonnet",
        "audience_mapper_r2": "sonnet",
        "content_council_consensus": "sonnet",
        "market_council_consensus": "sonnet",
        "cross_council_content": "sonnet",
        "cross_council_market": "sonnet",
        "critic": "opus",
        "synthesis": "opus",
    },
    # Fast mode — all Sonnet, no Round 2 or cross-council
    "fast": {
        "preprocess": "haiku",
        "hook_analyst_r1": "sonnet",
        "emotion_analyst_r1": "sonnet",
        "production_analyst_r1": "sonnet",
        "trend_analyst_r1": "sonnet",
        "subject_analyst_r1": "sonnet",
        "audience_mapper_r1": "sonnet",
        "content_council_consensus": "sonnet",
        "market_council_consensus": "sonnet",
        "critic": "sonnet",
        "synthesis": "sonnet",
    },
}

# Estimated token budgets per stage (input + output)
STAGE_TOKEN_ESTIMATES = {
    "full": {
        "preprocess": {"input": 500, "output": 200},
        "hook_analyst_r1": {"input": 12000, "output": 3000},
        "emotion_analyst_r1": {"input": 20000, "output": 3000},
        "production_analyst_r1": {"input": 20000, "output": 3000},
        "trend_analyst_r1": {"input": 14000, "output": 3000},
        "subject_analyst_r1": {"input": 20000, "output": 4000},
        "audience_mapper_r1": {"input": 14000, "output": 4000},
        "hook_analyst_r2": {"input": 15000, "output": 2000},
        "emotion_analyst_r2": {"input": 23000, "output": 2000},
        "production_analyst_r2": {"input": 23000, "output": 2000},
        "trend_analyst_r2": {"input": 17000, "output": 2000},
        "subject_analyst_r2": {"input": 23000, "output": 2000},
        "audience_mapper_r2": {"input": 17000, "output": 2000},
        "content_council_consensus": {"input": 8000, "output": 2000},
        "market_council_consensus": {"input": 8000, "output": 2000},
        "cross_council_content": {"input": 6000, "output": 1500},
        "cross_council_market": {"input": 6000, "output": 1500},
        "critic": {"input": 15000, "output": 4000},
        "synthesis": {"input": 12000, "output": 5000},
    },
    "fast": {
        "preprocess": {"input": 500, "output": 200},
        "hook_analyst_r1": {"input": 12000, "output": 3000},
        "emotion_analyst_r1": {"input": 20000, "output": 3000},
        "production_analyst_r1": {"input": 20000, "output": 3000},
        "trend_analyst_r1": {"input": 14000, "output": 3000},
        "subject_analyst_r1": {"input": 20000, "output": 4000},
        "audience_mapper_r1": {"input": 14000, "output": 4000},
        "content_council_consensus": {"input": 8000, "output": 2000},
        "market_council_consensus": {"input": 8000, "output": 2000},
        "critic": {"input": 12000, "output": 3000},
        "synthesis": {"input": 10000, "output": 4000},
    },
}

# Prompt caching savings — shared payload content cached across judges
CACHE_HIT_RATES = {
    "full": {
        # Round 1: 6 judges share same payload, first judge is a miss, others hit cache
        # ~83% of shared payload tokens are cache hits (5/6 judges)
        "round_1_shared_payload": 0.83,
        # Round 2: judges share Round 1 outputs + payload, similar cache rate
        "round_2_shared_context": 0.75,
        # Cross-council: smaller payloads, less cache benefit
        "cross_council": 0.50,
    },
    "fast": {
        "round_1_shared_payload": 0.83,
    },
}

# Cache pricing discount (cached input tokens cost 90% less)
CACHE_DISCOUNT = 0.10  # cached tokens cost 10% of normal input price


class TokenTracker:
    """Track token usage across pipeline stages."""

    def __init__(self, mode: str = "full"):
        self.mode = mode
        self.stages: dict[str, dict] = {}
        self.models = STAGE_MODELS.get(mode, STAGE_MODELS["full"])

    def record(self, stage: str, input_tokens: int, output_tokens: int,
               cache_hit_tokens: int = 0):
        """Record actual token usage for a stage."""
        model = self.models.get(stage, "sonnet")
        self.stages[stage] = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_hit_tokens": cache_hit_tokens,
            "model": model,
        }

    def estimate_all(self) -> dict:
        """Generate estimates for all stages based on mode defaults."""
        estimates = STAGE_TOKEN_ESTIMATES.get(self.mode, STAGE_TOKEN_ESTIMATES["full"])
        for stage, tokens in estimates.items():
            if stage not in self.stages:
                model = self.models.get(stage, "sonnet")
                self.stages[stage] = {
                    "input_tokens": tokens["input"],
                    "output_tokens": tokens["output"],
                    "cache_hit_tokens": 0,
                    "model": model,
                }
        return self.summary()

    def summary(self) -> dict:
        """Compute total tokens and cost."""
        total_input = 0
        total_output = 0
        total_cache_hits = 0
        total_cost = 0.0

        stage_details = {}
        for stage, data in self.stages.items():
            inp = data["input_tokens"]
            out = data["output_tokens"]
            cache = data.get("cache_hit_tokens", 0)
            model = data["model"]
            pricing = MODEL_PRICING.get(model, MODEL_PRICING["sonnet"])

            # Non-cached input tokens pay full price
            regular_input = inp - cache
            cache_cost = cache * pricing["input"] * CACHE_DISCOUNT / 1_000_000
            regular_cost = regular_input * pricing["input"] / 1_000_000
            output_cost = out * pricing["output"] / 1_000_000
            stage_cost = cache_cost + regular_cost + output_cost

            total_input += inp
            total_output += out
            total_cache_hits += cache
            total_cost += stage_cost

            stage_details[stage] = {
                "input": inp,
                "output": out,
                "cache_hits": cache,
                "model": model,
                "cost_usd": round(stage_cost, 4),
            }

        return {
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "total_cache_hit_tokens": total_cache_hits,
            "estimated_cost_usd": round(total_cost, 2),
            "mode": self.mode,
            "stages": stage_details,
        }

    def apply_cache_estimates(self):
        """Apply estimated cache hit rates to recorded/estimated stages."""
        cache_rates = CACHE_HIT_RATES.get(self.mode, {})

        # Round 1 judges share the same payload
        r1_payload_rate = cache_rates.get("round_1_shared_payload", 0)
        r1_judges = [s for s in self.stages if s.endswith("_r1")]
        if r1_judges and r1_payload_rate > 0:
            # First judge gets no cache, rest get cache hits on shared content
            # Shared content is roughly 60% of input tokens (payload portion)
            for i, stage in enumerate(sorted(r1_judges)):
                if i > 0:  # skip first judge (cache miss)
                    shared = int(self.stages[stage]["input_tokens"] * 0.6)
                    self.stages[stage]["cache_hit_tokens"] = int(shared * r1_payload_rate)

        # Round 2 judges share Round 1 outputs
        r2_rate = cache_rates.get("round_2_shared_context", 0)
        r2_judges = [s for s in self.stages if s.endswith("_r2")]
        if r2_judges and r2_rate > 0:
            for i, stage in enumerate(sorted(r2_judges)):
                if i > 0:
                    shared = int(self.stages[stage]["input_tokens"] * 0.5)
                    self.stages[stage]["cache_hit_tokens"] = int(shared * r2_rate)


def estimate_pipeline_cost(mode: str = "full", apply_caching: bool = True) -> dict:
    """Estimate total pipeline cost for a given mode."""
    tracker = TokenTracker(mode)
    tracker.estimate_all()
    if apply_caching:
        tracker.apply_cache_estimates()
    return tracker.summary()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Estimate Themis pipeline token usage and cost")
    parser.add_argument("--mode", default="full", choices=["full", "fast"],
                        help="Pipeline mode (default: full)")
    parser.add_argument("--no-cache", action="store_true",
                        help="Disable prompt caching estimates")
    parser.add_argument("--compare", action="store_true",
                        help="Show side-by-side comparison of full vs fast mode")
    args = parser.parse_args()

    if args.compare:
        print("Themis Pipeline Cost Comparison")
        print("=" * 60)
        for mode in ["full", "fast"]:
            summary = estimate_pipeline_cost(mode, apply_caching=not args.no_cache)
            print(f"\n{mode.upper()} MODE:")
            print(f"  Total tokens:      {summary['total_tokens']:>10,}")
            print(f"  Input tokens:      {summary['total_input_tokens']:>10,}")
            print(f"  Output tokens:     {summary['total_output_tokens']:>10,}")
            if not args.no_cache:
                print(f"  Cache hit tokens:  {summary['total_cache_hit_tokens']:>10,}")
            print(f"  Estimated cost:    ${summary['estimated_cost_usd']:>9.2f}")
        print()

        full = estimate_pipeline_cost("full", apply_caching=not args.no_cache)
        fast = estimate_pipeline_cost("fast", apply_caching=not args.no_cache)
        if full["estimated_cost_usd"] > 0:
            savings = (1 - fast["estimated_cost_usd"] / full["estimated_cost_usd"]) * 100
            print(f"Fast mode saves ~{savings:.0f}% vs full mode")
    else:
        summary = estimate_pipeline_cost(args.mode, apply_caching=not args.no_cache)
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
