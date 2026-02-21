#!/usr/bin/env python3
"""
Statistical text forensics for AI content detection.

Pure Python implementation using only standard library modules.
Computes linguistic metrics that correlate with AI-generated text:
burstiness, type-token ratio, hedging frequency, sentence-initial entropy,
paragraph length CV, readability variance, and transition word frequency.

Outputs JSON with all metrics + a composite AI probability score.
"""

import argparse
import json
import math
import re
import statistics
import sys


# LLM hedging phrases — common filler phrases in AI-generated text
HEDGING_PHRASES = [
    "it's important to note",
    "it is important to note",
    "it's worth noting",
    "it is worth noting",
    "it's worth mentioning",
    "it is worth mentioning",
    "it should be noted",
    "importantly",
    "significantly",
    "interestingly",
    "notably",
    "in other words",
    "that being said",
    "having said that",
    "at the end of the day",
    "when it comes to",
    "in terms of",
    "as a matter of fact",
    "needless to say",
    "it goes without saying",
    "as previously mentioned",
    "it's crucial to",
    "it is crucial to",
    "it's essential to",
    "it is essential to",
    "one might argue",
    "it could be argued",
    "there's no denying",
    "there is no denying",
    "in today's world",
    "in today's fast-paced",
    "in the realm of",
    "delve into",
    "delve deeper",
    "leverage",
    "utilize",
    "in conclusion",
    "to summarize",
    "in summary",
    "overall",
    "furthermore",
    "moreover",
    "additionally",
    "consequently",
    "subsequently",
    "nevertheless",
    "nonetheless",
    "notwithstanding",
]

# Formal transition words/phrases
TRANSITION_WORDS = [
    "furthermore",
    "moreover",
    "additionally",
    "consequently",
    "subsequently",
    "nevertheless",
    "nonetheless",
    "notwithstanding",
    "in addition",
    "as a result",
    "on the other hand",
    "in contrast",
    "conversely",
    "similarly",
    "likewise",
    "accordingly",
    "hence",
    "thus",
    "therefore",
    "meanwhile",
    "in particular",
    "specifically",
    "for instance",
    "for example",
    "in fact",
    "indeed",
    "certainly",
    "undoubtedly",
    "without a doubt",
    "to this end",
    "with this in mind",
    "in light of",
    "given that",
    "provided that",
    "assuming that",
    "insofar as",
    "inasmuch as",
    "to that end",
    "by the same token",
    "that said",
]

# Default minimum word count for analysis
DEFAULT_MIN_WORDS = 50

# Windowed TTR window size
TTR_WINDOW_SIZE = 100

# Composite score weights
COMPOSITE_WEIGHTS = {
    "burstiness": 0.15,
    "ttr": 0.10,
    "hedging": 0.20,
    "sentence_entropy": 0.15,
    "paragraph_cv": 0.10,
    "readability_variance": 0.15,
    "transition_frequency": 0.15,
}


def count_syllables(word: str) -> int:
    """
    Estimate syllable count using vowel-group heuristic.

    Count groups of consecutive vowels [aeiouy], adjust for silent-e,
    minimum 1 syllable per word.
    """
    word = word.lower().strip()
    if not word:
        return 0

    # Count vowel groups
    vowel_groups = re.findall(r'[aeiouy]+', word)
    count = len(vowel_groups)

    # Adjust for silent-e at end (but not words like "the", "be")
    if word.endswith('e') and len(word) > 2 and count > 1:
        count -= 1

    return max(1, count)


def split_sentences(text: str) -> list[str]:
    """Split text into sentences using punctuation boundaries."""
    # Split on sentence-ending punctuation followed by whitespace or end
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    # Filter empty and very short fragments
    return [s.strip() for s in sentences if len(s.strip()) > 2]


def split_paragraphs(text: str) -> list[str]:
    """Split text into paragraphs by blank lines."""
    paragraphs = re.split(r'\n\s*\n', text.strip())
    return [p.strip() for p in paragraphs if len(p.strip()) > 0]


def get_words(text: str) -> list[str]:
    """Extract words from text."""
    return re.findall(r'\b[a-zA-Z\']+\b', text)


def compute_burstiness(sentences: list[str]) -> float:
    """
    Compute burstiness as coefficient of variation of sentence lengths.

    Low burstiness (uniform sentence length) → AI signal.
    Returns 0.0-1.0 where lower values indicate more AI-like uniformity.
    """
    if len(sentences) < 3:
        return None

    lengths = [len(get_words(s)) for s in sentences]
    lengths = [l for l in lengths if l > 0]

    if len(lengths) < 3:
        return None

    mean = statistics.mean(lengths)
    if mean == 0:
        return None

    stdev = statistics.stdev(lengths)
    cv = stdev / mean

    # Normalize: typical human CV is 0.5-1.0+, AI is 0.2-0.4
    # Return the raw CV for transparency
    return round(cv, 4)


def compute_windowed_ttr(words: list[str], window_size: int = TTR_WINDOW_SIZE) -> float:
    """
    Compute windowed Type-Token Ratio.

    Averages TTR across sliding windows to normalize for text length.
    Higher TTR with less slang → AI signal.
    """
    if len(words) < window_size:
        # For short texts, compute simple TTR
        if len(words) == 0:
            return None
        lower_words = [w.lower() for w in words]
        return round(len(set(lower_words)) / len(lower_words), 4)

    ttrs = []
    for i in range(0, len(words) - window_size + 1, window_size // 2):
        window = words[i:i + window_size]
        lower_window = [w.lower() for w in window]
        ttr = len(set(lower_window)) / len(lower_window)
        ttrs.append(ttr)

    if not ttrs:
        return None

    return round(statistics.mean(ttrs), 4)


def compute_hedging_frequency(text: str, word_count: int) -> float:
    """
    Count hedging/LLM phrases per 1,000 words.

    High frequency → AI signal.
    """
    if word_count == 0:
        return None

    text_lower = text.lower()
    count = 0
    for phrase in HEDGING_PHRASES:
        count += len(re.findall(re.escape(phrase), text_lower))

    return round((count / word_count) * 1000, 4)


def compute_sentence_initial_entropy(sentences: list[str]) -> float:
    """
    Compute Shannon entropy of sentence-starting words.

    Low entropy (repetitive starts) → AI signal.
    """
    if len(sentences) < 5:
        return None

    first_words = []
    for s in sentences:
        words = get_words(s)
        if words:
            first_words.append(words[0].lower())

    if not first_words:
        return None

    # Compute frequency distribution
    total = len(first_words)
    freq = {}
    for w in first_words:
        freq[w] = freq.get(w, 0) + 1

    # Shannon entropy
    entropy = 0.0
    for count in freq.values():
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)

    # Normalize by max possible entropy (all unique)
    max_entropy = math.log2(total) if total > 1 else 1.0
    normalized = entropy / max_entropy if max_entropy > 0 else 0.0

    return round(normalized, 4)


def compute_paragraph_length_cv(paragraphs: list[str]) -> float:
    """
    Compute coefficient of variation of paragraph sizes (in words).

    Low CV (uniform paragraphs) → AI signal.
    """
    if len(paragraphs) < 3:
        return None

    lengths = [len(get_words(p)) for p in paragraphs]
    lengths = [l for l in lengths if l > 0]

    if len(lengths) < 3:
        return None

    mean = statistics.mean(lengths)
    if mean == 0:
        return None

    stdev = statistics.stdev(lengths)
    return round(stdev / mean, 4)


def flesch_kincaid_grade(text: str) -> float:
    """
    Compute Flesch-Kincaid Grade Level for a text passage.

    FK = 0.39 * (words/sentences) + 11.8 * (syllables/words) - 15.59
    """
    words = get_words(text)
    sentences = split_sentences(text)

    if not words or not sentences:
        return None

    word_count = len(words)
    sentence_count = len(sentences)
    syllable_count = sum(count_syllables(w) for w in words)

    grade = (0.39 * (word_count / sentence_count) +
             11.8 * (syllable_count / word_count) - 15.59)

    return round(grade, 2)


def compute_readability_variance(paragraphs: list[str]) -> float:
    """
    Compute standard deviation of Flesch-Kincaid grades across paragraphs.

    Low variance (uniform readability) → AI signal.
    """
    if len(paragraphs) < 3:
        return None

    grades = []
    for p in paragraphs:
        grade = flesch_kincaid_grade(p)
        if grade is not None:
            grades.append(grade)

    if len(grades) < 3:
        return None

    return round(statistics.stdev(grades), 4)


def compute_transition_frequency(text: str, word_count: int) -> float:
    """
    Count formal transition words/phrases per 1,000 words.

    High frequency → AI signal.
    """
    if word_count == 0:
        return None

    text_lower = text.lower()
    count = 0
    for phrase in TRANSITION_WORDS:
        # Use word boundaries for single words, looser match for phrases
        if ' ' in phrase:
            count += len(re.findall(re.escape(phrase), text_lower))
        else:
            count += len(re.findall(r'\b' + re.escape(phrase) + r'\b', text_lower))

    return round((count / word_count) * 1000, 4)


def metric_to_ai_probability(metric_name: str, value: float) -> float:
    """
    Convert a raw metric value to an AI probability signal (0.0-1.0).

    Uses empirically-informed thresholds for each metric.
    """
    if value is None:
        return 0.5  # neutral when no data

    if metric_name == "burstiness":
        # Low CV → AI. Human: 0.5-1.0+, AI: 0.15-0.35
        if value >= 0.7:
            return 0.1  # very human-like
        elif value >= 0.5:
            return 0.3
        elif value >= 0.35:
            return 0.5
        elif value >= 0.2:
            return 0.7
        else:
            return 0.9  # very uniform → AI

    elif metric_name == "ttr":
        # High TTR without slang → AI. Human: 0.4-0.65, AI: 0.6-0.8+
        if value >= 0.8:
            return 0.8
        elif value >= 0.7:
            return 0.65
        elif value >= 0.6:
            return 0.5
        elif value >= 0.45:
            return 0.3
        else:
            return 0.2  # low vocabulary diversity → human casual

    elif metric_name == "hedging":
        # High hedging per 1K words → AI. Human: 0-3, AI: 5-15+
        if value >= 12:
            return 0.9
        elif value >= 8:
            return 0.75
        elif value >= 5:
            return 0.6
        elif value >= 3:
            return 0.4
        else:
            return 0.15

    elif metric_name == "sentence_entropy":
        # Low entropy → AI. Human: 0.7-0.95, AI: 0.4-0.65
        if value >= 0.85:
            return 0.1
        elif value >= 0.7:
            return 0.3
        elif value >= 0.55:
            return 0.5
        elif value >= 0.4:
            return 0.7
        else:
            return 0.85

    elif metric_name == "paragraph_cv":
        # Low CV → AI. Human: 0.4-0.8+, AI: 0.1-0.3
        if value >= 0.6:
            return 0.15
        elif value >= 0.4:
            return 0.3
        elif value >= 0.25:
            return 0.55
        elif value >= 0.15:
            return 0.75
        else:
            return 0.85

    elif metric_name == "readability_variance":
        # Low variance → AI. Human: 2.0-5.0+, AI: 0.5-1.5
        if value >= 4.0:
            return 0.1
        elif value >= 2.5:
            return 0.25
        elif value >= 1.5:
            return 0.5
        elif value >= 0.8:
            return 0.7
        else:
            return 0.85

    elif metric_name == "transition_frequency":
        # High frequency → AI. Human: 2-8, AI: 10-20+
        if value >= 18:
            return 0.9
        elif value >= 12:
            return 0.7
        elif value >= 8:
            return 0.5
        elif value >= 4:
            return 0.3
        else:
            return 0.15

    return 0.5


def compute_composite_probability(metrics: dict) -> float:
    """
    Compute weighted composite AI probability from individual metrics.
    """
    metric_map = {
        "burstiness": metrics.get("burstiness_score"),
        "ttr": metrics.get("type_token_ratio"),
        "hedging": metrics.get("hedging_frequency_per_1k"),
        "sentence_entropy": metrics.get("sentence_initial_entropy"),
        "paragraph_cv": metrics.get("paragraph_length_cv"),
        "readability_variance": metrics.get("readability_variance"),
        "transition_frequency": metrics.get("transition_frequency_per_1k"),
    }

    total_weight = 0.0
    weighted_sum = 0.0

    for key, weight in COMPOSITE_WEIGHTS.items():
        value = metric_map.get(key)
        if value is not None:
            prob = metric_to_ai_probability(key, value)
            weighted_sum += prob * weight
            total_weight += weight

    if total_weight == 0:
        return 0.5

    return round(weighted_sum / total_weight, 4)


def analyze_text(text: str, min_words: int = DEFAULT_MIN_WORDS) -> dict:
    """
    Run full forensic analysis on text content.

    Returns dict with all metrics + composite AI probability.
    """
    words = get_words(text)
    word_count = len(words)

    if word_count < min_words:
        return {
            "insufficient_text": True,
            "word_count": word_count,
            "min_words_required": min_words,
            "burstiness_score": None,
            "type_token_ratio": None,
            "hedging_frequency_per_1k": None,
            "sentence_initial_entropy": None,
            "paragraph_length_cv": None,
            "readability_variance": None,
            "transition_frequency_per_1k": None,
            "composite_ai_probability": None,
            "caveat": "Insufficient text for reliable analysis.",
        }

    sentences = split_sentences(text)
    paragraphs = split_paragraphs(text)

    burstiness = compute_burstiness(sentences)
    ttr = compute_windowed_ttr(words)
    hedging = compute_hedging_frequency(text, word_count)
    sentence_entropy = compute_sentence_initial_entropy(sentences)
    paragraph_cv = compute_paragraph_length_cv(paragraphs)
    readability_var = compute_readability_variance(paragraphs)
    transition_freq = compute_transition_frequency(text, word_count)

    metrics = {
        "insufficient_text": False,
        "word_count": word_count,
        "sentence_count": len(sentences),
        "paragraph_count": len(paragraphs),
        "burstiness_score": burstiness,
        "type_token_ratio": ttr,
        "hedging_frequency_per_1k": hedging,
        "sentence_initial_entropy": sentence_entropy,
        "paragraph_length_cv": paragraph_cv,
        "readability_variance": readability_var,
        "transition_frequency_per_1k": transition_freq,
    }

    composite = compute_composite_probability(metrics)
    metrics["composite_ai_probability"] = composite

    # Add individual metric AI signals for transparency
    metrics["metric_signals"] = {
        "burstiness": metric_to_ai_probability("burstiness", burstiness),
        "ttr": metric_to_ai_probability("ttr", ttr),
        "hedging": metric_to_ai_probability("hedging", hedging),
        "sentence_entropy": metric_to_ai_probability("sentence_entropy", sentence_entropy),
        "paragraph_cv": metric_to_ai_probability("paragraph_cv", paragraph_cv),
        "readability_variance": metric_to_ai_probability("readability_variance", readability_var),
        "transition_frequency": metric_to_ai_probability("transition_frequency", transition_freq),
    }

    metrics["caveat"] = (
        "AI detection is inherently uncertain. These statistical metrics provide "
        "probabilistic signals, not definitive proof. Skilled human writers may "
        "exhibit AI-like patterns, and AI text may be edited to appear human-written. "
        "Use as one input among many, not as a sole determination."
    )

    return metrics


def extract_text_from_payload(payload: dict) -> str:
    """Extract analyzable text from a Themis payload JSON."""
    content_type = payload.get("content_type", "video")

    if content_type == "text":
        # Text content: concatenate sections
        sections = payload.get("sections", [])
        if sections:
            parts = []
            for section in sections:
                if isinstance(section, dict):
                    heading = section.get("heading", "")
                    content = section.get("content", "")
                    if heading:
                        parts.append(heading)
                    if content:
                        parts.append(content)
                elif isinstance(section, str):
                    parts.append(section)
            return "\n\n".join(parts)

        # Fallback: check for raw text field
        if "text" in payload:
            return payload["text"]

    # Video content or fallback: use transcript
    transcript = payload.get("transcript", {})
    if isinstance(transcript, dict):
        return transcript.get("text", "")
    elif isinstance(transcript, str):
        return transcript

    return ""


def main():
    parser = argparse.ArgumentParser(
        description="Statistical text forensics for AI content detection"
    )
    parser.add_argument(
        "payload",
        nargs="?",
        help="Path to Themis payload JSON"
    )
    parser.add_argument(
        "--text-file",
        help="Convenience mode: analyze a raw text file directly"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file path (default: stdout)"
    )
    parser.add_argument(
        "--min-words",
        type=int,
        default=DEFAULT_MIN_WORDS,
        help=f"Minimum word count for analysis (default: {DEFAULT_MIN_WORDS})"
    )
    args = parser.parse_args()

    if args.text_file:
        with open(args.text_file) as f:
            text = f.read()
    elif args.payload:
        with open(args.payload) as f:
            payload = json.load(f)
        text = extract_text_from_payload(payload)
    else:
        parser.error("Either payload path or --text-file is required")
        return

    result = analyze_text(text, min_words=args.min_words)

    output_json = json.dumps(result, indent=2)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(output_json)
            f.write('\n')
        print(f"Forensics output written to {args.output}", file=sys.stderr)
    else:
        print(output_json)


if __name__ == "__main__":
    main()
