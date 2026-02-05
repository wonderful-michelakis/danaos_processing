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

from pipeline_config import EntityType, PipelineConfig
from entity_classifier import EntityClassifier
from entity_processor import EntityProcessor, ProcessedEntity


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
        result: ConversionResult,
        page_num: int,
        bbox: list[float],
        entity_id: str,
        output_dir: Path
    ) -> Path | None:
        """Extract table region from page image using bounding box"""
        try:
            # Access page (convert 1-based to 0-based index)
            page = result.pages[page_num - 1]

            if not page.parsed_page or not page.parsed_page.image:
                return None

            # Get PIL image from ImageRef
            pil_image = page.parsed_page.image.pil_image

            # Crop using bbox coordinates [left, top, right, bottom]
            crop_box = (
                int(bbox[0]),
                int(bbox[1]),
                int(bbox[2]),
                int(bbox[3])
            )

            cropped = pil_image.crop(crop_box)
            temp_path = output_dir / f"temp_table_{entity_id}.png"
            cropped.save(temp_path)

            return temp_path

        except Exception as e:
            print(f"Warning: Failed to extract table region for {entity_id}: {e}")
            return None

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
                # Text block
                entity = self.processor.process_text_block(
                    text=item.text,
                    entity_id=entity_id,
                    page_num=page_num,
                    position=entity_counter,
                    bbox=bbox
                )
                entities.append(entity)
                entity_counter += 1

            elif isinstance(item, TableItem):
                # Step 1: Try Docling extraction
                table_md = item.export_to_markdown()

                # Step 2: Prepare fallback image if bbox available
                table_region_path = None
                if bbox:
                    table_region_path = self._extract_table_region_image(
                        result, page_num, bbox, entity_id, entities_dir
                    )

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

                # Step 4: Cleanup temp image
                if table_region_path and table_region_path.exists():
                    table_region_path.unlink()

            elif isinstance(item, PictureItem):
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

                    # Clean up temp image
                    temp_image_path.unlink()

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
