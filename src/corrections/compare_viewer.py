"""
PDF-HTML Comparison Viewer
Launch web interface to compare original PDF with processed HTML side-by-side

Usage:
    python compare_viewer.py input.pdf output/final_document_friendly.html
    python compare_viewer.py input.pdf output/final_document_judge_friendly.html --port 8080
    python compare_viewer.py input.pdf output/final_document_friendly.html --no-browser
"""

import argparse
from pathlib import Path
from flask import Flask, render_template, send_file, jsonify, request
import yaml
import webbrowser
import threading
import time
import asyncio
from .correction_manager import CorrectionManager


class ComparisonViewer:
    """PDF-HTML comparison viewer with synchronized navigation"""

    def __init__(self, pdf_path: Path, html_path: Path):
        self.pdf_path = pdf_path.resolve()
        self.html_path = html_path.resolve()
        self.output_dir = html_path.parent
        self.manifest_path = self.output_dir / "manifest.yaml"

        # Validate files exist
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {self.pdf_path}")
        if not self.html_path.exists():
            raise FileNotFoundError(
                f"HTML not found: {self.html_path}\n"
                f"Generate it first: python convert_to_friendly.py {self.output_dir}/final_document.md"
            )

        # Load manifest for page mapping
        self.manifest = self._load_manifest()

        # Initialize CorrectionManager with html_path so it knows which
        # source markdown to read (judge vs regular) for entity content
        self.correction_manager = CorrectionManager(self.output_dir, html_path=self.html_path)

    def _load_manifest(self):
        """Load manifest.yaml if it exists"""
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path) as f:
                    return yaml.safe_load(f)
            except Exception as e:
                print(f"Warning: Could not load manifest: {e}")
                return {}
        return {}

    def create_app(self):
        """Create and configure Flask application"""
        # Get project root (2 levels up from src/corrections/)
        project_root = Path(__file__).parent.parent.parent
        template_folder = project_root / 'web' / 'templates'
        static_folder = project_root / 'web' / 'static'

        app = Flask(__name__,
                   template_folder=str(template_folder),
                   static_folder=str(static_folder))

        @app.route('/')
        def index():
            """Render main comparison page"""
            return render_template(
                'compare.html',
                pdf_filename=self.pdf_path.name,
                document_title=self.manifest.get('document_title', 'Document Comparison'),
                manifest=self.manifest
            )

        @app.route('/pdf')
        def serve_pdf():
            """Serve the original PDF file"""
            return send_file(self.pdf_path, mimetype='application/pdf')

        @app.route('/html')
        def serve_html():
            """Serve the processed HTML file"""
            return send_file(self.html_path)

        @app.route('/html/content')
        def get_html_content():
            """Return HTML content as JSON for client-side rendering"""
            content = self.html_path.read_text(encoding='utf-8')
            return jsonify({'content': content})

        @app.route('/health')
        def health():
            """Health check endpoint"""
            return jsonify({'status': 'ok'})

        # Correction API routes

        @app.route('/api/entity/<entity_id>')
        def get_entity_content(entity_id):
            """
            GET: Return entity content for editing
            Response: {entity_id, type, page, content, metadata}
            """
            try:
                entity_data = self.correction_manager.get_entity_content(entity_id)
                return jsonify(entity_data)
            except ValueError as e:
                return jsonify({'error': str(e)}), 404
            except FileNotFoundError as e:
                return jsonify({'error': str(e)}), 404
            except Exception as e:
                return jsonify({'error': f'Internal error: {str(e)}'}), 500

        @app.route('/api/correct-with-ai', methods=['POST'])
        def correct_with_ai():
            """
            POST: AI-assisted correction
            Request: {entity_id, user_prompt}
            Response: {corrected_content}
            """
            try:
                data = request.get_json()
                entity_id = data.get('entity_id')
                user_prompt = data.get('user_prompt')

                if not entity_id or not user_prompt:
                    return jsonify({'error': 'entity_id and user_prompt required'}), 400

                # Run async correct_with_ai
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                corrected_content = loop.run_until_complete(
                    self.correction_manager.correct_with_ai(entity_id, user_prompt)
                )
                loop.close()

                return jsonify({'corrected_content': corrected_content})

            except ValueError as e:
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                return jsonify({'error': f'AI correction failed: {str(e)}'}), 500

        @app.route('/api/save-correction', methods=['POST'])
        def save_correction():
            """
            POST: Save correction and regenerate HTML
            Request: {entity_id, corrected_content, correction_type, reason, user_prompt?}
            Response: {success, message}
            """
            try:
                data = request.get_json()
                entity_id = data.get('entity_id')
                corrected_content = data.get('corrected_content')
                correction_type = data.get('correction_type')
                reason = data.get('reason')
                user_prompt = data.get('user_prompt')

                # Validation
                if not entity_id or not corrected_content or not correction_type or not reason:
                    return jsonify({
                        'error': 'entity_id, corrected_content, correction_type, and reason required'
                    }), 400

                if correction_type not in ['manual', 'ai']:
                    return jsonify({'error': 'correction_type must be "manual" or "ai"'}), 400

                # Apply correction
                self.correction_manager.apply_correction(
                    entity_id=entity_id,
                    corrected_content=corrected_content,
                    correction_type=correction_type,
                    reason=reason,
                    user_prompt=user_prompt
                )

                # Invalidate cache so next entity fetch reflects changes
                self.correction_manager.invalidate_cache()

                # Regenerate HTML
                html_path = self.correction_manager.regenerate_html()

                # Update html_path reference
                self.html_path = html_path

                return jsonify({
                    'success': True,
                    'message': f'Correction saved and HTML regenerated',
                    'html_path': '/html/content'
                })

            except ValueError as e:
                return jsonify({'error': str(e)}), 400
            except FileNotFoundError as e:
                return jsonify({'error': str(e)}), 404
            except Exception as e:
                return jsonify({'error': f'Save failed: {str(e)}'}), 500

        @app.route('/api/corrections')
        def list_corrections():
            """
            GET: Return all corrections
            Response: {corrections: {...}}
            """
            try:
                corrections = self.correction_manager.load_corrections()
                return jsonify(corrections)
            except Exception as e:
                return jsonify({'error': f'Failed to load corrections: {str(e)}'}), 500

        @app.route('/api/document-wide-correction', methods=['POST'])
        def document_wide_correction():
            """
            POST: Analyze entire document and propose AI corrections
            Request: {user_prompt: "Fix all dates to YYYY-MM-DD format"}
            Response: {proposed_changes: [{entity_id, original_content, corrected_content, reason}]}
            """
            try:
                data = request.get_json()
                user_prompt = data.get('user_prompt')

                if not user_prompt:
                    return jsonify({'error': 'user_prompt required'}), 400

                # Get proposed changes from AI (run async function synchronously)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    proposed_changes = loop.run_until_complete(
                        self.correction_manager.document_wide_correction(user_prompt)
                    )
                finally:
                    loop.close()

                return jsonify({
                    'success': True,
                    'proposed_changes': proposed_changes,
                    'total_changes': len(proposed_changes)
                })

            except ValueError as e:
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                import traceback
                traceback.print_exc()
                return jsonify({'error': f'Document-wide correction failed: {str(e)}'}), 500

        @app.route('/api/apply-document-wide-corrections', methods=['POST'])
        def apply_document_wide_corrections():
            """
            POST: Apply multiple corrections from document-wide analysis
            Request: {corrections: [...], user_prompt: "..."}
            Response: {success, corrections_applied, html_path}
            """
            try:
                data = request.get_json()
                corrections = data.get('corrections')
                user_prompt = data.get('user_prompt')

                if not corrections or not user_prompt:
                    return jsonify({'error': 'corrections and user_prompt required'}), 400

                # Apply all corrections
                result = self.correction_manager.apply_document_wide_corrections(corrections, user_prompt)

                # Invalidate cache and update html_path reference
                self.correction_manager.invalidate_cache()
                if result['success']:
                    self.html_path = Path(result['html_path'])

                return jsonify(result)

            except Exception as e:
                import traceback
                traceback.print_exc()
                return jsonify({'error': f'Apply corrections failed: {str(e)}'}), 500

        return app

    def launch(self, port=5000, auto_open=True):
        """Launch Flask server and optionally open browser"""
        app = self.create_app()

        if auto_open:
            # Open browser after short delay
            def open_browser():
                time.sleep(1.5)
                try:
                    webbrowser.open(f'http://localhost:{port}')
                except Exception as e:
                    print(f"Could not open browser: {e}")

            threading.Thread(target=open_browser, daemon=True).start()

        print(f"\n{'='*60}")
        print(f"  PDF-HTML Comparison Viewer")
        print(f"{'='*60}")
        print(f"\n  PDF:  {self.pdf_path.name}")
        print(f"  HTML: {self.html_path.name}")
        print(f"\n  URL:  http://localhost:{port}")
        print(f"\n  Press Ctrl+C to stop the server")
        print(f"{'='*60}\n")

        try:
            app.run(host='localhost', port=port, debug=False, threaded=True)
        except OSError as e:
            if "Address already in use" in str(e):
                print(f"\nError: Port {port} is already in use.")
                print(f"Try a different port: python compare_viewer.py {self.pdf_path} {self.output_dir} --port {port + 1}")
            else:
                raise


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Compare original PDF with processed HTML side-by-side",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s input.pdf output/final_document_friendly.html
  %(prog)s input.pdf output/final_document_judge_friendly.html --port 8080
  %(prog)s input.pdf output/final_document_friendly.html --no-browser
        """
    )
    parser.add_argument(
        'pdf_path',
        type=str,
        help='Path to original PDF file'
    )
    parser.add_argument(
        'html_path',
        type=str,
        help='Path to HTML file to view (e.g., final_document_friendly.html or final_document_judge_friendly.html)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=5000,
        help='Port number for web server (default: 5000)'
    )
    parser.add_argument(
        '--no-browser',
        action='store_true',
        help="Don't automatically open browser"
    )

    args = parser.parse_args()

    try:
        viewer = ComparisonViewer(
            Path(args.pdf_path),
            Path(args.html_path)
        )
        viewer.launch(port=args.port, auto_open=not args.no_browser)
    except FileNotFoundError as e:
        print(f"\nError: {e}\n")
        return 1
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        return 0
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
