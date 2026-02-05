"""
Entity Processor
Converts document entities to standardized formats
"""

import yaml
from pathlib import Path
from typing import Any
from dataclasses import dataclass, asdict

from pipeline_config import EntityType, EntityMetadata, PipelineConfig
from entity_classifier import EntityClassifier


@dataclass
class ProcessedEntity:
    """Represents a processed document entity"""
    metadata: EntityMetadata
    content: str
    file_extension: str


class EntityProcessor:
    """Processes and converts document entities to standardized formats"""

    def __init__(self, classifier: EntityClassifier):
        self.classifier = classifier
        self.config = PipelineConfig()

    def process_text_block(
        self,
        text: str,
        entity_id: str,
        page_num: int,
        position: int,
        bbox: list[float] | None = None
    ) -> ProcessedEntity:
        """Process a text block from Docling"""

        metadata: EntityMetadata = {
            "entity_id": entity_id,
            "type": EntityType.TEXT,
            "source_page": page_num,
            "position": position,
            "original_bbox": bbox,
            "confidence": 1.0,
            "processing_notes": "Direct text extraction from Docling"
        }

        # Clean and format text as markdown
        content = self._format_text_as_markdown(text)

        return ProcessedEntity(
            metadata=metadata,
            content=content,
            file_extension=self.config.EXTENSIONS[EntityType.TEXT]
        )

    def process_table(
        self,
        table_data: Any,
        entity_id: str,
        page_num: int,
        position: int,
        bbox: list[float] | None = None
    ) -> ProcessedEntity:
        """Process a table from Docling and convert to YAML"""

        metadata: EntityMetadata = {
            "entity_id": entity_id,
            "type": EntityType.TABLE,
            "source_page": page_num,
            "position": position,
            "original_bbox": bbox,
            "confidence": 1.0,
            "processing_notes": "Table extracted from Docling"
        }

        # Convert table to YAML
        content = self._table_to_yaml(table_data)

        return ProcessedEntity(
            metadata=metadata,
            content=content,
            file_extension=self.config.EXTENSIONS[EntityType.TABLE]
        )

    def process_image(
        self,
        image_path: Path,
        entity_id: str,
        page_num: int,
        position: int,
        bbox: list[float] | None = None
    ) -> ProcessedEntity:
        """Process an image and convert to appropriate format"""

        # Classify image first
        entity_type, confidence, classification = self.classifier.classify_image(image_path)

        # Extract content based on type
        if entity_type == EntityType.TEXT or entity_type == EntityType.IMAGE_TEXT:
            content = self.classifier.extract_text(image_path)
            entity_type = EntityType.IMAGE_TEXT

        elif entity_type == EntityType.TABLE:
            content = self.classifier.extract_table(image_path)

        elif entity_type == EntityType.DIAGRAM:
            content = self.classifier.extract_diagram(image_path)

        elif entity_type == EntityType.MIXED:
            # For mixed content, extract as text and include note
            content = self.classifier.extract_text(image_path)
            entity_type = EntityType.IMAGE_TEXT
            classification["note"] = "Mixed content - extracted as text"

        else:
            # Fallback: extract as text
            content = self.classifier.extract_text(image_path)
            entity_type = EntityType.IMAGE_TEXT

        metadata: EntityMetadata = {
            "entity_id": entity_id,
            "type": entity_type,
            "source_page": page_num,
            "position": position,
            "original_bbox": bbox,
            "confidence": confidence,
            "processing_notes": f"Image classification: {classification.get('description', 'N/A')}"
        }

        return ProcessedEntity(
            metadata=metadata,
            content=content,
            file_extension=self.config.EXTENSIONS[entity_type]
        )

    def _format_text_as_markdown(self, text: str) -> str:
        """Format text block as clean markdown"""
        # Basic cleaning
        text = text.strip()

        # Preserve existing structure
        lines = text.split('\n')
        formatted_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                formatted_lines.append("")
                continue

            # Detect headings (lines that are all caps or end with :)
            if line.isupper() and len(line.split()) <= 8:
                formatted_lines.append(f"## {line.title()}")
            elif line.endswith(':') and len(line.split()) <= 8:
                formatted_lines.append(f"### {line}")
            else:
                formatted_lines.append(line)

        return '\n'.join(formatted_lines)

    def _table_to_yaml(self, table_data: Any) -> str:
        """Convert table data to YAML format"""

        # Handle different input formats
        if isinstance(table_data, str):
            # If already markdown table, parse it
            return self._markdown_table_to_yaml(table_data)

        elif isinstance(table_data, dict):
            # If structured dict, convert directly
            return yaml.dump(table_data, default_flow_style=False, allow_unicode=True, sort_keys=False)

        elif isinstance(table_data, list):
            # If list of rows
            return yaml.dump({"table_data": table_data}, default_flow_style=False, allow_unicode=True)

        else:
            # Fallback
            return yaml.dump({"data": str(table_data)}, default_flow_style=False)

    def _markdown_table_to_yaml(self, md_table: str) -> str:
        """Convert markdown table string to YAML"""
        lines = [line.strip() for line in md_table.strip().split('\n') if line.strip()]

        if len(lines) < 2:
            return yaml.dump({"table": "empty"}, default_flow_style=False)

        # Parse header
        header = [col.strip() for col in lines[0].split('|') if col.strip()]

        # Skip separator line
        data_lines = lines[2:] if len(lines) > 2 else []

        # Parse data rows
        rows = []
        for line in data_lines:
            cols = [col.strip() for col in line.split('|') if col.strip()]
            if len(cols) == len(header):
                row_dict = {header[i]: cols[i] for i in range(len(header))}
                rows.append(row_dict)

        return yaml.dump({"table": rows}, default_flow_style=False, allow_unicode=True, sort_keys=False)

    def save_entity(self, entity: ProcessedEntity, output_dir: Path) -> Path:
        """Save entity to individual file with frontmatter"""

        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        filename = f"{entity.metadata['entity_id']}_{entity.metadata['type']}{entity.file_extension}"
        filepath = output_dir / filename

        # Create content with frontmatter
        frontmatter = yaml.dump(entity.metadata, default_flow_style=False, sort_keys=False)

        if entity.file_extension == ".yaml":
            # For YAML files, add frontmatter as comment
            full_content = f"# Metadata\n# {frontmatter.replace(chr(10), chr(10) + '# ')}\n\n{entity.content}"
        elif entity.file_extension == ".mmd":
            # For Mermaid files, add as comment
            full_content = f"%% Metadata\n%% {frontmatter.replace(chr(10), chr(10) + '%% ')}\n\n{entity.content}"
        else:
            # For markdown files, use proper frontmatter
            full_content = f"---\n{frontmatter}---\n\n{entity.content}"

        # Write file
        filepath.write_text(full_content, encoding='utf-8')

        return filepath
