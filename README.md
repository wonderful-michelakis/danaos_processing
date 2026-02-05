# Document Processing Pipeline

Convert unstructured PDFs into standardized, LLM-friendly formats with no images in output.

**Text** → Markdown | **Tables** → YAML | **Diagrams** → Mermaid

---

## Quick Start

```bash
# 1. Install
pip install -r requirements.txt

# 2. Configure
echo "OPENAI_API_KEY=your-key" > .env

# 3. Test
python test_pipeline.py

# 4. Process
python run_pipeline.py document.pdf
```

---

## What It Does

Takes a PDF like this:
- Mixed text and tables
- Images with text/tables/diagrams
- Scanned content

Produces this:
```
output/
├── entities/
│   ├── E001_text.md       ← Text in Markdown
│   ├── E002_table.yaml    ← Tables in YAML
│   └── E003_diagram.mmd   ← Diagrams in Mermaid
├── final_document.md      ← All entities assembled
└── manifest.yaml          ← Metadata & confidence scores
```

**No images in output** - everything converted to text-based formats.

---

## Features

✅ **Intelligent Classification** - Vision AI determines content type
✅ **High-Quality Extraction** - Docling + OpenAI for best results
✅ **Standardized Output** - Only 3 formats (MD, YAML, Mermaid)
✅ **Quality Tracking** - Confidence scores for every entity
✅ **LLM-Optimized** - Clean, parseable, ready for retrieval
✅ **Production-Ready** - Error handling, retry logic, validation

---

## Documentation

📚 **[ANSWERS.md](ANSWERS.md)** - Direct answers to architecture questions
🚀 **[QUICK_START.md](QUICK_START.md)** - Get started in 5 minutes
🏗️ **[PIPELINE_DESIGN.md](PIPELINE_DESIGN.md)** - Complete architecture details
📖 **[PIPELINE_README.md](PIPELINE_README.md)** - Full reference guide

---

## Example Output

**Input:** Emergency procedures manual (mixed text, tables, contact info, flowcharts)

**Output entities:**
```yaml
# E002_table.yaml
vessel_contacts:
  - vessel_name: "DIMITRIS C"
    flag: "MAL"
    telephone:
      master: "+870771306882"
    email: "vsl_123@danaos.com"
```

```mermaid
# E003_diagram.mmd
graph TD
    A[Observe vessel] --> B{Communicate?}
    B -->|Yes| C[Verify status]
    B -->|No| D[Inform RCC]
```

**Final document:** All entities in original order with markers

---

## Pipeline Architecture

```
PDF → Docling → Classify → Extract → Convert → Output
                   ↓
              Vision API
           (for images only)
```

**Docling extracts:**
- Text blocks → Direct to Markdown
- PDF tables → Convert to YAML
- Images → Send to Vision API

**Vision API processes images:**
1. Classify: Text? Table? Diagram?
2. Extract based on type
3. Convert to standard format

---

## Installation

```bash
# Clone/download this repository
cd document_processing

# Install dependencies
pip install -r requirements.txt

# Set up OpenAI API key
echo "OPENAI_API_KEY=sk-your-key-here" > .env

# Verify installation
python test_pipeline.py
```

---

## Usage

### Command Line

```bash
# Basic usage
python run_pipeline.py document.pdf

# Custom output directory
python run_pipeline.py document.pdf my_output/
```

### Programmatic

```python
from document_pipeline import DocumentPipeline

pipeline = DocumentPipeline()
final_doc = pipeline.process_document("document.pdf")
```

### Load Results

```python
import yaml

# Read manifest
with open('output/manifest.yaml') as f:
    manifest = yaml.safe_load(f)

# Get all tables
tables = [e for e in manifest['entities'] if e['type'] == 'table']

# Read final document for LLM
with open('output/final_document.md') as f:
    context = f.read()
```

---

## Configuration

Edit `pipeline_config.py`:

```python
# Vision model
VISION_MODEL = "gpt-4o"  # or "gpt-4o-mini"

# Max tokens for extraction
VISION_MAX_TOKENS = 4096

# Output directories
OUTPUT_DIR = "output"
```

---

## Quality Assurance

Every entity includes confidence score and metadata:

```yaml
entity_id: E002
type: table
source_page: 2
confidence: 0.88  # ← Check this!
processing_notes: "Image classification: Contact table"
```

**Review entities with confidence < 0.8**

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "API key required" | Create `.env` with `OPENAI_API_KEY=...` |
| Low quality extraction | Check image quality in source PDF |
| Slow processing | Normal: ~2-5 sec per image |
| Missing entities | Check console output for errors |

See [QUICK_START.md](QUICK_START.md#troubleshooting) for details.

---

## Cost Estimate

Approximate OpenAI API costs:
- Small doc (< 10 images): $0.10 - $0.50
- Medium doc (10-50 images): $0.50 - $2.00
- Large doc (> 50 images): $2.00+

Using `gpt-4o` model (best quality/cost balance).

---

## Limitations

- Does not preserve exact visual layout
- Complex diagrams (50+ nodes) may simplify
- Handwritten text recognition limited
- Processing is sequential (not parallel yet)

See [PIPELINE_DESIGN.md](PIPELINE_DESIGN.md#pitfalls) for details and solutions.

---

## Project Structure

```
document_processing/
├── pipeline_config.py       # Configuration
├── entity_classifier.py     # Vision API classification
├── entity_processor.py      # Format conversion
├── document_pipeline.py     # Main orchestrator
├── run_pipeline.py          # CLI interface
├── test_pipeline.py         # Installation test
└── docs/
    ├── ANSWERS.md           # Architecture Q&A
    ├── QUICK_START.md       # Quick reference
    ├── PIPELINE_DESIGN.md   # Detailed design
    └── PIPELINE_README.md   # Full documentation
```

---

## Next Steps

1. **Test installation:**
   ```bash
   python test_pipeline.py
   ```

2. **Process sample document:**
   ```bash
   python run_pipeline.py "All chapters - EMERGENCY PROCEDURES MANUAL_p17-21.pdf"
   ```

3. **Review outputs:**
   ```bash
   cat output/manifest.yaml
   ls output/entities/
   ```

4. **Integrate with your system**

---

## Support

- Check `manifest.yaml` for processing details
- Review entity files for conversion quality
- Examine console output for errors
- Read documentation files for detailed information

---

Built with [Docling](https://github.com/DS4SD/docling) and [OpenAI](https://openai.com)
