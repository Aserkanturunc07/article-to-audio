import re
import sys
import argparse
from pathlib import Path
from gtts import gTTS


def clean_text(text: str) -> str:
    """Remove URLs, markdown syntax, citations, and formatting artifacts."""
    # Remove URLs
    text = re.sub(r'https?://\S+|www\.\S+', '', text)

    # Remove markdown headers, bold, italic, code
    text = re.sub(r'#{1,6}\s*', '', text)         # ## Heading
    text = re.sub(r'\*{1,3}(.+?)\*{1,3}', r'\1', text)  # **bold** / *italic*
    text = re.sub(r'_{1,2}(.+?)_{1,2}', r'\1', text)    # __bold__ / _italic_
    text = re.sub(r'`+[^`]*`+', '', text)          # `code` / ```blocks```
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)    # ![image](url)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)  # [link text](url) → link text

    # Remove citation markers like [1], [2,3], (Author, 2020)
    text = re.sub(r'\[\d+(?:,\s*\d+)*\]', '', text)
    text = re.sub(r'\([A-Z][a-z]+(?:\s+et\s+al\.?)?,\s*\d{4}\)', '', text)

    # Remove horizontal rules
    text = re.sub(r'^[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)

    # Remove leading bullet/list markers
    text = re.sub(r'^\s*[-*+•]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)

    # Collapse multiple blank lines into one
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Strip extra whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    text = text.strip()

    return text


def article_to_audio(input_path: str, output_path, lang: str = 'en') -> None:
    input_file = Path(input_path)
    if not input_file.exists():
        print(f"Error: file not found — {input_path}", file=sys.stderr)
        sys.exit(1)

    if not output_path:
        output_path = input_file.with_suffix('.mp3').name

    raw_text = input_file.read_text(encoding='utf-8')
    print(f"Read {len(raw_text)} characters from {input_file.name}")

    cleaned = clean_text(raw_text)
    print(f"After cleanup: {len(cleaned)} characters")

    if not cleaned:
        print("Error: no text left after cleanup.", file=sys.stderr)
        sys.exit(1)

    print("Converting to audio with gTTS…")
    tts = gTTS(text=cleaned, lang=lang, slow=False)
    tts.save(output_path)
    print(f"Audio saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Convert an article text file to an MP3 audio file."
    )
    parser.add_argument('input', help='Path to the .txt article file')
    parser.add_argument(
        '-o', '--output',
        help='Output MP3 file path (default: same name as input with .mp3 extension)',
        default=None
    )
    parser.add_argument(
        '--lang',
        help='Language code for TTS, e.g. en, es, fr (default: en)',
        default='en'
    )
    args = parser.parse_args()
    article_to_audio(args.input, args.output, args.lang)


if __name__ == '__main__':
    main()
