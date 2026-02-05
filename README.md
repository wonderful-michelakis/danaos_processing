# Document Processing Pipeline

Complete pipeline for extracting, processing, and converting technical PDF documents into user-friendly HTML with entity-level corrections.

**Text** → Markdown | **Tables** → YAML | **Diagrams** → Mermaid → **User-Friendly HTML**

---

## Quick Start

```bash
# 1. Process PDF document
python run_pipeline.py document.pdf

# 2. Generate user-friendly HTML
python convert_to_friendly.py outputs/p86_90/final_document.md

# 3. Launch comparison viewer (with corrections)
python compare_viewer.py document.pdf outputs/p86_90/
```

**Setup:**
```bash
pip install -r requirements.txt
echo "OPENAI_API_KEY=your-key" > .env
```

---

## Complete Workflow

### Step 1: Process Document
Extract entities (text, tables, diagrams, forms) from PDF using Docling and OpenAI vision.

```bash
python run_pipeline.py document.pdf [--pages 86-90]
```

**Output**: `outputs/p86_90/` directory with:
- `entities/` - Individual entity files (E001.md, E002.yaml, E003.mmd)
- `manifest.yaml` - Entity metadata and confidence scores
- `final_document.md` - Assembled technical document

### Step 2: Generate User-Friendly HTML
Convert technical markdown to human-readable HTML with simplified language, visual tables, and professional styling.

```bash
python convert_to_friendly.py outputs/p86_90/final_document.md
```

**Output**: `outputs/p86_90/final_document_friendly.html`

### Step 3: Compare and Correct
Launch side-by-side PDF-HTML comparison viewer with entity-level corrections.

```bash
python compare_viewer.py document.pdf outputs/p86_90/ [--port 5000] [--no-browser]
```

**Features**:
- Synchronized PDF-HTML navigation
- Click entity badges to edit
- Manual or AI-assisted corrections
- Real-time HTML regeneration
- Full audit trail in `corrections.yaml`

### Step 4: Make Corrections (Optional)
In the comparison viewer:
1. Click any entity badge (E001, E002, etc.)
2. Choose correction method:
   - **Manual Edit**: Direct text/YAML editing
   - **AI-Assisted**: Describe issue → GPT-4 generates fix
3. Save → HTML auto-regenerates with changes

**Corrections tracked in**: `outputs/p86_90/corrections.yaml`

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
✅ **User-Friendly HTML** - Simplified language with visual tables
✅ **Side-by-Side Comparison** - PDF-HTML viewer with sync navigation
✅ **Entity-Level Corrections** - Manual or AI-assisted editing
✅ **Audit Trail** - Full correction history with metadata
✅ **Quality Tracking** - Confidence scores for every entity
✅ **LLM-Optimized** - Clean, parseable, ready for retrieval
✅ **Production-Ready** - Error handling, retry logic, validation

---

## Documentation

📚 **[Complete Documentation](docs/)** - All documentation organized by category
🚀 **[Quick Start](docs/guides/QUICK_START.md)** - Get started in 5 minutes
🏗️ **[Architecture](docs/architecture/)** - System design and architecture
📖 **[User Guides](docs/guides/)** - Complete reference guides
💻 **[Development](docs/development/)** - Implementation notes and decisions

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
# Process document
python run_pipeline.py document.pdf [--pages 86-90]

# Generate friendly HTML
python convert_to_friendly.py outputs/p86_90/final_document.md

# Launch comparison viewer
python compare_viewer.py document.pdf outputs/p86_90/ [--port 5000] [--no-browser]
```

### Programmatic

```python
# Process document
from document_pipeline import DocumentPipeline
pipeline = DocumentPipeline()
final_doc = pipeline.process_document("document.pdf")

# Convert to friendly HTML
from src.converter.document_converter import DocumentConverter
converter = DocumentConverter("outputs/p86_90/final_document.md", "outputs/p86_90")
html_path = converter.convert()

# Manage corrections
from src.corrections.correction_manager import CorrectionManager
manager = CorrectionManager("outputs/p86_90")
manager.apply_correction("E002", corrected_content, "manual", "Fixed unit")
manager.regenerate_html()
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
| Comparison viewer won't load | Generate HTML first: `python convert_to_friendly.py outputs/p86_90/final_document.md` |
| Corrections not showing | Check that `corrections.yaml` was created and HTML regenerated |
| Port 5000 in use | Use `--port 8080` flag |
| Entity badge not clickable | Refresh browser or check console for JS errors |

See [Quick Start Guide](docs/guides/QUICK_START.md#troubleshooting) for details.

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

See [Pipeline Design](docs/architecture/PIPELINE_DESIGN.md#pitfalls) for details and solutions.

---

## Correction System

The correction system allows entity-level edits with full audit trail:

### How It Works
1. **Entity-level corrections**: Each entity (E001, E002, etc.) can be individually corrected
2. **Dual correction modes**: Manual editing or AI-assisted (GPT-4)
3. **Automatic propagation**:
   - Entity file updated → `final_document.md` rebuilt → HTML regenerated
4. **Audit trail**: All corrections tracked in `corrections.yaml`

### Correction Example
```yaml
# corrections.yaml
corrections:
  E002:
    correction_type: manual
    timestamp: "2026-02-05T14:30:00"
    reason: "Fixed temperature unit"
    original_content: "Viscosity at 50°C: Max 10.0 cSt"
    corrected_content: "Viscosity at 60°C: Max 10.0 cSt"
```

### Revert Corrections
- Edit `corrections.yaml` to remove correction
- Restore entity file from backup
- Regenerate: `python convert_to_friendly.py outputs/p86_90/final_document.md`

---

## Project Structure

```
document_processing/
├── src/                          # Source code
│   ├── pipeline/                 # Document processing pipeline
│   │   ├── document_pipeline.py  # Main orchestrator
│   │   ├── entity_processor.py   # Format conversion
│   │   ├── entity_classifier.py  # Vision API classification
│   │   └── pipeline_config.py    # Configuration
│   ├── converter/                # HTML conversion
│   │   └── document_converter.py # Technical → friendly HTML
│   └── corrections/              # Correction system
│       ├── correction_manager.py # Correction backend
│       └── compare_viewer.py     # Flask server
├── web/                          # Web UI
│   ├── templates/                # HTML templates
│   │   └── compare.html
│   └── static/                   # CSS/JS assets
│       ├── css/
│       │   ├── compare.css
│       │   └── correction_modal.css
│       └── js/
│           ├── compare.js
│           └── correction_modal.js
├── outputs/                      # Processed documents
│   ├── p86_90/                   # Example output
│   │   ├── entities/             # Entity files
│   │   ├── manifest.yaml         # Metadata
│   │   ├── final_document.md     # Technical doc
│   │   ├── final_document_friendly.html
│   │   └── corrections.yaml      # Corrections
│   └── p307_308/                 # Another example
├── docs/                         # Documentation
│   ├── guides/                   # User guides
│   ├── architecture/             # System design
│   ├── development/              # Dev notes
│   └── README.md                 # Documentation index
├── run_pipeline.py               # CLI: Process PDF
├── convert_to_friendly.py        # CLI: Generate HTML
├── compare_viewer.py             # CLI: Launch viewer
├── test_pipeline.py              # Installation test
├── requirements.txt
├── README.md
└── .env                          # API keys
```

---

## Next Steps

1. **Test installation:**
   ```bash
   python test_pipeline.py
   ```

2. **Process document:**
   ```bash
   python run_pipeline.py document.pdf
   ```

3. **Generate friendly HTML:**
   ```bash
   python convert_to_friendly.py outputs/p86_90/final_document.md
   ```

4. **Launch comparison viewer:**
   ```bash
   python compare_viewer.py document.pdf outputs/p86_90/
   ```

5. **Make corrections** (click entity badges in viewer)

6. **Review outputs:**
   ```bash
   cat outputs/p86_90/manifest.yaml
   cat outputs/p86_90/corrections.yaml  # If corrections made
   ```

---

## Support

- Check `manifest.yaml` for processing details
- Review entity files for conversion quality
- Examine console output for errors
- Read documentation files for detailed information

---

Built with [Docling](https://github.com/DS4SD/docling) and [OpenAI](https://openai.com)
