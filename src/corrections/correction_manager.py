"""
Correction Manager for Entity-Level Document Corrections

Handles:
- Loading and saving corrections to corrections.yaml
- Applying corrections to entity files
- Updating manifest with correction metadata
- Triggering HTML regeneration
- AI-assisted corrections via OpenAI API
"""

import os
import yaml
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Literal, Optional
from datetime import datetime


@dataclass
class CorrectionEntry:
    """Represents a single entity correction"""
    entity_id: str
    correction_type: Literal["manual", "ai"]
    original_content: str
    corrected_content: str
    reason: str
    timestamp: str
    user_prompt: Optional[str] = None  # For AI corrections


class CorrectionManager:
    """Manages document corrections with audit trail"""

    def __init__(self, output_dir: Path):
        """
        Initialize CorrectionManager

        Args:
            output_dir: Path to output directory (e.g., p86_90/)
        """
        self.output_dir = Path(output_dir)
        self.corrections_path = self.output_dir / "corrections.yaml"
        self.manifest_path = self.output_dir / "manifest.yaml"
        self.entities_dir = self.output_dir / "entities"

        # Validate paths
        if not self.output_dir.exists():
            raise FileNotFoundError(f"Output directory not found: {self.output_dir}")
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {self.manifest_path}")

    def load_corrections(self) -> dict:
        """
        Load existing corrections from corrections.yaml

        Returns:
            Dictionary of corrections by entity ID
        """
        if not self.corrections_path.exists():
            return {"corrections": {}}

        try:
            with open(self.corrections_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                return data if data else {"corrections": {}}
        except Exception as e:
            print(f"Warning: Could not load corrections: {e}")
            return {"corrections": {}}

    def save_correction(self, correction: CorrectionEntry) -> None:
        """
        Save a single correction to corrections.yaml

        Args:
            correction: CorrectionEntry to save
        """
        # Load existing corrections
        corrections_data = self.load_corrections()

        # Add new correction
        corrections_data["corrections"][correction.entity_id] = {
            "correction_type": correction.correction_type,
            "timestamp": correction.timestamp,
            "reason": correction.reason,
            "original_content": correction.original_content,
            "corrected_content": correction.corrected_content,
        }

        # Add user_prompt if AI correction
        if correction.user_prompt:
            corrections_data["corrections"][correction.entity_id]["user_prompt"] = correction.user_prompt

        # Write to file
        with open(self.corrections_path, 'w', encoding='utf-8') as f:
            yaml.dump(corrections_data, f, default_flow_style=False, allow_unicode=True)

    def get_entity_content(self, entity_id: str) -> dict:
        """
        Get entity content and metadata for editing

        Args:
            entity_id: Entity ID (e.g., "E015")

        Returns:
            Dictionary with entity_id, type, page, content, metadata
        """
        # Load manifest to get entity metadata
        # Use Loader=yaml.Loader to handle Python object tags (EntityType enums)
        with open(self.manifest_path, 'r', encoding='utf-8') as f:
            manifest = yaml.load(f, Loader=yaml.Loader)

        # Find entity in manifest
        entity_info = None
        for entity in manifest.get('entities', []):
            if entity['id'] == entity_id:
                entity_info = entity
                break

        if not entity_info:
            raise ValueError(f"Entity {entity_id} not found in manifest")

        # Get entity file path
        entity_file = self.output_dir / entity_info['file']

        if not entity_file.exists():
            raise FileNotFoundError(f"Entity file not found: {entity_file}")

        # Read entity file content
        content = self._read_entity_file(entity_file)

        # Convert EntityType enum to string if needed
        entity_type = entity_info['type']
        if hasattr(entity_type, 'name'):
            # It's an enum, get the string name
            entity_type = entity_type.name.lower()
        elif hasattr(entity_type, 'value'):
            # It's an enum with value
            entity_type = str(entity_type.value).lower()
        else:
            # Already a string
            entity_type = str(entity_type).lower()

        return {
            "entity_id": entity_id,
            "type": entity_type,
            "page": entity_info['page'],
            "content": content,
            "metadata": {
                "position": entity_info['position'],
                "confidence": entity_info.get('confidence'),
                "file": entity_info['file']
            }
        }

    def _read_entity_file(self, file_path: Path) -> str:
        """
        Read entity content from file, stripping frontmatter

        Args:
            file_path: Path to entity file

        Returns:
            Entity content without frontmatter
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Strip frontmatter (YAML/Markdown format: ---\nfrontmatter\n---\ncontent)
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                return parts[2].strip()

        # Strip frontmatter (YAML/Mermaid format: # Metadata\n# ...\n\ncontent)
        if content.startswith('# Metadata') or content.startswith('# entity_id'):
            lines = content.split('\n')
            content_lines = []
            in_frontmatter = True

            for line in lines:
                if in_frontmatter and line.startswith('#'):
                    continue
                elif in_frontmatter and line.strip() == '':
                    in_frontmatter = False
                    continue
                else:
                    content_lines.append(line)

            return '\n'.join(content_lines).strip()

        # No frontmatter found, return as-is
        return content.strip()

    def _write_entity_file(self, file_path: Path, entity_info: dict, new_content: str) -> None:
        """
        Write entity content to file with frontmatter

        Args:
            file_path: Path to entity file
            entity_info: Entity metadata dictionary
            new_content: New entity content
        """
        # Determine file format based on extension
        ext = file_path.suffix

        if ext in ['.md']:
            # Markdown format with YAML frontmatter
            frontmatter = f"""---
entity_id: {entity_info['entity_id']}
type: {entity_info['type']}
source_page: {entity_info['page']}
position: {entity_info['metadata']['position']}
confidence: {entity_info['metadata'].get('confidence', 'null')}
corrected: true
correction_timestamp: {datetime.now().isoformat()}
---

{new_content}
"""
        elif ext in ['.yaml', '.yml']:
            # YAML format with commented metadata
            frontmatter = f"""# Metadata
# entity_id: {entity_info['entity_id']}
# type: {entity_info['type']}
# source_page: {entity_info['page']}
# position: {entity_info['metadata']['position']}
# confidence: {entity_info['metadata'].get('confidence', 'null')}
# corrected: true
# correction_timestamp: {datetime.now().isoformat()}

{new_content}
"""
        elif ext in ['.mmd']:
            # Mermaid format with commented metadata
            frontmatter = f"""%% Metadata
%% entity_id: {entity_info['entity_id']}
%% type: {entity_info['type']}
%% source_page: {entity_info['page']}
%% position: {entity_info['metadata']['position']}
%% confidence: {entity_info['metadata'].get('confidence', 'null')}
%% corrected: true
%% correction_timestamp: {datetime.now().isoformat()}

{new_content}
"""
        else:
            # Unknown format, write with markdown frontmatter
            frontmatter = f"""---
entity_id: {entity_info['entity_id']}
type: {entity_info['type']}
corrected: true
---

{new_content}
"""

        # Write to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(frontmatter)

    def apply_correction(
        self,
        entity_id: str,
        corrected_content: str,
        correction_type: Literal["manual", "ai"],
        reason: str,
        user_prompt: Optional[str] = None
    ) -> None:
        """
        Apply correction to entity file and update manifest

        Args:
            entity_id: Entity ID to correct
            corrected_content: Corrected content
            correction_type: "manual" or "ai"
            reason: Reason for correction
            user_prompt: User prompt (for AI corrections)
        """
        # Get entity data
        entity_data = self.get_entity_content(entity_id)

        # Create correction entry
        correction = CorrectionEntry(
            entity_id=entity_id,
            correction_type=correction_type,
            original_content=entity_data['content'],
            corrected_content=corrected_content,
            reason=reason,
            timestamp=datetime.now().isoformat(),
            user_prompt=user_prompt
        )

        # Save correction to corrections.yaml
        self.save_correction(correction)

        # Update entity file with corrected content
        entity_file = self.output_dir / entity_data['metadata']['file']
        self._write_entity_file(entity_file, entity_data, corrected_content)

        # Update manifest with correction metadata
        self._update_manifest_correction(entity_id, correction)

        print(f"✓ Correction applied to {entity_id}")

    def _update_manifest_correction(self, entity_id: str, correction: CorrectionEntry) -> None:
        """
        Update manifest.yaml with correction metadata

        Args:
            entity_id: Entity ID
            correction: CorrectionEntry
        """
        # Load manifest
        # Use Loader=yaml.Loader to handle Python object tags (EntityType enums)
        with open(self.manifest_path, 'r', encoding='utf-8') as f:
            manifest = yaml.load(f, Loader=yaml.Loader)

        # Find and update entity
        for entity in manifest.get('entities', []):
            if entity['id'] == entity_id:
                entity['corrected'] = True
                entity['correction_timestamp'] = correction.timestamp
                entity['correction_type'] = correction.correction_type
                break

        # Write updated manifest
        with open(self.manifest_path, 'w', encoding='utf-8') as f:
            yaml.dump(manifest, f, default_flow_style=False, allow_unicode=True)

    def _rebuild_final_document(self) -> Path:
        """
        Rebuild final_document.md from entity files

        Returns:
            Path to rebuilt final_document.md
        """
        # Load manifest to get entity order
        with open(self.manifest_path, 'r', encoding='utf-8') as f:
            manifest = yaml.load(f, Loader=yaml.Loader)

        final_doc_path = self.output_dir / "final_document.md"

        # Build final document from entities
        content_parts = []

        for entity in manifest.get('entities', []):
            entity_id = entity['id']
            entity_type = entity['type']
            entity_page = entity['page']
            entity_file = self.output_dir / entity['file']

            # Convert enum to string if needed
            if hasattr(entity_type, 'name'):
                entity_type_str = entity_type.name
            else:
                entity_type_str = str(entity_type).upper()

            # Read entity content (with frontmatter stripped)
            entity_content = self._read_entity_file(entity_file)

            # Add entity marker comment
            content_parts.append(f"<!-- Entity: {entity_id} | Type: {entity_type_str} | Page: {entity_page} -->")
            content_parts.append("")

            # Wrap content based on type
            file_ext = entity_file.suffix
            if file_ext == '.yaml':
                content_parts.append("```yaml")
                content_parts.append(entity_content)
                content_parts.append("```")
            elif file_ext == '.mmd':
                content_parts.append("```mermaid")
                content_parts.append(entity_content)
                content_parts.append("```")
            else:
                # Markdown content - add directly
                content_parts.append(entity_content)

            content_parts.append("")

        # Write rebuilt final_document.md
        final_content = "\n".join(content_parts)
        with open(final_doc_path, 'w', encoding='utf-8') as f:
            f.write(final_content)

        print(f"✓ Rebuilt final_document.md from entity files")
        return final_doc_path

    def regenerate_html(self) -> Path:
        """
        Regenerate HTML using DocumentConverter

        Returns:
            Path to regenerated HTML file
        """
        from ..converter.document_converter import DocumentConverter

        # First, rebuild final_document.md from entity files
        final_doc_path = self._rebuild_final_document()

        # Then create DocumentConverter and generate HTML
        converter = DocumentConverter(final_doc_path, self.output_dir)
        html_path = converter.convert()

        print(f"✓ HTML regenerated: {html_path.name}")
        return html_path

    async def correct_with_ai(self, entity_id: str, user_prompt: str) -> str:
        """
        Use OpenAI to generate correction

        Args:
            entity_id: Entity ID to correct
            user_prompt: User description of the issue

        Returns:
            Corrected content generated by AI
        """
        from openai import AsyncOpenAI

        # Load entity content and metadata
        entity_data = self.get_entity_content(entity_id)

        # Get OpenAI API key
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY not found in environment. "
                "Please set it in .env file or environment variables."
            )

        # Construct system prompt based on entity type
        system_prompts = {
            "text": "You are a document correction assistant. Fix errors in text content while preserving markdown formatting.",
            "table": "You are a table correction assistant. Fix errors in YAML-formatted tables while preserving structure.",
            "image_text": "You are a document correction assistant. Fix errors in text extracted from images.",
            "diagram": "You are a diagram correction assistant. Fix errors in Mermaid diagram syntax.",
            "form": "You are a form correction assistant. Fix errors in YAML-formatted form data.",
            "mixed": "You are a document correction assistant. Fix errors in mixed content (text, tables, etc)."
        }

        system_prompt = system_prompts.get(
            entity_data['type'],
            system_prompts['text']
        )

        # Construct user prompt
        full_prompt = f"""Original Content:
```
{entity_data['content']}
```

Issue Description:
{user_prompt}

Please provide the corrected content in the same format. Only output the corrected content, no explanations."""

        # Call OpenAI API
        client = AsyncOpenAI(api_key=api_key)

        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0.3  # Lower temperature for factual corrections
        )

        corrected_content = response.choices[0].message.content.strip()

        # Clean up (remove code fences if present)
        if corrected_content.startswith('```'):
            lines = corrected_content.split('\n')
            # Remove first and last lines (code fences)
            corrected_content = '\n'.join(lines[1:-1]) if len(lines) > 2 else corrected_content

        return corrected_content
