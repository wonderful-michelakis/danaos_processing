# Quick Start Guide

## Prerequisites

- Python 3.11+
- OpenAI API key

## Installation

```bash
# 1. Clone the repository
git clone <repo-url>
cd document_processing

# 2. Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Install dependencies (uv automatically creates and manages the virtual environment)
uv sync

# 4. Configure environment
cp .env.example .env
# Edit .env and add your OpenAI API key:
#   OPENAI_API_KEY=sk-your-key-here
```

## Pipeline Overview

The pipeline has 4 steps:

```
PDF → Extract → Judge → HTML → Review & Correct
```

1. **Extract** — Parse PDF into entities (text, tables, diagrams)
2. **Judge** — LLM merges fragmented entities, fixes OCR artifacts
3. **Convert** — Generate user-friendly HTML
4. **Review** — Side-by-side comparison with click-to-edit corrections

---

## Step 1: Process a PDF

```bash
uv run python run_pipeline.py document.pdf
```

Options:
```bash
uv run python run_pipeline.py document.pdf --pages 1-10       # specific page range
uv run python run_pipeline.py document.pdf --output mydir/     # custom output dir
```

Output (in `outputs/<name>/`):
```
outputs/<name>/
├── entities/                # Individual entity files
│   ├── E001_EntityType.TEXT.md
│   ├── E002_EntityType.TABLE.yaml
│   └── E003_EntityType.DIAGRAM.mmd
├── final_document.md        # All entities assembled with markers
└── manifest.yaml            # Entity metadata and confidence scores
```

## Step 2: Run the Judge (recommended)

The judge is an LLM post-processing step that merges fragmented entities, combines repeating page headers, and fixes OCR artifacts.

```bash
uv run python run_judge.py outputs/<name>/
```

Options:
```bash
uv run python run_judge.py outputs/<name>/ --model gpt-4o-mini  # cheaper model
```

Output: `outputs/<name>/final_document_judge.md`

## Step 3: Generate HTML

```bash
# From judge output (recommended):
uv run python convert_to_friendly.py outputs/<name>/final_document_judge.md

# From regular pipeline output:
uv run python convert_to_friendly.py outputs/<name>/final_document.md
```

Output: `final_document_judge_friendly.html` or `final_document_friendly.html`

## Step 4: Review and Correct

Launch the side-by-side comparison viewer:

```bash
uv run python compare_viewer.py document.pdf outputs/<name>/final_document_judge_friendly.html
```

Options:
```bash
uv run python compare_viewer.py document.pdf outputs/<name>/final_document_judge_friendly.html --port 8080
uv run python compare_viewer.py document.pdf outputs/<name>/final_document_judge_friendly.html --no-browser
```

In the viewer:
1. **Navigate** — PDF and HTML panels sync by page
2. **Review** — Compare original vs processed content
3. **Correct** — Click any entity badge (E001, E002, etc.) to open the correction modal
4. **Edit** — Choose manual editing or AI-assisted correction
5. **Save** — Changes auto-regenerate the HTML

All corrections are tracked in `outputs/<name>/corrections.yaml`.

---

## Full Example (end-to-end)

```bash
# Process the PDF
uv run python run_pipeline.py manuals/procedures_manual.pdf

# Run the judge to normalize entities
uv run python run_judge.py outputs/procedures_manual/

# Generate HTML from the judge output
uv run python convert_to_friendly.py outputs/procedures_manual/final_document_judge.md

# Review side-by-side and make corrections
uv run python compare_viewer.py manuals/procedures_manual.pdf outputs/procedures_manual/final_document_judge_friendly.html
```

---

## Understanding the Output

### Entity Files (`outputs/<name>/entities/`)

Each entity is saved as a separate file:

- `E001_EntityType.TEXT.md` — Text content in Markdown
- `E002_EntityType.TABLE.yaml` — Table data in YAML
- `E003_EntityType.DIAGRAM.mmd` — Diagram in Mermaid syntax
- `E004_EntityType.IMAGE_TEXT.md` — Text extracted from images via Vision API

### Final Document (`outputs/<name>/final_document.md`)

Complete document with all entities in original order, with markers:

```markdown
<!-- Entity: E001 | Type: EntityType.TEXT | Page: 1 -->
## Section Title
...

<!-- Entity: E002 | Type: EntityType.TABLE | Page: 2 -->
```yaml
table_data:
  - row1...
```

### Judge Document (`outputs/<name>/final_document_judge.md`)

Normalized version where the LLM judge has:
- Merged fragmented entities (split lists, headers, paragraphs)
- Combined repeating page headers into single entities
- Fixed OCR artifacts and formatting issues

### Manifest (`outputs/<name>/manifest.yaml`)

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
    file: "entities/E001_EntityType.TEXT.md"
```

### Corrections (`outputs/<name>/corrections.yaml`)

Audit trail of all corrections made in the comparison viewer:

```yaml
corrections:
  E015:
    correction_type: manual
    timestamp: "2026-02-05T14:30:00"
    reason: "Fixed unit conversion error"
    original_content: |
      Viscosity at 50C: Max 10.0 mm2/s
    corrected_content: |
      Viscosity at 50C: Max 10.0 cSt
```

---

## Common Use Cases

### Extract Only Tables

```python
import yaml

with open('outputs/<name>/manifest.yaml') as f:
    manifest = yaml.safe_load(f)

tables = [e for e in manifest['entities'] if 'TABLE' in str(e['type'])]

for table in tables:
    with open(f"outputs/<name>/{table['file']}") as f:
        table_data = yaml.safe_load(f)
        print(f"Table {table['id']}: {table_data}")
```

### Get Low-Confidence Entities for Review

```python
import yaml

with open('outputs/<name>/manifest.yaml') as f:
    manifest = yaml.safe_load(f)

review_needed = [
    e for e in manifest['entities']
    if e.get('confidence', 1.0) < 0.8
]

print(f"Review needed for {len(review_needed)} entities:")
for entity in review_needed:
    print(f"  - {entity['id']} ({entity['type']}): {entity['confidence']:.2f}")
```

---

## Configuration

Edit `src/pipeline/pipeline_config.py` to customize:

```python
VISION_MODEL = "gpt-4o"        # or "gpt-4o-mini" for lower cost
VISION_MAX_TOKENS = 4096        # max tokens for extraction
```

Judge model:
```bash
uv run python run_judge.py outputs/<name>/ --model gpt-4o       # default, best quality
uv run python run_judge.py outputs/<name>/ --model gpt-4o-mini   # faster, cheaper
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `OPENAI_API_KEY not set` | Create `.env` with `OPENAI_API_KEY=sk-...` |
| Low quality extraction | Check image quality in source PDF |
| Judge removes all entity markers | Already handled — falls back to original content |
| Mermaid diagram shows syntax error | Regenerate HTML: `uv run python convert_to_friendly.py ...` |
| Port 5000 in use | Use `--port 8080` flag |
| Correction modal shows partial content | Make sure you're viewing the judge HTML |

---

## Next Steps

1. Process your first document with `run_pipeline.py`
2. Run the judge with `run_judge.py`
3. Generate HTML with `convert_to_friendly.py`
4. Review in the comparison viewer with `compare_viewer.py`
5. Check confidence scores in `manifest.yaml`

## Further Reading

- [Pipeline Guide](PIPELINE_README.md) — Entity formats and detailed reference
- [Pipeline Design](../architecture/PIPELINE_DESIGN.md) — Architecture and design decisions
- [Pipeline Flow](../architecture/PIPELINE_FLOW.md) — Data flow diagrams
