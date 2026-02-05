"""
Pipeline Configuration
Defines output formats and entity types
"""

from enum import Enum
from typing import TypedDict, Literal

class EntityType(str, Enum):
    TEXT = "text"
    TABLE = "table"
    DIAGRAM = "diagram"
    IMAGE_TEXT = "image_text"
    FORM = "form"
    MIXED = "mixed"

class EntityMetadata(TypedDict):
    entity_id: str
    type: EntityType
    source_page: int
    position: int
    original_bbox: list[float] | None
    confidence: float | None
    processing_notes: str | None
    extraction_method: str  # "docling", "vision_api", or "failed"
    has_surrounding_text: bool  # Tracks if text extracted with diagram/table

class PipelineConfig:
    """Configuration for document processing pipeline"""

    # Output paths
    OUTPUT_DIR = "output"
    ENTITIES_DIR = "output/entities"

    # File extensions
    EXTENSIONS = {
        EntityType.TEXT: ".md",
        EntityType.TABLE: ".yaml",
        EntityType.DIAGRAM: ".mmd",
        EntityType.IMAGE_TEXT: ".md",
        EntityType.FORM: ".yaml",
        EntityType.MIXED: ".md"
    }

    # Vision API settings
    VISION_MODEL = "gpt-4o"  # Using the latest model with vision
    VISION_MAX_TOKENS = 4096

    # Image classification prompt
    CLASSIFY_PROMPT = """Analyze this image and classify its PRIMARY content type.

IMPORTANT: Pay special attention to text that appears NEAR, ABOVE, BELOW, or SURROUNDING the main content
(such as titles, captions, instructions, or explanatory text).

Content Types:
1. TEXT - Contains primarily readable text (paragraphs, lists, instructions)
2. TABLE - Contains structured data in rows/columns
3. DIAGRAM - Contains flowcharts, process diagrams, organizational charts
4. FORM - Contains a form with fields to fill
5. MIXED - Contains multiple significant content types (e.g., diagram with surrounding explanatory text, table with extensive notes)

Classification Rules:
- If the image has a diagram/table AND significant text nearby (titles, captions, instructions), classify as MIXED
- "Significant text" means 20+ words or important context (not just labels within the diagram)

Respond with JSON:
{
    "type": "TEXT|TABLE|DIAGRAM|FORM|MIXED",
    "confidence": 0.0-1.0,
    "description": "brief description",
    "has_diagram": true/false,
    "has_table": true/false,
    "has_text": true/false,
    "text_location": "above|below|surrounding|within|none",
    "text_significance": "high|medium|low|none",
    "primary_content": "text|table|diagram"
}

If has_diagram=true AND text_significance in ["high", "medium"], you MUST classify as MIXED."""

    # Extraction prompts by type
    EXTRACT_TEXT_PROMPT = """Extract ALL text from this image.
Return clean markdown with:
- Headings (use ##, ###)
- Lists (use -, *)
- Bold/italic where appropriate
- Preserve structure and hierarchy

Do not add commentary, just the extracted text."""

    EXTRACT_TABLE_PROMPT = """Extract the table from this image and convert to YAML.

Requirements:
- Use meaningful keys (not col1, col2)
- Preserve all data accurately
- Use lists for multiple rows
- Structure logically

Example output:
```yaml
contacts:
  - name: "John Doe"
    phone: "+1234567890"
    role: "Manager"
  - name: "Jane Smith"
    phone: "+0987654321"
    role: "Director"
```

Return ONLY the YAML, no markdown code blocks."""

    EXTRACT_DIAGRAM_PROMPT = """Extract the diagram/flowchart AND any surrounding text from this image.

IMPORTANT: Look for text OUTSIDE the diagram box:
- Titles or headings above the diagram
- Captions or descriptions below the diagram
- Explanatory text or instructions near the diagram

Return JSON with two fields:
{
    "surrounding_text": "All text appearing above, below, or near the diagram (empty string if none)",
    "diagram": "Mermaid syntax for the flowchart/diagram"
}

Diagram Requirements:
- Use appropriate Mermaid diagram type (graph, flowchart, sequence, etc.)
- Preserve all nodes and relationships
- Use clear, descriptive labels
- Maintain logical flow

If there is NO surrounding text, return empty string for surrounding_text (not null)."""

    # Document assembly
    ENTITY_MARKER_TEMPLATE = "<!-- Entity: {entity_id} | Type: {type} | Page: {page} -->"

    # Docling settings
    DOCLING_OPTIONS = {
        "do_table_structure": True,
        "do_ocr": True,
        "table_structure_options": {
            "do_cell_matching": True,
            "mode": "accurate"
        }
    }
