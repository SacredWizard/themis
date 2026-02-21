#!/usr/bin/env python3
"""
Preprocess text content for Themis evaluation.

Reads text files (.txt, .md, .html), extracts structure and metadata,
and outputs a structured JSON payload matching the video payload format.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path


def strip_html(html: str) -> str:
    """Convert HTML to plain text, preserving structure."""
    # Remove script and style blocks
    text = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
    # Convert headers to markdown-style
    for i in range(1, 7):
        text = re.sub(rf'<h{i}[^>]*>(.*?)</h{i}>', rf'\n{"#" * i} \1\n', text, flags=re.DOTALL | re.IGNORECASE)
    # Convert paragraphs and breaks
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<p[^>]*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)
    # Convert list items
    text = re.sub(r'<li[^>]*>(.*?)</li>', r'\n- \1', text, flags=re.DOTALL | re.IGNORECASE)
    # Convert links: keep text and URL
    text = re.sub(r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>(.*?)</a>', r'[\2](\1)', text, flags=re.DOTALL | re.IGNORECASE)
    # Convert bold/strong
    text = re.sub(r'<(b|strong)[^>]*>(.*?)</\1>', r'**\2**', text, flags=re.DOTALL | re.IGNORECASE)
    # Convert italic/em
    text = re.sub(r'<(i|em)[^>]*>(.*?)</\1>', r'*\2*', text, flags=re.DOTALL | re.IGNORECASE)
    # Strip remaining tags
    text = re.sub(r'<[^>]+>', '', text)
    # Decode common HTML entities
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&quot;', '"').replace('&#39;', "'").replace('&nbsp;', ' ')
    # Collapse multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def extract_sections(text: str) -> list[dict]:
    """Extract sections from text based on headings."""
    sections = []
    # Match markdown headings or lines that look like headings
    lines = text.split('\n')
    current_section = {"heading": "Introduction", "level": 0, "content": []}

    for line in lines:
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if heading_match:
            # Save current section if it has content
            if current_section["content"]:
                current_section["content"] = '\n'.join(current_section["content"]).strip()
                current_section["word_count"] = len(current_section["content"].split())
                sections.append(current_section)
            current_section = {
                "heading": heading_match.group(2).strip(),
                "level": len(heading_match.group(1)),
                "content": [],
            }
        else:
            current_section["content"].append(line)

    # Save last section
    if current_section["content"]:
        current_section["content"] = '\n'.join(current_section["content"]).strip()
        current_section["word_count"] = len(current_section["content"].split())
        sections.append(current_section)

    return sections


def compute_text_metadata(text: str) -> dict:
    """Compute metadata about the text content."""
    words = text.split()
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

    word_count = len(words)
    sentence_count = len(sentences)
    paragraph_count = len(paragraphs)

    # Reading time: average 238 words per minute
    reading_time_min = round(word_count / 238, 1)

    # Average sentence length
    avg_sentence_length = round(word_count / max(sentence_count, 1), 1)

    # Average paragraph length
    avg_paragraph_length = round(word_count / max(paragraph_count, 1), 1)

    return {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "paragraph_count": paragraph_count,
        "reading_time_min": reading_time_min,
        "avg_sentence_length": avg_sentence_length,
        "avg_paragraph_length": avg_paragraph_length,
    }


def extract_title(text: str, file_path: str) -> str:
    """Try to extract a title from the text content."""
    # Check for first markdown heading
    match = re.match(r'^#\s+(.+)$', text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    # Fall back to first non-empty line
    for line in text.split('\n'):
        line = line.strip()
        if line:
            return line[:200]
    # Fall back to filename
    return Path(file_path).stem


def preprocess(file_path: str, output_path: str | None = None) -> dict:
    """Run full text preprocessing pipeline and return payload."""
    file_path = os.path.abspath(file_path)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = Path(file_path).suffix.lower()
    if ext not in ('.txt', '.md', '.html', '.htm'):
        raise ValueError(f"Unsupported text format: {ext}. Supported: .txt, .md, .html")

    print(f"Preprocessing text: {file_path}")

    # 1. Read file
    with open(file_path, 'r', encoding='utf-8') as f:
        raw_text = f.read()

    # 2. Convert HTML if needed
    if ext in ('.html', '.htm'):
        print("  Converting HTML to text...")
        text = strip_html(raw_text)
    else:
        text = raw_text

    # 3. Extract metadata
    print("  Computing text metadata...")
    metadata = compute_text_metadata(text)
    print(f"  Words: {metadata['word_count']}, "
          f"Sentences: {metadata['sentence_count']}, "
          f"Reading time: {metadata['reading_time_min']} min")

    # 4. Extract title
    title = extract_title(text, file_path)
    print(f"  Title: {title[:80]}")

    # 5. Extract sections
    print("  Extracting sections...")
    sections = extract_sections(text)
    print(f"  Sections: {len(sections)}")

    # 6. Build payload (compatible with video payload structure)
    payload = {
        "source_file": os.path.basename(file_path),
        "content_type": "text",
        "metadata": {
            **metadata,
            "title": title,
            "file_format": ext.lstrip('.'),
            "file_size_bytes": os.path.getsize(file_path),
        },
        "keyframes": [],
        "keyframe_count": 0,
        "transcript": {
            "text": text,
            "segments": [],
            "language": "auto",
        },
        "sections": sections,
    }

    # 7. Save payload
    if output_path is None:
        output_path = os.path.splitext(file_path)[0] + "_payload.json"

    with open(output_path, "w") as f:
        json.dump(payload, f, indent=2)
    payload_size = os.path.getsize(output_path)
    print(f"  Payload saved: {output_path} ({payload_size:,} bytes)")

    return payload


def main():
    parser = argparse.ArgumentParser(
        description="Preprocess text content for Themis evaluation"
    )
    parser.add_argument("text_file", help="Path to text file (.txt, .md, .html)")
    parser.add_argument("-o", "--output", help="Output payload JSON path")
    args = parser.parse_args()

    try:
        preprocess(args.text_file, output_path=args.output)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
