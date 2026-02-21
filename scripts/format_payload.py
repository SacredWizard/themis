#!/usr/bin/env python3
"""
Format a preprocessed payload for judge consumption.

Takes the raw payload from preprocess_video.py and builds judge-specific
views with appropriate keyframe subsets and context.
"""

import argparse
import json
import sys
from copy import deepcopy


# Which keyframes each judge needs
JUDGE_KEYFRAME_CONFIGS = {
    "hook_analyst": {"strategy": "first_n", "n": 4},
    "emotion_analyst": {"strategy": "all"},
    "production_analyst": {"strategy": "all"},
    "trend_analyst": {"strategy": "sampled", "n": 6},
    "subject_analyst": {"strategy": "all"},
    "audience_mapper": {"strategy": "sampled", "n": 6},
    "critic": {"strategy": "none"},
    "orchestrator": {"strategy": "none"},
}


def select_keyframes(frames: list[dict], config: dict) -> list[dict]:
    """Select keyframes based on judge-specific strategy."""
    strategy = config.get("strategy", "all")

    if strategy == "none":
        return []
    if strategy == "all":
        return frames
    if strategy == "first_n":
        n = config.get("n", 4)
        return frames[:n]
    if strategy == "sampled":
        n = config.get("n", 6)
        if len(frames) <= n:
            return frames
        indices = [int(i * (len(frames) - 1) / (n - 1)) for i in range(n)]
        return [frames[i] for i in sorted(set(indices))]

    return frames


def strip_base64(frames: list[dict]) -> list[dict]:
    """Remove base64 data from frames, keeping metadata only."""
    return [
        {k: v for k, v in f.items() if k != "base64"}
        for f in frames
    ]


def format_for_judge(payload: dict, judge_name: str,
                     include_images: bool = True) -> dict:
    """Build a judge-specific view of the payload."""
    config = JUDGE_KEYFRAME_CONFIGS.get(judge_name, {"strategy": "all"})
    selected = select_keyframes(payload.get("keyframes", []), config)

    judge_payload = {
        "source_file": payload["source_file"],
        "content_type": payload["content_type"],
        "metadata": payload["metadata"],
        "transcript": payload["transcript"],
        "keyframe_count_total": payload.get("keyframe_count", len(payload.get("keyframes", []))),
        "keyframe_count_provided": len(selected),
        "keyframe_selection_strategy": config["strategy"],
    }

    if include_images:
        judge_payload["keyframes"] = selected
    else:
        judge_payload["keyframes"] = strip_base64(selected)

    return judge_payload


def format_all_judges(payload: dict, include_images: bool = True) -> dict[str, dict]:
    """Build payloads for all judges."""
    result = {}
    for judge_name in JUDGE_KEYFRAME_CONFIGS:
        # Critic and orchestrator never get images
        judge_images = include_images and JUDGE_KEYFRAME_CONFIGS[judge_name]["strategy"] != "none"
        result[judge_name] = format_for_judge(payload, judge_name, include_images=judge_images)
    return result


def estimate_token_sizes(judge_payloads: dict[str, dict]) -> dict[str, int]:
    """Rough estimate of token counts per judge payload."""
    estimates = {}
    for judge_name, payload in judge_payloads.items():
        # Text tokens: ~4 chars per token
        text_json = json.dumps({k: v for k, v in payload.items() if k != "keyframes"})
        text_tokens = len(text_json) // 4

        # Image tokens: ~1600 tokens per image (typical for Claude vision)
        image_count = sum(
            1 for f in payload.get("keyframes", []) if "base64" in f
        )
        image_tokens = image_count * 1600

        estimates[judge_name] = text_tokens + image_tokens

    return estimates


def main():
    parser = argparse.ArgumentParser(
        description="Format preprocessed payload for judge consumption"
    )
    parser.add_argument("payload", help="Path to payload JSON from preprocess_video.py")
    parser.add_argument("-j", "--judge", help="Format for specific judge only")
    parser.add_argument("--no-images", action="store_true",
                        help="Strip base64 image data (text metadata only)")
    parser.add_argument("--estimate-tokens", action="store_true",
                        help="Print estimated token counts per judge")
    args = parser.parse_args()

    with open(args.payload) as f:
        payload = json.load(f)

    if args.judge:
        result = format_for_judge(payload, args.judge, include_images=not args.no_images)
        print(json.dumps(result, indent=2))
    else:
        all_payloads = format_all_judges(payload, include_images=not args.no_images)

        if args.estimate_tokens:
            estimates = estimate_token_sizes(all_payloads)
            total = sum(estimates.values())
            print("Estimated token counts per judge:")
            for judge, tokens in sorted(estimates.items()):
                print(f"  {judge:25s}: {tokens:>8,} tokens")
            print(f"  {'TOTAL':25s}: {total:>8,} tokens")
        else:
            print(json.dumps(all_payloads, indent=2))


if __name__ == "__main__":
    main()
