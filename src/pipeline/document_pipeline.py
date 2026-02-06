"""
Document Processing Pipeline
Main orchestrator for single-document processing
"""

import os
from pathlib import Path
from typing import List
import yaml
from datetime import datetime
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.datamodel.document import ConversionResult
from docling_core.types.doc import ImageRefMode, PictureItem, TableItem, TextItem
import fitz  # PyMuPDF
from PIL import Image

from .pipeline_config import EntityType, PipelineConfig
from .entity_classifier import EntityClassifier
from .entity_processor import EntityProcessor, ProcessedEntity


class DocumentPipeline:
    """Single-document processing pipeline"""

    def __init__(self, openai_api_key: str | None = None):
        """
        Initialize pipeline

        Args:
            openai_api_key: OpenAI API key for vision processing.
                           If None, will try to read from environment.
        """
        self.config = PipelineConfig()

        # Get API key
        if openai_api_key is None:
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                raise ValueError("OpenAI API key required. Set OPENAI_API_KEY env var or pass to constructor.")

        # Initialize components
        self.classifier = EntityClassifier(openai_api_key)
        self.processor = EntityProcessor(self.classifier)

        # Initialize Docling converter
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_table_structure = True
        pipeline_options.do_ocr = True
        pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE
        pipeline_options.table_structure_options.do_cell_matching = True
        pipeline_options.images_scale = 2.0
        pipeline_options.generate_page_images = True
        pipeline_options.generate_picture_images = True

        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

    def process_document(self, pdf_path: str | Path, output_dir: str | Path = "output") -> Path:
        """
        Process a single PDF document

        Args:
            pdf_path: Path to PDF file
            output_dir: Directory for output files

        Returns:
            Path to final assembled document
        """
        pdf_path = Path(pdf_path)
        output_dir = Path(output_dir)

        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        print(f"Processing document: {pdf_path.name}")

        # Create output directories
        entities_dir = output_dir / "entities"
        entities_dir.mkdir(parents=True, exist_ok=True)

        # Step 1: Convert PDF with Docling
        print("Step 1: Extracting content with Docling...")
        result = self.converter.convert(str(pdf_path))
        doc = result.document

        # Step 2: Extract entities
        print("Step 2: Extracting and classifying entities...")
        entities = self._extract_entities(doc, result, pdf_path, entities_dir)

        # Step 3: Save individual entity files
        print(f"Step 3: Saving {len(entities)} individual entity files...")
        entity_files = []
        for entity in entities:
            filepath = self.processor.save_entity(entity, entities_dir)
            entity_files.append(filepath)
            print(f"  Saved: {filepath.name}")

        # Step 4: Assemble final document
        print("Step 4: Assembling final document...")
        final_doc_path = self._assemble_final_document(
            entities,
            output_dir,
            pdf_path.name
        )

        # Step 5: Create manifest
        print("Step 5: Creating manifest...")
        self._create_manifest(entities, output_dir, pdf_path.name)

        print(f"\n✓ Processing complete!")
        print(f"  - {len(entities)} entities extracted")
        print(f"  - Entity files: {entities_dir}")
        print(f"  - Final document: {final_doc_path}")

        return final_doc_path

    def _extract_table_region_image(
        self,
        pdf_path: Path,
        page_num: int,
        bbox: list[float],
        entity_id: str,
        output_dir: Path
    ) -> Path | None:
        """Extract table region from PDF page using PyMuPDF"""
        try:
            # Open PDF with PyMuPDF
            pdf_doc = fitz.open(str(pdf_path))

            # Get page (convert 1-based to 0-based index)
            page = pdf_doc[page_num - 1]

            # Transform PDF coordinates to PyMuPDF rect
            # Docling bbox: [left, top, right, bottom] - top-left origin
            # PyMuPDF rect: (x0, y0, x1, y1) - top-left origin
            # Note: PyMuPDF uses the same coordinate system as Docling for rendering

            # Docling's top > bottom in PDF coordinate space (bottom-left origin)
            # But when rendering, we need to use page coordinate space (top-left origin)
            page_height = page.rect.height

            # Transform to page rendering coordinates
            left = bbox[0]
            top_pdf = bbox[1]  # This is in PDF coords (origin bottom-left)
            right = bbox[2]
            bottom_pdf = bbox[3]

            # Convert to rendering coordinates (origin top-left)
            top_render = page_height - top_pdf
            bottom_render = page_height - bottom_pdf

            # Ensure correct order
            if top_render > bottom_render:
                top_render, bottom_render = bottom_render, top_render

            # Create rectangle for cropping
            rect = fitz.Rect(left, top_render, right, bottom_render)

            print(f"    [DEBUG] Page size: {page.rect.width}x{page.rect.height}")
            print(f"    [DEBUG] Crop rect: {rect}")

            # Render page to pixmap at high resolution
            mat = fitz.Matrix(2, 2)  # 2x zoom for better quality
            pix = page.get_pixmap(matrix=mat, clip=rect)

            # Convert to PIL Image
            img_data = pix.tobytes("png")
            from io import BytesIO
            pil_image = Image.open(BytesIO(img_data))

            print(f"    [DEBUG] Extracted image: {pil_image.width}x{pil_image.height}")

            # Save
            temp_path = output_dir / f"temp_table_{entity_id}.png"
            pil_image.save(temp_path)
            print(f"    [DEBUG] Saved to: {temp_path}")

            pdf_doc.close()
            return temp_path

        except Exception as e:
            print(f"    [ERROR] Failed to extract table region for {entity_id}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _is_list_intro(self, text: str) -> bool:
        """Check if text introduces a list (ends with colon)"""
        text = text.strip()
        return text.endswith(':') and len(text) > 10

    def _is_list_item(self, text: str, bbox: list[float] | None, prev_bbox: list[float] | None, after_colon: bool = False) -> bool:
        """
        Detect if a text item is likely a list item

        Criteria:
        - Has indentation from left margin
        - Has list markers (-, *, •, ##, numbers)
        - Following a sentence that ends with ":"
        """
        if not text or not bbox:
            return False

        text = text.strip()

        import re

        # CRITICAL: Exclude section headers with numbers (1.2, 1.3.1, etc.)
        # Check if text starts with section number pattern (with or without ##)
        # Match: "1.2 APPLICATION", "## 1.2 APPLICATION", "## - 1.2 APPLICATION"
        if re.match(r'^#*\s*-?\s*\d+\.\d+', text):
            return False

        # Exclude sentences that look like regular text (start with "The", "This", etc.)
        # UNLESS we're after a colon (list intro)
        if not after_colon and re.match(r'^(The|This|It|A|An|In|For|To|From|Furthermore)\s+\w+', text, re.IGNORECASE):
            return False

        # Check for explicit list markers
        list_markers = ['- ', '* ', '• ', '◦ ', '▪ ', '→ ']
        if any(text.startswith(marker) for marker in list_markers):
            return True

        # Check for numbered lists (1., 2., etc.) - but not section numbers (1.1, 1.2)
        if re.match(r'^\d+\.\s', text) and not re.match(r'^\d+\.\d+', text):
            return True

        # Check for markdown headers used as list items (##)
        # But only if they don't look like section headers or regular text
        if text.startswith('##'):
            # Remove ## and check content
            content = text.replace('##', '').strip().lstrip('-').strip()
            # If it starts with a number pattern like "1.3", it's a header not a list
            if re.match(r'^\d+\.', content):
                return False
            # If it looks like regular text, not a list
            if not after_colon and re.match(r'^(The|This|It|A|An|In|For)\s+\w+', content, re.IGNORECASE):
                return False
            return True

        # Check for indented short items (likely list titles/items)
        left_indent = bbox[0]

        # If we're after a colon, be more lenient - treat indented items as list items
        if after_colon and left_indent > 70 and len(text) < 150:
            return True

        # Otherwise, standard check
        if left_indent > 85 and left_indent < 110:  # Common list indentation range
            # Short text (< 100 chars) with indentation is likely a list item
            # But exclude if it looks like a section header
            if len(text) < 100 and not re.match(r'^\d+\.\d+', text):
                return True

        return False

    def _should_merge_with_list(
        self,
        current_text: str,
        current_bbox: list[float] | None,
        list_items: list,
        page_num: int
    ) -> bool:
        """
        Determine if current item should be merged with existing list

        Criteria:
        - Same page
        - Similar indentation or is continuation
        - Close vertical proximity
        """
        if not list_items or not current_bbox:
            return False

        import re

        text = current_text.strip()

        # Check if list started with a colon (intro text)
        first_item_text = list_items[0].get('text', '').strip()
        after_colon = first_item_text.endswith(':')

        # NEVER merge these with lists:
        # 1. Section headers (1.2, 1.3.1, etc.)
        if re.match(r'^#*\s*-?\s*\d+\.\d+', text):
            return False

        # 2. Regular sentences starting with common words (UNLESS after colon)
        if not after_colon and re.match(r'^(The|This|It|A|An|In|For|To|From|Furthermore|Moreover)\s+\w+', text, re.IGNORECASE):
            return False

        last_item = list_items[-1]
        last_bbox = last_item.get('bbox')
        last_page = last_item.get('page')

        # Must be same page
        if page_num != last_page:
            return False

        # Check vertical proximity - be more lenient after colon
        if last_bbox:
            vertical_gap = abs(current_bbox[1] - last_bbox[1])
            max_gap = 40 if after_colon else 30
            if vertical_gap > max_gap:
                return False

        # Check if it's a list item (pass after_colon context)
        if self._is_list_item(current_text, current_bbox, last_bbox, after_colon):
            return True

        # Check if it's a description/continuation (more indented than list item)
        if last_bbox and current_bbox[0] > last_bbox[0] + 15:
            # Also check it's not too long (descriptions should be reasonable length)
            if len(text) < 300:
                return True

        return False

    def _merge_list_items(self, list_items: list) -> str:
        """
        Merge list items into formatted markdown list

        Handles:
        - List items with descriptions
        - Nested indentation
        - Various list markers
        """
        if not list_items:
            return ""

        merged_lines = []
        is_first = True

        for item in list_items:
            text = item['text'].strip()
            indent = item.get('bbox', [0])[0]

            # Step 1: Remove ALL markdown formatting and bullet markers
            # Remove ## markers (can be multiple)
            while text.startswith('##'):
                text = text[2:].lstrip()

            # Remove bullet markers
            if text.startswith(('-', '*', '•', '◦', '▪', '→')):
                text = text[1:].lstrip()

            # Step 2: Add clean formatting based on content type
            if len(text) > 0:
                # Special case: first item ending with ":" is an intro, don't add bullet
                if is_first and text.endswith(':'):
                    merged_lines.append(text)
                elif len(text) < 200 and indent < 120:
                    # Short text = list item
                    merged_lines.append(f"- {text}")
                else:
                    # Long text = description/continuation
                    merged_lines.append(f"  {text}")

                is_first = False

        return '\n'.join(merged_lines)

    def _extract_entities(
        self,
        doc,
        result: ConversionResult,
        pdf_path: Path,
        entities_dir: Path
    ) -> List[ProcessedEntity]:
        """Extract all entities from Docling document"""

        entities = []
        entity_counter = 1

        # Buffer for collecting list items
        list_buffer = []
        prev_bbox = None

        # Iterate through document items using Docling 2.x API
        for item, level in doc.iterate_items():

            entity_id = f"E{entity_counter:03d}"

            # Get page number and bounding box from provenance
            page_num = 1  # default
            bbox = None
            if hasattr(item, 'prov') and item.prov:
                page_num = item.prov[0].page_no
                bbox = [
                    item.prov[0].bbox.l,
                    item.prov[0].bbox.t,
                    item.prov[0].bbox.r,
                    item.prov[0].bbox.b
                ]

            # Process based on item type
            if isinstance(item, TextItem):
                text = item.text.strip()

                # Check if this should be part of a list
                is_list_intro = self._is_list_intro(text)
                is_list_item_check = self._is_list_item(text, bbox, prev_bbox)
                should_merge = self._should_merge_with_list(text, bbox, list_buffer, page_num)

                if is_list_intro or is_list_item_check or should_merge:
                    # Add to list buffer (including intro sentences ending with :)
                    list_buffer.append({
                        'text': text,
                        'bbox': bbox,
                        'page': page_num
                    })
                    prev_bbox = bbox
                else:
                    # Not a list item - flush any buffered list first
                    if list_buffer:
                        # Create merged list entity
                        merged_text = self._merge_list_items(list_buffer)
                        first_item = list_buffer[0]
                        entity = self.processor.process_text_block(
                            text=merged_text,
                            entity_id=entity_id,
                            page_num=first_item['page'],
                            position=entity_counter,
                            bbox=first_item['bbox']
                        )
                        entities.append(entity)
                        entity_counter += 1
                        entity_id = f"E{entity_counter:03d}"
                        list_buffer = []

                    # Process current item as regular text
                    entity = self.processor.process_text_block(
                        text=text,
                        entity_id=entity_id,
                        page_num=page_num,
                        position=entity_counter,
                        bbox=bbox
                    )
                    entities.append(entity)
                    entity_counter += 1
                    prev_bbox = bbox

            elif isinstance(item, TableItem):
                # Flush any buffered list items before processing table
                if list_buffer:
                    merged_text = self._merge_list_items(list_buffer)
                    first_item = list_buffer[0]
                    entity = self.processor.process_text_block(
                        text=merged_text,
                        entity_id=entity_id,
                        page_num=first_item['page'],
                        position=entity_counter,
                        bbox=first_item['bbox']
                    )
                    entities.append(entity)
                    entity_counter += 1
                    entity_id = f"E{entity_counter:03d}"
                    list_buffer = []
                    prev_bbox = None
                # Step 1: Try Docling extraction
                table_md = item.export_to_markdown()

                # Table processing
                # Step 2: Prepare fallback image if bbox available
                table_region_path = None
                if bbox:
                    print(f"  [DEBUG {entity_id}] Extracting table region with bbox: {bbox}")
                    table_region_path = self._extract_table_region_image(
                        pdf_path, page_num, bbox, entity_id, entities_dir
                    )
                    print(f"  [DEBUG {entity_id}] Table region path: {table_region_path}")
                else:
                    print(f"  [DEBUG {entity_id}] No bbox available for table region extraction")

                # Step 3: Process with fallback option
                entity = self.processor.process_table(
                    table_data=table_md,
                    entity_id=entity_id,
                    page_num=page_num,
                    position=entity_counter,
                    bbox=bbox,
                    fallback_image_path=table_region_path
                )
                entities.append(entity)
                entity_counter += 1
                prev_bbox = None  # Reset for next items

                # Step 4: Cleanup temp image
                if table_region_path and table_region_path.exists():
                    table_region_path.unlink()

            elif isinstance(item, PictureItem):
                # Flush any buffered list items before processing picture
                if list_buffer:
                    merged_text = self._merge_list_items(list_buffer)
                    first_item = list_buffer[0]
                    entity = self.processor.process_text_block(
                        text=merged_text,
                        entity_id=entity_id,
                        page_num=first_item['page'],
                        position=entity_counter,
                        bbox=first_item['bbox']
                    )
                    entities.append(entity)
                    entity_counter += 1
                    entity_id = f"E{entity_counter:03d}"
                    list_buffer = []
                    prev_bbox = None
                # Image/Picture - need to extract and process
                # Save image temporarily
                if item.image:
                    temp_image_path = entities_dir / f"temp_{entity_id}.png"
                    item.image.pil_image.save(temp_image_path)

                    # Process image with vision API
                    entity = self.processor.process_image(
                        image_path=temp_image_path,
                        entity_id=entity_id,
                        page_num=page_num,
                        position=entity_counter,
                        bbox=bbox
                    )
                    entities.append(entity)
                    entity_counter += 1
                    prev_bbox = None  # Reset for next items

                    # Clean up temp image
                    temp_image_path.unlink()

        # Flush any remaining list items at end of document
        if list_buffer:
            entity_id = f"E{entity_counter:03d}"
            merged_text = self._merge_list_items(list_buffer)
            first_item = list_buffer[0]
            entity = self.processor.process_text_block(
                text=merged_text,
                entity_id=entity_id,
                page_num=first_item['page'],
                position=entity_counter,
                bbox=first_item['bbox']
            )
            entities.append(entity)

        return entities

    def _assemble_final_document(
        self,
        entities: List[ProcessedEntity],
        output_dir: Path,
        source_filename: str
    ) -> Path:
        """Assemble all entities into final document"""

        # Create document header
        doc_title = source_filename.replace('.pdf', '').replace('_', ' ').title()

        header = f"""---
document_title: "{doc_title}"
total_entities: {len(entities)}
processed_date: "{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
source_file: "{source_filename}"
---

# Document: {doc_title}

"""

        # Assemble entities
        content_parts = [header]

        for entity in entities:
            # Add entity marker
            marker = self.config.ENTITY_MARKER_TEMPLATE.format(
                entity_id=entity.metadata['entity_id'],
                type=entity.metadata['type'],
                page=entity.metadata['source_page']
            )
            content_parts.append(f"\n{marker}\n")

            # Add entity content with appropriate formatting
            if entity.metadata['type'] == EntityType.TABLE:
                content_parts.append(f"```yaml\n{entity.content}\n```\n")

            elif entity.metadata['type'] == EntityType.DIAGRAM:
                content_parts.append(f"```mermaid\n{entity.content}\n```\n")

            else:
                # Text content
                content_parts.append(f"{entity.content}\n")

        final_content = '\n'.join(content_parts)

        # Write final document
        final_path = output_dir / "final_document.md"
        final_path.write_text(final_content, encoding='utf-8')

        return final_path

    def _create_manifest(
        self,
        entities: List[ProcessedEntity],
        output_dir: Path,
        source_filename: str
    ):
        """Create manifest file with processing metadata"""

        manifest = {
            "source_document": source_filename,
            "processed_date": datetime.now().isoformat(),
            "total_entities": len(entities),
            "entity_type_counts": {},
            "entities": []
        }

        # Count entity types
        type_counts = {}
        for entity in entities:
            entity_type = entity.metadata['type']
            type_counts[entity_type] = type_counts.get(entity_type, 0) + 1

        manifest["entity_type_counts"] = type_counts

        # Add entity info
        for entity in entities:
            manifest["entities"].append({
                "id": entity.metadata['entity_id'],
                "type": entity.metadata['type'],
                "page": entity.metadata['source_page'],
                "position": entity.metadata['position'],
                "confidence": entity.metadata.get('confidence'),
                "file": f"entities/{entity.metadata['entity_id']}_{entity.metadata['type']}{entity.file_extension}"
            })

        # Write manifest
        manifest_path = output_dir / "manifest.yaml"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)

        print(f"  Manifest saved: {manifest_path}")
