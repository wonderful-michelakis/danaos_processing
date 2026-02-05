# Quick Start Guide

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file with your OpenAI API key
echo "OPENAI_API_KEY=sk-your-key-here" > .env
```

## Basic Usage

### Process a Single Document

```bash
python run_pipeline.py document.pdf
```

Output will be in `output/` directory:
- `entities/` - Individual entity files
- `final_document.md` - Complete assembled document
- `manifest.yaml` - Processing metadata

### Process with Custom Output Directory

```bash
python run_pipeline.py document.pdf my_output/
```

### Programmatic Usage

```python
from document_pipeline import DocumentPipeline

# Initialize
pipeline = DocumentPipeline()

# Process
final_doc = pipeline.process_document("document.pdf", "output")

print(f"Done! Final document: {final_doc}")
```

## Understanding the Output

### 1. Entity Files (`output/entities/`)

Each entity is saved as a separate file:

- `E001_text.md` - Text content in Markdown
- `E002_table.yaml` - Table data in YAML
- `E003_diagram.mmd` - Diagram in Mermaid syntax

**Entity naming:** `E{number}_{type}.{ext}`

### 2. Final Document (`output/final_document.md`)

Complete document with all entities in original order, with markers:

```markdown
<!-- Entity: E001 | Type: text | Page: 1 -->
## Section Title
...

<!-- Entity: E002 | Type: table | Page: 2 -->
```yaml
table_data:
  - row1...
```
```

### 3. Manifest (`output/manifest.yaml`)

Processing metadata:

```yaml
source_document: "document.pdf"
total_entities: 15
entity_type_counts:
  text: 8
  table: 4
  diagram: 2
  image_text: 1
entities:
  - id: E001
    type: text
    page: 1
    confidence: 1.0
    file: "entities/E001_text.md"
```

## Common Use Cases

### Extract Only Tables

```python
import yaml

# Read manifest
with open('output/manifest.yaml') as f:
    manifest = yaml.safe_load(f)

# Find table entities
tables = [e for e in manifest['entities'] if e['type'] == 'table']

# Read each table
for table in tables:
    with open(f"output/{table['file']}") as f:
        table_data = yaml.safe_load(f)
        print(f"Table {table['id']}: {table_data}")
```

### Extract Only Diagrams

```python
from pathlib import Path

# Find all Mermaid files
diagrams = Path("output/entities").glob("*.mmd")

for diagram in diagrams:
    print(f"\n{diagram.name}:")
    print(diagram.read_text())
```

### Get Low-Confidence Entities for Review

```python
import yaml

with open('output/manifest.yaml') as f:
    manifest = yaml.safe_load(f)

# Find entities with confidence < 0.8
review_needed = [
    e for e in manifest['entities']
    if e.get('confidence', 1.0) < 0.8
]

print(f"Review needed for {len(review_needed)} entities:")
for entity in review_needed:
    print(f"  - {entity['id']} ({entity['type']}): {entity['confidence']:.2f}")
```

### Load Full Document for LLM

```python
# Read final assembled document
with open('output/final_document.md') as f:
    full_document = f.read()

# Send to LLM
response = llm.complete(
    f"Based on this document:\n\n{full_document}\n\nAnswer: ..."
)
```

### Search Across Entities

```python
from pathlib import Path

def search_entities(keyword):
    results = []
    entity_files = Path("output/entities").glob("*")

    for file in entity_files:
        content = file.read_text()
        if keyword.lower() in content.lower():
            results.append(file.name)

    return results

# Find all entities mentioning "emergency"
matches = search_entities("emergency")
print(f"Found '{keyword}' in: {matches}")
```

## Configuration

Edit `pipeline_config.py` to customize:

```python
# Change Vision model
VISION_MODEL = "gpt-4o"  # or "gpt-4o-mini" for lower cost

# Adjust max tokens for extraction
VISION_MAX_TOKENS = 4096

# Modify output directories
OUTPUT_DIR = "output"
ENTITIES_DIR = "output/entities"
```

## Troubleshooting

### "OpenAI API key required"

Create `.env` file:
```bash
OPENAI_API_KEY=sk-your-key-here
```

Or set environment variable:
```bash
export OPENAI_API_KEY=sk-your-key-here
python run_pipeline.py document.pdf
```

### Low Quality Extraction

Check image quality in source PDF:
- Resolution should be >= 150 DPI
- Text should be clear and readable
- Contrast should be good

View confidence scores:
```bash
cat output/manifest.yaml | grep confidence
```

### Slow Processing

For documents with many images:
- Processing time ≈ 2-5 seconds per image
- 20 images ≈ 1-2 minutes
- Large documents (50+ images) may take 5-10 minutes

Consider:
- Using `gpt-4o-mini` for faster processing (edit `pipeline_config.py`)
- Processing during off-peak hours

### Missing Entities

Check console output for errors during processing.

Verify input PDF is not corrupted:
```bash
# Try opening with another tool
open document.pdf  # macOS
xdg-open document.pdf  # Linux
```

## Examples

### Process Emergency Manual

```bash
python run_pipeline.py "All chapters - EMERGENCY PROCEDURES MANUAL_p17-21.pdf"
```

Expected output:
- ~15-20 entities
- Mix of text, tables, and possibly diagrams
- Contact tables converted to YAML
- Procedure text in Markdown

### Process Technical Documentation

```bash
python run_pipeline.py technical_spec.pdf output/tech_spec/
```

### Batch Process Multiple Documents (via shell)

```bash
for pdf in *.pdf; do
    echo "Processing $pdf..."
    python run_pipeline.py "$pdf" "output/${pdf%.pdf}/"
done
```

## Next Steps

1. **Process your first document**
   ```bash
   python run_pipeline.py your_document.pdf
   ```

2. **Review the output**
   ```bash
   cat output/manifest.yaml
   ls output/entities/
   ```

3. **Check confidence scores**
   - Low scores (< 0.8) may need manual review
   - Found in manifest.yaml and entity metadata

4. **Integrate with your system**
   - Use entity files for retrieval
   - Load final_document.md for LLM context
   - Parse manifest.yaml for metadata

## Support

For detailed information:
- [PIPELINE_README.md](PIPELINE_README.md) - Full documentation
- [PIPELINE_DESIGN.md](PIPELINE_DESIGN.md) - Architecture details
- Check `manifest.yaml` for processing metadata
- Review entity files for conversion quality
