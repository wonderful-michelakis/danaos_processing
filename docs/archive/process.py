"""
Document Processing - Example Usage
Demonstrates how to use the document processing pipeline
"""

from pathlib import Path
from dotenv import load_dotenv
from document_pipeline import DocumentPipeline


def main():
    """Process a document using the pipeline"""

    # Load environment variables
    load_dotenv()

    # Initialize pipeline
    print("Initializing pipeline...")
    pipeline = DocumentPipeline()

    # Find PDF files in current directory
    pdf_files = list(Path(".").glob("*.pdf"))

    if not pdf_files:
        print("No PDF files found in current directory")
        return

    # Process first PDF found
    pdf_path = pdf_files[0]
    print(f"\nProcessing: {pdf_path}")
    print("-" * 60)

    try:
        # Process the document
        final_doc = pipeline.process_document(
            pdf_path=pdf_path,
            output_dir="output"
        )

        print("\n" + "=" * 60)
        print("Processing completed successfully!")
        print("=" * 60)
        print(f"\nFinal document: {final_doc}")
        print("\nOutput structure:")
        print("  output/")
        print("  ├── entities/         # Individual entity files")
        print("  ├── final_document.md # Complete assembled document")
        print("  └── manifest.yaml     # Processing metadata")

        # Show some statistics
        manifest_path = Path("output/manifest.yaml")
        if manifest_path.exists():
            import yaml
            with open(manifest_path) as f:
                manifest = yaml.safe_load(f)

            print("\nProcessing Statistics:")
            print(f"  Total entities: {manifest['total_entities']}")
            print("  Entity types:")
            for entity_type, count in manifest['entity_type_counts'].items():
                print(f"    - {entity_type}: {count}")

    except Exception as e:
        print(f"\nError processing document: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
