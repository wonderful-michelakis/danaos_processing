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
import re
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

    def __init__(self, output_dir: Path, html_path: Path = None):
        """
        Initialize CorrectionManager

        Args:
            output_dir: Path to output directory (e.g., p86_90/)
            html_path: Path to the HTML file being viewed (used to determine
                       which source markdown to read entity content from)
        """
        self.output_dir = Path(output_dir)
        self.corrections_path = self.output_dir / "corrections.yaml"
        self.manifest_path = self.output_dir / "manifest.yaml"
        self.entities_dir = self.output_dir / "entities"

        # Determine the active source markdown based on the HTML being viewed.
        # If viewing final_document_judge_friendly.html, use final_document_judge.md.
        # Otherwise use final_document.md.
        self.active_md_path = self._resolve_active_md(html_path)

        # Cache for parsed entity content from the active markdown
        self._md_entity_cache = None

        # Validate paths
        if not self.output_dir.exists():
            raise FileNotFoundError(f"Output directory not found: {self.output_dir}")
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {self.manifest_path}")

    def _resolve_active_md(self, html_path: Path = None) -> Path:
        """
        Determine which source markdown file to read entity content from.

        If viewing judge HTML, use judge MD. Otherwise use regular MD.
        """
        if html_path is not None:
            html_name = Path(html_path).name
            # If the HTML is from the judge output, use the judge markdown
            if 'judge' in html_name:
                judge_md = self.output_dir / "final_document_judge.md"
                if judge_md.exists():
                    return judge_md

        # Default: use regular final_document.md
        regular_md = self.output_dir / "final_document.md"
        if regular_md.exists():
            return regular_md

        return None

    def _get_md_entity_content(self, entity_id: str) -> str | None:
        """
        Parse entity content from the active source markdown file.

        This gives the actual content as it appears in the document after
        judge processing (with merged entities), rather than the original
        per-entity files which don't reflect merges.

        Args:
            entity_id: Entity ID (e.g., "E085")

        Returns:
            Entity content string, or None if not found
        """
        if self.active_md_path is None or not self.active_md_path.exists():
            return None

        # Use cache if available
        if self._md_entity_cache is None:
            self._md_entity_cache = self._parse_md_entity_blocks()

        return self._md_entity_cache.get(entity_id)

    def _parse_md_entity_blocks(self) -> dict[str, str]:
        """
        Parse the active markdown file into a dict of entity_id -> content.

        Splits on entity marker comments and extracts content between them.
        """
        content = self.active_md_path.read_text(encoding='utf-8')
        entity_pattern = r'<!-- Entity: (E\d+) \| Type: .*? \| Page: \d+ -->'

        # Find all entity markers and their positions
        markers = list(re.finditer(entity_pattern, content))

        if not markers:
            return {}

        entities = {}
        for i, match in enumerate(markers):
            entity_id = match.group(1)
            content_start = match.end()
            content_end = markers[i + 1].start() if i + 1 < len(markers) else len(content)
            block = content[content_start:content_end].strip()

            # Strip trailing judge change log if present
            changelog_match = re.search(r'\n---\s*\n# Judge Change Log', block)
            if changelog_match:
                block = block[:changelog_match.start()].strip()

            entities[entity_id] = block

        return entities

    def invalidate_cache(self):
        """Invalidate the parsed markdown cache (call after corrections)."""
        self._md_entity_cache = None

    def _load_manifest(self) -> dict:
        """
        Load manifest.yaml

        Returns:
            Dictionary with manifest data
        """
        try:
            with open(self.manifest_path, 'r', encoding='utf-8') as f:
                # Use yaml.Loader to handle EntityType enums
                manifest = yaml.load(f, Loader=yaml.Loader)
                return manifest if manifest else {}
        except Exception as e:
            print(f"Warning: Could not load manifest: {e}")
            return {}

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

        # Try to get content from the active markdown document first.
        # This reflects any judge merges (where multiple entities were
        # combined into one). Falls back to original entity files.
        content = self._get_md_entity_content(entity_id)

        if content is None:
            # Fallback: read from original entity file
            entity_file = self.output_dir / entity_info['file']
            if not entity_file.exists():
                raise FileNotFoundError(f"Entity file not found: {entity_file}")
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

    @property
    def is_judge_mode(self) -> bool:
        """Check if we're working with a judge-processed document."""
        if self.active_md_path is None:
            return False
        return 'judge' in self.active_md_path.name

    def _update_md_entity_content(self, entity_id: str, new_content: str) -> None:
        """
        Update entity content directly in the active markdown file.

        Replaces the content block for entity_id between its marker and
        the next entity marker (or end of file).
        """
        if self.active_md_path is None or not self.active_md_path.exists():
            raise FileNotFoundError(f"Active markdown not found: {self.active_md_path}")

        md_content = self.active_md_path.read_text(encoding='utf-8')
        entity_pattern = r'<!-- Entity: (E\d+) \| Type: .*? \| Page: \d+ -->'

        markers = list(re.finditer(entity_pattern, md_content))

        # Find the marker for our entity
        target_idx = None
        for i, match in enumerate(markers):
            if match.group(1) == entity_id:
                target_idx = i
                break

        if target_idx is None:
            raise ValueError(f"Entity {entity_id} not found in {self.active_md_path.name}")

        # Determine the content region to replace
        marker = markers[target_idx]
        content_start = marker.end()
        content_end = markers[target_idx + 1].start() if target_idx + 1 < len(markers) else len(md_content)

        # Check if the tail has the judge change log (only for last entity)
        tail = md_content[content_start:content_end]
        changelog_match = re.search(r'\n---\s*\n# Judge Change Log', tail)
        if changelog_match:
            content_end = content_start + changelog_match.start()

        # Replace the content block, preserving surrounding whitespace
        updated = md_content[:content_start] + f"\n\n{new_content}\n\n" + md_content[content_end:]

        self.active_md_path.write_text(updated, encoding='utf-8')
        print(f"✓ Updated {entity_id} in {self.active_md_path.name}")

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

        if self.is_judge_mode:
            # In judge mode: update the judge markdown directly.
            # The judge MD has merged entities that don't exist in
            # individual entity files, so we must edit the MD in-place.
            self._update_md_entity_content(entity_id, corrected_content)
        else:
            # In regular mode: update the individual entity file
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
        Regenerate HTML using DocumentConverter.

        In judge mode: converts the active judge markdown directly.
        In regular mode: rebuilds final_document.md from entity files first.

        Returns:
            Path to regenerated HTML file
        """
        from ..converter.document_converter import DocumentConverter

        if self.is_judge_mode:
            # Judge mode: convert the judge markdown directly
            # (it was already updated in-place by apply_correction)
            final_doc_path = self.active_md_path
        else:
            # Regular mode: rebuild final_document.md from entity files
            final_doc_path = self._rebuild_final_document()

        # Convert markdown to HTML
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

    async def document_wide_correction(self, user_prompt: str) -> list[dict]:
        """
        Apply document-wide AI corrections based on user prompt

        Args:
            user_prompt: Natural language instruction for corrections
                        (e.g., "Fix all date formats to YYYY-MM-DD")

        Returns:
            List of proposed changes with structure:
            [
                {
                    "entity_id": "E001",
                    "original_content": "...",
                    "corrected_content": "...",
                    "reason": "Fixed date format"
                },
                ...
            ]
        """
        from openai import AsyncOpenAI

        # Get API key
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        # Load all entities
        manifest = self._load_manifest()
        all_entities = []

        for entity_info in manifest.get('entities', []):
            entity_id = entity_info['id']
            entity_data = self.get_entity_content(entity_id)
            if entity_data:
                all_entities.append({
                    'entity_id': entity_id,
                    'type': entity_data['type'],
                    'page': entity_data['page'],
                    'content': entity_data['content']
                })

        # Prepare document context for AI
        document_context = "# Document Entities\n\n"
        for entity in all_entities:
            document_context += f"## Entity {entity['entity_id']} (Page {entity['page']}, Type: {entity['type']})\n"
            document_context += f"```\n{entity['content']}\n```\n\n"

        # Construct AI prompt
        system_prompt = """You are a document correction assistant. Analyze the entire document and propose corrections based on the user's instruction.

For each entity that needs correction, output in this EXACT JSON format:
{
  "corrections": [
    {
      "entity_id": "E001",
      "corrected_content": "...",
      "reason": "Brief explanation of what was corrected"
    }
  ]
}

IMPORTANT:
- Only include entities that need changes
- Output ONLY valid JSON, no explanations outside the JSON
- Preserve the original format (markdown, YAML, etc.) of each entity
- The corrected_content should be the COMPLETE corrected content, not just changes"""

        full_prompt = f"""{document_context}

User Instruction:
{user_prompt}

Analyze all entities above and propose corrections. Output in the specified JSON format."""

        # Call OpenAI API
        client = AsyncOpenAI(api_key=api_key)

        response = await client.chat.completions.create(
            model="gpt-4o",  # Using gpt-4o for better JSON output
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}  # Ensure JSON output
        )

        # Parse AI response
        import json
        ai_response = response.choices[0].message.content.strip()
        corrections_data = json.loads(ai_response)

        # Build proposed changes with original content
        proposed_changes = []
        for correction in corrections_data.get('corrections', []):
            entity_id = correction['entity_id']
            # Get original content
            entity_data = self.get_entity_content(entity_id)
            if entity_data:
                proposed_changes.append({
                    'entity_id': entity_id,
                    'original_content': entity_data['content'],
                    'corrected_content': correction['corrected_content'],
                    'reason': correction['reason']
                })

        return proposed_changes

    def apply_document_wide_corrections(self, corrections: list[dict], user_prompt: str) -> dict:
        """
        Apply multiple corrections and regenerate document

        Args:
            corrections: List of corrections from document_wide_correction()
            user_prompt: Original user prompt (for logging)

        Returns:
            dict with 'success', 'corrections_applied', 'html_path'
        """
        timestamp = datetime.now().isoformat()
        corrections_applied = []

        # Apply each correction
        for correction in corrections:
            try:
                # Create CorrectionEntry object
                correction_entry = CorrectionEntry(
                    entity_id=correction['entity_id'],
                    correction_type='ai',
                    original_content=correction.get('original_content', ''),
                    corrected_content=correction['corrected_content'],
                    reason=f"Document-wide AI correction: {correction['reason']}",
                    timestamp=timestamp,
                    user_prompt=user_prompt
                )

                # Save the correction
                self.save_correction(correction_entry)

                # Apply to entity file
                self.apply_correction(
                    entity_id=correction['entity_id'],
                    corrected_content=correction['corrected_content'],
                    correction_type='ai',
                    reason=f"Document-wide AI correction: {correction['reason']}",
                    user_prompt=user_prompt
                )

                corrections_applied.append(correction['entity_id'])
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"Warning: Failed to apply correction to {correction['entity_id']}: {e}")

        # Regenerate HTML
        try:
            html_path = self.regenerate_html()
        except Exception as e:
            return {
                'success': False,
                'error': f"Corrections applied but HTML regeneration failed: {e}",
                'corrections_applied': corrections_applied
            }

        return {
            'success': True,
            'corrections_applied': corrections_applied,
            'html_path': str(html_path),
            'message': f"Applied {len(corrections_applied)} corrections successfully"
        }
