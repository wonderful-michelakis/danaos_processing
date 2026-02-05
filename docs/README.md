# Documentation Index

Complete documentation for the Document Processing Pipeline.

## 📚 User Guides

**Start here if you're new to the project:**

- **[Quick Start](guides/QUICK_START.md)** - Get up and running in 5 minutes
- **[Pipeline README](guides/PIPELINE_README.md)** - Complete reference guide with examples

## 🏗️ Architecture

**Understanding how the system works:**

- **[Pipeline Design](architecture/PIPELINE_DESIGN.md)** - Overall architecture and design decisions
- **[Pipeline Flow](architecture/PIPELINE_FLOW.md)** - Data flow and processing steps
- **[Pipeline Diagram](architecture/PIPELINE_DIAGRAM.md)** - Visual system diagrams

## 💻 Development

**For contributors and developers:**

- **[Answers](development/ANSWERS.md)** - Common questions and design decisions
- **[Fixes Complete](development/FIXES_COMPLETE.md)** - Changelog of major fixes

## 📂 Archive

**Deprecated code and legacy documentation:**

- [Archived Files](archive/) - Old scripts and unused code

## Quick Reference

### Main Commands

```bash
# Process PDF
python run_pipeline.py document.pdf

# Generate HTML
python convert_to_friendly.py outputs/p86_90/final_document.md

# Launch comparison viewer
python compare_viewer.py document.pdf outputs/p86_90/
```

### Project Structure

```
document_processing/
├── src/           # Source code
├── web/           # Web UI
├── outputs/       # Generated documents
├── docs/          # Documentation (you are here)
└── README.md      # Main project README
```

## Need Help?

1. Check the [Quick Start Guide](guides/QUICK_START.md)
2. Review the [Pipeline README](guides/PIPELINE_README.md)
3. Look at [Architecture Docs](architecture/) for system design
4. See [Development Notes](development/) for implementation details
