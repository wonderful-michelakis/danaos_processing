"""
CLI tool to convert technical markdown to user-friendly HTML

Usage:
    python convert_to_friendly.py input/final_document.md
    python convert_to_friendly.py input/final_document.md -o custom_output/
"""

import argparse
from pathlib import Path
from document_converter import DocumentConverter


def main():
    parser = argparse.ArgumentParser(
        description="Convert technical final_document.md to user-friendly HTML"
    )
    parser.add_argument(
        "input_file",
        type=str,
        help="Path to final_document.md"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output directory (default: same as input)"
    )

    args = parser.parse_args()

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        return 1

    output_dir = Path(args.output) if args.output else input_path.parent

    try:
        converter = DocumentConverter(input_path, output_dir)
        html_path = converter.convert()
        print(f"\n✓ Success! Open in browser: {html_path}")
        return 0
    except Exception as e:
        print(f"Error during conversion: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
