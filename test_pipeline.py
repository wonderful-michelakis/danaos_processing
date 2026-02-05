"""
Test Pipeline Installation
Quick test to verify all components are working
"""

import sys
from pathlib import Path


def test_imports():
    """Test that all required packages are installed"""
    print("Testing imports...")

    try:
        import docling
        print("  ✓ docling")
    except ImportError as e:
        print(f"  ✗ docling - {e}")
        return False

    try:
        from openai import OpenAI
        print("  ✓ openai")
    except ImportError as e:
        print(f"  ✗ openai - {e}")
        return False

    try:
        import yaml
        print("  ✓ pyyaml")
    except ImportError as e:
        print(f"  ✗ pyyaml - {e}")
        return False

    try:
        from PIL import Image
        print("  ✓ Pillow")
    except ImportError as e:
        print(f"  ✗ Pillow - {e}")
        return False

    try:
        from dotenv import load_dotenv
        print("  ✓ python-dotenv")
    except ImportError as e:
        print(f"  ✗ python-dotenv - {e}")
        return False

    return True


def test_env():
    """Test that environment is configured"""
    print("\nTesting environment...")

    from dotenv import load_dotenv
    import os

    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        print(f"  ✓ OPENAI_API_KEY found (length: {len(api_key)})")
        return True
    else:
        print("  ✗ OPENAI_API_KEY not found")
        print("\n    Please create a .env file with:")
        print("    OPENAI_API_KEY=sk-your-key-here")
        return False


def test_pipeline():
    """Test that pipeline modules load"""
    print("\nTesting pipeline modules...")

    try:
        from pipeline_config import PipelineConfig
        print("  ✓ pipeline_config")
    except ImportError as e:
        print(f"  ✗ pipeline_config - {e}")
        return False

    try:
        from entity_classifier import EntityClassifier
        print("  ✓ entity_classifier")
    except ImportError as e:
        print(f"  ✗ entity_classifier - {e}")
        return False

    try:
        from entity_processor import EntityProcessor
        print("  ✓ entity_processor")
    except ImportError as e:
        print(f"  ✗ entity_processor - {e}")
        return False

    try:
        from document_pipeline import DocumentPipeline
        print("  ✓ document_pipeline")
    except ImportError as e:
        print(f"  ✗ document_pipeline - {e}")
        return False

    return True


def test_pipeline_init():
    """Test that pipeline can be initialized"""
    print("\nTesting pipeline initialization...")

    try:
        from document_pipeline import DocumentPipeline

        pipeline = DocumentPipeline()
        print("  ✓ Pipeline initialized successfully")
        return True

    except Exception as e:
        print(f"  ✗ Pipeline initialization failed: {e}")
        return False


def check_pdfs():
    """Check for available PDF files"""
    print("\nChecking for PDF files...")

    pdf_files = list(Path(".").glob("*.pdf"))

    if pdf_files:
        print(f"  ✓ Found {len(pdf_files)} PDF file(s):")
        for pdf in pdf_files[:5]:  # Show first 5
            print(f"    - {pdf.name}")
        if len(pdf_files) > 5:
            print(f"    ... and {len(pdf_files) - 5} more")
        return True
    else:
        print("  ℹ No PDF files found in current directory")
        print("    (This is OK - you can specify a path when running)")
        return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("Document Processing Pipeline - Installation Test")
    print("=" * 60)
    print()

    results = []

    # Test imports
    results.append(("Imports", test_imports()))

    # Test environment
    results.append(("Environment", test_env()))

    # Test pipeline modules
    results.append(("Pipeline Modules", test_pipeline()))

    # Test pipeline initialization
    if results[-1][1]:  # Only if modules loaded
        results.append(("Pipeline Init", test_pipeline_init()))

    # Check for PDFs
    check_pdfs()

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {test_name}")
        if not passed:
            all_passed = False

    print()

    if all_passed:
        print("🎉 All tests passed! Pipeline is ready to use.")
        print()
        print("Next steps:")
        print("  1. Process a document:")
        print("     python run_pipeline.py document.pdf")
        print()
        print("  2. Or try the example:")
        print("     python process.py")
        print()
        return 0
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        print()
        print("Common fixes:")
        print("  - Install dependencies: pip install -r requirements.txt")
        print("  - Set API key: Create .env file with OPENAI_API_KEY")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
