"""
Run Document Processing Pipeline
Simple script to process a single PDF document
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

from src.pipeline.document_pipeline import DocumentPipeline


def main():
    """Main entry point"""

    # Load environment variables
    load_dotenv()

    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not found in environment")
        print("Please create a .env file with your OpenAI API key")
        sys.exit(1)

    # Get PDF path from command line or use default
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        # Look for PDF files in current directory
        pdf_files = list(Path(".").glob("*.pdf"))
        if not pdf_files:
            print("ERROR: No PDF files found in current directory")
            print("Usage: python run_pipeline.py <path_to_pdf>")
            sys.exit(1)

        pdf_path = pdf_files[0]
        print(f"No PDF specified, using: {pdf_path}")

    # Get output directory from command line or use default
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"

    print("=" * 60)
    print("Document Processing Pipeline")
    print("=" * 60)
    print(f"Input:  {pdf_path}")
    print(f"Output: {output_dir}/")
    print("=" * 60)
    print()

    try:
        # Initialize pipeline
        pipeline = DocumentPipeline()

        # Process document
        final_doc_path = pipeline.process_document(pdf_path, output_dir)

        print()
        print("=" * 60)
        print("SUCCESS!")
        print("=" * 60)
        print(f"Final document: {final_doc_path}")
        print()
        print("Output structure:")
        print(f"  {output_dir}/")
        print(f"  ├── entities/          # Individual entity files")
        print(f"  ├── final_document.md  # Assembled document")
        print(f"  └── manifest.yaml      # Processing metadata")
        print()

    except Exception as e:
        print()
        print("=" * 60)
        print("ERROR!")
        print("=" * 60)
        print(f"{type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
