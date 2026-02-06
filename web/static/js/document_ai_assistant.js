/**
 * Document-Wide AI Assistant for Corrections
 * Allows users to apply AI corrections across the entire document
 */

class DocumentAIAssistant {
    constructor(comparator) {
        this.comparator = comparator;
        this.proposedChanges = [];
        this.userPrompt = '';

        // DOM elements (will be created dynamically)
        this.modal = null;
        this.floatingButton = null;

        this.init();
    }

    init() {
        this.createFloatingButton();
        this.createModal();
        this.setupEventListeners();
    }

    createFloatingButton() {
        // Create floating AI Assistant button
        const button = document.createElement('button');
        button.id = 'ai-assistant-fab';
        button.className = 'floating-action-button';
        button.innerHTML = `
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                <path d="M8 9h8M8 13h6"></path>
            </svg>
            <span>AI Assistant</span>
        `;
        button.title = 'Document-wide AI corrections';

        document.body.appendChild(button);
        this.floatingButton = button;
    }

    createModal() {
        const modalHTML = `
<div id="document-ai-modal" class="modal" style="display: none;">
    <div class="modal-overlay"></div>
    <div class="modal-content large-modal">
        <div class="modal-header">
            <h2>🤖 Document-Wide AI Assistant</h2>
            <button class="close-btn" id="ai-modal-close">&times;</button>
        </div>

        <div class="modal-body">
            <!-- Instructions -->
            <div class="ai-instructions">
                <p><strong>How it works:</strong> Describe what you want to fix across the entire document.
                The AI will analyze all entities and propose corrections.</p>
                <p><strong>Examples:</strong></p>
                <ul>
                    <li>"Fix all date formats to YYYY-MM-DD"</li>
                    <li>"Correct all instances of 'Master' to 'Captain'"</li>
                    <li>"Ensure all units use metric system"</li>
                    <li>"Fix spelling errors throughout the document"</li>
                </ul>
            </div>

            <!-- Prompt Input -->
            <div class="prompt-section">
                <label for="ai-document-prompt">What would you like to fix?</label>
                <textarea
                    id="ai-document-prompt"
                    class="prompt-textarea"
                    rows="4"
                    placeholder="Describe the corrections you want to apply..."
                ></textarea>
                <button id="analyze-document-btn" class="btn btn-primary">
                    <span class="btn-text">Analyze Document</span>
                    <span class="btn-loader" style="display:none;">
                        <span class="spinner"></span> Analyzing...
                    </span>
                </button>
            </div>

            <!-- Proposed Changes Preview -->
            <div id="changes-preview" class="changes-preview" style="display: none;">
                <h3>Proposed Changes (<span id="changes-count">0</span>)</h3>
                <div class="changes-list" id="changes-list">
                    <!-- Will be populated dynamically -->
                </div>
            </div>
        </div>

        <div class="modal-footer">
            <button id="ai-cancel-btn" class="btn btn-secondary">Cancel</button>
            <button id="apply-all-btn" class="btn btn-success" style="display:none;">
                Apply All Corrections
            </button>
        </div>

        <!-- Loading Overlay -->
        <div id="ai-modal-loading" class="loading-overlay" style="display: none;">
            <div class="spinner"></div>
            <p id="loading-message">Processing...</p>
        </div>
    </div>
</div>
        `;

        // Add modal to DOM
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        this.modal = document.getElementById('document-ai-modal');
    }

    setupEventListeners() {
        // Floating button click
        this.floatingButton.addEventListener('click', () => this.open());

        // Close buttons
        document.getElementById('ai-modal-close').addEventListener('click', () => this.close());
        document.getElementById('ai-cancel-btn').addEventListener('click', () => this.close());

        // Overlay click to close
        this.modal.querySelector('.modal-overlay').addEventListener('click', () => this.close());

        // Analyze button
        document.getElementById('analyze-document-btn').addEventListener('click', () => this.analyzeDocument());

        // Apply all button
        document.getElementById('apply-all-btn').addEventListener('click', () => this.applyAllCorrections());

        // ESC key to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.modal.style.display === 'block') {
                this.close();
            }
        });
    }

    open() {
        this.modal.style.display = 'block';
        document.getElementById('ai-document-prompt').focus();
    }

    close() {
        this.modal.style.display = 'none';
        this.resetModal();
    }

    resetModal() {
        document.getElementById('ai-document-prompt').value = '';
        document.getElementById('changes-preview').style.display = 'none';
        document.getElementById('apply-all-btn').style.display = 'none';
        this.proposedChanges = [];
    }

    async analyzeDocument() {
        const prompt = document.getElementById('ai-document-prompt').value.trim();

        if (!prompt) {
            this.showError('Please describe what you want to fix');
            return;
        }

        this.userPrompt = prompt;
        this.showLoading('Analyzing document with AI...');

        // Show analyzing state on button
        const analyzeBtn = document.getElementById('analyze-document-btn');
        analyzeBtn.querySelector('.btn-text').style.display = 'none';
        analyzeBtn.querySelector('.btn-loader').style.display = 'inline-flex';
        analyzeBtn.disabled = true;

        try {
            const response = await fetch('/api/document-wide-correction', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({user_prompt: prompt})
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Analysis failed');
            }

            this.proposedChanges = data.proposed_changes;
            this.displayProposedChanges(data.proposed_changes);

        } catch (error) {
            this.showError(`Analysis failed: ${error.message}`);
        } finally {
            this.hideLoading();
            analyzeBtn.querySelector('.btn-text').style.display = 'inline';
            analyzeBtn.querySelector('.btn-loader').style.display = 'none';
            analyzeBtn.disabled = false;
        }
    }

    displayProposedChanges(changes) {
        if (changes.length === 0) {
            document.getElementById('changes-list').innerHTML = `
                <div class="no-changes">
                    <p>✓ No corrections needed! The document looks good.</p>
                </div>
            `;
            document.getElementById('changes-preview').style.display = 'block';
            return;
        }

        const changesHTML = changes.map((change, index) => `
            <div class="change-item" data-index="${index}">
                <div class="change-header">
                    <h4>Entity ${change.entity_id}</h4>
                    <span class="change-reason">${change.reason}</span>
                </div>
                <div class="change-content">
                    <div class="change-column">
                        <label>Original:</label>
                        <pre class="change-text original">${this.escapeHtml(change.original_content.substring(0, 300))}${change.original_content.length > 300 ? '...' : ''}</pre>
                    </div>
                    <div class="change-arrow">→</div>
                    <div class="change-column">
                        <label>Corrected:</label>
                        <pre class="change-text corrected">${this.escapeHtml(change.corrected_content.substring(0, 300))}${change.corrected_content.length > 300 ? '...' : ''}</pre>
                    </div>
                </div>
                <div class="change-actions">
                    <button class="btn-small btn-remove" onclick="documentAI.removeChange(${index})">
                        Remove
                    </button>
                </div>
            </div>
        `).join('');

        document.getElementById('changes-count').textContent = changes.length;
        document.getElementById('changes-list').innerHTML = changesHTML;
        document.getElementById('changes-preview').style.display = 'block';
        document.getElementById('apply-all-btn').style.display = 'inline-block';
    }

    removeChange(index) {
        this.proposedChanges.splice(index, 1);
        this.displayProposedChanges(this.proposedChanges);
    }

    async applyAllCorrections() {
        if (this.proposedChanges.length === 0) {
            this.showError('No changes to apply');
            return;
        }

        const confirmed = confirm(
            `Apply ${this.proposedChanges.length} correction(s) to the document?\n\n` +
            `This will update the entities and regenerate the HTML.`
        );

        if (!confirmed) return;

        this.showLoading(`Applying ${this.proposedChanges.length} corrections...`);

        try {
            const response = await fetch('/api/apply-document-wide-corrections', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    corrections: this.proposedChanges,
                    user_prompt: this.userPrompt
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Apply failed');
            }

            // Success!
            this.hideLoading();
            this.close();

            // Show success message
            this.showSuccessMessage(
                `✓ Applied ${data.corrections_applied.length} corrections successfully!`,
                data.corrections_applied
            );

            // Reload HTML content
            await this.comparator.reloadHTMLContent();

            // Highlight corrected entities
            data.corrections_applied.forEach(entityId => {
                setTimeout(() => {
                    this.comparator.highlightCorrectedEntity(entityId);
                }, 500);
            });

        } catch (error) {
            this.hideLoading();
            this.showError(`Apply failed: ${error.message}`);
        }
    }

    showSuccessMessage(message, entityIds) {
        const successDiv = document.createElement('div');
        successDiv.className = 'success-toast';
        successDiv.innerHTML = `
            <div class="success-content">
                <h3>${message}</h3>
                <p>Corrected entities: ${entityIds.join(', ')}</p>
            </div>
        `;

        document.body.appendChild(successDiv);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            successDiv.style.opacity = '0';
            setTimeout(() => successDiv.remove(), 300);
        }, 5000);
    }

    showLoading(message) {
        document.getElementById('loading-message').textContent = message;
        document.getElementById('ai-modal-loading').style.display = 'flex';
    }

    hideLoading() {
        document.getElementById('ai-modal-loading').style.display = 'none';
    }

    showError(message) {
        alert(`Error: ${message}`);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Global instance (will be initialized by compare.js)
let documentAI = null;
