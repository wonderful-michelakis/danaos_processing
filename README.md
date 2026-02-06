# Document Processing Pipeline

Automated pipeline for extracting, normalizing, and converting unstructured PDF documents into clean, structured HTML — with a human-in-the-loop verification and correction interface.

**Text** → Markdown | **Tables** → YAML | **Diagrams** → Mermaid | **LLM Judge** → Normalized | **HTML** → User-Friendly

---

## Prerequisites

- Python 3.11+
- OpenAI API key (for vision classification, judge, and AI-assisted corrections)

## Setup

```bash

# 1. Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install dependencies (uv automatically creates and manages the virtual environment)
uv sync

# 3. Configure environment
cp .env.example .env
# Edit .env and add your OpenAI API key:
#   OPENAI_API_KEY=sk-your-key-here
```

### `.env` file

Create a `.env` file in the project root with:

```
OPENAI_API_KEY=sk-your-key-here
```

This key is used for:
- Vision API (image classification and extraction)
- Document Judge (entity merging and normalization)
- AI-assisted corrections in the comparison viewer

---

## Pipeline Overview

```
PDF
 │
 ├─ Step 1: Extract ──────── run_pipeline.py
 │   Docling parses PDF → entities (text, tables, images)
 │   Vision API classifies and extracts image content
 │   Output: entities/ + final_document.md + manifest.yaml
 │
 ├─ Step 2: Judge (optional) ── run_judge.py
 │   LLM merges fragmented entities (split lists, headers, etc.)
 │   Fixes OCR artifacts and formatting issues
 │   Output: final_document_judge.md
 │
 ├─ Step 3: Convert to HTML ── convert_to_friendly.py
 │   Markdown/YAML/Mermaid → styled, readable HTML
 │   Output: final_document_friendly.html (or _judge_friendly.html)
 │
 └─ Step 4: Review & Correct ── compare_viewer.py
     Side-by-side PDF vs HTML comparison
     Click entities to edit (manual or AI-assisted)
     Changes auto-regenerate HTML
     Output: corrections.yaml (audit trail)
```

---

## Usage

### Step 1: Process a PDF

```bash
uv run python run_pipeline.py document.pdf
```

Options:
```bash
uv run python run_pipeline.py document.pdf --pages 1-10     # specific page range
uv run python run_pipeline.py document.pdf --output mydir/   # custom output dir
```

**Output** (in `outputs/<name>/`):
```
outputs/<name>/
├── entities/              # Individual entity files
│   ├── E001_EntityType.TEXT.md
│   ├── E002_EntityType.TABLE.yaml
│   └── E003_EntityType.DIAGRAM.mmd
├── final_document.md      # All entities assembled with markers
└── manifest.yaml          # Entity metadata and confidence scores
```

### Step 2: Run the Judge (recommended)

The judge is an LLM post-processing step that:
- Merges fragmented entities (e.g., list items split across entities)
- Combines repeating page headers into single entities
- Fixes OCR artifacts and formatting issues
- Preserves all content — never adds or removes information

```bash
uv run python run_judge.py outputs/<name>/
```

Options:
```bash
uv run python run_judge.py outputs/<name>/ --model gpt-4o-mini  # cheaper model
```

**Output**: `outputs/<name>/final_document_judge.md`

### Step 3: Generate HTML

```bash
# From regular pipeline output:
uv run python convert_to_friendly.py outputs/<name>/final_document.md

# From judge output (recommended):
uv run python convert_to_friendly.py outputs/<name>/final_document_judge.md
```

**Output**: `final_document_friendly.html` or `final_document_judge_friendly.html`

### Step 4: Review and Correct

Launch the side-by-side comparison viewer:

```bash
# Compare original PDF with generated HTML
uv run python compare_viewer.py document.pdf outputs/<name>/final_document_judge_friendly.html

# Options
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

## Project Structure

```
document_processing/
├── src/
│   ├── pipeline/                    # Document processing pipeline
│   │   ├── pipeline_config.py       # Configuration and entity types
│   │   ├── document_pipeline.py     # Main orchestrator
│   │   ├── entity_processor.py      # Entity extraction and formatting
│   │   ├── entity_classifier.py     # Vision API classification
│   │   └── document_judge.py        # LLM judge (merging & normalization)
│   ├── converter/
│   │   └── document_converter.py    # Markdown/YAML/Mermaid → HTML
│   └── corrections/
│       ├── correction_manager.py    # Correction backend and audit trail
│       └── compare_viewer.py        # Flask server for comparison UI
├── web/
│   ├── templates/
│   │   └── compare.html             # Comparison viewer template
│   └── static/
│       ├── css/                     # Stylesheets
│       └── js/                      # Frontend logic
├── docs/                            # Documentation
│   ├── architecture/                # System design docs
│   ├── guides/                      # User guides
│   └── development/                 # Dev notes and changelogs
├── run_pipeline.py                  # CLI: Process PDF → entities
├── run_judge.py                     # CLI: LLM judge normalization
├── convert_to_friendly.py           # CLI: Generate HTML
├── compare_viewer.py                # CLI: Launch comparison viewer
├── judge_prompt.md                  # System prompt for the LLM judge
├── requirements.txt                 # Python dependencies
└── .env                             # API keys (not committed)
```

---

## How It Works

### Entity Extraction

The pipeline extracts content from PDFs into three standardized formats:

| Content Type | Output Format | Example |
|-------------|--------------|---------|
| Text / Headings | Markdown (`.md`) | Headers, paragraphs, lists |
| Tables | YAML (`.yaml`) | Data tables, forms, key-value pairs |
| Diagrams | Mermaid (`.mmd`) | Flowcharts, process diagrams |
| Image Text | Markdown (`.md`) | Text extracted from images via Vision API |

Every entity gets a unique ID (E001, E002, ...) and metadata tracked in `manifest.yaml`.

### Document Judge

The judge is an LLM-based post-processor that reads `final_document.md` and produces a normalized version. It uses `[ENTITY:EXXX]` placeholder tokens (instead of HTML comments) when communicating with the LLM to prevent marker stripping.

Key behaviors:
- **Merges** fragmented entities (split lists, headers, paragraphs)
- **Combines** repeating page headers into single entities per page
- **Formats** content according to specifications (bullets, tables, etc.)
- **Fixes** OCR artifacts and broken words
- **Never** adds or removes information

The judge prompt is configured in `judge_prompt.md` at the project root.

### Comparison Viewer

A Flask-based web app that shows the original PDF and processed HTML side-by-side:
- Synchronized page navigation
- Entity-level click-to-edit with manual or AI-assisted corrections
- Document-wide AI corrections (e.g., "fix all date formats")
- Automatic HTML regeneration after every correction
- Full audit trail in `corrections.yaml`

When viewing judge output, corrections are applied directly to `final_document_judge.md`. When viewing regular output, corrections update individual entity files and rebuild `final_document.md`.

---

## Configuration

### Pipeline Config

Edit `src/pipeline/pipeline_config.py`:

```python
VISION_MODEL = "gpt-4o"        # or "gpt-4o-mini" for lower cost
VISION_MAX_TOKENS = 4096        # max tokens for extraction
```

### Judge Model

```bash
uv run python run_judge.py outputs/<name>/ --model gpt-4o       # default, best quality
uv run python run_judge.py outputs/<name>/ --model gpt-4o-mini   # faster, cheaper
```

---

## Output Files Reference

| File | Description |
|------|-------------|
| `entities/` | Individual entity files (one per extracted element) |
| `manifest.yaml` | Entity metadata, confidence scores, file paths |
| `final_document.md` | All entities assembled with HTML comment markers |
| `final_document_judge.md` | Judge-normalized version (merged entities) |
| `final_document_friendly.html` | User-friendly HTML from pipeline output |
| `final_document_judge_friendly.html` | User-friendly HTML from judge output |
| `corrections.yaml` | Audit trail of all corrections made |

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

## Cost Estimate

Approximate OpenAI API costs per document:

| Document Size | Pipeline | Judge | Total |
|--------------|----------|-------|-------|
| Small (< 10 pages) | $0.10 - $0.50 | $0.05 - $0.10 | ~$0.50 |
| Medium (10-50 pages) | $0.50 - $2.00 | $0.10 - $0.30 | ~$2.00 |
| Large (> 50 pages) | $2.00+ | $0.30+ | ~$3.00+ |

AI-assisted corrections: ~$0.03-0.06 per correction (GPT-4o).

---

## Limitations

- Does not preserve exact visual layout (converts to structured formats)
- Complex diagrams with 50+ nodes may be simplified
- Handwritten text recognition is limited
- Processing is sequential (not parallelized)
- Judge effectiveness depends on prompt tuning for document type

---

## Documentation

- [Quick Start Guide](docs/guides/QUICK_START.md) — Get up and running
- [Pipeline Design](docs/architecture/PIPELINE_DESIGN.md) — Architecture and design decisions
- [Pipeline Guide](docs/guides/PIPELINE_README.md) — Detailed entity format reference
- [Development Notes](docs/development/) — Changelogs and implementation details

---

Built with [Docling](https://github.com/DS4SD/docling) and [OpenAI](https://openai.com)
