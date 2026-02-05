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
            "processing_notes": "Direct text extraction from Docling",
            "extraction_method": "docling",
            "has_surrounding_text": False
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
        bbox: list[float] | None = None,
        fallback_image_path: Path | None = None
    ) -> ProcessedEntity:
        """Process table with Vision API fallback for failed Docling extractions"""

        # Step 1: Primary extraction via Docling
        yaml_content = self._table_to_yaml(table_data)
        table_markdown = str(table_data) if isinstance(table_data, str) else ""

        # Step 2: Validate extraction quality
        is_valid, validation_reason = self._is_table_extraction_valid(
            yaml_content, table_markdown
        )

        # Track extraction metadata
        extraction_method = "docling"
        confidence = 1.0
        processing_notes = "Table extracted from Docling"

        # Step 3: Fallback to Vision API if validation fails
        if not is_valid and fallback_image_path:
            print(f"  Warning: Docling table extraction failed for {entity_id} ({validation_reason})")
            print(f"  Falling back to Vision API...")

            try:
                # Extract using Vision API
                yaml_content = self.classifier.extract_table(fallback_image_path)
                extraction_method = "vision_api"
                confidence = 0.85
                processing_notes = f"Docling extraction failed ({validation_reason}), used Vision API"

            except Exception as e:
                # Both methods failed - create error YAML
                yaml_content = yaml.dump({
                    "table_extraction_failed": True,
                    "error": "Both Docling and Vision API extraction failed",
                    "docling_result": validation_reason,
                    "vision_error": str(e),
                    "bbox": bbox,
                    "page": page_num
                }, default_flow_style=False)
                extraction_method = "failed"
                confidence = 0.0
                processing_notes = f"Extraction failed: {validation_reason}, Vision API error: {e}"

        # Step 4: Create metadata with extraction tracking
        metadata: EntityMetadata = {
            "entity_id": entity_id,
            "type": EntityType.TABLE,
            "source_page": page_num,
            "position": position,
            "original_bbox": bbox,
            "confidence": confidence,
            "processing_notes": processing_notes,
            "extraction_method": extraction_method,
            "has_surrounding_text": False
        }

        return ProcessedEntity(
            metadata=metadata,
            content=yaml_content,
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
        """Process an image and convert to appropriate format, extracting all content"""

        # Step 1: Classify image
        entity_type, confidence, classification = self.classifier.classify_image(image_path)

        surrounding_text = ""
        primary_content = ""

        # Step 2: Extract based on classification
        if entity_type == EntityType.MIXED:
            # Extract both text and primary content
            primary = classification.get('primary_content', 'diagram')
            mixed_result = self.classifier.extract_mixed_content(image_path, primary)

            surrounding_text = mixed_result.get('surrounding_text', '').strip()
            primary_content = mixed_result.get('primary_content', '').strip()

            # Set final type based on primary content
            entity_type = EntityType.DIAGRAM if primary == 'diagram' else EntityType.TABLE

        elif entity_type == EntityType.DIAGRAM:
            # Check for surrounding text significance
            text_significance = classification.get('text_significance', 'none')

            if text_significance in ['high', 'medium']:
                # Use mixed extraction to get both
                mixed_result = self.classifier.extract_mixed_content(image_path, 'diagram')
                surrounding_text = mixed_result.get('surrounding_text', '').strip()
                primary_content = mixed_result.get('primary_content', '').strip()
            else:
                # Standard diagram extraction (now returns JSON)
                diagram_result = self.classifier.extract_diagram(image_path)
                if isinstance(diagram_result, dict):
                    primary_content = diagram_result.get('diagram', '')
                    surrounding_text = diagram_result.get('surrounding_text', '')
                else:
                    primary_content = diagram_result

        elif entity_type == EntityType.TABLE:
            # Similar logic for tables
            text_significance = classification.get('text_significance', 'none')

            if text_significance in ['high', 'medium']:
                mixed_result = self.classifier.extract_mixed_content(image_path, 'table')
                surrounding_text = mixed_result.get('surrounding_text', '').strip()
                primary_content = mixed_result.get('primary_content', '').strip()
            else:
                primary_content = self.classifier.extract_table(image_path)

        else:  # TEXT or IMAGE_TEXT
            primary_content = self.classifier.extract_text(image_path)
            entity_type = EntityType.IMAGE_TEXT

        # Step 3: Combine content if we have both
        if surrounding_text and primary_content:
            content = f"{surrounding_text}\n\n{primary_content}"
            classification["note"] = "Contains surrounding text and structured content"
        else:
            content = primary_content or surrounding_text

        # Step 4: Create metadata
        metadata: EntityMetadata = {
            "entity_id": entity_id,
            "type": entity_type,
            "source_page": page_num,
            "position": position,
            "original_bbox": bbox,
            "confidence": confidence,
            "processing_notes": f"Image classification: {classification.get('description', 'N/A')}",
            "extraction_method": "vision_api",
            "has_surrounding_text": bool(surrounding_text)
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

    def _is_table_extraction_valid(self, yaml_content: str, table_markdown: str) -> tuple[bool, str]:
        """
        Validate table extraction quality.

        Returns:
            tuple[bool, str]: (is_valid, failure_reason)
        """
        # Check 1: Empty markdown
        if not table_markdown or not table_markdown.strip():
            return False, "Empty markdown output"

        # Check 2: Parse YAML and validate structure
        try:
            data = yaml.safe_load(yaml_content)
            if not isinstance(data, dict):
                return False, "Invalid YAML structure"

            table_data = data.get('table', [])

            # Check 3: Empty table array
            if not table_data:
                return False, "Empty table array"

            # Check 4: Minimum data requirement (at least 1 row with 2+ columns)
            if len(table_data) < 1:
                return False, "No data rows"

            if isinstance(table_data, list) and len(table_data) > 0:
                first_row = table_data[0]
                if isinstance(first_row, dict) and len(first_row) >= 2:
                    return True, "Valid table"
                return False, "Insufficient columns"

            return False, "Invalid table structure"

        except yaml.YAMLError as e:
            return False, f"YAML parse error: {e}"

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
            # Check if content has surrounding text (text before diagram)
            if entity.metadata.get('has_surrounding_text'):
                parts = entity.content.split('\n\n', 1)
                if len(parts) == 2:
                    text_part, diagram_part = parts
                    # Add surrounding text as comments
                    full_content = f"%% Metadata\n%% {frontmatter.replace(chr(10), chr(10) + '%% ')}\n\n"
                    full_content += f"%% Surrounding Text:\n%% {text_part.replace(chr(10), chr(10) + '%% ')}\n\n"
                    full_content += diagram_part
                else:
                    full_content = f"%% Metadata\n%% {frontmatter.replace(chr(10), chr(10) + '%% ')}\n\n{entity.content}"
            else:
                # Standard Mermaid file (no surrounding text)
                full_content = f"%% Metadata\n%% {frontmatter.replace(chr(10), chr(10) + '%% ')}\n\n{entity.content}"
        else:
            # For markdown files, use proper frontmatter
            full_content = f"---\n{frontmatter}---\n\n{entity.content}"

        # Write file
        filepath.write_text(full_content, encoding='utf-8')

        return filepath
