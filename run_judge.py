"""
Run Document Normalization Judge

Post-processing step that uses an LLM to validate and correct
the assembled final_document.md.

Usage:
    python run_judge.py outputs/p4_10/
    python run_judge.py outputs/p4_10/ --model gpt-4o-mini
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv
from src.pipeline.document_judge import DocumentJudge


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Run LLM judge on final_document.md to validate and correct"
    )
    parser.add_argument(
        "output_dir",
        help="Path to output directory containing final_document.md"
    )
    parser.add_argument(
        "--model",
        default="gpt-4o",
        help="OpenAI model to use (default: gpt-4o)"
    )

    args = parser.parse_args()
    output_dir = Path(args.output_dir)

    if not output_dir.exists():
        print(f"Error: Directory not found: {output_dir}")
        sys.exit(1)

    if not (output_dir / "final_document.md").exists():
        print(f"Error: final_document.md not found in {output_dir}")
        print(f"Run the pipeline first: python run_pipeline.py <pdf_file>")
        sys.exit(1)

    try:
        judge = DocumentJudge(output_dir, model=args.model)
        output_path = judge.run()
        print(f"\nNext step: Generate HTML from judged document:")
        print(f"  python convert_to_friendly.py {output_path}")
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
