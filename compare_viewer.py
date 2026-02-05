"""
PDF-HTML Comparison Viewer
Launch web interface to compare original PDF with processed HTML side-by-side

Usage:
    python compare_viewer.py input.pdf output/
    python compare_viewer.py input.pdf output/ --port 8080
    python compare_viewer.py input.pdf output/ --no-browser
"""

import argparse
from pathlib import Path
from flask import Flask, render_template, send_file, jsonify
import yaml
import webbrowser
import threading
import time


class ComparisonViewer:
    """PDF-HTML comparison viewer with synchronized navigation"""

    def __init__(self, pdf_path: Path, output_dir: Path):
        self.pdf_path = pdf_path.resolve()
        self.output_dir = output_dir.resolve()
        self.html_path = output_dir / "final_document_friendly.html"
        self.manifest_path = output_dir / "manifest.yaml"

        # Validate files exist
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {self.pdf_path}")
        if not self.html_path.exists():
            raise FileNotFoundError(
                f"HTML not found: {self.html_path}\n"
                f"Generate it first: python convert_to_friendly.py {output_dir}/final_document.md"
            )

        # Load manifest for page mapping
        self.manifest = self._load_manifest()

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
        app = Flask(__name__)

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
  %(prog)s input.pdf output/
  %(prog)s input.pdf output/ --port 8080
  %(prog)s input.pdf output/ --no-browser
        """
    )
    parser.add_argument(
        'pdf_path',
        type=str,
        help='Path to original PDF file'
    )
    parser.add_argument(
        'output_dir',
        type=str,
        help='Path to output directory containing final_document_friendly.html'
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
            Path(args.output_dir)
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
