"""
PDF-HTML Comparison Viewer (CLI Entry Point)

Usage:
    python compare_viewer.py input.pdf output/final_document_friendly.html
    python compare_viewer.py input.pdf output/final_document_judge_friendly.html --port 8080
    python compare_viewer.py input.pdf output/final_document_friendly.html --no-browser
"""

from src.corrections.compare_viewer import main

if __name__ == "__main__":
    main()
