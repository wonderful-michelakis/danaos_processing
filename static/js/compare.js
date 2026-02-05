/**
 * PDF-HTML Comparison Viewer
 * Handles PDF rendering, navigation, and synchronized scrolling
 */

class DocumentComparator {
    constructor() {
        this.pdfDoc = null;
        this.currentPage = 1;
        this.totalPages = 0;
        this.scale = 1.0;
        this.syncScrollEnabled = true;
        this.rendering = false;
        this.correctionModal = null;  // NEW: Reference to CorrectionModal

        // DOM elements
        this.canvas = document.getElementById('pdf-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.pdfContent = document.getElementById('pdf-content');
        this.htmlContent = document.getElementById('html-content');
        this.pageNumInput = document.getElementById('page-num');
        this.pageCountSpan = document.getElementById('page-count');
        this.zoomLevelSpan = document.getElementById('zoom-level');
        this.pdfLoading = document.getElementById('pdf-loading');

        // Initialize PDF.js
        pdfjsLib.GlobalWorkerOptions.workerSrc =
            'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

        this.init();
    }

    async init() {
        try {
            await Promise.all([
                this.loadPDF(),
                this.loadHTML()
            ]);
            this.setupEventListeners();
            this.correctionModal = new CorrectionModal(this);  // NEW: Initialize CorrectionModal
            this.setupEntityClickHandlers();  // NEW: Set up entity click handlers
            await this.renderPage(this.currentPage);
        } catch (error) {
            console.error('Initialization error:', error);
            this.showError('Failed to load documents. Please refresh and try again.');
        }
    }

    async loadPDF() {
        try {
            const response = await fetch('/pdf');
            const arrayBuffer = await response.arrayBuffer();

            this.pdfDoc = await pdfjsLib.getDocument({data: arrayBuffer}).promise;
            this.totalPages = this.pdfDoc.numPages;
            this.pageCountSpan.textContent = this.totalPages;
            this.pageNumInput.max = this.totalPages;

            console.log(`PDF loaded: ${this.totalPages} pages`);
        } catch (error) {
            console.error('PDF loading error:', error);
            throw new Error('Failed to load PDF');
        }
    }

    async loadHTML() {
        try {
            const response = await fetch('/html/content');
            const data = await response.json();

            // Parse HTML content
            const parser = new DOMParser();
            const doc = parser.parseFromString(data.content, 'text/html');

            // Extract and inject styles first
            const styles = doc.querySelectorAll('style');
            styles.forEach(style => {
                const styleElement = document.createElement('style');
                styleElement.textContent = style.textContent;
                document.head.appendChild(styleElement);
            });

            // Extract the body content (skip document header/footer if present)
            const bodyContent = doc.querySelector('.document-content') || doc.body;

            // Inject HTML content
            this.htmlContent.innerHTML = bodyContent.innerHTML;

            console.log('HTML content loaded');
        } catch (error) {
            console.error('HTML loading error:', error);
            throw new Error('Failed to load HTML');
        }
    }

    async renderPage(pageNum) {
        if (this.rendering) return;

        // Validate page number
        if (pageNum < 1 || pageNum > this.totalPages) {
            console.warn(`Invalid page number: ${pageNum}`);
            return;
        }

        this.rendering = true;
        this.currentPage = pageNum;

        try {
            // Hide loading message, show canvas
            if (this.pdfLoading) {
                this.pdfLoading.style.display = 'none';
            }
            this.canvas.style.display = 'block';

            // Get page
            const page = await this.pdfDoc.getPage(pageNum);

            // Calculate scaled viewport
            const viewport = page.getViewport({scale: this.scale});

            // Set canvas dimensions
            this.canvas.height = viewport.height;
            this.canvas.width = viewport.width;

            // Render PDF page
            const renderContext = {
                canvasContext: this.ctx,
                viewport: viewport
            };

            await page.render(renderContext).promise;

            // Update UI
            this.pageNumInput.value = pageNum;
            this.updateNavigationButtons();

            // Sync HTML scroll if enabled
            if (this.syncScrollEnabled) {
                this.scrollHTMLToPage(pageNum);
            }

            console.log(`Rendered page ${pageNum} at scale ${this.scale}`);
        } catch (error) {
            console.error('Page rendering error:', error);
            this.showError(`Failed to render page ${pageNum}`);
        } finally {
            this.rendering = false;
        }
    }

    scrollHTMLToPage(pageNum) {
        // Find the page section
        const pageSection = this.htmlContent.querySelector(`.page-section[data-page="${pageNum}"]`);

        if (pageSection) {
            // Remove active class from all sections
            this.htmlContent.querySelectorAll('.page-section.active').forEach(section => {
                section.classList.remove('active');
            });

            // Add active class to current section
            pageSection.classList.add('active');

            // Smooth scroll to section
            pageSection.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        } else {
            console.warn(`Page section not found: ${pageNum}`);
        }
    }

    updateNavigationButtons() {
        const prevBtn = document.getElementById('prev-page');
        const nextBtn = document.getElementById('next-page');

        prevBtn.disabled = (this.currentPage <= 1);
        nextBtn.disabled = (this.currentPage >= this.totalPages);
    }

    changePage(delta) {
        const newPage = this.currentPage + delta;
        this.renderPage(newPage);
    }

    goToPage(pageNum) {
        const num = parseInt(pageNum, 10);
        if (!isNaN(num) && num >= 1 && num <= this.totalPages) {
            this.renderPage(num);
        } else {
            // Reset to current page if invalid
            this.pageNumInput.value = this.currentPage;
        }
    }

    changeZoom(delta) {
        const newScale = this.scale + delta;

        // Limit zoom range: 50% to 300%
        if (newScale >= 0.5 && newScale <= 3.0) {
            this.scale = newScale;
            this.zoomLevelSpan.textContent = `${Math.round(this.scale * 100)}%`;
            this.renderPage(this.currentPage);
        }
    }

    toggleSyncScroll() {
        this.syncScrollEnabled = !this.syncScrollEnabled;

        if (this.syncScrollEnabled) {
            // Re-sync when enabled
            this.scrollHTMLToPage(this.currentPage);
        }
    }

    setupEventListeners() {
        // Previous/Next buttons
        document.getElementById('prev-page').addEventListener('click', () => {
            this.changePage(-1);
        });

        document.getElementById('next-page').addEventListener('click', () => {
            this.changePage(1);
        });

        // Page number input
        this.pageNumInput.addEventListener('change', (e) => {
            this.goToPage(e.target.value);
        });

        this.pageNumInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.goToPage(e.target.value);
            }
        });

        // Zoom controls
        document.getElementById('zoom-in').addEventListener('click', () => {
            this.changeZoom(0.1);
        });

        document.getElementById('zoom-out').addEventListener('click', () => {
            this.changeZoom(-0.1);
        });

        // Sync scroll toggle
        const syncCheckbox = document.getElementById('sync-scroll');
        syncCheckbox.addEventListener('change', () => {
            this.syncScrollEnabled = syncCheckbox.checked;
            if (this.syncScrollEnabled) {
                this.scrollHTMLToPage(this.currentPage);
            }
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Don't interfere if user is typing in input field
            if (e.target === this.pageNumInput) return;

            switch(e.key) {
                case 'ArrowLeft':
                case 'PageUp':
                    e.preventDefault();
                    this.changePage(-1);
                    break;
                case 'ArrowRight':
                case 'PageDown':
                    e.preventDefault();
                    this.changePage(1);
                    break;
                case 'Home':
                    e.preventDefault();
                    this.renderPage(1);
                    break;
                case 'End':
                    e.preventDefault();
                    this.renderPage(this.totalPages);
                    break;
                case '+':
                case '=':
                    e.preventDefault();
                    this.changeZoom(0.1);
                    break;
                case '-':
                case '_':
                    e.preventDefault();
                    this.changeZoom(-0.1);
                    break;
            }
        });

        // Panel resizing
        this.setupPanelResizing();
    }

    setupPanelResizing() {
        const divider = document.querySelector('.divider');
        const pdfPanel = document.querySelector('.pdf-panel');
        const htmlPanel = document.querySelector('.html-panel');

        let isResizing = false;

        divider.addEventListener('mousedown', (e) => {
            isResizing = true;
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
        });

        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;

            const container = document.querySelector('.comparison-container');
            const containerRect = container.getBoundingClientRect();
            const offsetX = e.clientX - containerRect.left;
            const percentage = (offsetX / containerRect.width) * 100;

            // Limit to 20%-80% range
            if (percentage >= 20 && percentage <= 80) {
                pdfPanel.style.flex = `0 0 ${percentage}%`;
                htmlPanel.style.flex = `0 0 ${100 - percentage}%`;
            }
        });

        document.addEventListener('mouseup', () => {
            if (isResizing) {
                isResizing = false;
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
            }
        });
    }

    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        errorDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #e74c3c;
            color: white;
            padding: 15px 20px;
            border-radius: 4px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            z-index: 1000;
        `;
        document.body.appendChild(errorDiv);

        setTimeout(() => {
            errorDiv.remove();
        }, 5000);
    }

    setupEntityClickHandlers() {
        // Add click handlers to all entity badges
        document.addEventListener('click', (e) => {
            // Check if clicked element is entity badge or within entity
            if (e.target.classList.contains('entity-badge')) {
                const entityId = e.target.textContent.trim();
                this.correctionModal.open(entityId);
            }
        });

        // Add hover effect to entity badges
        const observer = new MutationObserver(() => {
            document.querySelectorAll('.entity-badge').forEach(badge => {
                badge.style.cursor = 'pointer';
                badge.title = 'Click to edit this entity';
            });
        });
        observer.observe(this.htmlContent, {childList: true, subtree: true});
    }

    async reloadHTMLContent() {
        // Reload HTML content after correction
        await this.loadHTML();
        // Re-render current page
        await this.renderPage(this.currentPage);
    }

    highlightCorrectedEntity(entityId) {
        // Find entity and add 'corrected' class
        const entitySection = document.querySelector(`section[data-entity="${entityId}"]`);
        if (entitySection) {
            entitySection.classList.add('corrected');

            // Scroll to entity
            entitySection.scrollIntoView({behavior: 'smooth', block: 'center'});

            // Remove highlight after 3 seconds
            setTimeout(() => {
                entitySection.classList.remove('corrected');
            }, 3000);
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.comparator = new DocumentComparator();
});
