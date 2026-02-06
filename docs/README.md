# Documentation Index

Complete documentation for the Document Processing Pipeline.

## User Guides

- **[Quick Start](guides/QUICK_START.md)** — Setup and first run
- **[Pipeline Guide](guides/PIPELINE_README.md)** — Entity formats, output structure, configuration

## Architecture

- **[Pipeline Design](architecture/PIPELINE_DESIGN.md)** — Architecture and design decisions
- **[Pipeline Flow](architecture/PIPELINE_FLOW.md)** — Data flow and processing steps
- **[Pipeline Diagram](architecture/PIPELINE_DIAGRAM.md)** — Visual system diagrams

## Development

- **[Answers](development/ANSWERS.md)** — Design decisions and Q&A
- **[Fixes Complete](development/FIXES_COMPLETE.md)** — Changelog of major fixes

## Archive

- [Archived Files](archive/) — Deprecated scripts

## Quick Reference

```bash
# 1. Process PDF → entities
uv run python run_pipeline.py document.pdf

# 2. Run judge (normalize & merge entities)
uv run python run_judge.py outputs/<name>/

# 3. Generate HTML
uv run python convert_to_friendly.py outputs/<name>/final_document_judge.md

# 4. Launch comparison viewer
uv run python compare_viewer.py document.pdf outputs/<name>/final_document_judge_friendly.html
```
