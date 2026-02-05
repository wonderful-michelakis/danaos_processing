"""
PDF-HTML Comparison Viewer (CLI Entry Point)

Usage:
    python compare_viewer.py input.pdf output/
    python compare_viewer.py input.pdf output/ --port 8080
    python compare_viewer.py input.pdf output/ --no-browser
"""

from src.corrections.compare_viewer import main

if __name__ == "__main__":
    main()
