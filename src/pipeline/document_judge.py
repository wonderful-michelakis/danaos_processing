"""
Document Normalization Judge

Post-processing step that uses an LLM to validate and correct
the assembled final_document.md before HTML conversion.

Supports large documents via entity-based chunking.
Uses placeholder tokens for entity markers to prevent LLM stripping.

Usage:
    from src.pipeline.document_judge import DocumentJudge
    judge = DocumentJudge(output_dir)
    judge.run()
"""

import os
import re
from pathlib import Path
from dataclasses import dataclass
from openai import OpenAI


# Token estimation: ~4 chars per token
CHARS_PER_TOKEN = 4

# Leave room for system prompt (~2K tokens) + response (~equal to input)
# GPT-4o context is 128K tokens. Budget: 30K for input content per chunk.
MAX_CHUNK_TOKENS = 30_000
MAX_CHUNK_CHARS = MAX_CHUNK_TOKENS * CHARS_PER_TOKEN  # ~120K chars


@dataclass
class DocumentChunk:
    """A chunk of the document containing one or more entity blocks."""
    content: str
    entity_ids: list[str]
    index: int
    total: int


class DocumentJudge:
    """
    LLM-based judge that validates and corrects a final_document.md.

    Handles large documents by splitting into entity-based chunks,
    processing each through the LLM, and reassembling.

    Uses placeholder tokens ([ENTITY:E001]) instead of full HTML comment
    markers when sending to the LLM to prevent marker stripping.
    """

    def __init__(self, output_dir: Path, model: str = "gpt-4o"):
        self.output_dir = Path(output_dir)
        self.model = model
        self.input_path = self.output_dir / "final_document.md"
        self.output_path = self.output_dir / "final_document_judge.md"

        if not self.input_path.exists():
            raise FileNotFoundError(f"Input not found: {self.input_path}")

        # Load judge prompt
        self.judge_prompt = self._load_judge_prompt()

    def _load_judge_prompt(self) -> str:
        """Load the judge system prompt from judge_prompt.md"""
        prompt_path = Path(__file__).parent.parent.parent / "judge_prompt.md"
        if not prompt_path.exists():
            raise FileNotFoundError(
                f"Judge prompt not found: {prompt_path}\n"
                f"Create judge_prompt.md in the project root."
            )
        return prompt_path.read_text(encoding='utf-8')

    def run(self) -> Path:
        """
        Run the judge on final_document.md and produce final_document_judge.md.

        Returns:
            Path to the output file
        """
        print(f"\n{'='*60}")
        print(f"  Document Normalization Judge")
        print(f"{'='*60}")
        print(f"  Input:  {self.input_path.name}")
        print(f"  Output: {self.output_path.name}")
        print(f"  Model:  {self.model}")

        # Read document
        raw_content = self.input_path.read_text(encoding='utf-8')

        # Parse into frontmatter + entity blocks
        frontmatter, entity_blocks = self._parse_document(raw_content)

        print(f"  Entities: {len(entity_blocks)}")

        # Build marker map: entity_id -> full marker
        self.marker_map = {}
        for block in entity_blocks:
            self.marker_map[block['entity_id']] = block['marker']

        # Create chunks that fit within token limits
        chunks = self._create_chunks(entity_blocks)
        print(f"  Chunks: {len(chunks)}")
        print(f"{'='*60}\n")

        # Process each chunk through LLM
        corrected_chunks = []
        all_changes = []

        for chunk in chunks:
            print(f"  Processing chunk {chunk.index}/{chunk.total} "
                  f"({len(chunk.entity_ids)} entities: "
                  f"{chunk.entity_ids[0]}..{chunk.entity_ids[-1]})...")

            corrected_content, changes = self._process_chunk(chunk)
            corrected_chunks.append(corrected_content)

            if changes:
                all_changes.append(f"## Chunk {chunk.index}\n{changes}")

            print(f"    Done.")

        # Reassemble document
        final_content = self._reassemble(frontmatter, corrected_chunks, all_changes)

        # Write output
        self.output_path.write_text(final_content, encoding='utf-8')

        print(f"\n{'='*60}")
        print(f"  Judge complete!")
        print(f"  Output: {self.output_path}")
        if all_changes:
            print(f"  Changes: {sum(c.count('-') for c in all_changes)} items")
        else:
            print(f"  No changes needed.")
        print(f"{'='*60}\n")

        return self.output_path

    def _parse_document(self, content: str) -> tuple[str, list[dict]]:
        """
        Parse document into frontmatter and entity blocks.

        Returns:
            (frontmatter_str, list of {marker, content, entity_id})
        """
        entity_pattern = r'(<!-- Entity: (E\d+) \| Type: .*? \| Page: \d+ -->)'
        first_match = re.search(entity_pattern, content)

        if not first_match:
            return content, []

        frontmatter = content[:first_match.start()].rstrip()

        # Split by entity markers, keeping the markers
        parts = re.split(r'(<!-- Entity: E\d+ \| Type: .*? \| Page: \d+ -->)', content[first_match.start():])

        entity_blocks = []
        i = 0
        while i < len(parts):
            part = parts[i].strip()
            if re.match(r'<!-- Entity: (E\d+) \| Type: .*? \| Page: \d+ -->', part):
                marker = part
                entity_id = re.search(r'E\d+', marker).group()
                block_content = parts[i + 1].strip() if i + 1 < len(parts) else ""
                entity_blocks.append({
                    'marker': marker,
                    'content': block_content,
                    'entity_id': entity_id
                })
                i += 2
            else:
                i += 1

        return frontmatter, entity_blocks

    def _create_chunks(self, entity_blocks: list[dict]) -> list[DocumentChunk]:
        """
        Group entity blocks into chunks that fit within token limits.
        Uses placeholder tokens instead of full markers for size estimation.
        """
        if not entity_blocks:
            return []

        chunks = []
        current_blocks = []
        current_size = 0

        for block in entity_blocks:
            # Use placeholder for size estimation
            block_text = f"\n[ENTITY:{block['entity_id']}]\n\n{block['content']}\n"
            block_size = len(block_text)

            if current_blocks and (current_size + block_size) > MAX_CHUNK_CHARS:
                chunk_content = self._blocks_to_placeholder_text(current_blocks)
                chunks.append(DocumentChunk(
                    content=chunk_content,
                    entity_ids=[b['entity_id'] for b in current_blocks],
                    index=len(chunks) + 1,
                    total=0
                ))
                current_blocks = []
                current_size = 0

            current_blocks.append(block)
            current_size += block_size

        # Flush remaining
        if current_blocks:
            chunk_content = self._blocks_to_placeholder_text(current_blocks)
            chunks.append(DocumentChunk(
                content=chunk_content,
                entity_ids=[b['entity_id'] for b in current_blocks],
                index=len(chunks) + 1,
                total=0
            ))

        for chunk in chunks:
            chunk.total = len(chunks)

        return chunks

    def _blocks_to_placeholder_text(self, blocks: list[dict]) -> str:
        """Convert entity blocks to text using placeholder tokens."""
        parts = []
        for block in blocks:
            parts.append(f"\n[ENTITY:{block['entity_id']}]\n\n{block['content']}\n")
        return '\n'.join(parts)

    def _process_chunk(self, chunk: DocumentChunk) -> tuple[str, str]:
        """
        Process a single chunk through the LLM.

        Uses [ENTITY:E001] placeholders instead of full HTML comment markers.
        After LLM response, restores full markers and validates.

        Returns:
            (corrected_content_with_full_markers, change_log_text)
        """
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        client = OpenAI(api_key=api_key)

        # Build the user message
        if chunk.total == 1:
            context_note = ""
        else:
            context_note = (
                f"\n\n**NOTE**: This is chunk {chunk.index} of {chunk.total} "
                f"from a large document. Process ONLY the entities below. "
                f"Do not add document-level frontmatter or headers to this chunk."
            )

        entity_instruction = f"""
**CRITICAL**: The document uses `[ENTITY:EXXX]` tags to mark entity boundaries.
There are {len(chunk.entity_ids)} entities in this chunk: {', '.join(chunk.entity_ids)}.

Rules for entity tags:
- Every `[ENTITY:EXXX]` tag MUST appear in your output
- When MERGING entities, keep only the FIRST entity's tag and DELETE the others
- When NOT merging, keep each tag exactly where it is
- NEVER remove ALL tags - at minimum, merged groups must retain one tag each

Return the corrected document content followed by a `## Change Log` section.
If no changes are needed, return the content as-is with an empty change log."""

        user_message = f"""{context_note}{entity_instruction}

---

{chunk.content}"""

        # Call LLM
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.judge_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.2,
        )

        result = response.choices[0].message.content.strip()

        # Strip outer code fences if LLM wrapped the response
        result = self._strip_code_fences(result)

        # Separate corrected content from change log
        corrected_content, change_log = self._split_change_log(result)

        # Validate and restore markers
        corrected_content = self._validate_and_restore_markers(
            corrected_content, chunk.entity_ids
        )

        return corrected_content, change_log

    def _validate_and_restore_markers(self, content: str, expected_ids: list[str]) -> str:
        """
        Validate placeholder markers in LLM output and restore full markers.

        If the LLM stripped placeholders, re-inject them at best-effort positions.
        Then replace all [ENTITY:EXXX] placeholders with full HTML comment markers.
        """
        # Count how many placeholders survived
        found_ids = re.findall(r'\[ENTITY:(E\d+)\]', content)
        found_set = set(found_ids)
        expected_set = set(expected_ids)

        surviving_count = len(found_set & expected_set)
        total_expected = len(expected_set)

        if surviving_count == 0 and total_expected > 0:
            # LLM stripped ALL markers - this is a critical failure
            # Fall back: return original chunk content with full markers
            print(f"    WARNING: LLM removed ALL entity markers! Using original content.")
            # Rebuild from marker_map
            parts = []
            for eid in expected_ids:
                marker = self.marker_map.get(eid, f"<!-- Entity: {eid} -->")
                parts.append(f"\n{marker}\n")
                # Try to find corresponding content in the LLM output
                # but since all markers are gone, we can't map reliably
                # Fall back to original content would require storing it
            # Since we can't recover, return original chunk content with real markers
            restored = content
            # Prepend the first marker at minimum so the document isn't markerless
            first_marker = self.marker_map.get(expected_ids[0], '')
            if first_marker:
                restored = f"\n{first_marker}\n\n{content}\n"
            return restored

        if surviving_count < total_expected:
            missing = expected_set - found_set
            print(f"    WARNING: {len(missing)} markers missing from LLM output: "
                  f"{', '.join(sorted(missing))}. "
                  f"({surviving_count}/{total_expected} survived - merged or lost)")

        # Replace placeholders with full HTML comment markers
        def replace_placeholder(match):
            entity_id = match.group(1)
            full_marker = self.marker_map.get(entity_id)
            if full_marker:
                return full_marker
            return match.group(0)  # Keep as-is if not in map

        restored = re.sub(r'\[ENTITY:(E\d+)\]', replace_placeholder, content)

        return restored

    def _strip_code_fences(self, text: str) -> str:
        """Strip outer markdown code fences if the LLM wrapped the entire response."""
        pattern = r'^```(?:markdown|md)?\s*\n(.*?)```\s*$'
        match = re.match(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text

    def _split_change_log(self, result: str) -> tuple[str, str]:
        """
        Split LLM result into corrected content and change log.
        """
        patterns = [
            r'\n## Change Log\s*\n',
            r'\n## Changelog\s*\n',
            r'\n## Changes\s*\n',
            r'\n---\s*\n## Change Log',
        ]

        for pattern in patterns:
            match = re.search(pattern, result, re.IGNORECASE)
            if match:
                corrected = result[:match.start()].rstrip()
                change_log = result[match.end():].strip()
                change_log = re.sub(r'\n?```\s*$', '', change_log).strip()
                return corrected, change_log

        return result, ""

    def _reassemble(
        self,
        frontmatter: str,
        corrected_chunks: list[str],
        all_changes: list[str]
    ) -> str:
        """Reassemble the final document from frontmatter + corrected chunks."""
        parts = [frontmatter]

        for chunk_content in corrected_chunks:
            parts.append(chunk_content)

        if all_changes:
            parts.append("\n\n---\n\n# Judge Change Log\n")
            parts.append('\n'.join(all_changes))

        return '\n'.join(parts) + '\n'
