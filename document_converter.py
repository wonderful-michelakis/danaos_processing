"""
User-Friendly Document Converter
Converts technical final_document.md to beautiful HTML
"""

from pathlib import Path
from typing import List, Dict, Any, Tuple
import yaml
import re
import subprocess
import base64
from dataclasses import dataclass
import shutil


@dataclass
class DocumentEntity:
    """Represents a parsed entity from final_document.md"""
    entity_id: str
    entity_type: str  # 'table', 'diagram', 'text'
    page: int
    content: str
    rendered_html: str = ""


class DocumentConverter:
    """Converts technical markdown to user-friendly HTML"""

    def __init__(self, markdown_path: Path, output_dir: Path):
        self.markdown_path = Path(markdown_path)
        self.output_dir = Path(output_dir)
        self.temp_dir = output_dir / "temp_conversion"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        self.document_title = ""
        self.metadata = {}
        self.entities: List[DocumentEntity] = []

    def convert(self) -> Path:
        """Main conversion workflow"""
        print(f"Converting {self.markdown_path.name} to user-friendly HTML...")

        # Step 1: Parse document
        self.parse_document()

        # Step 2: Process entities
        self.process_entities()

        # Step 3: Generate HTML
        html_path = self.generate_html()

        # Step 4: Cleanup temp files
        self.cleanup()

        print(f"✓ Conversion complete: {html_path}")
        return html_path

    def parse_document(self):
        """Parse final_document.md into structured components"""
        content = self.markdown_path.read_text(encoding='utf-8')

        # Extract YAML frontmatter
        frontmatter_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
        if frontmatter_match:
            frontmatter_text = frontmatter_match.group(1)
            self.metadata = yaml.safe_load(frontmatter_text)
            self.document_title = self.metadata.get('document_title', 'Document')
            content = content[frontmatter_match.end():]

        # Split by entity markers
        entity_pattern = r'<!-- Entity: (E\d+) \| Type: (.*?) \| Page: (\d+) -->\n\n(.*?)(?=<!-- Entity:|$)'
        matches = re.findall(entity_pattern, content, re.DOTALL)

        for match in matches:
            entity_id, entity_type, page, entity_content = match

            # Clean entity type
            entity_type_clean = self._extract_type_from_enum(entity_type)

            entity = DocumentEntity(
                entity_id=entity_id,
                entity_type=entity_type_clean,
                page=int(page),
                content=entity_content.strip()
            )
            self.entities.append(entity)

        print(f"  Parsed {len(self.entities)} entities")

    def _extract_type_from_enum(self, type_str: str) -> str:
        """Extract clean type from 'EntityType.TABLE' format"""
        # EntityType.TABLE → table
        # EntityType.DIAGRAM → diagram
        if '.' in type_str:
            return type_str.split('.')[-1].lower()
        return type_str.lower()

    def process_entities(self):
        """Convert each entity to HTML"""
        for i, entity in enumerate(self.entities):
            print(f"  Processing {entity.entity_id} ({entity.entity_type})...")

            if entity.entity_type == 'table':
                entity.rendered_html = self._process_table(entity)
            elif entity.entity_type == 'diagram':
                entity.rendered_html = self._process_diagram(entity)
            else:  # text, image_text
                entity.rendered_html = self._process_text(entity)

    def _process_table(self, entity: DocumentEntity) -> str:
        """Convert YAML table to HTML table"""
        # Extract YAML from code block
        yaml_match = re.search(r'```yaml\n(.*?)\n```', entity.content, re.DOTALL)
        if not yaml_match:
            return f'<p class="error">Could not parse table {entity.entity_id}</p>'

        yaml_content = yaml_match.group(1)

        try:
            data = yaml.safe_load(yaml_content)

            # Handle different table structures
            if 'table' in data:
                table_data = data['table']
                return self._yaml_table_to_html(table_data, entity.entity_id)
            elif 'parameters' in data:
                # Special handling for parameter tables
                return self._parameters_to_html(data['parameters'], entity.entity_id)
            else:
                # Generic dict → table
                return self._dict_to_html_table(data, entity.entity_id)

        except yaml.YAMLError as e:
            return f'<p class="error">YAML parse error in {entity.entity_id}: {e}</p>'

    def _yaml_table_to_html(self, table_data: list, entity_id: str) -> str:
        """Convert YAML list of dicts to HTML table"""
        if not table_data or not isinstance(table_data, list):
            return '<p class="empty-table">Empty table</p>'

        # Extract headers from first row
        headers = list(table_data[0].keys())

        html = f'<div class="table-container" id="{entity_id}">\n'
        html += '  <table class="data-table">\n'
        html += '    <thead>\n      <tr>\n'

        for header in headers:
            html += f'        <th>{header}</th>\n'

        html += '      </tr>\n    </thead>\n'
        html += '    <tbody>\n'

        for row in table_data:
            html += '      <tr>\n'
            for header in headers:
                value = row.get(header, '')
                html += f'        <td>{value}</td>\n'
            html += '      </tr>\n'

        html += '    </tbody>\n'
        html += '  </table>\n'
        html += '</div>\n'

        return html

    def _parameters_to_html(self, parameters: list, entity_id: str) -> str:
        """Convert parameters list to transposed HTML table"""
        # This handles the complex fuel parameters table structure
        if not parameters:
            return '<p class="empty-table">Empty parameters</p>'

        # Extract all unique value keys across all parameters
        all_keys = set()
        for param in parameters:
            if 'values' in param:
                all_keys.update(param['values'].keys())

        column_names = sorted(list(all_keys))

        html = f'<div class="table-container" id="{entity_id}">\n'
        html += '  <table class="data-table parameters-table">\n'
        html += '    <thead>\n      <tr>\n'
        html += '        <th>Parameter</th>\n'
        html += '        <th>Unit</th>\n'
        html += '        <th>Limit</th>\n'

        for col_name in column_names:
            html += f'        <th>{col_name.replace("_", " ")}</th>\n'

        html += '      </tr>\n    </thead>\n'
        html += '    <tbody>\n'

        for param in parameters:
            html += '      <tr>\n'
            html += f'        <td class="param-name">{param.get("name", "")}</td>\n'
            html += f'        <td class="param-unit">{param.get("unit", "")}</td>\n'
            html += f'        <td class="param-limit">{param.get("limit", "")}</td>\n'

            values = param.get('values', {})
            for col_name in column_names:
                value = values.get(col_name, '')
                html += f'        <td>{value}</td>\n'

            html += '      </tr>\n'

        html += '    </tbody>\n'
        html += '  </table>\n'
        html += '</div>\n'

        return html

    def _dict_to_html_table(self, data: dict, entity_id: str) -> str:
        """Convert generic dict to HTML table"""
        html = f'<div class="table-container" id="{entity_id}">\n'
        html += '  <table class="data-table">\n'
        html += '    <tbody>\n'

        for key, value in data.items():
            html += '      <tr>\n'
            html += f'        <th>{key}</th>\n'
            html += f'        <td>{value}</td>\n'
            html += '      </tr>\n'

        html += '    </tbody>\n'
        html += '  </table>\n'
        html += '</div>\n'

        return html

    def _process_diagram(self, entity: DocumentEntity) -> str:
        """Convert Mermaid diagram to image"""
        # Extract Mermaid code from code block
        mermaid_match = re.search(r'```mermaid\n(.*?)\n```', entity.content, re.DOTALL)
        if not mermaid_match:
            return f'<p class="error">Could not parse diagram {entity.entity_id}</p>'

        mermaid_code = mermaid_match.group(1)

        # Check for surrounding text (before code block)
        text_before = entity.content[:mermaid_match.start()].strip()

        # Save Mermaid code to temp file
        mermaid_file = self.temp_dir / f"{entity.entity_id}.mmd"
        mermaid_file.write_text(mermaid_code, encoding='utf-8')

        # Render with mermaid-cli
        output_file = self.temp_dir / f"{entity.entity_id}.png"

        try:
            result = subprocess.run(
                ['mmdc', '-i', str(mermaid_file), '-o', str(output_file), '-b', 'white'],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                print(f"    Warning: mermaid-cli failed for {entity.entity_id}: {result.stderr}")
                return self._diagram_fallback(mermaid_code, entity.entity_id)

            # Embed image as base64 (for standalone HTML)
            image_data = output_file.read_bytes()
            b64_image = base64.b64encode(image_data).decode('utf-8')

            html = f'<div class="diagram-container" id="{entity.entity_id}">\n'

            if text_before:
                html += f'  <div class="diagram-caption">{text_before}</div>\n'

            html += f'  <img src="data:image/png;base64,{b64_image}" alt="Diagram {entity.entity_id}" class="diagram-image" />\n'
            html += '</div>\n'

            return html

        except FileNotFoundError:
            print("    Error: mermaid-cli not found. Install with: npm install -g @mermaid-js/mermaid-cli")
            return self._diagram_fallback(mermaid_code, entity.entity_id)
        except subprocess.TimeoutExpired:
            return f'<p class="error">Diagram rendering timeout for {entity.entity_id}</p>'

    def _diagram_fallback(self, mermaid_code: str, entity_id: str) -> str:
        """Fallback: Show Mermaid code if rendering fails"""
        escaped_code = mermaid_code.replace('<', '&lt;').replace('>', '&gt;')
        return f'''
    <div class="diagram-fallback" id="{entity_id}">
        <p class="error">Could not render diagram (mermaid-cli required)</p>
        <details>
            <summary>Show Mermaid code</summary>
            <pre><code>{escaped_code}</code></pre>
        </details>
    </div>
    '''

    def _process_text(self, entity: DocumentEntity) -> str:
        """Convert markdown text to HTML"""
        try:
            import markdown2

            # Convert markdown to HTML
            html = markdown2.markdown(
                entity.content,
                extras=['fenced-code-blocks', 'tables', 'break-on-newline']
            )

            return f'<div class="text-content" id="{entity.entity_id}">\n{html}\n</div>\n'

        except ImportError:
            # Fallback if markdown2 not installed
            print("    Warning: markdown2 not installed, using basic formatting")
            escaped_content = entity.content.replace('<', '&lt;').replace('>', '&gt;')
            return f'<div class="text-content" id="{entity.entity_id}">\n<pre>{escaped_content}</pre>\n</div>\n'

    def generate_html(self) -> Path:
        """Generate complete HTML document"""

        # Build entity sections
        entities_html = ""
        for entity in self.entities:
            entities_html += f'<section class="entity" data-entity="{entity.entity_id}" data-page="{entity.page}">\n'
            entities_html += f'  <div class="entity-badge">Page {entity.page}</div>\n'
            entities_html += entity.rendered_html
            entities_html += '</section>\n\n'

        # Generate full HTML
        html = self._get_html_template(entities_html)

        # Write output file
        output_path = self.output_dir / f"{self.markdown_path.stem}_friendly.html"
        output_path.write_text(html, encoding='utf-8')

        return output_path

    def _get_html_template(self, content: str) -> str:
        """HTML template with embedded CSS"""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.document_title}</title>
    <style>
        {self._get_css_styles()}
    </style>
</head>
<body>
    <header class="document-header">
        <h1>{self.document_title}</h1>
        <div class="document-meta">
            <span class="meta-item">Source: {self.metadata.get('source_file', 'Unknown')}</span>
            <span class="meta-item">Processed: {self.metadata.get('processed_date', 'Unknown')}</span>
            <span class="meta-item">Total Entities: {self.metadata.get('total_entities', len(self.entities))}</span>
        </div>
    </header>

    <main class="document-content">
        {content}
    </main>

    <footer class="document-footer">
        <p>Generated from technical document • Powered by Document Processing Pipeline</p>
    </footer>
</body>
</html>"""

    def _get_css_styles(self) -> str:
        """Professional CSS for user-friendly display"""
        return """
        /* Reset and base styles */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f7fa;
            padding: 20px;
        }

        /* Header */
        .document-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            border-radius: 12px;
            margin-bottom: 40px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .document-header h1 {
            font-size: 2.5rem;
            margin-bottom: 15px;
            font-weight: 700;
        }

        .document-meta {
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            opacity: 0.95;
            font-size: 0.95rem;
        }

        .meta-item {
            background: rgba(255,255,255,0.2);
            padding: 6px 12px;
            border-radius: 6px;
        }

        /* Main content */
        .document-content {
            max-width: 1200px;
            margin: 0 auto;
        }

        /* Entity sections */
        .entity {
            background: white;
            padding: 30px;
            margin-bottom: 30px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            position: relative;
        }

        .entity-badge {
            position: absolute;
            top: 15px;
            right: 15px;
            background: #667eea;
            color: white;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.85rem;
            font-weight: 600;
        }

        /* Tables */
        .table-container {
            overflow-x: auto;
            margin: 20px 0;
        }

        .data-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.95rem;
        }

        .data-table thead {
            background: #f8f9fa;
            border-bottom: 2px solid #dee2e6;
        }

        .data-table th {
            padding: 12px 15px;
            text-align: left;
            font-weight: 600;
            color: #495057;
            white-space: nowrap;
        }

        .data-table td {
            padding: 10px 15px;
            border-bottom: 1px solid #e9ecef;
        }

        .data-table tbody tr:hover {
            background: #f8f9fa;
        }

        .data-table tbody tr:last-child td {
            border-bottom: none;
        }

        /* Parameter tables */
        .parameters-table .param-name {
            font-weight: 600;
            color: #495057;
        }

        .parameters-table .param-unit {
            color: #6c757d;
            font-style: italic;
        }

        .parameters-table .param-limit {
            color: #dc3545;
            font-weight: 500;
        }

        /* Diagrams */
        .diagram-container {
            margin: 30px 0;
            text-align: center;
        }

        .diagram-caption {
            background: #e7f3ff;
            padding: 15px;
            border-left: 4px solid #0066cc;
            margin-bottom: 20px;
            text-align: left;
            border-radius: 4px;
            font-size: 0.95rem;
            line-height: 1.6;
        }

        .diagram-image {
            max-width: 100%;
            height: auto;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 20px;
            background: white;
        }

        .diagram-fallback {
            background: #fff3cd;
            padding: 20px;
            border-left: 4px solid #ffc107;
            border-radius: 4px;
        }

        .diagram-fallback details {
            margin-top: 15px;
        }

        .diagram-fallback summary {
            cursor: pointer;
            font-weight: 600;
            color: #856404;
        }

        .diagram-fallback pre {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
            overflow-x: auto;
            margin-top: 10px;
        }

        /* Text content */
        .text-content {
            line-height: 1.8;
        }

        .text-content h1,
        .text-content h2,
        .text-content h3 {
            margin-top: 20px;
            margin-bottom: 10px;
            color: #2c3e50;
        }

        .text-content h2 {
            font-size: 1.75rem;
            border-bottom: 2px solid #e9ecef;
            padding-bottom: 8px;
        }

        .text-content h3 {
            font-size: 1.35rem;
            color: #495057;
        }

        .text-content p {
            margin-bottom: 15px;
        }

        .text-content ul,
        .text-content ol {
            margin-left: 25px;
            margin-bottom: 15px;
        }

        .text-content li {
            margin-bottom: 8px;
        }

        /* Error states */
        .error {
            background: #f8d7da;
            color: #721c24;
            padding: 12px;
            border-radius: 4px;
            border-left: 4px solid #f5c6cb;
        }

        .empty-table {
            padding: 20px;
            text-align: center;
            color: #6c757d;
            font-style: italic;
        }

        /* Footer */
        .document-footer {
            text-align: center;
            padding: 40px 20px;
            color: #6c757d;
            font-size: 0.9rem;
        }

        /* Print styles */
        @media print {
            body {
                background: white;
                padding: 0;
            }

            .document-header {
                background: #667eea;
                color: white;
            }

            .entity {
                page-break-inside: avoid;
                box-shadow: none;
                border: 1px solid #dee2e6;
            }

            .entity-badge {
                background: #495057;
            }
        }

        /* Responsive */
        @media (max-width: 768px) {
            .document-header h1 {
                font-size: 1.75rem;
            }

            .document-meta {
                font-size: 0.85rem;
            }

            .entity {
                padding: 20px;
            }

            .data-table {
                font-size: 0.85rem;
            }

            .data-table th,
            .data-table td {
                padding: 8px 10px;
            }
        }
    """

    def cleanup(self):
        """Remove temporary files"""
        if self.temp_dir.exists():
            try:
                shutil.rmtree(self.temp_dir)
                print("  Cleaned up temporary files")
            except Exception as e:
                print(f"  Warning: Could not clean up temp directory: {e}")
